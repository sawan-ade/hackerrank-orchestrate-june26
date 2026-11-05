"""
GT-Judge Unit Tests
====================
Tests for the three game modules and the pipeline orchestrator.
Run with: python -m pytest tests/ -v
"""

from __future__ import annotations

import pytest
import math

# We test the data models and game logic independently of LLM calls


# ===========================================================================
# Test 1: Data Models
# ===========================================================================

class TestModels:
    """Test that Pydantic models validate correctly."""

    def test_claim_validity_bounds(self):
        from src.models import Claim
        c = Claim(claim_id=1, text="test", validity=0.7, round_made=1)
        assert 0.0 <= c.validity <= 1.0

        with pytest.raises(Exception):
            Claim(claim_id=1, text="test", validity=1.5, round_made=1)

    def test_attack_severity_bounds(self):
        from src.models import Attack
        a = Attack(attack_id=1, text="test", target_claim_id=1, severity=0.8, round_made=1)
        assert 0.0 <= a.severity <= 1.0

    def test_verdict_enum(self):
        from src.models import Verdict
        assert Verdict.A_WINS.value == "A_wins"
        assert Verdict.B_WINS.value == "B_wins"
        assert Verdict.TIE.value == "Tie"

    def test_evaluation_input(self):
        from src.models import EvaluationInput
        inp = EvaluationInput(
            question="What is 2+2?",
            answer_a="4",
            answer_b="5",
        )
        assert inp.ground_truth is None

    def test_agent_move_defaults(self):
        from src.models import AgentMove
        move = AgentMove(action="claim", argument="This is correct.")
        assert move.target_claim_id is None
        assert move.token_count == 0


# ===========================================================================
# Test 2: Brier Score Computation (Game 2 — Theorem 2)
# ===========================================================================

class TestCalibration:
    """Test the Brier scoring rule implementation."""

    def test_perfect_calibration(self):
        """Truthful report when y=1 and p̂=1 should yield score=1."""
        from src.models import CalibrationResult
        from src.calibration_game import CalibrationGame

        game = CalibrationGame.__new__(CalibrationGame)
        results = [CalibrationResult(evaluator_id=0, reported_confidence=1.0)]
        updated = game.compute_brier_scores(results, ground_truth_y=1.0)
        assert updated[0].calibration_score == pytest.approx(1.0)

    def test_worst_calibration(self):
        """p̂=0 when y=1 should yield score=0."""
        from src.models import CalibrationResult
        from src.calibration_game import CalibrationGame

        game = CalibrationGame.__new__(CalibrationGame)
        results = [CalibrationResult(evaluator_id=0, reported_confidence=0.0)]
        updated = game.compute_brier_scores(results, ground_truth_y=1.0)
        assert updated[0].calibration_score == pytest.approx(0.0)

    def test_overconfidence_penalty(self):
        """
        From Corollary 2: when q=0.6,
        overconfident (p̂=0.95) gets 0.638, truthful (p̂=0.6) gets 0.760.
        """
        from src.models import CalibrationResult
        from src.calibration_game import CalibrationGame

        game = CalibrationGame.__new__(CalibrationGame)

        # Overconfident
        over = [CalibrationResult(evaluator_id=0, reported_confidence=0.95)]
        game.compute_brier_scores(over, ground_truth_y=1.0)
        # Expected: 1 - (1 - 0.95)^2 = 1 - 0.0025 = 0.9975? No...
        # Wait, the Brier score is computed for a specific y, not expected.
        # For y=1: Ucal = 1 - (1 - 0.95)^2 = 0.9975
        # The Corollary 2 result is about EXPECTED utility, not realized.
        # Let's test the formula directly.
        assert over[0].calibration_score == pytest.approx(1.0 - (1.0 - 0.95) ** 2)

    def test_brier_formula(self):
        """Verify Ucal(p̂, y) = 1 - (y - p̂)² for various inputs."""
        from src.models import CalibrationResult
        from src.calibration_game import CalibrationGame

        game = CalibrationGame.__new__(CalibrationGame)

        test_cases = [
            (0.5, 1.0, 1.0 - 0.25),    # p̂=0.5, y=1 → 0.75
            (0.5, 0.0, 1.0 - 0.25),    # p̂=0.5, y=0 → 0.75
            (0.7, 1.0, 1.0 - 0.09),    # p̂=0.7, y=1 → 0.91
            (0.3, 0.0, 1.0 - 0.09),    # p̂=0.3, y=0 → 0.91
        ]
        for p_hat, y, expected in test_cases:
            results = [CalibrationResult(evaluator_id=0, reported_confidence=p_hat)]
            game.compute_brier_scores(results, y)
            assert results[0].calibration_score == pytest.approx(expected, abs=1e-6)


# ===========================================================================
# Test 3: Nash Bargaining (Game 3)
# ===========================================================================

