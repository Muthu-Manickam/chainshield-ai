---
type: product
status: agreed
updated: 2026-11-15
---
# Incident Tracking

Incidents are not live. They are replayed from a labelled dataset, then tracked through statuses.

## Sources
| Source | How | Real? |
|---|---|---|
| Replay feed (main) | ~15% of CrisisMMD tweets held back from training, released into the queue a few at a time | Real 2017 disaster tweets, replayed |
| Manual entry | Analyst pastes a message (email, call) | Whatever is typed |

## Lifecycle (`incidents` table)
| Status | Meaning | By |
|---|---|---|
| `new` | Arrived | System or analyst |
| `classified` | Model labelled it with confidence | signals |
| `needs_review` | Low confidence or too short | signals |
| `reviewed` | Analyst confirmed or corrected (saved for retraining) | Analyst |
| `investigating` | Investigation started | Analyst |
| `awaiting_approval` | Agents proposed actions needing sign-off | assistant |
| `actioned` / `closed` | Decided and reported, or closed as not useful | Supervisor or analyst |

Each row stores source, model version, confidence, reviewer, timestamps and linked investigation.
Human actions also go to `audit_log`.

## Optional live sources (later)
| Feed | Gives | Catch |
|---|---|---|
| GDACS alerts | Live floods, cyclones, earthquakes | Structured, not text |
| USGS earthquakes | Live quakes | Structured, not text |
| ReliefWeb API | Situation reports | Long text, not tweets |
| X API | Live tweets | Paid, limited |

Recommendation: keep replay + manual for the capstone; add GDACS as a separate "live alerts" panel if time allows.

## Related
- [[Product Overview]]
