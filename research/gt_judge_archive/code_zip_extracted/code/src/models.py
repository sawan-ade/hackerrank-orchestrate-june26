"""
GT-Judge Data Models
====================
Pydantic schemas for all game state objects, agent moves, and pipeline I/O.
Maps directly to the formal definitions in Phase 1 (Defs 1-6).
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action Enums — Definition 1, Eq. (1)
# ---------------------------------------------------------------------------

class ProposerAction(str, Enum):
    CLAIM = "claim"
    DEFEND = "defend"
    CLARIFY = "clarify"


class ChallengerAction(str, Enum):
    ATTACK = "attack"
    COUNTEREXAMPLE = "counterexample"
    CONCEDE = "concede"


class Verdict(str, Enum):
    A_WINS = "A_wins"
    B_WINS = "B_wins"
    TIE = "Tie"


# ---------------------------------------------------------------------------
# Agent Move — structured output from LLM (Fix 1: Definition 7)
# ---------------------------------------------------------------------------

class AgentMove(BaseModel):
    """A single move by an evaluator agent in the debate."""
    action: str = Field(description="The declared action tag (e.g. 'attack', 'defend').")
    argument: str = Field(description="The natural language justification text.")
    target_claim_id: Optional[int] = Field(
        default=None,
        description="ID of the claim being targeted (for attacks/defenses)."
    )
    token_count: int = Field(default=0, description="Number of tokens consumed by this move.")


# ---------------------------------------------------------------------------
# Claim & Attack Records — Definitions 2' and 3
# ---------------------------------------------------------------------------

class Claim(BaseModel):
    """A claim made by the Proposer during the debate."""
    claim_id: int
    text: str
    validity: float = Field(default=1.0, ge=0.0, le=1.0, description="v(c) ∈ [0,1]")
    round_made: int
    was_attacked: bool = False
    was_defended: bool = False


class Attack(BaseModel):
    """An attack made by the Challenger targeting a specific claim."""
    attack_id: int
    text: str
    target_claim_id: int
    severity: float = Field(default=0.0, ge=0.0, le=1.0, description="sev(a,c) ∈ [0,1]")
    round_made: int
    was_refuted: bool = False


# ---------------------------------------------------------------------------
# Game State Objects
# ---------------------------------------------------------------------------

class DebateState(BaseModel):
    """Full state of Game 1 at any point during the debate."""
    question: str
    answer_a: str
    answer_b: str
    current_answer_under_debate: str = Field(description="Which answer is being debated: 'A' or 'B'")
    current_round: int = 0
    max_rounds: int = 3
    claims: list[Claim] = Field(default_factory=list)
    attacks: list[Attack] = Field(default_factory=list)
    transcript: list[AgentMove] = Field(default_factory=list)
    proposer_tokens: int = 0
    challenger_tokens: int = 0


class DebateResult(BaseModel):
    """Output of Game 1 for one answer."""
    answer_label: str  # "A" or "B"
    debate_score: float = Field(description="DebateScore(X) = Σv(c) - Σsev(a,c)")
    surviving_claims: int
    successful_attacks: int
    total_proposer_tokens: int
    total_challenger_tokens: int
    transcript: list[AgentMove]
    total_claims: int = Field(default=0, description="Total number of claims made")
    total_attacks: int = Field(default=0, description="Total number of attacks made")


class CalibrationResult(BaseModel):
    """Output of Game 2 for one evaluator."""
    evaluator_id: int
    reported_confidence: float = Field(description="p̂ᵢ ∈ [0,1]")
    calibration_score: float = Field(default=0.0, description="Ucal = 1 - (y - p̂)²")


class ArbitrationResult(BaseModel):
    """Output of Game 3 — the final verdict."""
    verdict: Verdict
    nash_product: float = Field(description="Value of the Nash product at the solution")
    weights: dict[int, float] = Field(description="Bargaining weights wᵢ per evaluator")
    confidence: float = Field(description="Aggregated confidence in the verdict")


# ---------------------------------------------------------------------------
# Full Pipeline I/O — Definition 6
# ---------------------------------------------------------------------------

class EvaluationInput(BaseModel):
    """Input to the GT-Judge pipeline."""
    question: str
    answer_a: str
    answer_b: str
    ground_truth: Optional[str] = Field(
        default=None,
        description="Human label for benchmark mode: 'A', 'B', or 'Tie'"
    )


class EvaluationOutput(BaseModel):
    """Output of the GT-Judge pipeline — GT-Judge(Q, A, B)."""
    verdict: Verdict
    confidence: float
    debate_results: dict[str, DebateResult] = Field(description="Results per answer: {'A': ..., 'B': ...}")
    calibration_results: list[CalibrationResult]
    arbitration_result: ArbitrationResult
    total_tokens: int
    justification: str
