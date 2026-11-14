---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-006 Keep proposal models

**Status:** accepted

## Decision
Keep XGBoost, BiLSTM and DistilBERT as named in the proposal.

## Context
Changing them (LightGBM, BiGRU, DistilRoBERTa were suggested) needs supervisor approval for little gain.

## Details
XGBoost + Logistic Regression baseline + SHAP; TF-IDF baseline, BiLSTM, DistilBERT for text.

## Alternatives rejected
LightGBM, BiGRU, DistilRoBERTa (from the from-scratch stack reviews).

## Related
- [[Risk model]]
- [[Text models]]
