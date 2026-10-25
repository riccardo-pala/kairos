# Kairos functional requirements

**Document status:** Revision 0.3, 25 October 2026. Backend drafting, simulated-provider behavior, and CLI capabilities are implemented. A first stateless FastAPI endpoint has been added; local runtime verification is still pending because its dependencies could not be downloaded in the current environment. A limited real-model language evaluation found non-conforming results for the tested configuration and does not support general conclusions about the model.

## Executive summary

People who procrastinate may struggle to move from an intention or commitment to the actions needed to address it. Kairos is intended to support that transition with a personal assistant inspired by the idea of the right moment, keeping its features connected to that purpose.

The proposed experience collects an event or commitment, clarifies missing information, and organizes it with related before-or-after activities and user-selected reminders. The intended app supports voice and text plus interactive components; Android is the first planned platform, and Italian and English are required from the beginning. In the current backend and CLI, static messages follow the interface language, while clarifications and generated text follow the conversation language.

The intended proof of concept covers the journey from an intention to creating an event and receiving reminders. The current backend prepares an in-memory draft, and a first HTTP endpoint exposes the workflow. The mobile app, voice input, persistent event creation, and notification delivery remain unimplemented. The grocery-list idea is outside the first proof of concept.

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
4. The user can correct the draft and configure multiple reminders. The exact no-reminder interaction still needs definition. The backend and CLI can carry a conversation language across turns, but simulated-provider results do not guarantee language recognition by a real model.
5. The user reviews the draft before considering it ready. The review interface and explicit confirmation before creating an event have not been defined.

## Functional requirements

IDs are stable to support references and revisions. “Requested” describes an explicit user intention; the criteria describe observable outcomes while leaving undecided details open.

| ID | Requirement and observable criterion | Status and source |
| --- | --- | --- |
| **FR-01** | The user can describe an event or commitment in natural language. Kairos returns a draft structure consistent with the information provided. | Requested for the first version; multi-turn draft workflow is implemented in the backend. |
| **FR-02** | The user can submit a request by text or voice. Voice input enters the same functional flow as text. | Both modalities requested; voice capture and mobile interface are not implemented. |
| **FR-03** | The draft can include the event date and time, location, and duration when the user knows and provides them. Missing values are not invented. | Required for the use case; draft fields and clarifications are supported in the backend. |
| **FR-04** | The user can associate one or more activities to do before and/or after an event. Activities remain distinct from reminders. | Requested for the first version; before/after activities are supported by the backend draft. |
| **FR-05** | The user can choose multiple reminders for an event. If the user does not specify when to be reminded, Kairos asks before completing the draft. | Requested; the draft supports multiple reminders and clarification. Notification delivery is not implemented. |
| **FR-06** | Kairos asks for clarification when required information is missing or ambiguity prevents a safe representation. Answers update the same draft. | Requested; multi-turn draft updates are implemented. The required fields beyond date/time remain open. |
| **FR-07** | The user can correct or complete proposed information before considering the draft ready. | Corrections are supported by the workflow; a review UI and explicit confirmation before creation remain undefined. |
| **FR-08** | The experience offers text, voice, and in-app buttons or interactive components, so text is not the only interaction method. | Requested; the app and interactive controls are not implemented. |
| **FR-09** | Android Home Screen widgets are outside the current scope. | Explicit user exclusion. |
| **FR-10** | Static interface text and primary functional flows support Italian and English. Interface and conversation languages may differ. | Requested; the backend/CLI static catalog is complete and validated. The app is not implemented. |
| **FR-11** | Kairos accumulates essential information about the user over time to personalize assistance. | Requested; persistent profile is not implemented. Its content and controls remain open. |
| **FR-12** | Onboarding may offer guided choices, buttons, and tags while keeping manual entry optional. | Option to evaluate, not an approved requirement; not implemented. |
| **FR-13** | Kairos creates the event described by the user with its configured activities and reminders. | Requested first-version goal; the current workflow prepares only an in-memory draft. Persistent creation and destination remain open. |
| **FR-14** | The user receives the reminders configured for the event. | Requested goal; notifications, delivery timing, and permission handling remain unimplemented or undefined. |
| **FR-15** | Static text follows the interface language. Clarifications and generated text use one conversation language per turn. The initial preference comes from context; unsupported languages fall back to English. Clearly recognized greetings may indicate a language, while short, ambiguous, or neutral input preserves the prior choice. An explicit Italian or English request takes priority, and a later substantive message in either language may change the conversation language. Selection uses the existing model call without a separate agent or language-detection call. | Prompt rule implemented and covered by simulated tests. A limited evaluation with Ollama `qwen3:8b` Q4_K_M (`think=False`, temperature 0, seed 42; 6 scenarios and 9 turns per variant) found failures, including Italian output for an English start and failure to retain English fallback through a French/neutral/explicit-Italian sequence. The 354-word baseline prompt remains in runtime; the compact candidate was not promoted because of semantic regressions in injection cases. No general conclusion about the model is warranted. |
| **FR-16** | When the provider streams text, the CLI and HTTP API may display it progressively. Tool-call arguments remain internal until collected and validated; the interface presents the validated draft and does not expose partial JSON or reasoning. | User decision of 25 October 2026. Streaming is optional and separate from tool calls. CLI behavior is implemented and simulated-provider verified; HTTP streaming is implemented but awaits local runtime verification. |
| **FR-17** | During a turn, the CLI and HTTP API report static progress messages in the interface language, tied to workflow phases actually reached. They do not simulate waiting or describe model thoughts, and require no extra LLM calls. | User decision of 25 October 2026. CLI behavior is implemented and simulated-provider verified; HTTP event mapping is implemented but awaits local runtime verification. |

