# Official Submission Requirements Check

**Checked:** 2026-10-20 UTC, against Apart Research's official AI Collusion Research Sprint page: <https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25>.

## Verified requirements

| Item | Official page states | Candidate status |
|---|---|---|
| Report | PDF uploaded through the official form; the linked official template is required. The form shows a 25 MB file limit. | PDF candidate exists, 419,491 bytes. Exact official template use is **unverified** because the template's Google Docs `/copy` link redirects to Google sign-in and could not be retrieved. Do not claim template compliance. |
| Abstract | 150 words or fewer. | Current Markdown abstract is counted by the build script; final count recorded in `SUBMISSION_FORMAT_AND_RENDER_CHECK.md`. |
| Authors | Author names and affiliations required. | Not supplied; explicit placeholders remain. Must be completed by the actual entrant(s). |
| Ethics/limitations | Required appendix titled “Limitations and Dual-Use / Ethical Considerations”, explaining what the results establish and possible misuse. | Appendix A is explicitly labeled in the candidate and discusses evidence limits, privacy, surveillance/accusation risks and non-operational scope. |
| Length | “Most strong projects are 4 to 8 pages.” This is a recommendation, not a stated hard limit on the Guidelines section. | Five US-letter pages including references; within the recommendation. |
| Report content | Recommended introduction, related work, methodology, results, discussion, limitations/dual-use, references. Report enough model, prompt, environment, seed and metric detail to replicate. | Sections and evidence/reproduction package are present, but the full local M3 raw trace is ACL-restricted and not in Git; exact official template is unavailable. |
| Work during sprint | Building on existing work is allowed, but new work during the Sprint must be clearly identified; undisclosed prior work can disqualify. | Every current M0-M3 result is pre-sprint. The proposed validation is not run. This candidate alone is **not evidence of sprint-time work**; a new, separately frozen Sprint result is needed if submitting as a Sprint project. |
| AI drafting | AI can assist review/debugging; the report itself must be the team's own writing and factual claims linked. Generic AI-written text may not be scored. | Candidate explicitly discloses AI assistance. Entrant(s) must verify and rewrite it in their own words before submission. |
| Submission state | The form displays: “The submission window has closed. Your draft is still here so you can copy it, but it can no longer be submitted.” The same page and its FAQ state the deadline is Sunday 25 October 2026, 11:59 PM AoE. | **Unresolved blocker.** As of this check, these statements conflict. No inference is made that the deadline passed, the page is stale, or submissions remain possible. Do not attempt submission until organizer clarification. |
| Signup/eligibility | The page provides a Sign up form and states the Sprint runs 23-25 October. | The entrant's signup/participation state is unknown and was not checked or changed. Ask whether signup is still possible and whether prior work plus a new weekend result meets eligibility. |

The status and deadline appear together on the official page: its submission form says closed, while overview/FAQ/schedule text repeats the future Oct 25 AoE deadline. The official template URL on the Guidelines page was opened directly; the fetch failed after redirect to Google account login. This is an access limitation, not evidence that the template is defective.

## Questions for the entrant to ask Apart

Contact listed on the official page: `sprints@apartresearch.com` or Discord help-desk with `@Support`. No message was sent by this task.

1. The page says the submission window is closed, but the FAQ and schedule list 25 October 2026, 11:59 PM AoE. Is the form currently accepting submissions, and if not, when will it open? Is the “closed” message a registration state or an intentional submission lock?
2. Can a person/team still sign up after this status appears, and does signup need to precede the Sprint start?
3. Is the current Google Docs template link the correct current template? Can the organizers provide a direct downloadable copy or an alternate access path for a participant whose browser is redirected to Google sign-in?
4. Does the report need a distinct result generated during 23-25 October to count as a Sprint submission when the project has a substantial, fully disclosed pre-sprint baseline? Is a small new validation under the attached preregistered plan sufficient if it is clearly separated?
5. Are there page-count, appendix-placement, or template-specific formatting rules beyond the current 4-8-page recommendation, 150-word abstract limit, and required appendix?
6. What team name/location fields are mandatory for a solo entrant, and can author/affiliation fields be “independent researcher” or left blank if the entrant has no institutional affiliation?

## Current blockers

- Submission form availability and deadline status conflict on the official page.
- Exact current Google Docs template cannot be inspected in the available read-only session.
- Actual author names, affiliations, team details and entrant signup status are not provided.
- All present results are pre-sprint; the proposed new validation is only a protocol and has no model outputs.
- The current manuscript is AI-assisted. The official page requires entrant-authored writing, so it cannot be submitted verbatim.
