# ChainShield AI build plan: deep review

Inputs read: the tracker extract (Sheet 1-3 and Sheet5 stories US-01 to US-04 and US-08), the Group 12 proposal PDF, and `stack-and-modules.md`. I checked the datasets directly. I downloaded DataCo and the India–Nepal corpus from Mendeley and the CrisisMMD split JSONs from Hugging Face, then profiled them with pandas in a scratch folder outside the workspace. Numbers marked "measured" come from that profiling. Numbers marked "estimate" are my own judgement.

## 1. Verdict

The core of the plan can be built: one risk model, one text-screening comparison, one humanitarian classifier, a small RAG, a three-agent LangGraph and a Streamlit app. One determined builder can deliver it in 8 weeks, but only after removing about a third of the tracker's work. The candidates for removal are the checksum and provenance ceremony, the 20 held-out classical models plus 19 neural jobs, the cascade, and the optional US-06/US-07 stories. Two data findings change the design. First, the India half of the India–Nepal corpus looks template-generated. Second, DataCo's markets occupy separate time blocks, so no DataCo order falls inside any CrisisMMD 2017 event window or the Nepal 2015 window. The incident-to-order link therefore has to be an openly labelled simulation. The tracker also has no story for the agents, the event catalogue or the exposure join, which together form the project's integrating feature.

## 2. Research findings

### 2.1 DataCo Smart Supply Chain

| Item | Finding | Source |
|---|---|---|
| Source / licence | Mendeley Data, Constante, Silva, Pereira (2019), DOI 10.17632/8gx2fvg2k6.5, **CC BY 4.0**. The API publishes a SHA-256 for each file, so the team does not need its own checksum manifest. | https://data.mendeley.com/datasets/8gx2fvg2k6/5, `https://data.mendeley.com/public-api/datasets/8gx2fvg2k6` |
| Shape | 180,519 item rows × 53 columns. **65,752 unique `Order Id`** (measured), so the tracker figure is correct. Each order has 2.75 items on average. Label and shipping mode are constant within every order (measured: 0 inconsistent orders). | measured |
| Date range | Order dates run from 2015-01-01 to 2018-01-31. 2018-Q1 is thin (2,123 orders). | measured |
| Label | `Late_delivery_risk` = 1 **exactly when** `Delivery Status` = "Late delivery" (measured crosstab). It equals `real days > scheduled days` on 97.5% of rows. The base rate is 54.8%. | measured; description CSV on Mendeley |
| Leakage columns | `Days for shipping (real)`, `Delivery Status`, `shipping date` (r = 0.996 with real days), and `Order Status` (CANCELED and SUSPECTED_FRAUD always have label 0). `Type` = TRANSFER contains all of those statuses, so it acts as a proxy for the same leak. Also exclude the PII columns: `Customer Email/Fname/Lname/Password/Street`. | measured |
| Scheduled days | Fixed by shipping mode: Same Day = 0, First = 1, Second = 2, Standard = 4. First Class is late 95% of the time. | measured; https://medium.com/@abijahkabiro/when-more-than-half-your-deliveries-are-late-the-data-has-something-to-say-7bc40d995d18 |
| **Market time blocks** | USCA orders run only from 2016-04 to 2017-01 (US orders only from 2016-04 to 2016-08). LATAM ends 2017-06 and Africa covers 2016-08 to 2017-01. After 2017-10 every order is Pacific Asia or Europe. Country names are in Spanish ("Estados Unidos", "México", "Irak"). | measured |
| Honest performance | I fitted order-level gradient boosting on a 70/15/15 chronological split. Majority-class accuracy is 0.55. Shipping mode alone gives AUC 0.73. Pre-dispatch features give **AUC 0.76-0.77, F1 0.70, accuracy 0.72**. Repositories that report about 97% accuracy use the leaky columns. | measured; https://github.com/PolinaBurova/Predicting-Delivery-Delays-in-Supply-Chain |