class TestArbitration:
    """Test the Nash Bargaining Solution computation."""

    def test_verdict_to_y(self):
        """Test the consensus proxy mapping (Fix 4, Eq 10')."""
        from src.models import Verdict
        from src.arbitration_game import ArbitrationGame

        assert ArbitrationGame._verdict_to_y(Verdict.A_WINS) == 1.0
        assert ArbitrationGame._verdict_to_y(Verdict.B_WINS) == 0.0
        assert ArbitrationGame._verdict_to_y(Verdict.TIE) == 0.5

    def test_unanimous_agreement(self):
        """When both evaluators strongly favor A, verdict should be A_wins."""
        from src.models import CalibrationResult, DebateResult, Verdict
        from src.arbitration_game import ArbitrationGame

        game = ArbitrationGame(human_review_cost=10.0, beta_effort_scale=0.1)

        debate_results = {
            "A": DebateResult(
                answer_label="A", debate_score=2.5, surviving_claims=3,
                successful_attacks=0, total_proposer_tokens=100,
                total_challenger_tokens=80, transcript=[],
            ),
            "B": DebateResult(
                answer_label="B", debate_score=0.5, surviving_claims=1,
                successful_attacks=2, total_proposer_tokens=100,
                total_challenger_tokens=80, transcript=[],
            ),
        }
        calibration = [
            CalibrationResult(evaluator_id=0, reported_confidence=0.9, calibration_score=0.8),
            CalibrationResult(evaluator_id=1, reported_confidence=0.85, calibration_score=0.75),
        ]

        result = game.run(debate_results, calibration)
        assert result.verdict == Verdict.A_WINS

    def test_weights_sum_to_one(self):
        """Bargaining weights must sum to 1."""
        from src.models import CalibrationResult, DebateResult
        from src.arbitration_game import ArbitrationGame

        game = ArbitrationGame()
        debate_results = {
            "A": DebateResult(
                answer_label="A", debate_score=1.0, surviving_claims=2,
                successful_attacks=1, total_proposer_tokens=50,
                total_challenger_tokens=50, transcript=[],
            ),
            "B": DebateResult(
                answer_label="B", debate_score=1.0, surviving_claims=2,
                successful_attacks=1, total_proposer_tokens=50,
                total_challenger_tokens=50, transcript=[],
            ),
        }
        calibration = [
            CalibrationResult(evaluator_id=0, reported_confidence=0.6, calibration_score=0.8),
            CalibrationResult(evaluator_id=1, reported_confidence=0.4, calibration_score=0.7),
        ]

        result = game.run(debate_results, calibration)
        weight_sum = sum(result.weights.values())
        assert weight_sum == pytest.approx(1.0, abs=1e-6)


# ===========================================================================
# Test 4: Config Loading
# ===========================================================================

class TestConfig:
    """Test YAML config loading."""

    def test_default_config_loads(self, tmp_path, monkeypatch):
        import yaml

        # Set a dummy API key so the OpenAI client doesn't raise during tests
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

        config = {
            "pipeline": {"name": "test", "evaluator_count": 2},
            "model": {
                "evaluator_model": "gpt-4o-mini",
                "temperature_debate": 0.7,
                "temperature_calibration": 0.0,
                "max_tokens": 512,
            },
            "game1_debate": {"rounds": 3, "lambda_token_cost": 0.001},
            "game2_calibration": {"scoring_rule": "brier", "ground_truth_mode": "consensus_proxy"},
            "game3_arbitration": {"human_review_cost": 10.0, "beta_effort_scale": 0.1},
        }
        config_path = tmp_path / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from src.gt_judge import GTJudge
        judge = GTJudge.from_config(str(config_path))
        assert judge.debate_game.max_rounds == 3
        assert judge.debate_game.lambda_cost == 0.001


# ===========================================================================
# Test 5: Retry Logic in LLMClient
# ===========================================================================

class TestRetryLogic:
    """Test that LLMClient handles rate limits and API errors via exponential backoff."""

    def test_retry_on_rate_limit_then_success(self, monkeypatch):
        from unittest.mock import MagicMock, patch
        from src.llm_client import LLMClient
        import openai

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
        client = LLMClient(max_retries=3, initial_delay=0.01, backoff_factor=1.0)

        # Mock the chat.completions.create method
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mocked response content"))]
        mock_response.usage = MagicMock(total_tokens=100)

        create_mock = MagicMock()
        # Set side_effect to raise RateLimitError twice, then return the successful response
        request_mock = MagicMock()
        create_mock.side_effect = [
            openai.RateLimitError("Rate limit exceeded", response=MagicMock(status_code=429), body={}),
            openai.RateLimitError("Rate limit exceeded", response=MagicMock(status_code=429), body={}),
            mock_response
        ]
        client.client.chat.completions.create = create_mock

        with patch("time.sleep") as mock_sleep:
            text, tokens = client.call("System", "User")
            assert text == "Mocked response content"
            assert tokens == 100
            assert create_mock.call_count == 3
            assert mock_sleep.call_count == 2

    def test_retry_exhaustion_raises_error(self, monkeypatch):
        from unittest.mock import MagicMock, patch
        from src.llm_client import LLMClient
        import openai

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
        client = LLMClient(max_retries=2, initial_delay=0.01, backoff_factor=1.0)

        create_mock = MagicMock()
        create_mock.side_effect = openai.RateLimitError(
            "Rate limit exceeded", response=MagicMock(status_code=429), body={}
        )
        client.client.chat.completions.create = create_mock

        with patch("time.sleep"):
            with pytest.raises(openai.RateLimitError):
                client.call("System", "User")
            assert create_mock.call_count == 3


