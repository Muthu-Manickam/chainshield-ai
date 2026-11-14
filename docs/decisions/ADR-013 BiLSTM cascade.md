---
type: decision
status: open
date: 2026-11-15
---
# ADR-013 BiLSTM cascade

**Status:** open

## Decision
How to use BiLSTM screening before DistilBERT classification.

## Context
The informativeness and humanitarian tasks are nested in CrisisMMD, so a live cascade repeats the same decision and compounds errors.

## Details
Proposed: keep BiLSTM as a compared model and run the cascade as an offline analysis of suppressed reports only.

## Related
- [[Text models]]
