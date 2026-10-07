# Example: a style-match proposal and the recorded decision

Synthetic. The owner, the study, and the features below are invented.

**Owner:** Ben, who owns three physiotherapy clinics. Approver for the style choice: Ben.

## The proposal as sent

Project: `SYN-PROJ-031` · Short-form vertical · Study `OS-SYN-014` · Blueprint `SB-SYN-014` v1
Evidence depth: `owner_supplied_reference` · References studied: 3 from 3 accounts

**What the study found.** The outliers studied share these features, and the contrast set does not:

| Feature | Range across the references | Tag |
| --- | --- | --- |
| First cut | 0.6 to 0.9 seconds | measured |
| Cut rhythm | 18 to 26 cuts per minute | measured |

**What the evidence cannot show.** It cannot show why these videos performed. It cannot show that this style will produce any result for this video. Three references is a small set.

**Options**

| | A. House style | B. Outlier-matched | C. Hybrid |
| --- | --- | --- | --- |
| What changes | Nothing | Opening, cut rhythm, and a neon caption look | Opening and cut rhythm only |
| What stays | Everything | Your logo and colors in the end card | Your caption font, colors, and lower-third |
| Extra footage needed | None | Two more cutaways | Two more cutaways |
| Extra edit and render time | None | About one more draft cycle | About one more draft cycle |
| Risk to brand consistency | None | High: the neon captions conflict with your brand guide | Low |

**Recommendation.** Option C, because the outlier caption look conflicts with your brand identity, and the two features that separate the outliers are structural.

**What must not be copied.** No script lines, on-screen wording, graphics, music, or footage from any reference.

**How the result will be compared.** Here is an edit in that style, and here is how the result will be compared after posting: `social-media` compares this edit with your past edits on the same platform and format at a similar age, by edit ID and blueprint ID, and reports the sample size. One edit is one data point.

## The decision as recorded

Ben replied "C". The editor recorded:

```yaml
decision_id: SD-SYN-031
project_id: SYN-PROJ-031
version: v1
decision: hybrid
study_id: OS-SYN-014
blueprint_id: SB-SYN-014
blueprint_version: 1
blueprint_valid_until: 2026-11-05
decided_by: Ben (owner)
decided_by_role: owner
decided_at: 2026-10-06T15:20:00Z
proposal_reference: style-match-proposal.md
comparison_plan: social-media compares by edit ID and blueprint ID at 14 days
edit_state: style_chosen
```

`hf.py style-check` then reported `style decision recorded`.
