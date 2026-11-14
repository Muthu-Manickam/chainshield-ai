# ChainShield: tech stack and database (chosen from first principles)

Versions, licences and limits were checked on 15 Nov 2026; numbered sources are at the end. Items I could not confirm first-hand are marked *unverified*.

## 1. Summary

One Python 3.12 package, locked with uv, run entirely on the laptop. pandas and Parquet for data; LightGBM with SHAP for late risk; scikit-learn, a PyTorch BiGRU and fine-tuned DistilRoBERTa for tweets (GPU training on Kaggle). Retrieval is local `bge-small` embeddings searched exactly with NumPy plus SQLite FTS5. A minimal LangGraph graph orchestrates three roles calling Claude Haiku 5.5 through the Anthropic SDK, with Pydantic-validated outputs and a deterministic rule checker. **One SQLite file** holds app state, traces, chunks, vectors and the LLM replay cache. Streamlit is the UI. No server, container or cloud service is needed to demo.

## 2. Stack table

| Layer | Choice | Why | Alternative rejected |
|---|---|---|---|
| Language/runtime | Python 3.12 | Floor for SHAP 0.54 and XGBoost wheels [1]; matches the last Colab runtime I could confirm (*Enterprise docs only*) [2]. | 3.14: newer than hosted notebooks, no benefit here. |
| Env/packaging | uv 0.13 + `uv.lock`; Typer CLI (`uv run chainshield …`) | One cross-platform lockfile gives fresh-clone reproducibility; a Python CLI works on Windows, unlike Make. | conda: slower, no universal lock. Poetry: no Python management. |
| Data processing | pandas 3.1 + PyArrow Parquet | 180k rows is small; scikit-learn, SHAP and LightGBM take DataFrames natively; most tutorials. | Polars: faster, but speed is irrelevant at 96 MB and adds a second API to learn. |
| Tabular ML + explainability | LightGBM 4.7, logistic-regression baseline, SHAP `TreeExplainer` | Strong on mixed categoricals, trains in seconds on CPU, exact tree SHAP. | XGBoost: near tie. AutoGluon/deep tabular: hides the evaluation examiners grade. |
| Text, classical | scikit-learn 1.9 TF-IDF (word + char n-grams) + logistic regression | Honest, fast baseline with readable coefficients. | fastText: unmaintained, opaque. |
| Text, recurrent | PyTorch 2.15 BiGRU, trainable embeddings | Same framework as the transformer; about 100 lines. | Keras/TensorFlow: second DL framework for one model. |
| Text, transformer | `distilroberta-base` (82M params, Apache-2.0) [3] with `transformers` 5 `Trainer` | Small enough for free GPU and CPU inference in the demo. | BERTweet: tweet-specific but larger with a custom tokenizer; optional stretch comparison. |
| Training environment | Kaggle notebooks (T4×2/P100, 12 h sessions; ~30 GPU h/week *unverified*) [4]; Colab as backup; CPU models train locally | Kaggle states a quota; Colab publishes no limits [5]. Only safetensors + JSON cross machines, so no pickle version drift. | Paid GPU: unnecessary for 16k tweets. |
| Embeddings | `BAAI/bge-small-en-v1.5` (33M, 384-d, MIT) [3] via sentence-transformers 6.3 | Local, free, deterministic, works offline at query time. | API embeddings: every query needs the network, breaking the offline demo. |
| Vector search | Exact cosine in NumPy over vectors stored in SQLite; FTS5 BM25; reciprocal-rank fusion | A few hundred chunks is a 150 KB matrix; exact search has no index recall error to explain. | See §3. |
| Document parsing | pypdf 7 (BSD) + trafilatura 2.3 (Apache-2.0); parsed JSONL cached | Pure Python, permissive, page numbers for citations. | PyMuPDF: AGPL [1]. Docling: heavy model downloads for 20 files; one-off fallback for table-heavy PDFs. |
| Agent orchestration | LangGraph 1.2 (MIT), control flow only: plain-function nodes, per-node `RetryPolicy`, Mermaid export [6] | Explicit graph with a bounded revise loop after the rule check; diagram goes in the report. | CrewAI: role-play autonomy is hard to make reproducible. Plain Python: close second and the fallback. |
| LLM provider + client | Claude Haiku 5.5 (`claude-haiku-5-5`, $0.10/$0.50 per MTok) [7] via `anthropic` 2.8; Ollama local fallback [8] | My estimate: ~$0.005 per investigation, so 500 runs ≈ $2.50. Model ID is config; a stronger Claude model is one ablation. | Gemini free tier: quotas reported as low as 20 requests/day (*unverified*) [9], and unpaid content may be human-reviewed and used for product improvement [10], which conflicts with the tweet licence. LiteLLM: needless layer. |
| Structured output | Pydantic 2.14 models with `client.messages.parse` [11]; rules in YAML, checked by pure Python | Schema-valid outputs; cost and approval verdicts never depend on an LLM. | Instructor: duplicates what the SDK now does. |
| Caching | `llm_cache` table keyed by request hash; modes `live`/`record`/`replay`; `HF_HUB_OFFLINE=1` | Replay gives an offline, zero-cost, bit-identical demo. | diskcache: pickle-based, last release 2023 [1]. |
| Observability | Own `agent_step` rows, shown in a Streamlit run-log page | The dashboard must display traces anyway; nothing leaves the laptop. | LangSmith/Langfuse cloud: tweet text to a third party. Phoenix: Elastic licence, second UI. |
| App/UI | Streamlit 1.67 (Apache-2.0), `st.navigation` pages [12], Altair + matplotlib | Five views in pure Python calling the package directly. | Gradio: demo-oriented, weaker multipage tables. FastAPI + React: weeks of non-AI work. |
| Testing/quality | pytest 9 (replay mode), ruff, nbstripout, GitHub Actions | Scenario tests are also the agent evaluation; nbstripout keeps tweets out of git. | ragas: LLM-judged, costly, non-deterministic; hand-rolled recall@k/MRR/nDCG instead. |
| Artifact/data storage | Parquet, safetensors, LightGBM text model, metrics JSON; transformer weights in a private Hugging Face repo (100 GB free private) [13] | Git stays small; weights pinned by revision hash. | DVC/MLflow: extra servers and remotes for five models. |
| Deployment/demo | `uv sync` → `chainshield build-db` → `chainshield demo --replay` on localhost; recorded video as backup | Nothing to break on demo day. | Docker: heavy on laptops. Streamlit Community Cloud: public hosting would publish the tweets. |

