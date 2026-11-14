# SOP-01 Route Verification After Infrastructure Damage

> Team-authored, illustrative procedure for the ChainShield demo.

## Purpose
This procedure confirms that a planned route is still usable after a flood, earthquake, storm or other event damages roads, bridges, rail lines or tunnels. It applies to every in-transit and scheduled shipment whose lane crosses the affected area.

## Roles
- **Logistics Analyst**: runs the verification and records the result.
- **Carrier Account Manager** (at the carrier): confirms the route in writing.
- **Operations Supervisor**: approves any route marked Restricted or Closed.

## Trigger
Start this procedure when an incident of severity Medium or higher is logged within 50 km of a lane in the shipment plan, or when a public road authority reports a closure on a lane we use.

## Steps
1. **List affected shipments (within 1 hour).** Query open orders whose route intersects the incident area. Record order ID, carrier, current position and promised delivery date.
2. **Contact the carrier (within 4 hours).** Phone the carrier dispatcher, then follow up by email. Ask which road segments, bridges and border crossings are open, and whether trucks are being diverted.
3. **Cross-check public sources.** Compare the carrier answer with the national or state road authority bulletin and any bridge inspection notice. If the two disagree, the more restrictive answer wins until resolved.
4. **Obtain written confirmation (within 24 hours).** The carrier must email the confirmed route, any weight or height limits, and a revised transit estimate. Without this the route stays unverified.
5. **Classify the route.**
   - *Open*: no change, resume normal tracking.
   - *Restricted*: usable with limits or delays of up to 24 hours.
   - *Closed*: not usable; go to SOP-06 for expedite and re-route rules.
6. **Re-verify.** A Restricted route is re-checked every 12 hours. A Closed route is re-checked every 24 hours until reopened.

## Cost guidance (illustrative)
A detour typically adds about $450 per truck per 100 km of extra distance. Waiting at a closed crossing costs about $85 per truck per hour in driver and equipment time. Record these in the incident note so the Supervisor can compare options.

## Escalation
If the carrier has not replied within 4 hours, escalate using the order in SOP-04. If the route cannot be verified at all within 24 hours, treat it as Closed.

## Records
Store the carrier email, the road authority bulletin and the classification in the incident record. The classification, time and analyst name are mandatory. The incident review in SOP-08 reads this record.
