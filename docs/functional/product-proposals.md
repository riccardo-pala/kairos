# Kairos product proposals

These proposals outline possible experiments for Kairos. They are hypotheses unless explicitly marked as decisions. The reference is helping people who procrastinate act at the right moment. Android is the first context to consider; iOS and web remain open.

## 1. From a list to a first step

**Hypothesis:** when a task is being postponed, suggest one small, concrete action the user can start immediately. For example, “prepare the presentation” could become “open the document and write the title.” The user can accept, edit, or reject the suggestion.

- **Potential value:** reduce uncertainty about how to start and make a manageable action visible.
- **First experiment/MVP:** an Android screen to enter a task and receive one next step, with “Start now”, “Edit”, and “Later” actions. Check with a small number of users whether the suggestion helps them begin.
- **LLM role:** propose a short breakdown using the user's written context. The interface, final choice, and recording of a start remain deterministic and under user control.
- **Risks to validate:** vague, oversized, or unsuitable steps; sensitive activities sent to a provider; suggestions that add work instead of helping the user begin.

## 2. An invitation at the right moment

**Hypothesis:** Kairos can offer a gentle invitation to return to a user-selected task within a chosen window or at a selected time. The invitation suggests a short action and an easy way to postpone or disable reminders.

- **Potential value:** bring attention to an intention at a user-chosen time without making the reminder feel compulsory.
- **First experiment/MVP:** a configurable Android reminder for one task and one time window, with “Start”, “Snooze”, and “Disable” actions. Observe whether users find it useful and respectful.
- **LLM role:** optionally rewrite the task as a brief invitation consistent with the selected tone. Times, frequency, muting, and button actions follow deterministic rules.
- **Risks to validate:** intrusive or insistent notifications, operating-system permissions and limits, or a judgmental tone. Do not claim clinical benefit.

## 3. Restart without blame

**Hypothesis:** if a task does not start or is postponed, offer a short practical choice: reduce the step, choose another time, or drop the task. Not starting is not presented as failure.

- **Potential value:** make it easy to adjust a plan when the first suggestion does not work and keep the user in control.
- **First experiment/MVP:** after a postponement, show three options (“Make the step smaller”, “Choose a time”, “Drop it”) and use observed sessions to assess clarity and usefulness.
- **LLM role:** when asked, help formulate a smaller step or practical reason without interpreting mental states. The app controls the options, postponements, and task changes.
- **Risks to validate:** making the user feel monitored or blamed, wording that sounds diagnostic, or collecting more data than needed.

## Possible event, activity, and reminder flow

The current focus is the event flow and its related activities and reminders, as a basis for facilitating a concrete action. An agenda alone does not demonstrate or guarantee that procrastination is overcome. The following describes a possible flow for discussion, not an approved specification.

From voice or text, Kairos could show an editable summary with the event and any supplied location or duration, related before-or-after activities, and requested reminders. Transcribed voice and typed text should enter the same interpretation and review flow. If reminder timing is missing, the assistant asks; it clarifies only ambiguity or necessary data, such as a missing year or timezone when relevant, or which event an activity refers to. It does not invent missing values; the user reviews the summary before creation.

Activities, events, and reminders are distinct objects: a before/after activity describes something to do, while a reminder specifies when to notify. An event may have multiple configurable reminders. Scheduling, date/time validation, and recording choices are deterministic; the LLM interprets the request and proposes a structure that the user can correct.

## Proposed filter for new features

These operating criteria are proposals derived from the product intent, not newly approved constraints. Before adding a feature, ask:

- Which concrete delay or obstacle does it help address?
- Which concrete action does it make easier to start or complete?
- Is the added complexity proportionate to the benefit for that use case?

If no clear link exists between the obstacle and the facilitated action, the feature can remain outside the proof of concept and be reconsidered later.

## Interaction, profile, and guardrails

In-app controls could offer quick actions and voice input. Android Home Screen widgets are excluded for now. Guided onboarding with tags or selections is an option to evaluate, while keeping free text optional.

As a proposed first-version approach, saved profile information should be essential, explicit, editable, and deletable. It should be shown and managed separately from conversation history and model inferences; an unconfirmed inference should not become a profile fact. Clear limits are needed on tool access, deterministic parameter validation, data protection in memory, and inputs that attempt to override instructions. User confirmation should match the effect: review before creating or changing commitments, and explicit confirmation for external or hard-to-reverse actions.

Feedback handling remains future work. An agent may collect and organize reports for review, but should not change code or delete feedback autonomously. Reports and review outcomes should remain traceable.

Before defining the MVP, decide how data is handled locally or in the cloud and what notification reliability to expect in different situations. These proposals do not select technologies.

## Questions for discussion

- Which daily situation should guide the first prototype?
- Are user-selected reminders consistent with the idea of a “right moment”?
- What tone should Kairos use when a user postpones or does not start a task?
- Which data may stay on the device, and which, if any, would be sent to an LLM provider?
- Which confirmations are needed to create or change events and activities, and which are needed for future external actions?
- How should the chosen flow handle timezones, ambiguous times, and notification permissions?
- Which profile data may the user save explicitly, and how can they view, edit, or delete it?
- Which in-app controls and quick actions are valuable enough for the first version?
- How can language selection and retention improve without semantic regressions? Current evidence is limited to the Ollama configuration described in the [requirements](requirements.md).
