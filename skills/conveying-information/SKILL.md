---
name: conveying-information
description: "Create, simplify, restructure, or review a data deck, slides, readout, report, one-pager, or findings doc for a product or leadership audience (\"make this clearer for the product team\") so the first pass stands alone without narration. Pairs with visualize-data for charts."
---

# Conveying information

Make the first pass understandable without narration. Help the audience say what happened, to whom, when, why it matters and what decision follows. Treat a page as a slide or a report section built around one finding.

## Record the evidence before drafting

Write one row per claim in a working ledger so wording and design cannot silently change its meaning.

| Record | Include |
|---|---|
| Claim | A plain sentence stating the finding |
| Measure | Metric definition, outcome, numerator and denominator |
| Population | Who qualifies, exclusions, selection filters and sample limitations |
| Period | Observation dates, comparison windows and eligibility to reach the outcome |
| Source | Query or file with a precise location and data date |
| Evidence status | Observed, associated, assumed or unknown |
| Related claims | Shared definitions, different populations and limits on comparisons |

Carry each claim's evidence status into its wording. State observations directly, describe associations without implying cause, label assumptions and say what is unknown. For example, "Members who watched tutorials renewed more often" supports an association. It does not establish that tutorials caused renewal.

## Decide the story before layout

- Order sections by consequence to the audience, highest impact first. Establish the evidence before asking for action so readers can judge the decision.
- Give each page one finding or investigation and its product consequence. Storyboard the takeaway, why it matters and what remains unknown before designing. Split pages that ask readers to reconcile unrelated results.
- Remove unrequested housekeeping pages, test-order lists and standalone lists of open questions. Put an unresolved question beside the finding it limits so uncertainty has a clear purpose.
- Answer direct questions on the relevant page, including the limits of the answer. For example, "We have no representative measure of customer priorities. Four of six interviewees named speed." Preserve the useful evidence without generalizing from a small sample.

## Write pages that stand alone

- Write a literal headline someone could say aloud, naming the subject and result. Include the number for a quantitative finding. For example, "47% of monthly buyers reach a third payment" gives readers a measurable outcome.
- Keep each headline to one population unless comparing groups is the point. Name both groups when comparing them, and put selection limits in the headline when they change who the result describes. Trial conversion and third-payment attainment among buyers need separate findings because their denominators differ. Before finalizing, check every headline number against the ledger and confirm the numbers share one denominator. Rewrite or split any headline that mixes denominators, such as a share of clicks beside a share of builders.
- Give each comparison's periods beside its measures. Include different windows in the headline if readers would otherwise assume they match. For example, "Users fell 15% year over year, while buyers fell 26% from winter to spring."
- Name all supported contributors when explaining a change, and leave unsupported causes unknown. A before/after comparison alone cannot isolate a product change from other changes. For example, attribute lower revenue per buyer to both plan mix and regional mix when both contribute.
- Label each chart directly above the visual with its subject and relevant time dimension. Use readable sentence case and plain black text on light backgrounds. "Paying members over time" tells readers what they are looking at. Remove section eyebrows that add no information.
- Keep supporting body copy to 25 words total per slide across one or two short lines that add interpretation the visual does not provide. In the final pass, delete every body sentence that restates the headline, a label or the visual so readers get only added meaning.
- Keep each footer to eight words or fewer naming the report or system and date. File paths and query names belong in the ledger, never on the slide. Keep a caveat only if it changes the reading, in one short sentence beside the claim, once. Cut other caveats so essential context survives skimming.
- End with a supported implication, decision or concrete test. Name the action and success measure when proposing a test. Replace "explore retention" with "Test a pause option and compare 60-day paid revenue." Leave the intervention unresolved when the evidence only identifies a problem.

## Choose visuals that answer the question

Use `visualize-data` to build charts. Make these decisions before rendering.

- Match the measure to the question. Use rates to compare risk when the base changes, and counts to describe volume. Define the rate's denominator and annotate billing or collection artifacts that distort the trend. Rising cancellations can reflect a growing customer base even when cancellation risk stays flat.
- Show the net consequence beside its components so readers do not have to calculate the impact. For example, show buyer volume, revenue per buyer and total revenue per day together when evaluating a price change. Use comparable windows and retain caveats about the before/after comparison.
- Choose the simplest comparison with a clear baseline. Replace splits that require cross-checking with directly labeled outcomes. For example, "Out of every 100 trials: paid, finished and left, other unpaid" makes mutually exclusive outcomes readable.
- Label groups, outcomes and windows literally. For example, "Regional-card buyers on USD plans" identifies the group that "USD prices" hides. Keep one period per chart unless comparing periods is the point.

## Ground recommendations and opportunity sizing

- Verify current product behavior before proposing a change. Name the proposed before/after, location, eligible audience and supporting source. "Offer annual at signup" is empty if annual is already there. Establish why buyers overlook or reject the existing offer before choosing a change.
- Separate scenario arithmetic from evidence about an intervention's effect. Putting a revenue scenario beside a copy proposal implies copy can deliver that gain. Show value per unit of metric movement and state that the achievable movement remains unknown until tested.
- Explain opportunity arithmetic literally. State the affected buyers or payments, incremental value per unit and time horizon, plus assumptions such as fixed buyer volume. For example, "400 buyers switching plans each add $180 in first-year revenue" exposes the mechanism for checking.
- Label scenario ranges as assumptions so readers cannot mistake them for uncertainty intervals or forecasts. For example, "Assuming a 1 to 3 percentage point increase" states which inputs were chosen.

## Check the complete artifact

1. Preserve evidence through copy edits. When delegating deck or report copy edits to a collaborator or a writer from a different model family, give them the ledger's exact numbers, populations and arithmetic, and have the lead merge and check the rewrite against it to restore any essential comparisons, facts or evidence lost during simplification.
2. Have an independent analyst or reviewer audit every headline, number, qualifier, explanation and caveat against sources. Prefer a reviewer from a different model family than the copy author when using models. Assign each claim a verdict of verified, wrong, unsupported or misleading, with a source location. Check selected populations, alternate metric definitions and filters, adjacent-page consistency and scenario arithmetic. Resolve flags against evidence before dismissing them. A caveat such as "including cancellations removes the gap" needs the same proof as a headline.
3. Render and inspect every page at its intended viewing size. Check fit, readability, chart scales and baselines, labels, references and whether the visual supports the headline. Dense qualifications that technically fit can still make a page unreadable.
4. Give the rendered artifact to a cold reader who has no analysis history or narration. Ask them to paraphrase what happened, to whom, when, why it matters and what decision follows. Have them read awkward sentences aloud. Rewrite any page that needs a second reading, another page or an explanation to avoid a misleading interpretation.
5. Show the rendered first pass to the user as soon as these checks pass. State any remaining verification gap in one line so the user can judge what is ready to rely on.
