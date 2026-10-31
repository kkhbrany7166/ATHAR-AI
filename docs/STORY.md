# ATHAR: story, demo script, pitch and slides (for review)

This replaces the storyboard and slide outline in `SUBMISSION-PLAN.md`. Every example below is a real stored record in the synthetic demo class. Nothing here has been recorded or designed yet.

## The story in one line

**Every test passed. So did a misunderstanding.** ATHAR helps one professor see that, act on it with care, and check whether the help worked, without handing the judgment to the machine.

### The arc

| # | Beat | What carries it |
|---|---|---|
| 1 | **The human problem:** one professor, 120 students, an autograder that says "pass" | Layla's CS201 class |
| 2 | **The insight:** standard systems treat everyone the same; AI could give back individual attention if humans keep the judgment | The personalisation idea that also led to HADIR |
| 3 | **The concrete example:** Noura's code passes 10/10, and her sentence says recursion stops "when the function hits the return statement" | Landing card → her submission |
| 4 | **The hard part:** reading every explanation fairly, without inventing evidence or overruling the professor | Verbatim quotes, flags as questions, conflict check (Layan) |
| 5 | **What ATHAR does:** groups students by what they need, not by score | The review queue |
| 6 | **How the agent acts:** drafts, validates in a sandbox, waits for approval, delivers once, tracks | Plan for 14 → validation pair → approve |
| 7 | **What the student experiences:** her own result first, think before help, practise with help, show it alone | Sara's studio |
| 8 | **What the new evidence reveals:** demonstrated on a new task, with honest caveats | Sara's result → Layla's outcomes |
| 9 | **How we know:** measured on untouched sets, including where it fails | Evaluation page |
| 10 | **Why it matters, and what's next:** more individual attention at the same scale; a privacy-preserving local model and a real pilot next | Closing |

**The thread through every scene:** AI does the reading, the professor decides, the student learns. Say it once at the start and show it in every scene.

---

## A. Official demo video: 2:50, the real application only