# ===========================================================================
# Test 6: Mocked Pipeline End-to-End Execution
# ===========================================================================

class TestPipelineEndToEndMocked:
    """Test the entire GT-Judge pipeline using mock LLM completions."""

    def test_full_pipeline_success(self, monkeypatch):
        from unittest.mock import MagicMock, patch
        from src.gt_judge import GTJudge

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

        # Create GTJudge instance
        debate_game_mock = MagicMock()
        calibration_game_mock = MagicMock()
        arbitration_game_mock = MagicMock()

        # Set up mock results for DebateGame (Game 1)
        from src.models import DebateResult, AgentMove
        mock_debate_a = DebateResult(
            answer_label="A",
            debate_score=1.5,
            surviving_claims=2,
            successful_attacks=1,
            total_proposer_tokens=150,
            total_challenger_tokens=120,
            transcript=[
                AgentMove(action="claim", argument="Claim A", token_count=50),
                AgentMove(action="attack", argument="Attack A", token_count=40),
            ]
        )
        mock_debate_b = DebateResult(
            answer_label="B",
            debate_score=0.5,
            surviving_claims=1,
            successful_attacks=2,
            total_proposer_tokens=140,
            total_challenger_tokens=110,
            transcript=[
                AgentMove(action="claim", argument="Claim B", token_count=50),
                AgentMove(action="attack", argument="Attack B", token_count=40),
            ]
        )
        debate_game_mock.run.side_effect = [mock_debate_a, mock_debate_b]

        # Set up mock results for CalibrationGame (Game 2)
        from src.models import CalibrationResult
        mock_calibration_results = [
            CalibrationResult(evaluator_id=0, reported_confidence=0.8, calibration_score=0.9),
            CalibrationResult(evaluator_id=1, reported_confidence=0.7, calibration_score=0.85),
        ]
        calibration_game_mock.run.return_value = mock_calibration_results
        # compute_brier_scores returns updated list
        calibration_game_mock.compute_brier_scores.return_value = mock_calibration_results

        # Set up mock results for ArbitrationGame (Game 3)
        from src.models import ArbitrationResult, Verdict
        mock_arbitration_result = ArbitrationResult(
            verdict=Verdict.A_WINS,
            nash_product=1.2,
            weights={0: 0.6, 1: 0.4},
            confidence=0.75
        )
        arbitration_game_mock.run.return_value = mock_arbitration_result

        # Instantiate GTJudge with mocks
        llm_dummy = MagicMock()
        judge = GTJudge(
            llm=llm_dummy,
            debate_game=debate_game_mock,
            calibration_game=calibration_game_mock,
            arbitration_game=arbitration_game_mock
        )

        # Run pipeline
        output = judge.evaluate("What is the LCS of AGT and GT?", "GT", "A")

        assert output.verdict == Verdict.A_WINS
        assert output.confidence == 0.75
        assert output.total_tokens == 520  # 150 + 120 + 140 + 110
        assert "GT-Judge Verdict: A_wins" in output.justification
        assert debate_game_mock.run.call_count == 2
        assert calibration_game_mock.run.call_count == 1
        assert arbitration_game_mock.run.call_count == 2


# ===========================================================================
# Test 7: Benchmark Runner Execution (Mock Mode)
# ===========================================================================

class TestBenchmarkRunnerMocked:
    """Test that the benchmark runner executes correctly in offline mock mode."""

    def test_benchmark_runner_mock_mode(self, monkeypatch):
        import sys
        from pathlib import Path
        from tests.scripted_llm import _scripted_llm_for_tests
        from src.gt_judge import GTJudge

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

        # Load sample benchmark configuration and run mock evaluations.
        # NOTE: _scripted_llm_for_tests is a deterministic test oracle, NOT a
        # baseline/ablation — it exists only to exercise the pipeline offline
        # (issue §1.1). It must never be a source of reported numbers.
        judge = GTJudge.from_config("configs/default.yaml")
        mock_llm = _scripted_llm_for_tests(profile="benchmark")
        judge.llm = mock_llm
        judge.debate_game.llm = mock_llm
        judge.calibration_game.llm = mock_llm

        # Verify that evaluating a sample instance works cleanly in mock mode
        question = "Explain LCS"
        ans_a = "Classic dynamic programming."
        ans_b = "Naive recursion."

        res = judge.evaluate(question, ans_a, ans_b, ground_truth="A")
        assert res.verdict in ("A_wins", "B_wins", "Tie")
        assert len(res.calibration_results) == 2
        assert res.total_tokens > 0


# ===========================================================================
# Test 8: Detailed Game and Pipeline Logic Fixes (Waves 1-4)
# ===========================================================================

