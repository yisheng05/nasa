# 2026 rules check

Status on **Saturday 14 November 2026**, updated from the **Singapore Local Lead's email to participants** (Cory Meilany, 13 Nov). That email is the authoritative source for our Local Event. Earlier entries came from search-engine extracts of spaceappschallenge.org, because automated fetches of the site failed on 13 Nov.

Confidence key: **Confirmed (LL)** = Local Lead email · **Confirmed (FAQ)** = 2026 Participant FAQ via search index · **Precedent** = an earlier year · **Open** = not found.

| Rule | 2026 answer | Confidence and source | Impact on our plan |
|---|---|---|---|
| Event window | Virtual. Starts Sat 14 Nov 9:00 am SGT, ends Sun 15 Nov 11:59 pm SGT. | **Confirmed (LL)** | Internal deadline Sun 10:00 pm SGT. |
| Submission route | Through the official Space Apps site. The Project Submission section opens Sat 14 Nov. | **Confirmed (LL)** | Draft text in the repo; paste it in early. |
| Project Summary | "Explain your solution, the problem it addresses and its impact." | **Confirmed (LL)** | Lead with the problem (judged under Impact). |
| Project Demo | "Either a 30-second demonstration video OR a 7-slide presentation." | **Confirmed (LL)** | 7 slides recommended (handoff §19.1). |
| Final Project Link | "A publicly accessible link to your project or supporting materials." | **Confirmed (LL)** | Make the repo public before submitting, after reviewing `docs/` (README). |
| Project Details | "Explain your approach, tools, technologies and NASA datasets used." | **Confirmed (LL)** | Fill from `REFERENCES.md`, including AI tools. |
| NASA data | At least one NASA dataset is mandatory for Global Awards. Name the datasets, give source links and explain how the data supports the solution. Imagery, CSV/JSON, processed data and charts all count. | **Confirmed (LL)** | HLS, SMAP L4, POWER and MSLSP30NA, each with a link and its role. |
| Live API | "A live NASA API connection is not required." | **Confirmed (LL)** | The precomputed demo fields are fine. |
| Prototype standard | "A fully functional application is not required. A well-presented concept or prototype demonstrating meaningful NASA data usage is acceptable." | **Confirmed (LL)** | Put presentation quality ahead of live extraction. |
| Other data | Allowed to complement NASA data. | **Confirmed (LL)** | CDL, SSURGO, Crop Progress are fine. |
| Challenge-specific datasets | "Some challenges specify particular datasets or resources." | **Confirmed (LL)**. Field Shift Resources tab read 14 Nov: it recommends datasets but requires none. | Every resource is mapped in handoff §10.1. |
| Non-U.S. Government data | "For non-U.S. Government websites, participants must comply with any data use parameters of that specific website." | **Confirmed** (Resources tab) | Copernicus attribution for Sentinel-2 (HLS S30); PRISM terms if used. |
| "SI" terminology | The Resources tab says "SI tools" and "SI models" where earlier years said AI. | Resources tab | Terminology only. Our design keeps any model out of evidence and ratings (handoff §12). |
| Team size | 1–6 members; solo welcome. | **Confirmed (LL)** | — |
| Work before the event | "Teams are not allowed to begin working on the challenges prior to the hackathon." | **Confirmed (FAQ)** | Product code from Sat 9:00 am SGT. Pre-event material is logged in the README; no further follow-up (team decision, 14 Nov). |
| Finality | No edits after the deadline. | Precedent (2025 guide) | Submit early. |
| AI tools | Not mentioned in the LL email. The 2025 guidance asked teams to state where and how AI tools were used. | Precedent / **Open** | Disclose every AI tool in Project Details and `REFERENCES.md`. |
| Rights and originality | Teams must have rights to submitted materials; no plagiarism or unauthorised use of another team's work. | FAQ via search index (year uncertain) | Don't copy from other teams' public repos. |

## Judging criteria (confirmed by the Local Lead, each scored 1–5)

| Criterion | Judges' question (2026) | How we answer it |
|---|---|---|
| Impact | What problem are you solving, and why does it matter? | Soil without living cover for about seven months a year and stress recurring at silking, on a field whose rotation decision is made every November. Diversified rotations cut drought-year losses by 14–90% (Bowles et al. 2020). |
| Creativity | How innovative or original is your approach? | Field-scale history from 30 m HLS, where most tools use coarse grids. |
| Validity | Is your solution supported by relevant evidence and appropriate data? | Validation chart (V3, V4, V6); every number traced to a NASA dataset and date; stated limits. |
| Relevance | How well does your project address the challenge you've selected? | Every screen maps to a phrase in the brief (handoff §1.2). |
| Presentation | How clearly and effectively do you communicate your solution? | One farmer, one field, one rotation decision; 7 slides. |

Selected Singapore projects advance as Global Nominees.

## Support

- Zoom Q&A (optional): Sat 14 Nov 8:00 pm SGT; Sun 15 Nov 5:00 pm SGT. Mentors: Roman Shirochenko (technical), Cory Meilany (design).
- Local Lead: Cory Meilany. Discord link in the Local Lead's email.

## Still to do

- [x] Field Shift **Resources** tab: read 14 Nov, mapped in handoff §10.1, NASA and partner items added to `REFERENCES.md`. None is mandatory.
- [ ] Challenge **Details** tab: compare with handoff §1.1.
- [ ] Confirm the AI-tool disclosure wording if the submission form has a field for it.
