# Kairos functional requirements

**Document status:** Revision 0.4, 25 October 2026. The backend provides multi-turn event drafting, a CLI, and a FastAPI service with PostgreSQL-backed sessions. Container runtime verification is pending.

## Executive summary

People who procrastinate may struggle to move from an intention or commitment to the actions needed to address it. Kairos is intended to support that transition with a personal assistant inspired by the idea of the right moment, keeping its features connected to that purpose.

The proposed experience collects an event or commitment, clarifies missing information, and organizes it with related before-or-after activities and user-selected reminders. The intended app supports voice and text plus interactive components; Android is the first planned platform, and Italian and English are required from the beginning. The backend, CLI, and API provide static messages in the interface language, while clarifications and generated text follow the conversation language.

The intended proof of concept covers the journey from an intention to creating an event and receiving reminders. The current backend prepares event drafts and stores the current workflow state in PostgreSQL. The mobile app, voice input, persistent event creation, calendar integration, and notification delivery remain unimplemented.

## Problem, users, and expected value

- **Problem:** people who procrastinate may find it difficult to move from an intention or concrete commitment to the action it requires.
- **Intended users:** people who procrastinate and want practical help organizing commitments and related activities. No narrower segment has been defined.
- **Expected value:** make it easier to express a commitment, clarify missing details, and organize activities and reminders the user considers helpful.
- **Product principle:** help the user act at the right moment and keep features focused on procrastination. Assess proposed features against this purpose.
- **Evidence limit:** this value is a product intention to validate with users. No user research results or clinical efficacy evidence are available.

## Intended user journey

1. The user starts a request in Italian or English, by text or voice.
2. The user describes an event or commitment and may provide a location, duration, or related activities.
3. Kairos organizes the supplied information and asks for required details that are missing or ambiguous. In particular, it asks the user to choose a reminder time if none was provided.
4. The user can correct the draft and configure multiple reminders. The exact no-reminder interaction still needs definition. The backend carries the conversation language across turns; real-model language behavior requires further evaluation.
5. The user reviews the draft before considering it ready. The review interface and explicit confirmation before creating an event have not been defined.

## Functional requirements

IDs are stable to support references and revisions. Each criterion describes an observable outcome; the status column summarizes current availability.

| ID | Requirement and observable criterion | Implementation status |
| --- | --- | --- |
| **FR-01** | The user can describe an event or commitment in natural language. Kairos returns a draft structure consistent with the information provided. | The multi-turn draft workflow is implemented in the backend. |
| **FR-02** | The user can submit a request by text or voice. Voice input enters the same functional flow as text. | Text input is available in the backend and CLI. Voice capture and mobile interface are not implemented. |
| **FR-03** | The draft can include the event date and time, location, and duration when the user knows and provides them. Missing values are not invented. | Draft fields and clarifications are supported in the backend. |
| **FR-04** | The user can associate one or more activities to do before and/or after an event. Activities remain distinct from reminders. | Before-and-after activities are supported by the backend draft. |
| **FR-05** | The user can choose multiple reminders for an event. If the user does not specify when to be reminded, Kairos asks before completing the draft. | Draft reminders and clarification are supported. Notification delivery is not implemented. |
| **FR-06** | Kairos asks for clarification when required information is missing or ambiguity prevents a safe representation. Answers update the same draft. | Multi-turn draft updates are implemented. Required fields beyond date and time remain to be defined. |
| **FR-07** | The user can correct or complete proposed information before considering the draft ready. | Draft corrections are supported. The review interface and confirmation before event creation remain undefined. |
| **FR-08** | The experience offers text, voice, and in-app buttons or interactive components, so text is not the only interaction method. | Voice input, mobile interface, and interactive controls are not implemented. |
| **FR-09** | Android Home Screen widgets are outside the current scope. | Not included in the current product scope. |
| **FR-10** | Static interface text and primary functional flows support Italian and English. Interface and conversation languages may differ. | The backend, CLI, and API support Italian and English. The mobile app is not implemented. |
| **FR-11** | Kairos accumulates essential information about the user over time to personalize assistance. | Persistent profile storage and user controls are not implemented. |
| **FR-12** | Onboarding may offer guided choices, buttons, and tags while keeping manual entry optional. | Not implemented; onboarding design remains open. |
| **FR-13** | Kairos creates the event described by the user with its configured activities and reminders. | The current workflow prepares a draft only. Persistent event creation and its destination remain undefined. |
| **FR-14** | The user receives the reminders configured for the event. | Notification delivery, timing, and permission handling are not implemented or defined. |
| **FR-15** | Static text follows the interface language. Clarifications and generated text use one conversation language per turn. Unsupported languages default to English. Clearly recognized greetings may indicate a language; short, ambiguous, or neutral input preserves the previous choice. An explicit request for Italian or English takes priority, and a later substantive message in either language may change the conversation language. Selection uses the existing model call without a separate language-detection call. | Implemented in the prompt and covered by simulated tests. A limited real-model evaluation found language-selection failures in the tested configuration; see the [prompt evaluation](../technology/prompt-evaluation.md). |
| **FR-16** | When the provider streams text, the CLI and HTTP API may display it progressively. Tool-call arguments remain internal until collected and validated; the interface presents the validated draft and does not expose partial JSON or reasoning. | Implemented in the CLI and HTTP API. Container runtime verification is pending. |
| **FR-17** | During a turn, the CLI and HTTP API report static progress messages in the interface language, tied to workflow phases actually reached. They do not simulate waiting or describe model thoughts, and require no extra LLM calls. | Implemented in the CLI and HTTP API. Container runtime verification is pending. |

