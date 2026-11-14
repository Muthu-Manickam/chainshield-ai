# ChainShield AI build plan: deep review

Reviewed 2026-11-15 against the tracker and the proposal. "Measured" means I streamed the public raw file and counted it myself; everything else is cited.

## 1. Verdict

The plan is buildable, but not as written by one builder in 8 weeks. Two of the three datasets check out (DataCo, CrisisMMD). The third, the India–Nepal corpus, is a seven-week-old unreviewed upload whose India half is almost certainly template-generated, so every task built on it (US-03-T05, the reciprocal transfers, most of the "twenty held-out models") should be cut or replaced. The tracker spends about a quarter of its effort on data-readiness ceremony and puts integration last, with core tasks blocked by optional stories. Fix the dependencies, build a stubbed end-to-end skeleton in week 1, drop the cascade and the India files, and the remaining scope fits 8 weeks with one buffer week.

## 2. Research findings

### DataCo Smart Supply Chain

- **Source and licence:** Mendeley Data, Constante, Silva, Pereira, v5, 12 Mar 2019, DOI 10.17632/8gx2fvg2k6.5, CC BY 4.0. https://data.mendeley.com/datasets/8gx2fvg2k6/5
- **Measured from the raw CSV** (sha256 `fa6d022e…0aa6`, 95.9 MB):
  - 180,519 order-item rows, 53 columns, **65,752 unique `Order Id`**. The tracker number is correct.
  - Order dates run 2015-01-01 to 2018-01-31.
  - `Late_delivery_risk` is consistent within every order (0 conflicts). Order-level late rate is 54.8%.
  - The label equals `Delivery Status == "Late delivery"` exactly, and equals `real days > scheduled days` on 97.5% of rows.
  - 2,855 orders are `CANCELED` or `SUSPECTED_FRAUD`; all are labelled 0. The plan has no rule for them.
  - Late rate by `Shipping Mode`: First Class 95.3%, Second Class 76.7%, Same Day 46.1%, Standard 38.1%. A shipping-mode-only rule scores about 69.5% accuracy on all orders (my arithmetic from those rates).
- **Leakage columns:** `Days for shipping (real)`, `Delivery Status`, `Order Status`, `shipping date`, and the realised profit fields (`Benefit per order`, `Order Profit Per Order`, `Order Item Profit Ratio`). PII to drop: customer email, password, names, street.
- **Honest performance:** two independent leak-free projects report ROC-AUC 0.75–0.78 and accuracy 70–73% for LR, RF, XGBoost and LightGBM; the leaky version scores 100%. Both are unreviewed GitHub work. https://github.com/emraankazmi5-coder/dataco-late-delivery-prediction , https://github.com/dave-sm/dataco-supply-chain-analytics
- **Risk:** the model adds roughly 2–3 accuracy points over the shipping baseline. That is the honest finding; plan the write-up around it. One of those projects also argues the data looks partly simulated (unconfirmed).

### CrisisMMD v2.0 (text)

- **Size and labels:** 16,058 tweets, 18,082 images, seven 2017 events (Irma, Harvey, Maria, California wildfires, Mexico earthquake, Iraq–Iran earthquake, Sri Lanka floods). Text informativeness: 11,509 informative, 4,549 not. Text humanitarian (8 classes): other relevant 5,954; not humanitarian 4,549; rescue/donation 3,293; infrastructure 1,210; injured/dead 486; affected individuals 472; vehicle damage 54; missing/found 40. https://huggingface.co/datasets/QCRI/CrisisMMD
- **Licence:** CC BY-NC-SA 4.0 on the Hugging Face card. The original host, crisisnlp.qcri.org, did not resolve from my environment, so I could not read its own terms. Pin a copy in week 1.
- **Tracker's 16,018:** consistent with 16,058 minus the 40 quarantined conflicts. CrisisBench independently reports 16,020 after its filtering. https://ar5iv.labs.arxiv.org/html/2004.06774
- **Tracker's 8,369/3,504/4,145 split: not a published split, and I could not reproduce it.**
  - Official "all" split: 13,608/2,237/2,237 image-text rows (Hugging Face card).
  - Official agreed-label split: informative 8,293/1,573/1,534 text; humanitarian 5,263/998/955 with classes merged to five. https://arxiv.org/pdf/2004.11838
  - The team's "shared view" trains on 52% of the data and is not comparable with the literature. Use the official per-task splits.
- **The two tasks are nested.** Not-informative and not-humanitarian have identical counts (4,549), and the card says one was mapped to the other. Confirm with a crosstab; if it holds, an informativeness → humanitarian cascade makes the same decision twice.
- **Text-only baselines:** CNN on agreed labels scores accuracy 80.8 / F1 80.9 (informative) and 70.4 / 67.7 (humanitarian, 5 classes). https://arxiv.org/pdf/2004.11838

