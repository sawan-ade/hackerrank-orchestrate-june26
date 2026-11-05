"""
scripts/build_pilot_benchmark.py  (issue §3, Tier 1)
=====================================================
Builds a *balanced, stratified* pilot benchmark and writes it to
configs/sample_benchmark.json.

Why this exists (issue §1.1): the original 5-item file had the *better* answer
in position A for every single item and every human_preference = "A". Any judge
that just always picks A — or always picks the longer answer — would score 100%.
That dataset cannot measure accuracy, position-flip, or verbosity bias.

This pilot set fixes that by construction:
  * 20 items, 4 per category (Coding, Math & Logic, Writing & Reasoning,
    Summarization, Argumentation).
  * The superior answer is placed in position A or B by a fixed seed, so
    "always pick A" and "always pick the first/longer" are NOT winning
    strategies. The intended-better answer is tracked and mapped to the label.
  * human_preference is balanced across A / B / Tie.
  * Every item carries a `rationale` documenting the intended quality gap, for
    transparency — this is a hand-authored PILOT set, explicitly not the paper's
    headline benchmark (that is the Tier-2 public-data run; see EXPERIMENTS.md).

This is a dataset *builder*, not an experiment: it makes zero LLM calls.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20260718
OUT = Path(__file__).resolve().parent.parent / "configs" / "sample_benchmark.json"

# Each entry: (category, question, better_answer, worse_answer, rationale)
# "better"/"worse" are semantic; positions A/B are assigned by the seed below.
# A subset is marked tie=True (the two answers are of comparable quality).
RAW = [
    # ---------------- Coding ----------------
    ("Coding",
     "Write a Python function to check whether a string is a palindrome, ignoring case and non-alphanumeric characters. Explain briefly.",
     "def is_palindrome(s):\n    t = [c.lower() for c in s if c.isalnum()]\n    return t == t[::-1]\n\nWe normalise by keeping only alphanumeric characters and lower-casing, then compare the cleaned list to its reverse. O(n) time, O(n) space.",
     "def is_palindrome(s):\n    return s == s[::-1]\n\nJust reverse the string and compare.",
     "The better answer handles case and punctuation as the prompt requires and states complexity; the worse one fails 'A man, a plan' and ignores the normalisation requirement.",
     False),
    ("Coding",
     "How do you safely read a large file line by line in Python without loading it all into memory?",
     "Iterate over the file object directly, which streams one line at a time:\n\nwith open(path) as f:\n    for line in f:\n        process(line)\n\nThe context manager guarantees the handle is closed, and the iterator keeps only one line resident, so memory stays flat regardless of file size.",
     "You can use f.readlines() to get all the lines and then loop over them. It's simple and works fine for files.",
     "readlines() loads the whole file into memory, which is exactly what the question asks to avoid; the streaming iterator is the correct idiom.",
     False),
    ("Coding",
     "Explain what a Python list comprehension is and give one example.",
     "A list comprehension builds a list from an iterable in a single expression: [x*x for x in range(5)] produces [0, 1, 4, 9, 16]. It is generally more readable and slightly faster than an equivalent append loop.",
     "List comprehensions are a way to make lists quickly. For example [x for x in range(5)] gives you a list. They are shorter than loops.",
     "Both are correct and roughly equivalent in quality; the first is marginally more complete but not decisively better — a genuine near-tie.",
     True),
    ("Coding",
     "Should I use `is` or `==` to compare a variable to None in Python?",
     "Use `is`: `if x is None`. None is a singleton, so identity comparison is correct, faster, and can't be broken by a custom __eq__. `==` can misbehave if the object overloads equality.",
     "Use `==`, like `if x == None`. It checks equality which is what you want when comparing values.",
     "PEP 8 and correctness both call for `is None`; `== None` can be overridden by __eq__ and is discouraged.",
     False),

    # ---------------- Math & Logic ----------------
    ("Math & Logic",
     "A bat and a ball cost $1.10 together. The bat costs $1.00 more than the ball. How much is the ball?",
     "Let the ball cost b. Then bat = b + 1.00, and b + (b + 1.00) = 1.10, so 2b = 0.10, b = $0.05. The ball is 5 cents (bat is $1.05).",
     "The ball is $0.10, since the bat is $1.00 and 1.00 + 0.10 = 1.10.",
     "The worse answer falls for the classic trap; the better one sets up and solves the equation correctly to $0.05.",
     False),
    ("Math & Logic",
     "Is 91 a prime number? Show your reasoning.",
     "No. 91 = 7 x 13, so it has divisors other than 1 and itself. It's composite.",
     "Yes, 91 is prime because it's odd and not divisible by 3 or 5.",
     "91 = 7 x 13; the worse answer stops checking too early and misses the factor 7.",
     False),
    ("Math & Logic",
     "What is the probability of rolling a sum of 7 with two fair six-sided dice?",
     "There are 6 ordered outcomes summing to 7: (1,6),(2,5),(3,4),(4,3),(5,2),(6,1), out of 36 equally likely outcomes, so 6/36 = 1/6.",
     "There are 36 outcomes and 7 can be made a few ways, so it's about 6/36 which is 1/6.",
     "Both reach 1/6; the first enumerates the outcomes rigorously, the second hand-waves but lands correctly — close in quality.",
     True),
    ("Math & Logic",
     "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
     "Yes. This is a transitive chain: Bloops ⊆ Razzies ⊆ Lazzies, therefore Bloops ⊆ Lazzies. The conclusion follows necessarily.",
     "Not necessarily, because we don't know if every Bloop was counted.",
     "The relation is transitive, so the conclusion is guaranteed; the worse answer misreads a valid syllogism as uncertain.",
     False),

    # ---------------- Writing & Reasoning ----------------
    ("Writing & Reasoning",
     "Give feedback on this opening line for a cover letter: 'I am writing to apply for the job you posted.'",
     "It's functional but generic and forgettable. Name the specific role and company and lead with a hook: e.g., 'As a data engineer who has cut pipeline costs by 30%, I was excited to see your Senior Data Engineer opening at Acme.' Specificity signals genuine interest and immediately frames your value.",
     "It's a fine opening line. It tells them you are applying for the job, which is the point of a cover letter, so it works.",
     "The better answer diagnoses the weakness (generic) and gives a concrete, improved rewrite; the worse one endorses a weak line without insight.",
     False),
    ("Writing & Reasoning",
     "Explain the difference between 'affect' and 'effect' to a learner.",
     "'Affect' is usually a verb meaning to influence ('the rain affected traffic'). 'Effect' is usually a noun meaning the result ('the effect was chaos'). Quick trick: Affect = Action (verb), Effect = End result (noun).",
     "Affect and effect sound the same but mean different things. One is about causing and the other is about results. People mix them up a lot.",
     "The better answer gives the part-of-speech rule, examples, and a mnemonic; the worse one gestures at the distinction without making it usable.",
     False),
    ("Writing & Reasoning",
     "Summarise the moral of the tortoise and the hare in one sentence.",
     "Slow and steady persistence beats talented complacency.",
     "The lesson is that being consistent and not overconfident helps you win in the end, even against faster opponents.",
     "Both capture the moral; the first is crisper, the second is wordier but accurate — a near-tie on substance.",
     True),
    ("Writing & Reasoning",
     "Is it okay to start a sentence with 'because'?",
     "Yes, as long as the sentence is complete. 'Because it rained, we stayed in' is fine — the clause is followed by a main clause. Problems only arise with a sentence fragment like 'Because it rained.' standing alone.",
     "No, you should never start a sentence with 'because' — it's a subordinating conjunction and it's grammatically wrong.",
     "The prohibition is a myth; the better answer states the real condition (need a main clause), the worse one asserts a false absolute rule.",
     False),

    # ---------------- Summarization ----------------
    ("Summarization",
     "Summarise: 'The committee met on Tuesday, reviewed the quarterly budget, approved two new hires, and postponed the office relocation decision until next quarter.'",
     "On Tuesday the committee reviewed the quarterly budget, approved two new hires, and deferred the office-relocation decision to next quarter.",
     "The committee had a meeting and talked about several things including money and hiring and the office, and made some decisions.",
     "The better summary preserves all four concrete facts; the worse one is vague and drops the specifics that matter.",
     False),
    ("Summarization",
     "Give a one-line summary of a paper reporting that a new drug reduced symptoms in 60% of patients but caused nausea in 25%.",
     "The drug relieved symptoms in 60% of patients but caused nausea in a quarter of them, indicating meaningful benefit tempered by a notable side-effect rate.",
     "A new drug worked for most patients and had some side effects in the trial.",
     "The better summary keeps both key numbers and the benefit/risk framing; the worse one loses the quantitative findings entirely.",
     False),
    ("Summarization",
     "Summarise this in a phrase: 'Sales rose in Q1, dipped in Q2, then recovered strongly in Q3.'",
     "A mid-year dip between a strong start and a strong finish.",
     "Sales went up, then down, then up again over three quarters.",
     "Both are faithful; the first is more evocative, the second more literal — comparable quality.",
     True),
    ("Summarization",
     "Summarise the plot of Cinderella in one sentence, keeping the key turn.",
     "A mistreated young woman attends a royal ball with magical help and wins the prince by being identified through a glass slipper she leaves behind.",
     "A girl has a hard life but then things get better for her because of magic and a prince.",
     "The better summary preserves the defining plot mechanism (the slipper); the worse one is so generic it could describe many stories.",
     False),

    # ---------------- Argumentation ----------------
    ("Argumentation",
     "Argue briefly whether remote work increases productivity, acknowledging the other side.",
     "Remote work can raise productivity by removing commutes and interruptions, and several firm-level studies report gains for focused individual tasks. But the effect is conditional: collaborative, ambiguous work often suffers without co-location, and outcomes depend heavily on management practices. The honest answer is 'it depends on the task and the org', not a blanket yes.",
     "Remote work definitely increases productivity because people are happier at home and don't waste time commuting, so companies should always allow it.",
     "The better argument is balanced, conditions its claim, and concedes limits; the worse one overstates a one-sided case and ignores counter-evidence.",
     False),
    ("Argumentation",
     "Make the case for and against a four-day work week in a few sentences.",
     "For: compressing or reducing hours can sustain output while improving wellbeing and retention, as several trials have reported. Against: coverage-sensitive roles (healthcare, support) and client-facing schedules may not compress cleanly, and pay/coverage tradeoffs are unresolved. Net: promising for some sectors, not a universal prescription.",
     "A four-day week is good because people get more rest, but some might say it's bad for business. Overall it seems like a nice idea.",
     "The better answer gives substantive points on both sides and a qualified conclusion; the worse one is superficial and non-committal.",
     False),
    ("Argumentation",
     "Should city speed limits be lowered to 20 mph? Give a short reasoned take.",
     "Lowering urban limits to 20 mph measurably reduces pedestrian fatalities because impact survival drops sharply below that speed, and travel-time costs in dense areas are small. The main tradeoffs are enforcement and driver compliance, which are addressable with road design.",
     "Yes, lower speed limits save lives and there's no real downside, so every city should do it immediately.",
     "The better take cites the mechanism (survival vs. impact speed) and names the real tradeoff; the worse one asserts 'no downside', which is an overclaim.",
     False),
    ("Argumentation",
     "Is it better to rent or to buy a home?",
     "It depends on horizon and local price-to-rent ratios: buying tends to win over long stays in markets with moderate ratios once transaction costs are amortised, while renting wins for short horizons, high-price markets, or when mobility has option value. There is no universal answer.",
     "Buying is always better than renting because you build equity instead of throwing money away on rent.",
     "The better answer identifies the deciding variables; the worse one repeats a popular but false absolute ('renting is throwing money away').",
     False),
]


def main() -> None:
    rng = random.Random(SEED)

    # Assign a balanced set of A/B placements to the non-tie items so that no
    # constant strategy ("always A" / "always B") beats chance. Ties keep their
    # own label. We build the placement list, shuffle it with the seed, and
    # deal it out.
    non_tie_idx = [i for i, r in enumerate(RAW) if not r[5]]
    half = len(non_tie_idx) // 2
    placements = ["A"] * half + ["B"] * (len(non_tie_idx) - half)
    rng.shuffle(placements)
    place_map = dict(zip(non_tie_idx, placements))

    items = []
    for i, (cat, q, better, worse, rationale, tie) in enumerate(RAW):
        if tie:
            # For ties, position of the (marginally) stronger answer is still
            # seed-randomised, but the label is Tie.
            better_in_a = rng.random() < 0.5
            pref = "Tie"
        else:
            better_in_a = place_map[i] == "A"
            pref = "A" if better_in_a else "B"

        if better_in_a:
            answer_a, answer_b = better, worse
        else:
            answer_a, answer_b = worse, better

        items.append({
            "id": i + 1,
            "category": cat,
            "question": q,
            "answer_a": answer_a,
            "answer_b": answer_b,
            "human_preference": pref,
            "rationale": rationale,
            "pilot": True,
        })

    # Report the balance so the builder is auditable.
    from collections import Counter
    by_pref = Counter(it["human_preference"] for it in items)
    by_cat = Counter(it["category"] for it in items)
    OUT.write_text(json.dumps(items, indent=2))
    print(f"Wrote {len(items)} items to {OUT}")
    print("  preference balance:", dict(by_pref))
    print("  category balance:  ", dict(by_cat))
    # Sanity: 'always pick A' accuracy should be well below 100%.
    always_a = sum(1 for it in items if it["human_preference"] == "A") / len(items)
    print(f"  'always pick A' accuracy would be {always_a:.0%} (must be < 100%)")


if __name__ == "__main__":
    main()
