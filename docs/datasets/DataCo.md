---
type: dataset
licence: CC BY 4.0
---
# DataCo Smart Supply Chain

- Source: https://data.mendeley.com/datasets/8gx2fvg2k6/5
- 180,519 item rows, 53 columns, 65,752 unique orders; orders 2015-01 to 2018-01.
- Label `Late_delivery_risk` equals `Delivery Status == "Late delivery"`. Base rate 54.8%.
- Leaky columns (exclude): `Days for shipping (real)`, `Delivery Status`, `Order Status`, `shipping date`, `Type`, profit fields. Drop PII columns.
- Exclude 2,855 CANCELED / SUSPECTED_FRAUD orders (always labelled 0).
- Honest performance: AUC about 0.75-0.78; shipping mode alone about 0.73. AUC above 0.85 means leakage.
- Markets sit in separate time blocks; a chronological test set is Pacific Asia + Europe only.
- No orders fall inside any CrisisMMD or Nepal event window. See [[ADR-012 Incident-to-order link]].
