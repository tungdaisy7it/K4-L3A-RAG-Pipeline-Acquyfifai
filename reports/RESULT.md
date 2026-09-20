# RAG Evaluation Results — Đà Nẵng Tourism Assistant

## Executive summary

The delivered system includes dense retrieval, BM25, RRF fusion, grounded generation, citation labels and a Streamlit demo. The automated repository checks pass. The four generation metrics are intentionally marked as not measured because the handoff environment has no configured LLM provider/model; no evaluation numbers are invented.

## Run information

| Field | Value |
|---|---|
| Evaluation date | 2026-09-20 |
| Framework/version | Ragas 0.4.3 declared in `pyproject.toml`; repository tests use pytest |
| Evaluator model | Not configured in handoff environment |
| Generator model | Not configured in handoff environment |
| Embedding model | `BAAI/bge-m3` |
| Corpus | 44 standardized Markdown documents: legal/policy and tourism content |
| Corpus version | Retrieval implementation commit `4178d12`; record the final corpus commit when running the official benchmark |
| Golden dataset size | 15 cases |
| `top_k` | 5 |
| Fallback threshold | `0.61`; calibration midpoint `0.611638`, balanced accuracy 100% on the reported 353-chunk calibration pool |
| UI smoke test | Streamlit started successfully on a local port |

## Configurations

- **Config A — dense-only:** `retrieve(query, top_k=5, use_reranking=False)`. Uses the dense result list and the shared threshold.
- **Config B — hybrid + RRF:** `retrieve(query, top_k=5, use_reranking=True)`. Combines dense and BM25 rankings once with RRF.

Both configurations must use the same 15-question dataset, prompt, generator, evaluator, embedding model and `top_k`. Only retrieval strategy changes.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
|---|---:|---:|---:|
| Faithfulness | Not measured | Not measured | Not calculated |
| Answer relevance | Not measured | Not measured | Not calculated |
| Context recall | Not measured | Not measured | Not calculated |
| Context precision | Not measured | Not measured | Not calculated |
| **Average** | Not measured | Not measured | Not calculated |

Latency and cost are also not reported because no real provider call was available during handoff. The threshold calibration is retrieval evidence only; it is not a generation score.

## A/B comparison

No configuration can be declared the winner until the same generator and evaluator produce per-case outputs for both runs. Config B is the intended production candidate because BM25/RRF adds exact-keyword evidence for names and policy terms, while Config A remains the clean dense baseline. The trade-off is extra lexical retrieval work and a small retrieval-latency increase; LLM cost should remain comparable when context size is fixed.

## Worst performers to verify

These are test cases requiring focused inspection, not fabricated metric results.

| # | Case | Likely failure stage | Verification |
|---:|---|---|---|
| 1 | Exact name: `My Son Sanctuary` | Retrieval | Compare dense top-5 with BM25/RRF and verify `article_07` appears. |
| 2 | Three-day, two-night Da Nang itinerary | Retrieval/generation | Check multi-chunk recall from `article_21` and citation coverage for each itinerary claim. |
| 3 | Out-of-domain Linux/kernel panic question | Safety/generation | Confirm weak evidence leads to safe refusal rather than an unsupported answer. |

## Recommendations

| Priority | Action | How to verify |
|---:|---|---|
| 1 | Configure one real provider/model and run both retrieval configurations on the same golden set. | Save per-case answers, sources, four Ragas metrics, model name and token usage. |
| 2 | Add exact-name and policy-keyword retrieval slices. | Compare hit@5 and context precision for dense-only versus hybrid + RRF. |
| 3 | Add citation-map and out-of-domain refusal assertions. | Every `[Ck]` in an answer must map to a returned source; weak OOD queries must refuse. |
| 4 | Record stage latency and cost. | Measure retrieval, provider latency and tokens for the same batch and environment. |

## Reproducible commands

From the repository root on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest tests/test_contracts.py -q
pytest tests/test_acceptance.py -q
pytest -q
streamlit run app.py
```

The UI works without an API key: it shows a safe refusal when no provider is configured. For grounded answers, copy `.env.example` to `.env`, set `LLM_PROVIDER`, `LLM_MODEL` and the matching local API key, then restart Streamlit. Never commit `.env`.