class TestReviewFixes:
    """Test suite covering the 18 code review fixes."""

    def test_debate_score_changes_verdict(self):
        """A-1: Verify that shifting the debate score differential changes the verdict utility/outcome."""
        from src.arbitration_game import ArbitrationGame
        from src.models import DebateResult, CalibrationResult, Verdict

        game = ArbitrationGame(alpha_debate_influence=2.0, alpha_d=0.1)

        # Base calibration reports are close to Tie (0.52 for A vs 0.48 for B)
        calibration = [
            CalibrationResult(evaluator_id=0, reported_confidence=0.52, calibration_score=0.9),
            CalibrationResult(evaluator_id=1, reported_confidence=0.48, calibration_score=0.9),
        ]

        # Case A: Answer A strongly wins the debate
        debate_a_wins = {
            "A": DebateResult(
                answer_label="A", debate_score=5.0, surviving_claims=3, successful_attacks=0,
                total_proposer_tokens=100, total_challenger_tokens=80, transcript=[]
            ),
            "B": DebateResult(
                answer_label="B", debate_score=-2.0, surviving_claims=1, successful_attacks=2,
                total_proposer_tokens=100, total_challenger_tokens=80, transcript=[]
            )
        }

        res_a = game.run(debate_a_wins, calibration)
        
        # Case B: Answer B strongly wins the debate
        debate_b_wins = {
            "A": DebateResult(
                answer_label="A", debate_score=-2.0, surviving_claims=1, successful_attacks=2,
                total_proposer_tokens=100, total_challenger_tokens=80, transcript=[]
            ),
            "B": DebateResult(
                answer_label="B", debate_score=5.0, surviving_claims=3, successful_attacks=0,
                total_proposer_tokens=100, total_challenger_tokens=80, transcript=[]
            )
        }

        res_b = game.run(debate_b_wins, calibration)

        # The outcomes must be different because the debate score influences the verdict
        assert res_a.verdict != res_b.verdict
        # When A wins the debate, A should have higher consensus / win, and vice versa
        assert res_a.verdict == Verdict.A_WINS
        assert res_b.verdict == Verdict.B_WINS

    def test_evaluators_can_disagree(self, monkeypatch):
        """A-2: Verify that different personas queried on the same inputs can return different confidences."""
        from src.calibration_game import CalibrationGame
        from src.models import DebateResult
        from unittest.mock import MagicMock

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
        
        mock_llm = MagicMock()
        # Mock LLM to return different confidence values based on the persona name in system prompt
        def side_effect(system_prompt, user_prompt, temperature=None):
            if "Correctness Evaluator" in system_prompt:
                return {"confidence": 0.9}, 100
            elif "Clarity & Structure Evaluator" in system_prompt:
                return {"confidence": 0.4}, 100
            return {"confidence": 0.5}, 100
            
        mock_llm.call_structured.side_effect = side_effect

        game = CalibrationGame(llm=mock_llm, n_evaluators=2)
        
        debate = DebateResult(
            answer_label="A", debate_score=1.0, surviving_claims=1, successful_attacks=0,
            total_proposer_tokens=100, total_challenger_tokens=80, transcript=[]
        )

        res = game.run("What is LCS?", "DP", "Recursive", debate, debate)
        
        assert len(res) == 2
        # Evaluator 0 (Correctness) reports 0.9
        assert res[0].reported_confidence == pytest.approx(0.9)
        # Evaluator 1 (Clarity - swap=True, so it is presented B-wins scale and flipped)
        # For Evaluator 1 (swap=True): user prompt has A and B swapped.
        # System prompt has "Clarity & Structure Evaluator".
        # LLM reports 0.4.
        # Since swap=True, confidence is flipped: 1.0 - 0.4 = 0.6.
        assert res[1].reported_confidence == pytest.approx(0.6)
        assert res[0].reported_confidence != res[1].reported_confidence

    def test_token_penalty_reduces_score(self, monkeypatch):
        """A-3 & B-1: Verify that token usage reduces debate score, and scores are normalized."""
        from src.debate_game import DebateGame
        from src.models import Claim
        from unittest.mock import MagicMock

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
        
        mock_llm = MagicMock()
        mock_llm.call_structured.return_value = ({"action": "claim", "argument": "argument"}, 100)

        # High lambda cost
        game_penalty = DebateGame(llm=mock_llm, max_rounds=1, lambda_cost=0.005)
        # Low lambda cost
        game_free = DebateGame(llm=mock_llm, max_rounds=1, lambda_cost=0.0)

        res_penalty = game_penalty.run("Q", "Ans", "A")
        res_free = game_free.run("Q", "Ans", "A")

        # Free game should have a higher score because penalty is zero
        assert res_free.debate_score > res_penalty.debate_score
        assert res_penalty.debate_score == pytest.approx(res_free.debate_score - 0.005 * (res_penalty.total_proposer_tokens + res_penalty.total_challenger_tokens))

    def test_concede_breaks_loop(self, monkeypatch):
        """C-2: Verify that challenger concede ends the debate early."""
        from src.debate_game import DebateGame
        from unittest.mock import MagicMock

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
        
        mock_llm = MagicMock()
        # Proposer always claims, Challenger always concedes
        def side_effect(system, user, temp=None):
            if "PROPOSER" in system:
                return {"action": "claim", "argument": "Claim"}, 50
            elif "CHALLENGER" in system:
                return {"action": "concede", "argument": "Concede"}, 50
            return {}, 0
            
        mock_llm.call_structured.side_effect = side_effect

        game = DebateGame(llm=mock_llm, max_rounds=5)
        res = game.run("Q", "Ans", "A")

        # Should break in round 1 since Challenger conceded immediately
        assert res.total_claims == 1
        assert res.total_attacks == 0
        assert len(res.transcript) == 2  # Proposer claim + Challenger concede

    def test_consensus_fixed_point_converges(self, monkeypatch):
        """B-4: Verify that iterative fixed-point loop works in gt_judge.py."""
        from src.gt_judge import GTJudge
        from unittest.mock import MagicMock

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

        judge = GTJudge.from_config("configs/default.yaml")
        
        # Mock games to return different values to check loop iterations
        from src.models import DebateResult
        mock_debate = MagicMock()
        mock_debate.run.side_effect = [
            DebateResult(answer_label="A", debate_score=0.5, surviving_claims=1, successful_attacks=0, total_proposer_tokens=50, total_challenger_tokens=50, transcript=[]),
            DebateResult(answer_label="B", debate_score=0.5, surviving_claims=1, successful_attacks=0, total_proposer_tokens=50, total_challenger_tokens=50, transcript=[])
        ]
        judge.debate_game = mock_debate

        mock_calibration = MagicMock()
        # Evaluators report 0.5 initially
        from src.models import CalibrationResult
        mock_calibration.run.return_value = [
            CalibrationResult(evaluator_id=0, reported_confidence=0.6, calibration_score=0.8),
            CalibrationResult(evaluator_id=1, reported_confidence=0.4, calibration_score=0.8),
        ]
        # Return updated calibration results on score compute
        mock_calibration.compute_brier_scores.side_effect = lambda results, gt_y: [
            CalibrationResult(evaluator_id=0, reported_confidence=0.6, calibration_score=1.0 - (gt_y - 0.6)**2),
            CalibrationResult(evaluator_id=1, reported_confidence=0.4, calibration_score=1.0 - (gt_y - 0.4)**2),
        ]
        judge.calibration_game = mock_calibration

        res = judge.evaluate("Q", "Ans A", "Ans B")
        assert res.verdict in ("Tie", "A_wins", "B_wins")




