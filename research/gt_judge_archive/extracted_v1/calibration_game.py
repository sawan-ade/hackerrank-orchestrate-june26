"""
Game 2: Confidence Calibration Game
=====================================
Implements the proper scoring mechanism (G₂ = ⟨N, [0,1]^|N|, Ucal⟩).
Ref: Phase 1 Formalization, Section 3.

Each evaluator reports a calibrated confidence p̂ᵢ ∈ [0,1].
Scored using the Brier rule: Ucal(p̂, y) = 1 - (y - p̂)² [Eq. 10]

Ground truth resolution follows Fix 4:
  - Benchmark mode: use human labels as y
  - Deployment mode: use consensus proxy ỹ from Game 3 output
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from src.models import CalibrationResult, DebateResult
from src.llm_client import LLMClient
from src.prompts import CALIBRATION_SYSTEM, CALIBRATION_USER


EVALUATOR_PERSONAS = [
    {
        "name": "Correctness Evaluator",
        "focus": "factual accuracy, logical soundness, and technical correctness. Analyze if the claims are true, identify hidden bugs/flaws, and grade based on correctness.",
        "temp": 0.1
    },
    {
        "name": "Clarity & Structure Evaluator",
        "focus": "explanation quality, readability, structural organization, and clarity. Check if the concepts are explained well, is concise but complete, and uses proper formatting/code comments.",
        "temp": 0.2
    },
    {
        "name": "Completeness & Depth Evaluator",
        "focus": "depth of reasoning, rigor of argumentation, and completeness of analysis. Penalize answers that omit edge cases, skip key explanations, or lack detail.",
        "temp": 0.15
    }
]


class CalibrationGame:
    """
    Runs the confidence calibration stage for each evaluator.
    
    After the debate, each evaluator independently reports their
    posterior belief that Answer A is superior.
    """

    def __init__(
        self,
        llm: LLMClient,
        n_evaluators: int = 2,
        ground_truth_mode: str = "consensus_proxy",
    ):
        self.llm = llm
        self.n_evaluators = n_evaluators
        self.ground_truth_mode = ground_truth_mode

    def run(
        self,
        question: str,
        answer_a: str,
        answer_b: str,
        debate_a: DebateResult,
        debate_b: DebateResult,
        ground_truth: str | None = None,
    ) -> list[CalibrationResult]:
        """
        Collect calibrated confidence estimates from each evaluator.
        
        Args:
            question: The evaluation question.
            answer_a: Answer A text.
            answer_b: Answer B text.
            debate_a: Game 1 results for Answer A.
            debate_b: Game 1 results for Answer B.
            ground_truth: Optional human label ('A', 'B', 'Tie') for benchmark mode.
            
        Returns:
            List of CalibrationResult, one per evaluator.
        """
        def elicit_task(evaluator_id: int) -> CalibrationResult:
            confidence = self._elicit_confidence(
                evaluator_id=evaluator_id,
                question=question,
                answer_a=answer_a,
                answer_b=answer_b,
                debate_a=debate_a,
                debate_b=debate_b,
            )
            return CalibrationResult(
                evaluator_id=evaluator_id,
                reported_confidence=confidence,
            )

        with ThreadPoolExecutor(max_workers=self.n_evaluators) as executor:
            results = list(executor.map(elicit_task, range(self.n_evaluators)))

        results.sort(key=lambda r: r.evaluator_id)
        return results

    def compute_brier_scores(
        self,
        results: list[CalibrationResult],
        ground_truth_y: float,
    ) -> list[CalibrationResult]:
        """
        Compute the Brier score for each evaluator given the resolved ground truth.
        
        Ucal(p̂, y) = 1 - (y - p̂)²   [Eq. 10]
        
        Args:
            results: Calibration results with reported confidence.
            ground_truth_y: The ground truth signal y ∈ {0, 0.5, 1}.
                           1.0 = A is superior, 0.0 = B is superior, 0.5 = Tie.
        
        Returns:
            Updated CalibrationResult list with calibration_score filled in.
        """
        for r in results:
            r.calibration_score = 1.0 - (ground_truth_y - r.reported_confidence) ** 2
        return results

    def _elicit_confidence(
        self,
        evaluator_id: int,
        question: str,
        answer_a: str,
        answer_b: str,
        debate_a: DebateResult,
        debate_b: DebateResult,
    ) -> float:
        """
        Ask one evaluator to report their calibrated confidence.
        Returns p̂ ∈ [0, 1].
        """
        # Summarize debate transcripts
        debate_a_summary = self._summarize_debate(debate_a)
        debate_b_summary = self._summarize_debate(debate_b)

        # Retrieve evaluator persona (A-2)
        persona = EVALUATOR_PERSONAS[evaluator_id % len(EVALUATOR_PERSONAS)]
        system_prompt = CALIBRATION_SYSTEM.format(
            persona_name=persona["name"],
            persona_focus=persona["focus"],
        )

        # Position counterbalancing (B-5)
        # Alternate presentation order based on evaluator_id to avoid positional bias
        swap = (evaluator_id % 2 == 1)

        if swap:
            user_prompt = CALIBRATION_USER.format(
                question=question,
                answer_a=answer_b,
                answer_b=answer_a,
                debate_a_summary=debate_b_summary,
                debate_b_summary=debate_a_summary,
                score_a=f"{debate_b.debate_score:.3f}",
                score_b=f"{debate_a.debate_score:.3f}",
            )
        else:
            user_prompt = CALIBRATION_USER.format(
                question=question,
                answer_a=answer_a,
                answer_b=answer_b,
                debate_a_summary=debate_a_summary,
                debate_b_summary=debate_b_summary,
                score_a=f"{debate_a.debate_score:.3f}",
                score_b=f"{debate_b.debate_score:.3f}",
            )

        parsed, _ = self.llm.call_structured(
            system_prompt, user_prompt, temperature=persona["temp"]
        )

        confidence = parsed.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5

        # If we swapped presentation order, flip the confidence back to A-wins scale
        if swap:
            confidence = 1.0 - confidence

        return max(0.0, min(1.0, float(confidence)))

    def _summarize_debate(self, debate: DebateResult) -> str:
        """Create a concise summary of a debate for the calibration prompt."""
        lines = [f"Answer {debate.answer_label} debate — Score: {debate.debate_score:.3f}"]
        lines.append(f"  Surviving claims: {debate.surviving_claims}")
        lines.append(f"  Successful attacks: {debate.successful_attacks}")
        for move in debate.transcript[-4:]:  # Last 4 moves for context
            role = "PROP" if move.action in ("claim", "defend", "clarify") else "CHAL"
            lines.append(f"  [{role}|{move.action}]: {move.argument[:200]}")
        return "\n".join(lines)
