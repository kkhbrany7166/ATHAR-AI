# Product walkthrough

Every screen below comes from the running application with the synthetic CS201 class. The intervention screens come from one real run of the workflow: the AI note draft and Sara's check reading were live `gpt-4.1-mini` calls, and everything else was deterministic. Desktop at 1280 px. Mobile layouts were checked for sideways overflow on the main screens, but they aren't pictured here.

## Landing
![Landing page with the headline and one stored example from the class](assets/screens/01-landing.png)
One real stored case, so a first-time visitor sees the idea in a few seconds. *Inspect the evidence* signs in as the professor and opens that submission.

## Professor

**Course overview: what needs attention today**
![Course overview listing what needs the professor's attention](assets/screens/02-course-attention.png)

**Who needs attention: the review queue**
![Review queue for Assignment 3 grouped by evidence and suggested action](assets/screens/03-review-queue.png)
Each student is in exactly one group, built by fixed rules from test results and the stored AI reading. Amber marks evidence that rests partly on AI.

**Evidence review: working code, flagged reasoning (Noura)**
![Noura's submission with findings, highlighted explanation and code](assets/screens/04-noura-evidence.png)

**Evidence review: conflicting evidence (Layan)**
![Layan's submission marked as disputed and needing review](assets/screens/05-layan-conflict.png)
The AI's claim quotes a sentence that states the correct stopping condition, so ATHAR marks it as disputed and sends Layan to the professor. The original AI output stays below for audit.

**Proposed support and approval**
![Intervention draft with flow strip, editable note and word count](assets/screens/06-draft-approval.png)
![Practice and check validation: the correct solution passes, code with the misconception is caught](assets/screens/07-validation-pair.png)

**Outcomes**
![Intervention outcomes with Sara's before and after](assets/screens/13-layla-outcome.png)

**Evaluation**
![Evaluation page with three numbered findings](assets/screens/14-evaluation-findings.png)

## Student (Sara)

![Why this: a personal opener from her earlier result and the approved note](assets/screens/08-sara-why-this.png)
![Think first: her first answer before any help](assets/screens/09-sara-think-first.png)
![Practise with help: passing tests, a hint and the assistant](assets/screens/10-sara-practice.png)
![Look back: first and revised answers side by side](assets/screens/11-sara-look-back.png)
![Show it: the independent check and its result with caveats](assets/screens/12-sara-show-it.png)
