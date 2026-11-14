# SOP-02 Shipment Hold and Release

> Team-authored, illustrative procedure for the ChainShield demo.

## Purpose
A hold stops a shipment from moving further while we confirm that it is safe or sensible to continue. This procedure sets who may place or release a hold and how long a hold may last.

## Roles
- **Logistics Analyst**: proposes and records holds.
- **Operations Supervisor**: approves larger holds and all releases above the analyst limit.
- **Operations Manager**: approves the largest holds.

## When to hold
Consider a hold when the shipment route is Closed or unverified (SOP-01), when the destination warehouse or port is disrupted (SOP-03, SOP-07), or when the order risk score is 0.8 or higher and the cause is not yet understood.

## Approval limits
Value means the total goods value of the shipment, not the freight cost.
| Shipment value | Who may place the hold |
|---|---|
| Up to $10,000 | Analyst, with the Supervisor notified the same shift |
| Over $10,000 and up to $50,000 | Supervisor approval required before the hold |
| Over $50,000 | Operations Manager approval required |

Holds over $10,000 need supervisor approval. Without it the hold must not be applied unless a safety hazard makes immediate action necessary; in that case record the reason and seek approval within 2 hours.

## Steps to place a hold
1. Record the order ID, value, location, reason and expected hold duration.
2. Obtain the approval required by the table above.
3. Instruct the carrier or warehouse to stop movement and confirm in writing.
4. Start the hold clock and notify the customer team so SOP-05 can be started if the delay will reach 24 hours.

## Time limits
A hold is reviewed after 24 hours and may not exceed 48 hours without a fresh approval from the next role up. Holds on perishable or temperature-controlled goods are reviewed every 6 hours.

## Costs (illustrative)
Storage during a hold costs about $35 per pallet per day. Driver waiting time costs about $85 per hour. Include both in the decision to continue the hold.

## Steps to release
1. Confirm the reason for the hold has been resolved, for example the route is classified Open or Restricted with limits the load can meet.
2. Obtain approval from the same role that approved the hold, or higher.
3. Tell the carrier or warehouse to resume, and update the expected delivery date.
4. Notify the customer team of the new date.

## Records
Keep the approval, the carrier confirmation and the release time in the incident record for the review in SOP-08.