**Before recording**
- Run `reset-interventions` (free) and open the browser at 1280–1360 px.
- Two scenes make live calls (the note draft and Sara's check, about $0.005 in total). Trim any waiting in the edit.
- Put a small caption on screen for the whole video: *"Synthetic class. Class grading by gpt-4.1-mini, stored from an earlier run. Note draft and Sara's check run live."*

| Time | Screen | Click or action | What changes in the app | Narration | Evidence shown | Criterion |
|---|---|---|---|---|---|---|
| 0:00–0:12 | Landing | none | — | "Every test passed. So did a misunderstanding. This is Noura, from a synthetic class of 120. Her code passes ten out of ten." | Stored example card | Communication |
| 0:12–0:32 | Noura's submission | *Inspect the evidence →* | Signs in as Layla, opens submission 2 | "Her explanation says recursion stops when the function hits a return statement. That's a misconception tests can't see. ATHAR's AI reads every explanation, quotes the student word for word, and marks it as a suggestion. It doesn't grade her." | Test result vs AI reading tags; highlighted quotes; *Accept / Change* | Task performance |
| 0:32–0:50 | Assignment 3 → Who needs attention | Breadcrumb → Assignment 3 | Review queue | "Across the class, ATHAR groups students by what they need: code that didn't run gets debugging, working code with confused reasoning gets an explain-your-reasoning task, and students who understand get nothing extra." Open *Evidence conflicts*: "And when the evidence contradicts itself, like Layan, whose explanation is right but whose code is wrong, ATHAR doesn't guess. She goes to the professor." | Seven groups; disputed flag | Robustness |
| 0:50–1:15 | Same queue → *Plan for 14* → draft | Click *Plan for 14*, then scroll to the validation pair | Draft created (live AI note); flow strip at *Your approval · now* | "Let's follow one group all the way: fourteen students whose code fails at exponent zero, the way this misconception predicts. ATHAR drafts a short note. Before any student sees the new check, the sandbox proves correct code passes and the misconception is caught." | Note *N / 90 words*; validation pair | Technical judgment |
| 1:15–1:25 | Draft | *Approve and send to 14 students* | Status → Delivered, 14 activities | "Nothing reaches a student until Layla approves." | Approval gate; delivered count | Engineering quality |
| 1:25–2:05 | Switch to Sara → her task | *Demo · switch view* → *Picked for you* → steps 1–4 | Checkpoint saved; practice runs; hint; revised answer | "Sara is one of the fourteen. Her code stopped at exponent one, and she wrote that power never needs to handle zero. She starts from her own result, writes what she thinks before any help, then practises with real tests, a hint and an assistant. Help here is learning, so it never counts against her." | Personal *Why this*; locked first answer; 3/4 → 4/4; before and after | Task performance, Robustness |
| 2:05–2:22 | *Show it* | Submit attempt 1 | Live reading; result card *You showed it on this task* | "Then a new problem, on her own: no hints, no assistant. Every test passes, including zero, and her explanation names the stopping condition. The app says what this is: evidence on one task, not lasting mastery." | 5/5; caveats | Task performance |
| 2:22–2:35 | Switch to Layla → intervention | *Demo · switch view* → intervention | 1 demonstrated, 13 not attempted, 0 simulated | "Layla sees new evidence, not a claim: Sara before and after, and real students counted apart from simulated ones." | Before/after; real vs simulated | Communication |
| 2:35–2:50 | Evaluation | Sidebar → Evaluation; open *Where the AI over-flags* | — | "We measured it on hand-written sets nobody tuned on. The AI found 13 of 14 misconceptions; keyword rules found one. But it over-flags, so every flag waits for a human. AI reads. The professor decides. The student learns." | 0.93 vs 0.12; 7/7 vs 2/7; 45 vs 20 | Evaluation and iteration |

**Consistency notes**
- Noura (submission 2) is in the *working code, reasoning flagged* group. Sara (submission 1) is in the *base-case gap* group. The narration says so explicitly at 0:50 ("Let's follow one group all the way"), so no two students are merged.
- Don't show *Simulate synthetic classmates* in the video, unless you add "simulated" to the narration.

---

## B. Spoken pitch: about 3:30, first person

> Hi, I'm Khalid, a computer science graduate.
>
> I started this hackathon with a question bigger than any one product: most systems we rely on are standardised. They're built for the average person, and the individual gets lost. I wanted to see whether agentic AI could give people back individual attention at scale, without taking the human judgment out. I explored that in two prototypes. ATHAR is the one about university teaching, because that's where I felt the problem most clearly.
>
> Picture a professor with 120 students. The autograder says most of them passed. But passing tests tells you the code worked, not that the student understands why. Students write explanations, and nobody has time to read 120 of them carefully every week.
>
> Here's a case from our synthetic class. Noura's code passes all ten tests. But in her explanation she writes that recursion stops "when the function hits the return statement." That's a real misconception. Her grade says she's fine. Her own words say she might not be.
>
> ATHAR reads every explanation with a language model, but under rules. It has to quote the student word for word, or the claim is dropped. It flags; it doesn't grade. Code is never judged by the model: it runs in a sandbox, because whether a test passes is a fact.
>
> Then it acts like an agent, with a boundary. It groups students by what they actually need, drafts a short note, picks a practice problem, and proposes a new check, and it proves in the sandbox that the check can tell understanding from the misconception. Then it stops and waits for the professor. Only after she approves does it deliver, track progress, and judge a new attempt the student does alone.
>
> For the student, help is part of learning. Sara practises with hints and an assistant, and none of that counts against her. The evidence comes from a separate check with no built-in help.
>
> We measured it on hand-written sets that were frozen before we ran anything. On 36 explanations, the AI found 13 of 14 misconceptions; keyword rules found one. On another 24 cases, it caught all 7 students whose code worked but whose reasoning didn't. Rules caught 2.
>
> We also measured what's wrong with it. It over-flags: on our synthetic class it flagged 45 students where 20 had the misconception. It's too cautious about correct answers. And once it flagged a student whose explanation was right and whose code was wrong. We didn't retune the model against our test set to hide that. We added a rule that sends contradictory evidence to the professor, and kept the original output for audit.
>
> A mentor here pushed me on privacy, so I've studied small open models a university could host itself. That's the next measurement, along with a second annotator and a real, consented pilot.
>
> All the data here is synthetic, and no professor has used it yet. What I'm confident about is the design: AI does the repetitive reading, the professor makes the judgments, and the student does the learning. That's how I think AI should personalise education.

*Spoken time is about 3:30 at a calm pace. To shorten it, cut the paragraph about the student.*

---

## C. Nine slides

Each slide has one message, should work without a presenter, and shouldn't repeat the demo scene by scene.

| # | Message (slide title) | Visual | Supporting evidence (minimal on-slide text) | Story beat |
|---|---|---|---|---|
| 1 | **Every test passed. So did a misunderstanding.** | Noura's card: 10/10 next to her quoted sentence | "Synthetic class · CS201 · ATHAR \| أثر" | Hook |
| 2 | **One professor can't read 120 explanations. Tests can't read any.** | A simple diagram: grade vs reasoning | 120 students; 114 explanations per assignment | Human problem |
| 3 | **AI reads. The professor decides. The student learns.** | The principle table, three rows mapped to the code | Origin: personalisation without removing human judgment | Insight |
| 4 | **Assess → Understand → Intervene → Verify** | The loop diagram with the approval gate highlighted | AI steps vs rule steps in two colours | What it does |
| 5 | **Different needs get different help, and conflicts go to a human.** | Class routing chart | 7 groups; 9 conflicts to review | How the agent acts |
| 6 | **Help while learning. Evidence on your own.** | Sara: think first → practice → show it (3 small screenshots) | 3/4 → 4/4 with a hint; new check 5/5, *demonstrated on this task* | Student |
| 7 | **Measured on data nobody tuned on.** | Two charts: final (36) and final-2 (24), separate | 0.93 vs 0.12; 7/7 vs 2/7; quotes 101/101 verbatim | Evaluation |
| 8 | **What it gets wrong, and what we changed because of it.** | Over-flagging chart + three "found → changed" lines | 45 vs 20; C3 20/36; v3.1 rejected; conflict check | Iteration |
| 9 | **Next: private, validated, real.** | Three steps: local small model → second annotator → consented pilot | Synthetic data and no educator validation yet, stated plainly | Impact |

---

## D. Submission checklist

| Requirement | Status | Note |
|---|---|---|
| 8–10 slide presentation | ☐ | Outline above, 9 slides |
| Demo video ≤ 3:00, showing the working agent | ☐ | Storyboard above, 2:50 |
| Functional prototype | ✅ | 15-step journey verified in the browser |
| Accessible source code | ☐ | Waiting on your approval of account, repository name, visibility, history and licence |
| GitHub link in *Demo Link* if there's no dedicated field | ☐ | After publishing |
| Supporting files linked in *About* | ☐ | README, `docs/AUDIT.md`, `docs/EVALUATION.md`, `docs/LOCAL-MODELS.md` |
| Links work without special access | ☐ | Test in a private browser window after publishing |
| Description matches the implementation | ✅ | README §3, §6, §10 |
| Correct challenge selected | ☐ | Check on the form |
| Submitted before 8:00 PM Saudi time | ☐ | |
| Be ready to explain the technical choices | ✅ | `docs/SUBMISSION-PLAN.md` §D, README §7–§9, AUDIT §4 |
| Decide whether `docs/STORY.md` and `docs/SUBMISSION-PLAN.md` stay public | ☐ | They're internal planning notes |