Flags:
- **The chronological split confounds time with market.** The test block is entirely Pacific Asia and Europe, so the test set never contains a USCA, LATAM or Africa order. US-01-T01-S05 should report the market mix of each split and add one secondary split stratified by market.
- **No real overlap between orders and events.** Inside the event windows I counted 0 orders for Texas during Harvey, Florida during Irma, California during the October 2017 wildfires, Mexico during the September 2017 earthquake, Sri Lanka during the May 2017 floods, Iran during the November 2017 earthquake, and Nepal during April-May 2015. The exposure module must match on region only, or apply a declared date shift, and must mark every result `simulated=true`. The stack doc already calls the link "a labelled simulation"; the data leaves no other option.
- The realistic target is AUC 0.72-0.78 (estimate, based on the measured run above). Any result above about 0.85 should be treated as a leakage alarm.

### 2.2 CrisisMMD v2.0 (text)

| Item | Finding | Source |
|---|---|---|
| Content | 7 events from 2017. Tweets per event (measured): Irma 4,021, Maria 3,995, Harvey 3,992, California wildfires 1,486, Mexico earthquake 1,238, Sri Lanka floods 830, Iraq-Iran earthquake 496. | https://huggingface.co/datasets/QCRI/CrisisMMD |
| Size | 16,058 tweet texts in v2.0. The tracker's **16,018 = 16,058 − 40 quarantined**, which is plausible. CrisisBench reports 16,020 after its own filtering. | HF card; https://arxiv.org/pdf/2004.06774v2 (Table 1) |
| Text labels | Informative 11,509 vs not informative 4,549. Humanitarian has 8 classes: other 5,954, not humanitarian 4,549, rescue/donation 3,293, infrastructure 1,210, injured/dead 486, affected 472, **vehicle 54, missing/found 40**. | HF card |
| Licence | The HF card states **CC BY-NC-SA 4.0**. I could not load crisisnlp.qcri.org (DNS failure), so I have not read the terms page. Do not commit tweet text to a public repo. | HF card |
| Official splits | `datasplit_all` has **11,584 / 2,237 / 2,237 tweets** (measured from the HF JSONs: 18,082 image rows, no tweet in two splits, the same partition for both tasks). The agreed-label split of Ofli et al. has informative text 8,293/1,573/1,534 and humanitarian text 5,263/998/955, with the classes merged to 5. | measured; https://arxiv.org/html/2004.11838 |
| Baselines (text only) | Ofli et al.'s CNN: informativeness accuracy 80.8, F1 80.9; humanitarian (5 classes) weighted F1 67.7. In the test confusion matrix, "affected individuals" gets 0 of 9 correct. | https://arxiv.org/html/2004.11838 |

Flags:
- **8,369 / 3,504 / 4,145 is not an official split.** It matches neither split above, and its 52/22/26 ratio moves about 3,200 tweets out of training. Results on it cannot be compared with published numbers. Use `datasplit_all` (already shared across both tasks) or the agreed-label split.
- **The HF mirror's single `label` field is not the text label.** Its informative counts are 11,121/6,961, which match neither the text counts (11,509/4,549) nor the image counts (9,374/8,708). In 283 tweets the label differs between images of the same tweet. Take `label_text` from the original v2.0 TSVs instead.
- Merge vehicle damage into infrastructure, and missing/found plus injured/dead into affected individuals, as Ofli et al. did. Report macro-F1 and per-class recall.

### 2.3 "India–Nepal Disaster Tweet Classification Corpus"