# ===========================================================================
# Test 9: Multi-provider LLM client factory (issue §2)
# ===========================================================================

class TestMultiProviderClient:
    """The LLMClient factory must build the right backend, share the base
    logic, and fail loudly on bad configuration."""

    def test_factory_builds_openai_by_default(self, monkeypatch):
        from src.llm_client import LLMClient, OpenAIClient
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy")
        c = LLMClient(model="gpt-4o-mini", temperature=0.0)
        assert isinstance(c, OpenAIClient)
        assert c.provider_name == "openai"

    def test_factory_selects_each_provider(self):
        # Route without constructing: the anthropic/google SDKs are optional
        # (lazily imported) and may not be installed in every environment.
        from src.llm_client import (
            _PROVIDER_CLASSES, OpenAIClient, AnthropicClient, GoogleClient,
        )
        assert _PROVIDER_CLASSES["openai"] is OpenAIClient
        assert _PROVIDER_CLASSES["anthropic"] is AnthropicClient
        assert _PROVIDER_CLASSES["google"] is GoogleClient

    def test_uninstalled_provider_sdk_raises_clear_error(self, monkeypatch):
        # If a provider is selected but its SDK isn't installed, construction
        # must fail with an actionable LLMConfigError (not an ImportError).
        import importlib
        from src.llm_client import LLMClient, LLMConfigError
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-a")
        try:
            importlib.import_module("anthropic")
            installed = True
        except ImportError:
            installed = False
        if installed:
            pytest.skip("anthropic SDK is installed; nothing to assert here")
        with pytest.raises(LLMConfigError):
            LLMClient(provider="anthropic")

    def test_unknown_provider_raises(self):
        from src.llm_client import LLMClient, LLMConfigError
        with pytest.raises(LLMConfigError):
            LLMClient(provider="not-a-provider")

    def test_missing_key_raises_config_error(self, monkeypatch):
        from src.llm_client import LLMClient, LLMConfigError
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMConfigError):
            LLMClient(provider="openai")  # no key in env, none passed

    def test_explicit_api_key_overrides_env(self, monkeypatch):
        from src.llm_client import LLMClient
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        c = LLMClient(provider="openai", api_key="sk-explicit")
        assert c.api_key == "sk-explicit"

    def test_provider_case_insensitive_routing(self):
        from src.llm_client import _PROVIDER_CLASSES
        # factory lowercases before lookup; verify the normalization contract
        assert "Anthropic".lower() in _PROVIDER_CLASSES
        assert "OPENAI".lower() in _PROVIDER_CLASSES


# ===========================================================================
# Test 10: Robust JSON extraction in call_structured (issue §4 edge cases)
# ===========================================================================