### India–Nepal corpus

- **Found:** "Hierarchical Disaster Tweet Classification Corpus (India + Nepal)", Sinha, Nath, Swain, Mendeley Data, DOI 10.17632/psv6b4zy9f.1, published **22 Sep 2026**, CC BY 4.0. One `dataset.zip` (2.6 MB, sha256 `17f7ee65…f501d`). https://data.mendeley.com/datasets/psv6b4zy9f/1
- **Unverifiable provenance:** no linked paper (the README cites "the paper" without naming it), no institutions, no collection or labelling method.
- **Measured:** seven CSVs, **101,582 rows in total**, which matches the tracker. The eligible counts (50,278/17,670/21,877) are plausible after de-duplication but I did not reproduce them.
- **The four India files (47,000 rows, 46%) look template-generated:**

| Signal | India files | Real files |
|---|---|---|
| Vocabulary | 820–1,213 words over 7,200–17,000 tweets | 7,703 words over 5,778 Nepal tweets |
| Tweets naming a state or city | 98–99% | 1–2% |
| Row counts | 9,200 / 7,200 / 17,000 / 13,600 | irregular |
| Tweet IDs | strictly ascending in file order; each file's whole ID range decodes to under half a second of Twitter time | unordered, spanning days to years |

  Samples differ only in the place slot: "ndrf boat team reach durg chhattisgarh flood rescue" and "ndrf boat team reach agatti lakshadweep flood rescue".
- **The real files are not India–Nepal either.** The flood class is Queensland, January 2013 (56% contain "queensland"); the earthquake class is Nepal, April 2015 (83% contain "nepal"). "Disaster type" is therefore event identity. `NEPALEARTHQUAKE.csv` is almost entirely contained in the type file (5,567 of 5,568 unique texts), and `TweetMasterData.csv` IDs are rounded to 63 distinct values.
- **Consequence:** models on the India files will score near-perfectly and mean nothing; an examiner who opens the CSV will see it. The underlying CrisisNLP/CrisisLex tweets are third-party content the CC BY tag may not cover.

### Model comparisons and cross-event generalisation

- **In-domain, weighted F1 (CrisisBench consolidated English):** informativeness CNN 0.866, fastText 0.844, DistilBERT 0.870; humanitarian CNN 0.829, fastText 0.824, DistilBERT 0.856. https://ar5iv.labs.arxiv.org/html/2004.06774
- **HumAID average over 19 events:** RF 0.700, SVM 0.710, fastText 0.712, DistilBERT 0.769. https://ar5iv.labs.arxiv.org/html/2104.03090
- **BiLSTM:** Dinani and Caragea (2023) find LSTM/BiLSTM below BERT on both tasks; I could not open their tables. https://www.scitepress.org/Documents/2023/121293
- **Out-of-domain:** DistilBERT trained on CrisisLex drops from 0.949 to 0.681 (informativeness) and 0.935 to 0.628 (humanitarian) on CrisisNLP. Leave-one-event-type-out BERT falls from macro-F1 72.5 to 44.1 and accuracy 87.5 to 65.4. https://arxiv.org/html/2111.04052v1
- **Gap:** I found no published leave-one-event-out results on CrisisMMD for these three models.
- **Targets (my estimates from the above):** informativeness macro-F1 about 0.75–0.80 for TF-IDF and BiLSTM, 0.80–0.85 for DistilBERT; humanitarian (5 merged classes) macro-F1 0.55–0.70; expect 5–25 point drops on held-out events. Expect the transformer to win by 3–6 points, not 20.

### RAG targets

