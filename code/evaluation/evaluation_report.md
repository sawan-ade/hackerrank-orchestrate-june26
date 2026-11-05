# Operational Analysis & Evaluation Report

This report summarizes the performance, cost, token usage, and rate-limiting strategy for the Multi-Modal Evidence Review System implemented for the HackerRank Orchestrate challenge.

---

## 1. Workload Summary

| Metric | Sample Dataset | Test Dataset (claims.csv) |
| --- | --- | --- |
| **Number of Claims** | 20 | 44 |
| **Number of Images** | 27 | 66 |
| **Stage 1 (Vision) API Calls** | 27 | 66 |
| **Stage 2 (Logic Checker) API Calls** | 20 | 44 |
| **Total API Calls** | 47 | 110 |

---

## 2. Token Usage Estimates

- **Vision Call (Stage 1):**
  - Input: ~1,500 tokens (System prompt & context) + ~85 tokens (base image) + ~680 tokens (4 tiles for 1024px resized image) = **~2,265 tokens**
  - Output: **~200 tokens** (Structured JSON report)
- **Logic Checker Call (Stage 2):**
  - Input: ~1,500 tokens (System prompt) + ~800 tokens (conversation transcript, history details, vision reports, checklist) = **~2,300 tokens**
  - Output: **~300 tokens** (Structured JSON claim decision)

### Total Estimated Tokens for Full Test Set (110 calls)
- **Input Tokens:** 110 calls × ~2,300 tokens = **~253,000 tokens**
- **Output Tokens:** 66 vision calls × 200 + 44 logic calls × 300 = **~26,800 tokens**

---

## 3. Cost Projection & Pricing Assumptions

We assume standard Google AI Studio Pay-As-You-Go pricing for the Gemini Flash family (e.g. Gemini 1.5 Flash / Gemini 2.5 Flash):
- **Input Tokens:** $0.075 / 1 million tokens
- **Output Tokens:** $0.300 / 1 million tokens

### Cost Calculations
- **Input Cost:** 253,000 tokens × ($0.075 / 1M) = **$0.019**
- **Output Cost:** 26,800 tokens × ($0.300 / 1M) = **$0.008**
- **Total Operational Cost:** **$0.027**

*Note: Under the Free Tier, the actual cost is $0.00.*

---

## 4. Latency & Runtime

- **Throttling Interval:** A global `MIN_CALL_INTERVAL` lock enforces **13.0 seconds** between all API calls to comply with the 5 RPM Free Tier rate limit.
- **Estimated Total Latency:**
  - 110 total calls × 13.0s = **~24 minutes** total execution time for the full test set.

---

## 5. Rate Limits & Quota Mitigation Strategy

1. **RPM (Requests Per Minute) Throttling:**
   - Enforced a global asyncio lock in `utils.py` that serializes all API requests across all concurrent tasks.
   - Enforced a 13-second sleep between requests to guarantee we never exceed 5 RPM.
2. **RPD (Requests Per Day) Model Rotation:**
   - Since free tier models have a limit of 20 requests per day per project, we implemented a **Self-Healing Model Rotator**.
   - The rotator cycles through available models (e.g. `gemini-flash-lite-latest`, `gemini-2.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.1-flash-lite-preview`, `gemma-4-26b-a4b-it`, `gemma-4-31b-it`).
   - If a model throws a 429 daily quota exceeded error, the rotator instantly switches to the next model in the list and retries the call.
3. **Stage Merging Optimization:**
   - Combined Stage 2 (Evidence Checker) and Stage 3 (Risk & Decision) into a single Stage 2 logic call.
   - This architectural change reduced the total number of required API calls by **~30%**, saving significant quota and latency.
4. **Image Resizing:**
   - Resized all images to a maximum of 1024px on the longest dimension, reducing visual tiles and token counts.