## Cross-cutting characteristics

- **Accessibility — explicit request:** text must not be the only interaction method; voice, buttons, and in-app components are requested.
- **Focus — explicit intent:** features should meaningfully relate to procrastination and avoid accumulating unrelated functions.
- **Missing information — requested behavior:** incomplete examples are not facts. Do not invent an unstated year, location, duration, or other detail; define precise clarification by field and scenario.
- **Data and action controls — proposal to define:** the user requests an accumulating essential profile, but consent, retention, editing, deletion, and assistant-action controls are not yet decided.
- **Model guardrails — recognized priority, timing open:** the user considers guardrails important and placed them in the future. Bringing them into the first version is a coordinator proposal, not an approved decision. Specific behaviors and criteria remain open.
- **Quality and outcomes — to validate:** no indicators, thresholds, or improvement claims are defined. No feature implies diagnosis or clinical treatment.
- **Language, streaming, and progress — decision of 25 October 2026:** static text follows the UI language; clarifications and generated text follow the conversation language; progress messages follow the UI language. Simulated tests pass. A limited real-model language evaluation failed in the configuration described in FR-15.

## Proof-of-concept scope and future work

| Area | Intended first proof of concept | Current availability | Future work or exclusions |
| --- | --- | --- | --- |
| Event flow | Draft a commitment, activities before/after, clarifications, create the event, and deliver multiple reminders; Android is the planned first platform. | Backend multi-turn in-memory drafting workflow, scripted provider, optional Ollama adapter, CLI, and initial stateless HTTP API. | Persistent creation, notifications, and mobile app remain unimplemented; calendar integration and reminder delivery need definition. |
| Interaction | Voice or text, plus in-app buttons and interactive components; Italian and English. | Backend, CLI, and initial HTTP endpoint do not constitute the requested mobile experience. | Voice UI and Android UI remain future work; Android Home Screen widgets are excluded for now. |
| Profile | Retain essential information that helps personalize assistance. | No persistent profile; the workflow carries the current draft and latest question. | Profile contents and user controls remain undefined. |
| Grocery list | Excluded from the first proof of concept to preserve focus. | Not implemented. | Future idea to reconsider only if it supports the product's procrastination focus. |
| Feedback | Outside the first proof-of-concept scope. | Not implemented. | Future idea: collect and organize feedback; human review is a proposal, not a decision. |
| Guardrails | Inclusion in the first proof of concept is not approved. | Argument validation and a basic tool boundary exist; this is not complete prompt-injection protection. | The user considers guardrails important for the future; earlier inclusion is only a coordinator proposal. |
| Language, streaming, and progress | Complete Italian/English static strings; one conversation language for generated text and clarifications; optional text streaming; static progress tied to real workflow phases. | Implemented in backend and CLI with simulated-provider verification; initial HTTP mapping is implemented and awaits runtime verification. Limited real-model evaluation found language failures. | Mobile UI, persistence, and notifications are outside the current decision. |
| First steps, timely invitations, and restarting | Not approved as first-version requirements in the available sources. | Not implemented. | Product proposals to discuss: suggest a small first step, offer an invitation at a chosen time, and help the user restart without blame. |

Current implementation status is summarized from the repository documentation; runtime availability of the new HTTP API has not yet been independently verified.

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
| 24 October 2026 | Initial functional baseline: explicit requirements separated from proposals and implementation status; grocery list excluded from the first proof of concept. |
| 25 October 2026 | Revision 0.2: recorded and implemented decisions about conversation language, text streaming, and progress in the backend/CLI; simulated-provider verification and limited real-model language evaluation recorded. |
| 25 October 2026 | Revision 0.3: recorded the initial stateless HTTP API and separated startup, functional, and technology documentation. |

## Document management

This Markdown file is the single functional source. The Word document is a presentation copy generated for substantive revisions; update it from this source and review its rendered pages. Any functional edits made directly in Word must be copied back here before regeneration.
