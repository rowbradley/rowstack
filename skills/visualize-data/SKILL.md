---
name: visualize-data
description: Choose, build, revise, and verify quantitative charts for inline answers, reports, dashboards, notebooks, and exported figures. Use when a comparison, distribution, relationship, or movement benefits from a visual. Keep analytical validation distinct and select the renderer from the requested output.
---

# Visualize data

Make the comparison clear and keep every displayed claim traceable to reviewed data. Keep analytical and methodological validation distinct from chart construction.

## Start from the question

Before plotting, identify the reader's decision, comparison, population, observation grain, window, denominator, and units. State whether the inputs are observations, estimates, targets, or scenarios.

Keep a compact authoring note with the question, supported takeaway, chart family, source, relevant uncertainty, and delivery surface. Reuse an existing analysis note. Keep authoring notes out of the reader's report unless they affect interpretation.

Use actual source rows. Trace an important claim to its query or calculation rather than treating a report or prior validation label as proof. Keep missing observations distinct from zero. Combine rates using valid numerators and denominators, not an unweighted mean of percentages.

When evidence is sparse, use a form that fits it. A few periods can support grouped bars or a slope chart. Query more history only when it changes the answer. Ordered exposure buckets are categories, not evenly spaced time or evidence of a within-person trajectory.

## Choose the chart

| Comparison | Useful starting form | Decision that changes the form |
|---|---|---|
| Values across categories | Bar or dot | Horizontal for long labels. Sort unless order carries meaning. |
| Movement over time | Line | Use comparable units and enough observed history to reveal the relevant pattern. |
| Composition | Stacked bar or area | Parts must be exclusive and additive. Use lines when individual trajectories matter more. |
| Ranking or concentration | Ranked bar, compact leaderboard, or Pareto | Keep top-N previews short. Use a table for long-tail lookup. |
| Distribution | Histogram or box plot | Histogram for shape, box plot for group comparisons. |
| Two numeric measures | Scatter | Retain point identity, observation grain, and useful volume context. |
| Estimate with uncertainty | Dot and interval, or line and band | Identify the interval's meaning and level. |
| Cohort matrix | Heatmap | Use one quantitative scale and distinguish structural zero from missing data. |
| Additive contributions | Waterfall | Drivers must reconcile to the total. Otherwise use ranked bars. |
| Ordered progression | Stage bars or funnel | Stages must belong to one coherent population and sequence. |

Use tables when exact lookup is the reader's task. Do not force chart variety or choose a chart to satisfy a renderer's menu.

## Select delivery once

Respect the user's selected surface and the active host's delivery tools. Keep chart judgment separate from platform setup.

- **Inline answer.** Use the host's supported inline visualization surface. When the host provides inline HTML preview and rendering tools, deliver self-contained HTML with clean theme styling, responsive layout, and inspectable source notes. If the host provides a dedicated inline chart renderer, follow its instructions. Do not impose a report application on a short answer.
- **Data report or dashboard.** When an existing dashboard framework or report contract owns the artifact, follow its component and data-binding conventions. Preserve reviewed rows, source inspection, stable authored chart or query IDs, and supported filters.
- **Static figure, notebook, slide, or export.** Use a reproducible local plotting library (such as Matplotlib, Seaborn, ggplot2, or Vega-Lite) appropriate to the selected output. Export the requested format and inspect it in the actual destination. A portable static HTML document can embed PNG figures; retain SVG or vector PDF when required for export quality.
- **Existing BI application.** Use its governed measures and native chart controls. This skill supplies selection and visual QA.

Resolve unavailable rendering capabilities once. Continue with another suitable surface only within the user's requested outcome. Do not install dependencies, create an application, publish, or change saved source preferences solely to render a chart.

## Make the evidence readable

- Use aligned position or length for precise comparisons. Absolute-magnitude bars start at zero. Disclose focused scales used for changes or estimates.
- Keep units, periods, ordering, and scales consistent across comparable panels. Identify independent scales explicitly.
- Make the title factual. Put a supported interpretation in adjacent prose when useful. Put essential population, period, units, and denominator beside the chart.
- Retain volume or sample context when its absence could mislead. Never label repeated event density as unique-person conversion.
- Show material uncertainty beside the estimate. Preserve asymmetric bounds and identify their method and level. Use a visible bounds table if the renderer cannot express them faithfully.
- Use uncertainty supported by the analysis. Repeated observations may need person-clustered inference. Event density is not automatically a binomial probability. Scenarios are not confidence intervals.
- Prefer one non-neutral color for a simple comparison, two for a focal group and comparator, and a limited stable palette when category identity matters. Declare colors explicitly.
- Distinguish series through direct labels, line style, marker shape, open fill, or faceting as well as color. Preserve meaningful domain states.
- Keep labels readable. Remove redundant ticks or abbreviate with accessible full labels rather than shrinking type. Reserve space for long labels, negative values, and annotations.
- Keep grids and borders quiet. Omit decorative gradients, repeated legends, and annotations that compete with the data.
- Keep group membership fixed where the comparison requires it. Do not sum overlapping categories or combine them into Other without a valid additive denominator.

## Verify the delivered view

Recompute consequential values from the selected inputs. Check the displayed binding after filters and transformations, including denominators and missing-data behavior.

Render the actual artifact at its normal and narrow widths. Check marks, labels, axes, legends, annotations, and export completeness. Use the host's preview or an isolated headless browser. Preserve useful distinctions in grayscale and under relevant color-vision limitations.

Exercise any authored filter. Marks, counts, captions, caveats, inspected rows, and exports must describe the same selected population. Keep uncertainty visible through filtering and export.

Report the supported takeaway, source, material caveat, and any unavailable check. Separate arithmetic verification from methodological validation and causal interpretation. Finish when the requested chart answers its question and the relevant checks pass.
