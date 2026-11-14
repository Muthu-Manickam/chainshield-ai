---
type: product
status: agreed
updated: 2026-11-15
---
# Product Assessment

Verdict: makes sense as a capstone; as a real product it is a prototype until incidents can be linked to shipments.

## What makes sense
- Real problem; commercial tools exist (Everstream, Resilinc, Interos).
- Each part is useful alone: explained risk scores, noise filtering, cited procedures, approvals, audit trail.
- Human in the loop: AI suggests, supervisor decides.

## Gaps
| Gap | Why it matters |
|---|---|
| Incidents and orders not linked | No DataCo order falls inside any tweet event window; analyst picks orders by hand |
| Tweets are not how companies learn about disruptions | Real teams use carrier notices, port alerts, GDACS/USGS, risk vendors |
| Orders are historical | Nothing in transit to reroute |
| Risk model mostly learns shipping mode | First Class is late 95% of the time; model adds only a few points |

## Three changes to make it hang together
1. Frame it as an "operations control tower prototype"; say the feed is replayed and the analyst picks the orders.
2. Add one real live source (GDACS or USGS alert panel).
3. Labelled what-if link: "assume this incident hits LATAM" → show high-risk orders there, marked simulated.

## Related
- [[Product Overview]]
- [[Alignment with Proposal and Tracker]]
