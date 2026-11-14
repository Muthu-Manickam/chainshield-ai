---
type: module
status: planned
path: backend/chainshield/risk/ + ml/risk/
---
# Risk model

**Path:** `backend/chainshield/risk/ + ml/risk/`
**Status:** planned

## Purpose
Order late-risk prediction with explanations.

## Scope
Train: order-level table, leakage allowlist, chronological split, LR + XGBoost, calibration, SHAP. Serve: `predict(order_id)` returns probability + top factors.

## Related
- [[ADR-006 Keep proposal models]]
- [[DataCo]]

## Notes