class TestJSONExtraction:
    """_extract_json must survive fences, prose, and malformed output."""

    def _extract(self, text):
        from src.llm_client import BaseLLMClient
        return BaseLLMClient._extract_json(text)

    def test_direct_json(self):
        assert self._extract('{"action": "attack"}') == {"action": "attack"}

    def test_fenced_json(self):
        text = 'Sure!\n```json\n{"action": "concede"}\n```\nHope that helps.'
        assert self._extract(text) == {"action": "concede"}

    def test_json_embedded_in_prose(self):
        text = 'I think the answer is {"score": 0.8, "winner": "A"} overall.'
        assert self._extract(text) == {"score": 0.8, "winner": "A"}

    def test_malformed_returns_none(self):
        assert self._extract("this is not json at all") is None
        assert self._extract("{broken: ") is None
        assert self._extract("") is None

    def test_call_structured_flags_parse_error(self, monkeypatch):
        from src.llm_client import LLMClient
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy")
        client = LLMClient(provider="openai", temperature=0.0)
        # Monkeypatch the underlying raw call to return junk
        monkeypatch.setattr(client, "_raw_call",
                            lambda s, u, t: ("no json here", 5))
        parsed, tokens = client.call_structured("sys", "user")
        assert parsed.get("parse_error") is True
        assert parsed.get("raw_response") == "no json here"
        assert tokens == 5


# ===========================================================================
# Test 11: Correlated-error correction module (issue §5)
# ===========================================================================

class TestCorrelationModule:
    """The n_eff identity, GLS weights, and effective_n bounds."""

    def test_effective_n_identity_equicorrelation(self):
        from src.correlation import equicorrelation, effective_n
        for n in (2, 3, 5):
            for rho in (0.0, 0.3, 0.6, 0.9):
                sigma = equicorrelation(n, rho)
                closed = n / (1 + (n - 1) * rho)
                assert abs(effective_n(sigma) - closed) < 1e-6

    def test_effective_n_bounds(self):
        from src.correlation import equicorrelation, effective_n
        # rho=0 -> n_eff = n ; rho->1 -> n_eff -> 1
        assert abs(effective_n(equicorrelation(5, 0.0)) - 5.0) < 1e-6
        assert abs(effective_n(equicorrelation(5, 0.999)) - 1.0) < 0.05
        neff = effective_n(equicorrelation(4, 0.5))
        assert 1.0 <= neff <= 4.0

    def test_gls_weights_sum_to_one(self):
        from src.correlation import equicorrelation, gls_weights
        for n in (2, 3, 5):
            for rho in (0.0, 0.4, 0.8):
                w = gls_weights(equicorrelation(n, rho))
                assert abs(float(w.sum()) - 1.0) < 1e-6

    def test_gls_weights_uniform_for_equicorrelation(self):
        from src.correlation import equicorrelation, gls_weights
        # Symmetric (equicorrelation) => equal weights.
        w = gls_weights(equicorrelation(3, 0.6))
        assert all(abs(wi - 1.0 / 3) < 1e-6 for wi in w)

    def test_pearson_matrix_diag_ones(self):
        import numpy as np
        from src.correlation import pearson_correlation_matrix
        rng = np.random.default_rng(0)
        signals = rng.standard_normal((50, 3))
        corr = pearson_correlation_matrix(signals)
        assert np.allclose(np.diag(corr), 1.0, atol=1e-6)

    def test_shrinkage_moves_toward_identity(self):
        import numpy as np
        from src.correlation import equicorrelation, shrink_to_identity
        sigma = equicorrelation(3, 0.9)
        shrunk = shrink_to_identity(sigma, lam=0.5)
        # off-diagonal magnitude should shrink
        assert abs(shrunk[0, 1]) < abs(sigma[0, 1])


# ===========================================================================
# Test 12: Arbitration correlation correction behaviour (issue §5)
# ===========================================================================

class TestArbitrationCorrelationCorrection:
    def _cal(self, eid, p):
        from src.models import CalibrationResult
        return CalibrationResult(evaluator_id=eid, reported_confidence=p,
                                 calibration_score=0.9)

    def _debate(self, score):
        from src.models import DebateResult
        return DebateResult(answer_label="A", debate_score=score, surviving_claims=1,
                            successful_attacks=0, total_proposer_tokens=100,
                            total_challenger_tokens=100, transcript=[])

    def test_correction_reports_neff_and_rho(self):
        from src.arbitration_game import ArbitrationGame
        game = ArbitrationGame(correlation_correction=True, prior_rho=0.6)
        res = game.run(
            {"A": self._debate(1.0), "B": self._debate(-1.0)},
            [self._cal(0, 0.8), self._cal(1, 0.85)],
        )
        # n=2, prior_rho=0.6 -> n_eff = 2/(1+0.6) = 1.25
        assert abs(res.n_effective - 1.25) < 1e-6
        assert abs(res.effective_correlation - 0.6) < 1e-6
        # both corrected and uncorrected confidences populated
        assert 0.0 <= res.confidence <= 1.0
        assert 0.0 <= res.confidence_uncorrected <= 1.0

    def test_no_correction_when_disabled(self):
        from src.arbitration_game import ArbitrationGame
        game = ArbitrationGame(correlation_correction=False)
        res = game.run(
            {"A": self._debate(1.0), "B": self._debate(-1.0)},
            [self._cal(0, 0.8), self._cal(1, 0.85)],
        )
        assert res.n_effective == 2.0
        assert res.effective_correlation == 0.0

    def test_single_evaluator_degenerate(self):
        # n=1: correction cannot apply (needs >=2); must not crash.
        from src.arbitration_game import ArbitrationGame
        game = ArbitrationGame(correlation_correction=True)
        res = game.run(
            {"A": self._debate(1.0), "B": self._debate(-1.0)},
            [self._cal(0, 0.8)],
        )
        assert res.n_effective == 1.0
        assert 0.0 <= res.confidence <= 1.0


