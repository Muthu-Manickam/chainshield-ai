---
type: product
status: agreed
updated: 2026-11-15
---
# Product Overview

## Who it is for
The internal operations (logistics) team of a company like DataCo, which sells online and ships worldwide.
Customers never use the app. Orders are historical (DataCo 2015-2018); the app never creates orders.

## Problems it solves
1. About 55% of orders arrive late: the team needs to know which orders are risky and why.
2. Disasters damage roads, bridges and ports: the team must spot the few useful reports among many and know the procedure.

## Users
| Role | Does |
|---|---|
| Analyst | Reviews order risk and incidents, starts investigations, uses the chatbot |
| Supervisor | Approves or rejects actions, watches dashboards, reads reports |
| Admin | Users and roles, guidance documents, action rules, retraining and model promotion |

## Use cases
| # | Who | Question | What the app does |
|---|---|---|---|
| 1 | Analyst | Which orders will be late, and why? | Risk model ranks orders with reasons (SHAP) |
| 2 | Analyst | Which messages matter? | Text model marks useful vs noise |
| 3 | Analyst | What kind of problem is this report? | Labels infrastructure damage, affected people, rescue, ... |
| 4 | Analyst | What is our procedure? | RAG finds it with a citation |
| 5 | Analyst | Help me work through this incident | Agents combine risk, incident and guidance into recommended actions |
| 6 | Supervisor | Should we spend on this action? | Approve or reject actions that need sign-off |
| 7 | Supervisor | What did we decide and why? | Cited report |
| 8 | Anyone | Quick questions | Chatbot answers from data and documents, read-only |
| 9 | Admin | Can the model learn from mistakes? | Analyst corrections → retrain → compare → promote or roll back |
| 10 | Admin | Who can do what? | Users, roles, audit log |

## Typical session
1. Analyst opens Orders, filters high-risk orders, opens one to see the reasons.
2. A report arrives in Incidents already labelled; analyst confirms or corrects (saved for retraining).
3. Analyst clicks Investigate and picks the order scope; agent steps stream live.
4. Supervisor approves the action; a cited report is written.

## Pages
Overview, Orders, Incidents, Investigations, Assistant (chatbot), Knowledge, Models, Admin.

## Related
- [[Incident Tracking]]
- [[RAG Contents]]
- [[Product Assessment]]
- [[Alignment with Proposal and Tracker]]