## 3. Database

**Decision: SQLite only, one file (`chainshield.db`, WAL mode), accessed with stdlib `sqlite3` and a hand-written `schema.sql`. No vector database, no ORM.**

*Files:* raw CSV, tweets and PDFs (git-ignored); cleaned Parquet used for training; model weights; figures. They are large, immutable and read whole. *Database:* everything the app filters, joins or mutates. The DB is a build product, rebuilt from files, except runtime state (reviews, runs).

```sql
orders(order_id PK, order_date, market, region, shipping_mode, sched_days, value, late_actual)
order_risk(order_id FK, model_version, p_late, band, top_factors JSON)
incident(incident_id PK, tweet_id, text, event, split)
incident_label(incident_id FK, model, p_informative, category, p_category)
review_item(review_id PK, incident_id FK, status, reviewer_label, note, updated_at)
document(doc_id PK, title, source_url, sha256)
chunk(chunk_id PK, doc_id FK, ordinal, page, section, text)
chunk_fts            -- FTS5 over chunk.text
chunk_embedding(chunk_id FK, model, dim, vector BLOB)   -- float32, L2-normalised
agent_run(run_id PK, scenario_id, config JSON, git_sha, mode, status, cost_usd, started_at)
agent_step(step_id PK, run_id FK, seq, role, kind, input JSON, output JSON,
           status, error, latency_ms, tokens_in, tokens_out, cache_hit)
retrieval_hit(step_id FK, rank, chunk_id FK, dense, bm25, fused)
proposed_action(action_id PK, run_id FK, text, est_cost, verdict, violated_rules JSON)
report(run_id FK, markdown);  report_citation(run_id FK, claim_idx, chunk_id FK)
llm_cache(key PK, model, request JSON, response JSON)
eval_result(suite, subject, metric, value, config JSON, git_sha)
```