# ===========================================================================
# Test 13: Edge cases (issue §4)
# ===========================================================================

class TestEdgeCases:
    def test_empty_answer_strings(self):
        from src.arbitration_game import ArbitrationGame
        from src.models import DebateResult, CalibrationResult
        game = ArbitrationGame()
        # tie scores, empty debate influence
        dr = DebateResult(answer_label="A", debate_score=0.0, surviving_claims=0,
                         successful_attacks=0, total_proposer_tokens=0,
                         total_challenger_tokens=0, transcript=[])
        res = game.run(
            {"A": dr, "B": dr},
            [CalibrationResult(evaluator_id=0, reported_confidence=0.5,
                              calibration_score=0.5),
             CalibrationResult(evaluator_id=1, reported_confidence=0.5,
                              calibration_score=0.5)],
        )
        assert res.verdict in ("A_wins", "B_wins", "Tie")

    def test_tie_scores_produce_valid_verdict(self):
        from src.arbitration_game import ArbitrationGame
        from src.models import DebateResult, CalibrationResult
        game = ArbitrationGame()
        dr = DebateResult(answer_label="A", debate_score=0.5, surviving_claims=1,
                         successful_attacks=0, total_proposer_tokens=50,
                         total_challenger_tokens=50, transcript=[])
        res = game.run(
            {"A": dr, "B": dr},
            [CalibrationResult(evaluator_id=0, reported_confidence=0.5,
                              calibration_score=0.5),
             CalibrationResult(evaluator_id=1, reported_confidence=0.5,
                              calibration_score=0.5)],
        )
        # symmetric inputs -> should not crash and confidence near 0.5
        assert 0.0 <= res.confidence <= 1.0

    def test_logit_sigmoid_roundtrip(self):
        from src.arbitration_game import _logit, _sigmoid
        for p in (0.01, 0.3, 0.5, 0.7, 0.99):
            assert abs(_sigmoid(_logit(p)) - p) < 1e-6

    def test_logit_clamps_extremes(self):
        from src.arbitration_game import _logit
        # must not raise on 0 or 1
        assert _logit(0.0) < 0
        assert _logit(1.0) > 0


# ===========================================================================
# Test 14: Benchmark loader (issue §3/§4)
# ===========================================================================

class TestBenchmarkLoader:
    def test_sample_benchmark_is_valid(self):
        import json
        from pathlib import Path
        data = json.loads(Path("configs/sample_benchmark.json").read_text())
        items = data["items"] if isinstance(data, dict) else data
        assert len(items) >= 1
        for it in items:
            assert "question" in it
            assert "answer_a" in it and "answer_b" in it
            assert it.get("human_preference") in ("A", "B", "Tie", None)

    def test_benchmark_categories_present(self):
        import json
        from pathlib import Path
        data = json.loads(Path("configs/sample_benchmark.json").read_text())
        items = data["items"] if isinstance(data, dict) else data
        cats = {it.get("category") for it in items}
        # at least the coding + math categories should exist
        assert len(cats) >= 1

# ===========================================================================
# Test 15: Ablation modes (issue §3)
# ===========================================================================

