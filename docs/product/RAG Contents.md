---
type: product
status: agreed
updated: 2026-11-15
---
# RAG Contents

RAG stores guidance documents ("what should we do"), not orders or tweets. 15-25 documents.

## 1. Public guidance (real documents; candidates to verify and download)
- WFP Logistics Cluster *Logistics Operational Guide*
- FEMA supply chain resilience guidance
- Government guidance on road and bridge inspection after floods and earthquakes
- OCHA / IFRC emergency logistics guidance

## 2. Team-written company procedures (labelled "illustrative")
| Document | Example content |
|---|---|
| SOP-03 Route verification | After infrastructure damage, confirm the route with the carrier within 24 hours |
| SOP-05 Shipment hold | Holding shipments over $10k needs supervisor approval |
| SOP-07 Port disruption | Confirm an alternate port with the carrier |
| Carrier escalation list | Who to call, in what order |
| Approval policy | Which actions need which role |

## How it works
1. Store: admin uploads PDF → split into ~350-token chunks → embedded (bge-small) → saved in Postgres with a citation key like `SOP-03#4`.
2. Search: pgvector meaning search + keyword search together → top 5 chunks.
3. Answer: LLM writes only from those chunks and cites them.
4. Evidence gap: if no chunk is close enough, the app says no guidance was found.

Owner task in the team tracker: US-04-T01 (select 15-25 permitted sources).

## Related
- [[Product Overview]]
- [[ADR-004 Postgres with pgvector]]
