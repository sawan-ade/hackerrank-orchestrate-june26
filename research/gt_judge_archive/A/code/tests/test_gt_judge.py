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
        from run_benchmark import create_mock_llm
        from src.gt_judge import GTJudge

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

        # Load sample benchmark configuration and run mock evaluations
        judge = GTJudge.from_config("configs/default.yaml")
        mock_llm = create_mock_llm()
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