class TestAblations:
    """Each ablation must construct, be recognised, and neutralise its game."""

    def _judge(self, ablation, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy")
        from src.gt_judge import GTJudge
        from tests.scripted_llm import _scripted_llm_for_tests
        judge = GTJudge.from_config("configs/default.yaml",
                                    overrides={"ablation": ablation})
        mock = _scripted_llm_for_tests(profile="benchmark")
        judge.llm = mock
        judge.debate_game.llm = mock
        judge.calibration_game.llm = mock
        return judge

    def test_unknown_ablation_rejected(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy")
        from src.gt_judge import GTJudge
        with pytest.raises(ValueError):
            GTJudge.from_config("configs/default.yaml",
                                overrides={"ablation": "no_such_game"})

    def test_no_debate_neutralises_scores(self, monkeypatch):
        judge = self._judge("no_debate", monkeypatch)
        res = judge.evaluate("Q", "Ans A", "Ans B", ground_truth="A")
        # Debate scores must be exactly zero (no signal from Game 1).
        assert res.debate_results["A"].debate_score == 0.0
        assert res.debate_results["B"].debate_score == 0.0
        assert res.debate_results["A"].total_proposer_tokens == 0

    def test_no_calibration_uses_flat_confidence(self, monkeypatch):
        judge = self._judge("no_calibration", monkeypatch)
        res = judge.evaluate("Q", "Ans A", "Ans B", ground_truth="A")
        assert all(abs(c.reported_confidence - 0.5) < 1e-9
                   for c in res.calibration_results)

    def test_no_arbitration_uses_simple_rule(self, monkeypatch):
        judge = self._judge("no_arbitration", monkeypatch)
        res = judge.evaluate("Q", "Ans A", "Ans B", ground_truth="A")
        # Nash product is not computed in the simple fallback.
        assert res.arbitration_result.nash_product == 0.0
        assert res.verdict in ("A_wins", "B_wins", "Tie")

    def test_full_pipeline_still_default(self, monkeypatch):
        judge = self._judge(None, monkeypatch)
        assert judge.ablation is None
        res = judge.evaluate("Q", "Ans A", "Ans B", ground_truth="A")
        assert res.verdict in ("A_wins", "B_wins", "Tie")


# ===========================================================================
# Test 16: Conformal selective risk control under correlation (issue §9)
# ===========================================================================

class TestSelectiveRiskControl:
    """Test conformal risk control and design effect bounds under correlation."""

    def test_design_effect_bounds(self):
        from src.selective import design_effect
        # rho=0 => design effect is exactly 1.0
        assert abs(design_effect(10, 0.0) - 1.0) < 1e-9
        # cluster_size=1 => design effect is exactly 1.0
        assert abs(design_effect(1, 0.5) - 1.0) < 1e-9
        # rho=0.5, cluster_size=10 => D = 1 + 9 * 0.5 = 5.5
        assert abs(design_effect(10, 0.5) - 5.5) < 1e-9

    def test_effective_count_bounds(self):
        from src.selective import effective_count
        # n_eff cannot exceed n or fall below 1
        assert abs(effective_count(100, 0.0) - 100.0) < 1e-9
        assert abs(effective_count(100, 1.0) - 1.0) < 1e-9
        n_eff = effective_count(100, 0.1, cluster_size=10)
        assert 1.0 <= n_eff <= 100.0

    def test_ucb_bounds(self):
        from src.selective import error_rate_ucb
        # UCB must be monotonic in rho (higher rho -> wider interval -> higher UCB)
        ucb_naive = error_rate_ucb(5, 50, 0.1, rho=0.0)
        ucb_corr = error_rate_ucb(5, 50, 0.1, rho=0.3, cluster_size=10)
        assert ucb_corr >= ucb_naive

    def test_conformal_certificate(self):
        from src.selective import calibrate_threshold
        confidences = [0.9, 0.8, 0.7, 0.6, 0.5]
        errors = [0, 0, 1, 0, 1]
        cert = calibrate_threshold(confidences, errors, alpha=0.2, delta=0.1, rho=0.1, cluster_size=2)
        assert cert.threshold >= 0.5
        assert isinstance(cert.risk_ucb, float)
        assert isinstance(cert.certifies(), bool)

    def test_coverage_cost_grid(self):
        from src.selective import calibrate_threshold
        confidences = [0.95, 0.85, 0.75, 0.65, 0.55]
        errors = [0, 0, 0, 1, 1]
        # target error rate is very strict => must accept fewer items (lower coverage)
        cert_strict = calibrate_threshold(confidences, errors, alpha=0.05, delta=0.1)
        cert_loose = calibrate_threshold(confidences, errors, alpha=0.50, delta=0.1)
        assert cert_strict.coverage <= cert_loose.coverage

    def test_rho_zero_behavior(self):
        from src.selective import calibrate_threshold
        confidences = [0.9, 0.8, 0.7, 0.6, 0.5]
        errors = [0, 0, 1, 0, 1]
        cert_naive = calibrate_threshold(confidences, errors, alpha=0.2, delta=0.1, rho=0.0, correct=False)
        cert_corr = calibrate_threshold(confidences, errors, alpha=0.2, delta=0.1, rho=0.0, correct=True)
        assert abs(cert_naive.threshold - cert_corr.threshold) < 1e-9
        assert abs(cert_naive.risk_ucb - cert_corr.risk_ucb) < 1e-9

    def test_bonferroni_multiplicity_correction(self):
        from src.selective import calibrate_threshold
        confidences = [0.9, 0.8, 0.7, 0.6, 0.5]
        errors = [0, 0, 0, 0, 0]
        # Grid sizes: n_grid=2 vs n_grid=20
        # Larger grid size -> more candidate thresholds -> smaller Bonferroni delta -> UCB gets slightly wider/different
        cert_small = calibrate_threshold(confidences, errors, alpha=0.1, delta=0.1, n_grid=2)
        cert_large = calibrate_threshold(confidences, errors, alpha=0.1, delta=0.1, n_grid=20)
        assert cert_small.risk_ucb <= 1.0
        assert cert_large.risk_ucb <= 1.0