**Found:** Mendeley "Hierarchical Disaster Tweet Classification Corpus (India + Nepal)" by Sinha, Nath and Swain, DOI 10.17632/psv6b4zy9f.1, **CC BY 4.0**, published 22 Sep 2026, with no linked article ([page](https://data.mendeley.com/datasets/psv6b4zy9f/1), [API](https://data.mendeley.com/public-api/datasets/psv6b4zy9f)). It has 7 CSVs and **101,582 rows in total** (measured, matching the tracker). The tasks are: (1) disaster vs non-disaster; (2) 0/1/2 = non-disaster/flood/earthquake; (3) five `Help` classes: other useful information, donations and volunteering, sympathy and support, food and medicine, infrastructure and utilities. These classes differ from CrisisMMD's taxonomy. The Nepal/CrisisLex half matches Nath et al.'s counts (33,370 / 15,435 / 5,779), and those papers report 92-96% accuracy ([CMC 2026](https://www.techscience.com/cmc/v87n2/66568/TSP_CMC_73486.pdf), [JATIT](http://www.jatit.org/volumes/Vol103No22/8Vol103No22.pdf)).

I reproduced the tracker's eligible counts after text deduplication and conflict removal: relevance **50,278**, type **17,670** (flood and earthquake rows only, which makes the type task binary), humanitarian **21,878** (tracker: 21,877).

Flags (measured):
- **The India half looks synthetic.** Its row counts are round (17,000; 13,600; 9,200; 7,200). Between 24% and 33% of rows end in an appended number, for example "puri puri 94" and "new delhi 22". Removing digits collapses more than 1,000 rows per file. Some India earthquake tweets are copies of Nepal tweets with the place swapped ("dua affected earthquake india delhi stay safe…"). The Help-class proportions are nearly identical in every file (44/18/18/13/6%). Do not present India results as performance on real tweets.
- `TweetMasterData.csv` has 33,368 IDs in scientific notation and only 63 distinct IDs, so deduplication has to use text.
- Tasks overlap across files: 5,567 of the 5,778 Nepal Task-3 texts also appear in the Task-2 file. Grouped splits across tasks are therefore required; the tracker already plans this.

### 2.4 Techniques: realistic NLP targets

- **TF-IDF vs transformers.** On HumAID (all events combined, 10 classes, weighted F1), SVM scores 0.731, fastText 0.744, BERT 0.758 and **DistilBERT 0.758**. Averaged over the per-event models, SVM scores 0.710 and DistilBERT 0.769 ([HumAID Table 7](https://arxiv.org/pdf/2104.03090v2)). Expect DistilBERT to beat TF-IDF by about 2-6 points.
- **BiLSTM.** BERT models beat BiLSTM on every dataset tested in [Springer 2024](https://link.springer.com/chapter/10.1007/978-3-031-68919-2_4). Expect BiLSTM to land between TF-IDF and DistilBERT, or to tie with TF-IDF.
- **Cross-event generalization.** Queensland floods scored F1 80.2 in-domain but only 59.1 when trained on Nepal ([Alam et al. 2018](https://arxiv.org/html/1805.05151v1)). Overfitting to in-domain events is also documented on TREC-IS ([2211.11468](https://arxiv.org/html/2211.11468v1)). Expect a drop of 5-20 macro-F1 points under leave-one-event-out (LOEO). Report the drop as a finding, not as a pass/fail target.
- **Targets (estimate)** on the official CrisisMMD text split: informativeness F1 0.82-0.86 for DistilBERT and 0.78-0.82 for TF-IDF. Humanitarian (5 classes): weighted F1 0.70-0.76, with macro-F1 about 0.55-0.65.

### 2.5 RAG targets

- **Recall@5 ≥ 80%** is easy to reach on 15-25 documents (a few hundred chunks) when the people who wrote the questions also read the documents, so the number can be inflated. To make it credible:
  - Write the questions from the scenarios before indexing.
  - Have someone who did not write a question label its relevant chunks (qrels).
  - Make about 20% of the questions unanswerable.
  - Report a BM25 baseline, which [BEIR](https://arxiv.org/abs/2104.08663) shows is a strong baseline.
  - Report confidence intervals. With n = 40 and p = 0.8, the 95% CI is about ±12 points, so tune on 15 questions and report on the other 25-35.
- **Grounded claims ≥ 90%** is achievable when every answer sentence must cite a chunk, but it is hard to *measure*. RAGAS faithfulness agreed with humans on the easy pairwise WikiEval task ([RAGAS](https://arxiv.org/html/2309.15217v1)). On FaithBench, however, detectors scored about 50% balanced accuracy, and the best judges reached roughly 76-80% ([Vectara/FaithJudge](https://arxiv.org/html/2505.04847v2)). Use an LLM judge only as a screen. Have two people label about 150 claims, and report the result together with Cohen's kappa.

## 3. Story-by-story review

**Cross-cutting.** The tracker and the stack doc disagree. The stack doc removes the BiLSTM cascade and makes India–Nepal optional, but the tracker still has US-02-T03 (cascade) and US-03-T05 (India–Nepal readiness, worth 6 points). Every data-readiness task asks for an "acquisition manifest, license record, checksums". One `DATA_CARD.md` per dataset with the source URL, licence, the SHA-256 that Mendeley already publishes, the row counts and the banned columns is enough. Examiners value a clean comparison table, a sound leakage argument, error analysis and a working demo far more than provenance machinery.

**US-01 (risk).**
- *Correct:* order-level aggregation, allowlist, chronological split, sealed test, majority and shipping-mode baselines.
- *Missing:*
  - A written banned-column list (§2.1).
  - A split-composition table by market.
  - Saved per-order SHAP top-k, which the dashboard and agents need.
  - A `predict(order_id) -> RiskResult` contract in week 1.
- *Vague ACs:*
  - Replace "no outcome leakage" with an automated test that the feature list shares nothing with the banned list.
  - Replace "reproducible test metrics" with a requirement that XGBoost beats the shipping-mode rule on test AUC, with a bootstrap CI.
- *Dependency:* T04 waits on US-08-T03, which in turn waits on US-03-T03 (the 19 neural jobs). The risk model's final evaluation should not wait for NLP, so freeze each module separately.
- *Effort:* T01 is worth 6 points but needs about 2 days.

**US-02 (screening).**
- *Wrong data:* 16,018 with 8,369/3,504/4,145 is a team-made split. Use the official 11,584/2,237/2,237.
- *Contradiction:* T03 is the cascade (it depends on US-03-T03). Turn it into an offline analysis that counts how many humanitarian reports a threshold would suppress, or delete it.
- *LOEO folds:* "Seven event models" is cheap for TF-IDF, but the Iraq-Iran fold has only 496 tweets. For BiLSTM, run 3 grouped folds (earthquake, flood, wildfire), or none.
- *Missing:*
  - The embedding choice for BiLSTM.
  - Class weights.
  - A recall-oriented threshold chosen on dev.
- *Unmeasurable AC:* "Route unknown domains to review" needs a defined test, for example 200 non-crisis tweets with the share routed to review reported.

**US-03 (classification).**
- *Data risk:* T05 depends on the corpus described in §2.3. Make it optional, or keep only the Nepal half with a "synthetic" label on India.
- *Over-engineering:* "Twenty held-out models" and "all 19 neural jobs" add compute without adding insight. Replace them with:
  - 2 primary DistilBERT models (humanitarian, plus informativeness for the comparison in US-02).
  - TF-IDF LOEO on all 7 events.
  - DistilBERT on the 3 type-grouped folds.
- *Wrong dependencies:* T02 (DistilBERT) does not need T01 (TF-IDF baselines).
- *Missing:*
  - The 8→5 class merge decision.
  - A confidence threshold for "low confidence → review", using a temperature-scaled softmax.
  - `classify(text) -> IncidentResult`.
  - A model card.
- *Vague AC:* "without truth claims" should become a requirement that the UI and report label every output as a model prediction, with its confidence shown.

**US-04 (RAG).**
- *Correct:* 15-25 sources, labelled hypothetical SOPs, stable chunk IDs, LLM-only vs RAG vs validated RAG.
- *Wrong dependency:* T01 depends on US-03-T03. The knowledge base has no NLP dependency and can start in week 1.
- *Missing:*
  - The BM25 + dense hybrid named in the stack doc.
  - The blind question and qrels protocol and the unanswerable questions (§2.5).
  - Per-sentence citation in the answer schema.
  - A definition of citation accuracy (the cited chunk supports the sentence).
  - `retrieve()` and `answer()` contracts.
- *ACs:* keep ≥80% and ≥90%, but require CIs and a human audit.

**US-08 (app/integration).**
- *Wrong dependencies:*
  - T01 (dashboard) waits for three finished models. Build it on stubs from week 1.
  - T02 depends on US-06-T04 and T04 depends on US-07-T03, so optional stories block core delivery. Remove both dependencies.
  - T03 couples every module's freeze.
- *Missing:* the scripted scenario set (the stack doc lists 30-50 cases, but no tracker task covers it), CI on stubs, and an offline cached-LLM demo mode.
- *Over-engineering:* "Colab and PowerShell guide" plus fresh-install validation. Choose one supported path (`uv run` locally, plus one Colab notebook).
- *ACs:* make "three complete journeys" measurable as three scripted runs that pass in CI with the cached LLM, with the expected route and outputs asserted.

## 4. Draft missing stories

### US-05: Multi-agent investigation (core)

*As an operations investigator, I want one workflow that classifies an incident, finds possibly exposed orders, retrieves guidance and proposes permitted follow-up actions, so that I get a traceable recommendation with uncertainty and simulated links clearly marked.*

| Level | ID | Item | Dependencies | Acceptance criteria |
|---|---|---|---|---|
| TASK | US-05-T01 | Contracts, state, LLM client (stub-first) | None | Graph runs end-to-end on stubs with no network (cached LLM); schema tests pass in CI |
| SUB | S01 | Pydantic `InvestigationState`, tool I/O contracts | | |
| SUB | S02 | OpenRouter client: pinned model + fallback, temp 0, disk cache, retry once then template, spend cap | | |
| SUB | S03 | Stub risk/NLP/retrieval/rules providers | | |
| TASK | US-05-T02 | Intelligence agent + event catalogue + exposure simulation | T01; US-01-T04, US-02-T04, US-03-T04 (stubs until ready) | Location extraction accuracy reported on 50 hand-labelled tweets; every exposure row has `simulated=true` and states the matching rule |
| SUB | S01 | Call screening then classification tools | | |
| SUB | S02 | Location extraction (NER + gazetteer incl. Spanish DataCo country names) | | |
| SUB | S03 | Event catalogue (7 CrisisMMD events, Nepal 2015) and region/date-shift match → orders ranked by risk | | |
| TASK | US-05-T03 | Knowledge + Planning agents, routing, validator | T02; US-04-T02 | On the scenario set: route accuracy ≥90%; 0 actions outside the catalogue; 100% of recommendations cite ≥1 chunk or state an evidence gap |
| SUB | S01 | Knowledge agent builds query from structured fields, calls `retrieve()` | | |
| SUB | S02 | Planning agent picks from rule-checked actions only | | |
| SUB | S03 | Conditional edges: not informative → stop; low confidence → human review; infrastructure damage → exposure + SOP + plan | | |
| SUB | S04 | Validator: citation and rule checks, else route to review | | |
| TASK | US-05-T04 | Agent evaluation and ablation | T03 | Table: route accuracy, action validity, citation correctness, caveat inclusion, latency, cost vs single-LLM-call and template baselines; 100% of injected failures (empty retrieval, provider error, malformed output) handled without a crash |
| SUB | S01 | Author 30-50 scenarios with expected route/actions/caveats (week 1, before building) | | |
| SUB | S02 | Run graph and both baselines; JSON trace per node | | |
| SUB | S03 | Failure injection and error analysis | | |

### US-06*: Scenario-based mitigation planning (optional)

*As a planner, I want to compare follow-up actions under declared cost, approval and lead-time assumptions, so that I can see which actions are eligible and why others are rejected.*

| Level | ID | Item | Dependencies | Acceptance criteria |
|---|---|---|---|---|
| TASK | US-06-T01 | Action catalogue (YAML, 10-15 actions: verify with carrier, hold, expedite, alternate lane, notify customer…) with cost, lead time, approval role, preconditions, all labelled hypothetical | US-05-T01 | Each action has every field; source of each assumption recorded |
| TASK | US-06-T02 | Pure-Python constraint checker → `Action(allowed, reason, cost, needs_approval)` | T01 | Unit and property tests pass; 0 eligible actions violate a constraint across the scenario set |
| TASK | US-06-T03 | Scenario inputs (budget, approval level, delay tolerance) and comparison view | T02; US-08-T01 | Changing one input changes eligibility as the rules predict (scripted test) |
| TASK | US-06-T04 | LLM explanation restricted to checker output | T02; US-05-T01 | Automated check: explanation names only actions and costs present in checker output |

### US-07*: Explainable generative reporting (optional)

*As a reviewer, I want an exportable report that separates historical risk, classified incident content, cited evidence and assumptions, so that I can audit the recommendation.*

| Level | ID | Item | Dependencies | Acceptance criteria |
|---|---|---|---|---|
| TASK | US-07-T01 | Fixed report schema (four sections + limitations) | US-05-T01 | 100% of reports contain all sections |
| TASK | US-07-T02 | SHAP top-k per order and model-confidence rendering | US-01-T03 | Every number in the report traces to a state field (automated check) |
| TASK | US-07-T03 | LLM narrative from structured fields only, per-sentence citations, template fallback | US-05-T03; US-04-T04 | Human audit of 20 reports: ≥90% of claims supported, 0 simulated links presented as fact |
| TASK | US-07-T04 | Markdown/PDF export | T03 | Export works offline in cached mode |

## 5. Critical path and 8-week build order

Critical path: **contracts and stubs → CrisisMMD text-label readiness → DistilBERT → `classify()` → Intelligence agent → full graph on the scenario set → per-module freeze → sealed tests → report.** The risk model and the knowledge base run in parallel and are not on the critical path.

| Week | Build |
|---|---|
| 1 | Repo, CI, schemas and **stubs for every service**. LangGraph skeleton routing on stubs with a cached fake LLM. Streamlit shell on stubs. Data cards. DataCo banned list. CrisisMMD `label_text` loaded and counts checked against 11,509/4,549. KB source list. **Scenarios and RAG questions drafted blind.** |
| 2 | DataCo order table, chronological split with market table, majority/mode/LR baselines. CrisisMMD official split, TF-IDF for both tasks. KB chunking, BM25 + dense index. Real LLM client and cache. Event catalogue. |
| 3 | XGBoost, calibration, SHAP. BiLSTM informativeness. DistilBERT informativeness and humanitarian on Colab (about 11.6k tweets, max_len 128, 3 epochs). Non-author labels qrels. Location extraction. |
| 4 | Replace stubs with the real risk, classify and retrieve services. Retrieval tuning on dev questions. Planning agent with a minimal rule check. Order Risk and Incident Queue pages on real artifacts. |
| 5 | LOEO (TF-IDF ×7, DistilBERT ×3). Thresholds and abstention. Grounded answer service. Full graph on the scenario set. The three journeys scripted in CI. |
| 6 | Agent evaluation, ablation and failure injection. Investigation, Model Comparison and Run Logs pages. **Freeze per module.** US-06 if on schedule. |
| 7 | Sealed test runs. Human audits of claims and routes. US-07 if on schedule. Fresh-install check. Cached demo mode. |
| 8 | Report, figures, slides, demo rehearsal, buffer. |

## 6. Top risks and mitigations

| Risk | Mitigation |
|---|---|
| India half of the India–Nepal corpus is synthetic; scores look inflated | Make the corpus optional. Use the Nepal half only, or present India as a labelled synthetic transfer test. State the issue in the report. |
| No real order-event overlap; the chronological test set is Pacific Asia and Europe only | Use the simulated exposure (region match or declared date shift, `simulated=true`). Publish the market mix per split. Add a secondary split stratified by market. |
| DataCo leakage (Order Status, Type, shipping date) | Automated banned-list test. Leakage probe: show that the banned features give AUC near 1.0. Treat test AUC > 0.85 as an alarm. |
| Wrong CrisisMMD labels (HF mirror) or a non-standard split | Use `label_text` from the v2.0 TSVs and the official split. Assert the counts in a test. |
| Rare humanitarian classes (40 and 54 tweets) | Merge to 5 classes. Report macro-F1 and per-class recall. |
| Self-authored RAG questions; weak LLM judges | Blind question authoring, qrels from a non-author, unanswerable questions, BM25 baseline, CIs, two-person claim audit with kappa. |
| LLM cost, rate limits, nondeterminism | Pinned model, temp 0, disk cache, spend cap, offline replay for the demo. |
| Late integration | Stubs and CI in week 1. The dashboard and graph run on stubs before any model exists. |
| Colab GPU quota | Small runs (3 epochs, max_len 128). Save checkpoints to the Hub or Drive. Only 2 primary fine-tunes plus 3 folds. |
| Licence (CrisisMMD NC-SA, tweet redistribution) | Keep tweet text out of the public repo. Use the data for non-commercial academic work only. Cite the papers. |

## 7. What to cut if time runs short (in order)

1. India–Nepal experiments, including the flood/earthquake head. Record it as a documented limitation.
2. US-07 generated reports. Keep the structured investigation summary on the Investigation page.
3. Cross-encoder reranking, Langfuse/LangSmith, and Streamlit Cloud deployment (demo locally in cached mode).
4. DistilBERT LOEO. Keep TF-IDF LOEO as the generalization evidence.
5. The US-06 scenario UI. Keep the rule checker inside the Planning agent.
6. The template-pipeline ablation. Keep the single-LLM-call baseline.
7. BiLSTM tuning. Keep one configuration, since BiLSTM is required for the course but not for the product.

Never cut: the leakage controls, the sealed test, the official splits, citations with the evidence-gap path, the scenario-based agent evaluation, and the `simulated` labelling of the incident-to-order link.