- **Recall@5 ≥ 80% on 15–25 documents is easy to hit and hard to prove.** At 30–50 questions the 95% interval around an observed 80% is 63–90% (n=30) to 67–89% (n=50) (Wilson interval, my calculation). The number is also inflated if the builder writes questions while reading the chunks.
- **Grounded claims ≥ 90% cannot rest on an LLM judge alone.** In the TREC 2024 RAG track, GPT-4o matched human support labels on 56% of from-scratch judgments and 72% with post-editing, although system rankings correlated well (Kendall τ > 0.79). https://arxiv.org/html/2504.15205v1
- **Credible measurement:**
  - 60–80 questions, including 10–15 unanswerable ones, written by someone other than the retriever's builder or paraphrased.
  - Gold evidence labelled at section level so re-chunking does not invalidate it.
  - A BM25 baseline, a dev/test split of the questions, and intervals on every number.
  - Faithfulness as supported sentences over total sentences (the RAGAS definition, https://arxiv.org/abs/2309.15217), hand-labelled on at least 100 claims. At 90% observed that gives roughly 83–95%.
  - Abstention rate reported beside it, because abstaining inflates groundedness.

## 3. Story-by-story review

**Cross-cutting**
- There is no story for shared contracts and stubs. Add one and do it first.
- Six "acquisition manifest / checksum / export quality evidence" subtasks per dataset are over-engineering. One hash line per file and one saved split file is what an examiner values.
- The freeze gate (US-08-T03) is a good idea wrapped in ceremony. Replace "authorize" and "immutable" with a tagged commit and a script that scores test once.

**US-01 (shipment risk).** Correct in substance.
- Missing: a rule for the 2,855 cancelled/fraud orders (exclude them); an explicit prediction time (order creation, so `Shipping Mode` and scheduled days are allowed); aggregation rules for multi-item orders (2.75 items per order); PII removal.
- Unnecessary: S02 is a ten-minute check (zero label conflicts); persisting a majority baseline.
- Vague: "fidelity checks and feature interpretation". Replace with: Brier score and reliability plot before and after calibration; SHAP plus a shipping-mode ablation.
- Add: "XGBoost and LR reported against the shipping-mode baseline on ROC-AUC and PR-AUC; expected AUC 0.75–0.78; any AUC above 0.9 triggers a leakage audit."
- Wording: objective O1 says "dispatch-delay"; the label is late delivery.

**US-02 (BiLSTM screening).**
- Use the official split, not 8,369/3,504/4,145.
- Cut T03 (cascade). It depends on US-03-T03, which puts the cheapest model behind the most expensive job, and the tasks are nested.
- Keep the seven event folds; BiLSTM and TF-IDF train in minutes.
- Missing: pretrained embeddings versus random initialisation, class weights, three seeds with mean and deviation, near-duplicate (retweet) handling across splits, and use of the text label rather than the image label.
- Unmeasurable: "Positive recall, cascade false negatives and latency documented". Replace with informative-class recall at a dev-chosen threshold, plus macro-F1.
- "Route unknown domains to review" needs a definition: non-English, under three tokens, or maximum probability below the threshold.

**US-03 (DistilBERT).** The weakest story.
- T05 spends six units preparing a largely synthetic dataset. Drop the India files. Either keep the real files as a labelled limitation or replace the disaster-type task with HumAID, which has 19 real events across four types including the 2018 Kerala floods. Both are proposal deviations; get them approved in week 1.
- "Twenty held-out models" and "19 neural jobs" become meaningless without India. Keep two primary DistilBERT models plus seven humanitarian event folds, with TF-IDF on the same folds.
- Merge or mark unsupported the two classes with 40 and 54 examples, as Ofli et al. did.
- Wrong dependency: T01's CrisisMMD baselines wait on India–Nepal readiness. Decouple.

**US-04 (RAG).**
- Wrong dependency: T01 (source register) depends on US-03-T03 (neural jobs). It depends on nothing; start in week 1.
- Targets need the protocol in section 2. Thirty questions cannot support a dev/test split.
- Missing: definitions of "claim", "citation accuracy" and "evidence gap" (no chunk above a similarity threshold); questions drawn from what the Knowledge Agent will actually ask; cached LLM responses.
- Keep the LLM-only / RAG / validated-RAG comparison; it is the best ablation in the plan.

**US-08 (dashboard and handover).**
- T01 depends on real model artifacts, so the app starts in week 5. Build on stubs in week 1.
- T02 depends on US-06-T04 and T04 on US-07-T03, both optional stories. Optional work must not block core tasks.
- Seven pages is too many; four is enough (Risk, Incidents, Investigation, Evaluation).
- T04's criterion is unclear. Replace with: "fresh clone plus one command reproduces three demos in cached mode in under 15 minutes."

## 4. Missing stories (drafted)

**US-05 | O5/F5 | WS4.** As an operations reviewer, I want one investigation that combines order risk, incident classification and cited guidance, so that I can see what to verify and why, with every step traceable.

| Task | Subtasks | Dependencies | Acceptance criteria |
|---|---|---|---|
| US-05-T01 State, contracts and stubbed graph | Define state and result schemas; build Intelligence, Knowledge, Planning nodes on stub tools; add conditional routes (not informative → stop; low confidence → review) | None | Graph runs end to end on stubs; every node writes a JSON log; three routes covered by tests |
| US-05-T02 Real tools and validator | Swap in risk, NLP and retrieval services; add a deterministic validator (schema, citation IDs exist, no order–incident causal claim); handle provider failure with retry and template fallback | US-05-T01; US-01-T02; US-03-T02; US-04-T02 | Invalid output never reaches the user; LLM outage still yields a templated result; calls cached |
| US-05-T03 Workflow evaluation | Write 30 scripted cases with expected route and required caveats; measure route accuracy, completion, validator catch rate; compare with a single LLM call | US-05-T02 | Route accuracy and completion reported with counts; every failure listed; ablation table produced |

**US-06 (optional) | O6/F6 | WS5.** As an operations manager, I want candidate follow-up actions checked against declared rules, so that I only see permitted options and know why others were rejected.

| Task | Subtasks | Dependencies | Acceptance criteria |
|---|---|---|---|
| US-06-T01 Action catalogue | List 6–10 actions with illustrative cost and approval level; mark all values hypothetical | None | Catalogue reviewed; every value labelled illustrative |
| US-06-T02 Rule checker | Pure-code eligibility function; reasons for each rejection; unit tests | US-06-T01 | 100% of rule tests pass; same input gives same output |
| US-06-T03 Planning integration | Planning node calls the checker; LLM explains but cannot add actions | US-06-T02; US-05-T02 | No action outside the catalogue appears in 30 scripted cases |
| US-06-T04 Scenario comparison | Compare two or three scenarios side by side; record assumptions | US-06-T03 | Each scenario shows eligible and rejected actions with rule IDs |

**US-07 (optional) | O7/F7 | WS4.** As a reviewer, I want a report that separates model output, retrieved evidence and assumptions, so that I can audit each statement.

| Task | Subtasks | Dependencies | Acceptance criteria |
|---|---|---|---|
| US-07-T01 Report template | Fixed sections: risk estimate and top features; incident classification and confidence; cited evidence; assumptions; limits | US-05-T01 | Template renders from stub state with no LLM |
| US-07-T02 Generated narrative | LLM writes section summaries from structured fields only; validator rejects uncited sentences | US-07-T01; US-05-T02 | Every factual sentence carries a source ID or is tagged as assumption |
| US-07-T03 Report check and export | Hand-check 20 reports for unsupported claims; export Markdown/PDF | US-07-T02 | Unsupported-claim rate reported with counts; export works offline from cache |

## 5. Critical path and 8-week order

Critical path: contracts and stubs → stubbed graph and app → DataCo model → CrisisMMD models → RAG index and evaluation → real tools in the graph → scripted-case evaluation → freeze and test → handover.

| Week | Build | Stub first |
|---|---|---|
| 1 | Schemas; stub risk/NLP/retrieval providers; stubbed graph (US-05-T01); four-page app shell; download and hash datasets; DataCo order table and date split; India–Nepal decision approved | All three services, LLM (canned responses) |
| 2 | US-01 baselines, LR, XGBoost, calibration, SHAP; risk service replaces its stub; start RAG source register | NLP, retrieval |
| 3 | TF-IDF on both CrisisMMD tasks with seven event folds; BiLSTM with folds | Retrieval |
| 4 | Two DistilBERT models; seven humanitarian folds; error analysis; NLP service replaces its stub | Retrieval |
| 5 | Chunking, index, retrieval; question set; retrieval evaluation; grounded answers with hand-labelled claims | none |
| 6 | US-05-T02 and T03; minimal US-06 (catalogue and checker) | none |
| 7 | Freeze; score test sets once; three journeys; failure cases; template report | none |
| 8 | Fresh-install run, report, slides, buffer | none |

## 6. Top risks and mitigations

1. **India–Nepal data credibility.** Drop the India files; decide on replacement or limitation in week 1 with supervisor sign-off; state the finding in the report.
2. **DataCo leakage or an unimpressive honest result.** Allowlist features, audit any AUC above 0.9, and present the shipping-baseline comparison as the result.
3. **Integration left to the end.** Walking skeleton in week 1; replace one stub per fortnight.
4. **LLM dependency at demo time.** Cache every call, pin one model, keep a template fallback.
5. **RAG numbers that do not survive questioning.** Independent questions, hand-labelled claims, intervals.
6. **CrisisMMD availability and terms.** Pin a copy now; cite the non-commercial licence; do not redistribute tweets.
7. **Free GPU limits.** Run TF-IDF and BiLSTM on CPU; batch the nine DistilBERT jobs into one saved session.
8. **Over-claiming.** The validator blocks any statement linking an incident to an order.

## 7. What to cut, in order

1. India files and reciprocal transfers.
2. BiLSTM → DistilBERT cascade (US-02-T03).
3. Shared "conservative" CrisisMMD split and checksum manifests.
4. US-07 beyond the fixed template.
5. US-06 beyond catalogue and checker.
6. DistilBERT event folds (keep the TF-IDF and BiLSTM folds).
7. The disaster-type model.
8. RAG configuration comparisons and reranking.
9. Dashboard down to three pages.

Do not cut: the leak-free DataCo evaluation, one honest three-model text comparison, the hand-audited RAG evaluation, and one complete traced investigation.
