"""
Game 1: Reasoning Debate Game
===============================
Implements the extensive-form Proposer-Challenger debate (G₁ = ⟨N, H, Z, A, σ, u⟩).
Ref: Phase 1 Formalization, Section 2.

The debate runs for K rounds:
  1. Proposer makes claims about an answer's quality
  2. Challenger attacks the weakest claims
  3. Proposer defends (or abandons) attacked claims
  4. Validity assessor scores attack severity (endogenous v(c), Fix 2)

Computes DebateScore(X) = Σ v(c) - Σ sev(a, c(a))  [Eq. 22]
"""

from __future__ import annotations

from src.models import (
    AgentMove, Attack, Claim, DebateResult, DebateState,
    ProposerAction, ChallengerAction,
)
from src.llm_client import LLMClient
from src.prompts import (
    PROPOSER_SYSTEM, PROPOSER_USER,
    CHALLENGER_SYSTEM, CHALLENGER_USER,
    VALIDITY_SYSTEM, VALIDITY_USER,
)


class DebateGame:
    """
    Runs a structured debate between a Proposer and Challenger for one answer.
    
    The debate is run TWICE per evaluation instance (once for Answer A, once for B)
    to enforce position invariance (Proposition 1', Fix 5).
    """

    def __init__(
        self,
        llm: LLMClient,
        max_rounds: int = 3,
        lambda_cost: float = 0.001,
    ):
        self.llm = llm
        self.max_rounds = max_rounds
        self.lambda_cost = lambda_cost
        # NOTE: claim/attack ID counters are intentionally NOT instance state.
        # gt_judge.py runs the SAME DebateGame instance concurrently for answers
        # A and B in a ThreadPoolExecutor; instance-level counters would race and
        # hand out duplicate/interleaved IDs (issue §4). IDs are scoped per debate
        # and allocated locally inside run() instead.

    def run(self, question: str, answer: str, answer_label: str) -> DebateResult:
        """
        Run the full K-round debate for one answer.
        
        Args:
            question: The evaluation question.
            answer: The answer text to debate.
            answer_label: "A" or "B".
            
        Returns:
            DebateResult with scores and transcript.
        """
        state = DebateState(
            question=question,
            answer_a=answer if answer_label == "A" else "",
            answer_b=answer if answer_label == "B" else "",
            current_answer_under_debate=answer_label,
            max_rounds=self.max_rounds,
        )

        # Per-run, thread-local ID allocators (issue §4 race fix). `next(...)`
        # on an itertools.count is atomic w.r.t. the GIL and, more importantly,
        # each run() call gets its OWN counters so concurrent A/B debates on a
        # shared DebateGame instance never collide.
        import itertools
        claim_ids = itertools.count(1)
        attack_ids = itertools.count(1)

        for round_num in range(1, self.max_rounds + 1):
            state.current_round = round_num

            # Step 1: Proposer makes claims or clarifies
            proposer_move = self._proposer_turn(state, answer, question, round_num)
            state.transcript.append(proposer_move)
            state.proposer_tokens += proposer_move.token_count

            # Process proposer move
            if proposer_move.action == ProposerAction.CLAIM:
                claim = Claim(
                    claim_id=next(claim_ids),
                    text=proposer_move.argument,
                    round_made=round_num,
                )
                state.claims.append(claim)

                # Step 2: Challenger turn (targets the new claim)
                challenger_move = self._challenger_turn(state, answer, question, round_num)
                state.transcript.append(challenger_move)
                state.challenger_tokens += challenger_move.token_count

                if challenger_move.action == ChallengerAction.CONCEDE:
                    # Early exit on concede (C-2)
                    break

                if challenger_move.action in (ChallengerAction.ATTACK, ChallengerAction.COUNTEREXAMPLE):
                    attack = Attack(
                        attack_id=next(attack_ids),
                        text=challenger_move.argument,
                        target_claim_id=claim.claim_id,
                        round_made=round_num,
                    )
                    state.attacks.append(attack)
                    claim.was_attacked = True

                    # Step 3: Proposer defends in the same round (B-2)
                    defense_move = self._proposer_defend(state, claim, attack, answer, question, round_num)
                    state.transcript.append(defense_move)
                    state.proposer_tokens += defense_move.token_count
                    claim.was_defended = True

                    # Step 4: Validity assessor scores attack severity and defense success
                    severity, defense_success = self._assess_validity(
                        claim_text=claim.text,
                        attack_text=attack.text,
                        defense_text=defense_move.argument,
                        claim_id=claim.claim_id,
                    )
                    attack.severity = severity
                    
                    if defense_success:
                        # Defended but potentially weakened by severity (B-2)
                        claim.validity = max(0.0, 1.0 - severity * 0.3)
                        attack.was_refuted = True
                    else:
                        claim.validity = max(0.0, 1.0 - severity)
                        attack.was_refuted = False

            elif proposer_move.action == ProposerAction.CLARIFY:
                # Explicitly handle clarify action (C-1)
                target_id = proposer_move.target_claim_id
                if target_id is None and state.claims:
                    target_id = state.claims[-1].claim_id
                
                if target_id is not None:
                    for c in state.claims:
                        if c.claim_id == target_id:
                            c.text += f" (Clarification: {proposer_move.argument})"

        # Compute normalized debate score with lambda cost penalty (B-1, A-3)
        n_claims = len(state.claims)
        n_attacks = len(state.attacks)
        
        mean_validity = sum(c.validity for c in state.claims) / n_claims if n_claims > 0 else 0.0
        mean_severity = sum(a.severity for a in state.attacks) / n_attacks if n_attacks > 0 else 0.0
        
        token_penalty = self.lambda_cost * (state.proposer_tokens + state.challenger_tokens)
        debate_score = mean_validity - mean_severity - token_penalty

        surviving = sum(1 for c in state.claims if c.validity > 0.3)
        successful_attacks = sum(1 for a in state.attacks if a.severity > 0.5)

        return DebateResult(
            answer_label=answer_label,
            debate_score=debate_score,
            surviving_claims=surviving,
            successful_attacks=successful_attacks,
            total_proposer_tokens=state.proposer_tokens,
            total_challenger_tokens=state.challenger_tokens,
            transcript=state.transcript,
            total_claims=n_claims,
            total_attacks=n_attacks,
        )

    # --- Private Methods ---

    def _proposer_turn(self, state: DebateState, answer: str, question: str, round_num: int) -> AgentMove:
        """Generate the Proposer's move for this round."""
        history_text = self._format_history(state.transcript)
        system = PROPOSER_SYSTEM.format(lambda_cost=self.lambda_cost)
        user = PROPOSER_USER.format(
            question=question,
            answer=answer,
            debate_history=history_text if history_text else "No debate history yet.",
            round=round_num,
            max_rounds=self.max_rounds,
        )
        parsed, tokens = self.llm.call_structured(system, user)
        
        # Normalize action to enum at parse time (D-2)
        raw_action = parsed.get("action", "claim")
        try:
            action = ProposerAction(raw_action)
        except ValueError:
            action = ProposerAction.CLAIM

        return AgentMove(
            action=action,
            argument=parsed.get("argument", parsed.get("raw_response", "")),
            target_claim_id=parsed.get("target_claim_id"),
            token_count=tokens,
        )

    def _proposer_defend(
        self, state: DebateState, claim: Claim, attack: Attack, answer: str, question: str, round_num: int
    ) -> AgentMove:
        """Generate a Proposer's defense move specifically responding to an attack (B-2)."""
        defend_user_prompt = f"""QUESTION: {question}

ANSWER UNDER REVIEW:
{answer}

A claim you made has been attacked!
CLAIM: [Claim {claim.claim_id}] {claim.text}
ATTACK: {attack.text}

You must defend your claim.
RULES:
1. Your action MUST be "defend".
2. Provide a clear defense rebuttal explaining why the attack is incorrect or how your claim still holds.
3. Every extra token costs you λ={self.lambda_cost}. Be concise.

OUTPUT FORMAT (JSON):
{{
  "action": "defend",
  "argument": "Your detailed defense/rebuttal text here",
  "target_claim_id": {claim.claim_id}
}}"""

        system = PROPOSER_SYSTEM.format(lambda_cost=self.lambda_cost)
        parsed, tokens = self.llm.call_structured(system, defend_user_prompt)
        return AgentMove(
            action=ProposerAction.DEFEND,
            argument=parsed.get("argument", parsed.get("raw_response", "")),
            target_claim_id=claim.claim_id,
            token_count=tokens,
        )

    def _challenger_turn(self, state: DebateState, answer: str, question: str, round_num: int) -> AgentMove:
        """Generate the Challenger's move for this round."""
        claims_text = "\n".join(
            f"[Claim {c.claim_id}] (validity={c.validity:.2f}): {c.text}"
            for c in state.claims
        )
        history_text = self._format_history(state.transcript)
        system = CHALLENGER_SYSTEM.format(lambda_cost=self.lambda_cost)
        user = CHALLENGER_USER.format(
            question=question,
            answer=answer,
            claims_text=claims_text,
            debate_history=history_text,
            round=round_num,
            max_rounds=self.max_rounds,
        )
        parsed, tokens = self.llm.call_structured(system, user)
        
        # Normalize action to enum at parse time (D-2)
        raw_action = parsed.get("action", "concede")
        try:
            action = ChallengerAction(raw_action)
        except ValueError:
            action = ChallengerAction.CONCEDE

        return AgentMove(
            action=action,
            argument=parsed.get("argument", parsed.get("raw_response", "")),
            target_claim_id=parsed.get("target_claim_id"),
            token_count=tokens,
        )

    def _assess_validity(
        self, claim_text: str, attack_text: str, defense_text: str, claim_id: int
    ) -> tuple[float, bool]:
        """
        Assess attack severity using a separate LLM call (endogenous validity).
        Returns (severity ∈ [0, 1], defense_success ∈ {True, False}).
        """
        user = VALIDITY_USER.format(
            claim_id=claim_id,
            claim_text=claim_text,
            attack_text=attack_text,
            defense_text=defense_text if defense_text else "(No defense submitted)",
        )
        parsed, _ = self.llm.call_structured(
            VALIDITY_SYSTEM, user, temperature=0.0
        )
        severity = parsed.get("attack_severity", 0.5)
        if not isinstance(severity, (int, float)):
            severity = 0.5
        severity = max(0.0, min(1.0, float(severity)))
        
        defense_success = parsed.get("defense_success", False)
        if not isinstance(defense_success, bool):
            defense_success = False

        return severity, defense_success

    def _format_history(self, transcript: list[AgentMove]) -> str:
        """Format the debate transcript for inclusion in prompts."""
        if not transcript:
            return ""
        lines = []
        for i, move in enumerate(transcript):
            role = "PROPOSER" if move.action in (ProposerAction.CLAIM, ProposerAction.DEFEND, ProposerAction.CLARIFY) else "CHALLENGER"
            lines.append(f"[{role} | {move.action.upper()}]: {move.argument[:300]}")
        return "\n".join(lines)