## Cross-cutting characteristics

- **Accessibility:** text is not the only intended interaction method; voice, buttons, and in-app components are part of the product direction.
- **Product focus:** features should meaningfully relate to procrastination and avoid accumulating unrelated functions.
- **Missing information:** do not invent an unstated year, location, duration, or other detail; ask for clarification when needed.
- **Data and action controls:** consent, retention, editing, deletion, and assistant-action controls for a persistent profile remain to be defined.
- **Model guardrails:** field validation and a basic tool boundary exist. Broader prompt-injection safeguards and their evaluation criteria remain to be defined.
- **Quality and outcomes:** no indicators, thresholds, or improvement claims are defined. No feature implies diagnosis or clinical treatment.
- **Language, streaming, and progress:** behavior is summarized in FR-15 through FR-17. Real-model language limits are described in the [prompt evaluation](../technology/prompt-evaluation.md).

## Proof-of-concept scope and future work

| Area | Intended first proof of concept | Current availability | Future work or exclusions |
| --- | --- | --- | --- |
| Event flow | Draft a commitment, activities before/after, clarifications, create the event, and deliver multiple reminders; Android is the planned first platform. | Backend multi-turn drafting workflow, scripted provider, optional Ollama adapter, CLI, and stateful HTTP API with PostgreSQL sessions. | Persistent event creation, notifications, and mobile app remain unimplemented; calendar integration and reminder delivery need definition. |
| Interaction | Voice or text, plus in-app buttons and interactive components; Italian and English. | Backend, CLI, and HTTP API do not provide the requested mobile experience. | Voice UI and Android UI remain future work; Android Home Screen widgets are excluded for now. |
| Profile | Retain essential information that helps personalize assistance. | No persistent profile; the workflow carries the current draft and latest question. | Profile contents and user controls remain undefined. |
| Feedback | Not included in the current proof of concept. | Not implemented. | Feedback collection and review flow remain undefined. |
| Guardrails | Reliable interpretation and safe handling of user input. | Field validation and a basic tool boundary exist; comprehensive prompt-injection protection is not implemented. | Broader safeguards and evaluation criteria remain undefined. |

## Open questions

1. Which fields besides date and time are needed to complete an event? Which are required, and which require clarification?
2. How should multiple reminders be added, changed, or removed, including the “no reminders” choice?
3. Must a draft always receive explicit confirmation before event creation? Where is the boundary between preparing a draft and creating a commitment?
4. Which essential information may enter the profile, and what controls will the user have over it?
5. Is guided onboarding part of the proof of concept? Which choices help without adding friction?
6. Are guardrails future work or part of the first version? Which observable rules define their scope?
7. Which scenarios and users will determine whether the flow is understandable and useful?

## Revision history

| Date | Revision |
| --- | --- |
| 24 October 2026 | Initial functional baseline. |
| 25 October 2026 | Revision 0.2: updated language, streaming, and progress behavior and its implementation status. |
| 25 October 2026 | Revision 0.3: documented the HTTP API and organized documentation by audience. |
| 25 October 2026 | Revision 0.4: updated API persistence, implementation status, and scope. |

## Document management

This Markdown file is the single functional source. The Word document is a presentation copy generated for substantive revisions; update it from this source and review its rendered pages. Any functional edits made directly in Word must be copied back here before regeneration.
