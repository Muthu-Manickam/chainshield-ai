# SOP-06 Expedite and Re-route Decision Rules

> Team-authored, illustrative procedure for the ChainShield demo.

## Purpose
When a disruption threatens an order, we can wait, re-route over another path, or expedite using a faster mode. This procedure gives simple rules to choose, so decisions are consistent and costs are controlled.

## Roles
- **Logistics Analyst**: calculates options and recommends one.
- **Operations Supervisor**: approves mid-size spend.
- **Operations Manager**: approves large spend.

## Inputs
Gather before deciding: order value, order risk score, customer tier, promised date, current route status (SOP-01), and quotes from the carrier for each option.

## Decision rules
1. **Wait** if the expected extra delay is under 24 hours and the order is not perishable. Apply SOP-05 only if it grows.
2. **Re-route** if the original route is Closed or the delay is above 48 hours, and a verified alternative adds less than 20% to transit time. The carrier must confirm the new route in writing.
3. **Expedite** if the order risk score is 0.7 or higher and the order value is at least $5,000, or if the customer is Platinum, or if goods are perishable or time-critical. Typical expedite methods are air freight, a dedicated truck, or a team driver.
4. **Split the order** if only part of it is urgent. Expedite the urgent items and send the remainder normally.
5. If two options meet the rules, choose the one with the lower total cost including late-delivery penalties.

## Costs (illustrative)
Air freight costs about $2.10 per kg more than road. A dedicated truck costs about $1.80 per km. A late-delivery penalty under contract is typically 2% of order value per day. Expedite only when the expedite premium is below the expected penalty plus lost-customer cost.

## Approvals
| Extra cost of chosen option | Approver |
|---|---|
| Up to $2,000 | Analyst |
| $2,001 to $10,000 | Operations Supervisor |
| Over $10,000 | Operations Manager |

If the cost is not yet firm, the quoted maximum is used for approval.

## Steps
1. Calculate the cost and time of each option.
2. Recommend one using the rules above.
3. Obtain the approval from the table.
4. Instruct the carrier and obtain written confirmation.
5. Notify the customer using SOP-05 and, if a shipment hold is in place, release it under SOP-02.

## Records
Record the options considered, the rule applied and the approver. Compare actual and quoted cost in the incident review (SOP-08).
