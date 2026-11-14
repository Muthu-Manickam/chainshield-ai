---
type: module
status: planned
path: backend/chainshield/nlp/ + ml/nlp/
---
# Text models

**Path:** `backend/chainshield/nlp/ + ml/nlp/`
**Status:** planned

## Purpose
Screen tweets (informative or not) and classify humanitarian category.

## Scope
Train: TF-IDF baseline, BiLSTM, DistilBERT; event-held-out evaluation. Serve: `classify(text)` returns labels, confidence, review flag.

## Related
- [[ADR-006 Keep proposal models]]
- [[ADR-011 CrisisMMD split]]
- [[ADR-013 BiLSTM cascade]]
- [[CrisisMMD]]

## Notes
