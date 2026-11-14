---
type: decision
status: open
date: 2026-11-15
---
# ADR-011 CrisisMMD split

**Status:** open

## Decision
Use the official CrisisMMD text split instead of the tracker's 8,369/3,504/4,145.

## Context
The tracker split matches no published split and drops ~3,200 training tweets; results would not be comparable with published baselines.

## Details
Proposed: official split (11,584/2,237/2,237 tweets) and `label_text` from the original v2.0 files; merge the two rarest humanitarian classes.

## Related
- [[CrisisMMD]]
- [[Text models]]