**How vectors and relational data relate.** A vector is just a column of a row keyed by `chunk_id`. At start-up the app loads the matrix into memory, scores `matrix @ query`, fuses with FTS5 ranks, then joins the winning `chunk_id`s to `chunk` and `document` for text and provenance. Every hit is logged in `retrieval_hit`, and report citations are foreign keys, so "every citation points to a chunk that was actually retrieved" is a SQL query and an evaluation metric.

**Why not the others.** sqlite-vec is the natural upgrade, but it is pre-v1 with a breaking-change warning [14] and needs loadable extensions, which not every Python build enables; at this size it buys nothing. Chroma, LanceDB and FAISS add a second store whose IDs must be kept in sync with SQLite. Postgres + pgvector needs a running server, breaking fresh-clone simplicity. DuckDB suits analytics, but its single-writer model fits a UI plus agent runs less well than WAL, and pandas already covers the analytics.

## 4. Deliberately not used

- **LangChain chains, retrievers, model wrappers:** hide prompts and retrieval logic the examiners want to see.
- **Vector DB, Docker, Postgres, FastAPI, React:** production scale that costs demo reliability.
- **Hosted tracing or experiment trackers:** tweets are CC BY-NC-SA and must stay private [15].
- **LLM-judged metrics as headline results:** non-deterministic; use labelled gold sets.
- **LLM for tweet classification or rule checking:** the course requires trained models; rules must be deterministic.
- **`temperature=0` as the reproducibility mechanism:** current Claude models restrict sampling parameters (*from the SDK reference; confirm on first call*); replay is the guarantee.

## 5. Top three risks

1. **Demo-day LLM or network failure.** Mitigation: record all demo scenarios, default to `--replay`, test Ollama fallback weekly, keep a video. Cached responses contain tweet text, so the cache stays git-ignored or the repo private.
2. **Platform friction on a fresh clone.** LightGBM on macOS needs `brew install libomp` [16]; PyTorch ships no Intel-Mac wheels [1]. Mitigation: a `chainshield doctor` preflight command, CI on macOS-arm64 and Windows, documented fallback to scikit-learn `HistGradientBoosting`.
3. **Framework churn and free-GPU limits.** LangGraph releases weekly and Kaggle/Colab quotas can change. Mitigation: commit `uv.lock`, keep nodes as plain functions (a 150-line orchestrator can replace the graph in a day), checkpoint each epoch, and finish transformer training by week 4.

## Sources

1. PyPI package metadata (versions, licences, wheel platforms), e.g. https://pypi.org/project/shap/ , https://pypi.org/project/torch/#files , https://pypi.org/project/PyMuPDF/ , https://pypi.org/project/diskcache/ , https://pypi.org/project/langgraph/
2. https://docs.cloud.google.com/colab/docs/runtimes ; Python lifecycle: https://devguide.python.org/versions/
3. https://huggingface.co/distilbert/distilroberta-base ; https://huggingface.co/BAAI/bge-small-en-v1.5
4. https://www.kaggle.com/docs/notebooks (page did not render when fetched; quota figure from https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
5. https://research.google.com/colaboratory/faq.html
6. https://docs.langchain.com/oss/python/langgraph/use-graph-api
7. https://platform.claude.com/docs/en/about-claude/pricing
8. https://docs.ollama.com/api/anthropic-compatibility ; https://docs.ollama.com/capabilities/structured-outputs
9. https://aistudio.google.com/docs/rate-limits ; third-party report: https://imisofts.com/blog/gemini-api-free-tier-limits/
10. https://aistudio.google.com/docs/terms
11. https://platform.claude.com/docs/en/build-with-claude/structured-outputs
12. https://docs.streamlit.io/develop/api-reference/navigation/st.navigation
13. https://huggingface.co/docs/hub/storage-limits
14. https://github.com/asg017/sqlite-vec
15. https://huggingface.co/datasets/QCRI/CrisisMMD ; CrisisNLP terms (site unreachable when fetched): https://crisisnlp.qcri.org/terms-of-use.html
16. https://github.com/microsoft/LightGBM/blob/master/python-package/README.rst
