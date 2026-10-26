# Kairos ideas and decisions

This document records ideas and decisions for the project. Unapproved proposals remain marked as hypotheses; open questions are not decisions.

## Explicit user ideas

- **Date: 24 October 2026 — Product:** an app for people who procrastinate.
- **Date: 24 October 2026 — Name and philosophy:** “Kairos” refers to the right or opportune moment. The idea is not to postpone because now is the right moment; features should follow this philosophy.
- **Source:** the user's first explicit idea, recorded in the project-start context.

## Proposed first-version requirements from the user

These use cases and capabilities were proposed for the first version. Details not specified remain open.

1. **Create events and activities through voice or text.** The user can describe a commitment (for example, a medical visit on 31 October at 14:30, with a location, duration, and activities before and after). The assistant extracts structured information and creates the event with related activities. The example is illustrative: it must not become a real event or authorize inventing a year, duration, or location. If the user does not specify a reminder time, the assistant asks. Each event may have multiple reminders.
2. **Simple, flexible interaction.** Text must not be mandatory: the user may use voice, buttons, or interactive in-app components. Android Home Screen widgets are excluded for now.
3. **Accumulated personal context.** The assistant should learn about the user over time and retain essential details that help personalize assistance.
4. **Possible guided onboarding.** Consider a guided start with buttons, tags, and selections, leaving manual entry optional and not requiring text.
5. **Multilingual support from the start.** English and Italian are the requested initial languages.
6. **Multilingual text and question coverage.** Text and questions should be selected by language code and follow a contract that guarantees coverage of every supported language.
7. **Extensible multi-tool architecture.** The model may choose among available tools, while the application keeps each turn's flow defined.

## Clarification about widgets

- “Widgets” means interactive components inside the app.
- Android Home Screen widgets are excluded for now.

## Future ideas explicitly raised by the user

- **Grocery list for a recipe:** previously proposed as a first-version requirement, then removed from the first proof of concept to avoid an unrelated feature set. Keep it as a future possibility and reconsider only if it fits an app for people who procrastinate. The original idea was an editable list separating recurring items from one-time purchases.
- **Bug and improvement feedback:** a place where users can report bugs or suggest improvements; an agent collects, organizes, structures, and filters feedback by usefulness.
- **Model guardrails:** the user considers these very important and placed them in future work.

## Future UI proposals to evaluate

- During draft review, the frontend could offer selectable alternative titles and a small calendar for choosing a date.
- The location can start as a simple field; a map or geographic picker may be considered later. None of these proposals is part of the current implementation.

## Coordinator proposal to evaluate

Bring model guardrails into the first version, although the user placed them in future work. This is a coordinator proposal, not a user decision.

## Decisions from 25 October 2026 implemented in the backend and CLI

- Keep the static Italian and English message catalog complete; generate LLM clarifications in one language per turn, without an extra agent or model call.
- Derive the initial language preference from context and retain the previous language for short replies such as “ok”, dates, and numbers. An explicit or clearly expressed switch in the same model call determines the language for that turn.
- If the conversation uses an unsupported language, use English as its default in the existing model call. An explicit request in Italian or English takes priority; a later substantive message in either language may also change the conversation language. Clearly recognized greetings may indicate the language; short, ambiguous, or neutral input preserves the previous one. No separate agent or detector is added. The prompt rule is implemented and simulated tests passed. A limited test with Ollama `qwen3:8b` Q4_K_M found non-conforming language choices in that configuration, without supporting a general conclusion about the model.
- Allow optional text streaming, separate from tool calls. Collect and validate tool arguments, then present the validated draft; never display partial JSON or reasoning.
- Generate progress messages in code, tied to workflow phases that actually occur and static in the CLI interface language. Do not simulate waiting, expose model thoughts, or add model calls for progress. LLM text and clarifications follow the conversation language.
- At the time of this decision, limit the implementation to the backend and CLI; API, mobile app, persistence, and notifications were outside its scope.
- A limited real evaluation of `qwen3:8b` Q4_K_M with `think=False`, temperature 0, and seed 42 covered six scenarios and nine turns per variant. The baseline failed some language selection and retention cases. The compact candidate passed 3/6 checks versus 2/6 for the baseline, but was rejected due to semantic regressions in injection cases. Runtime retains the 354-word baseline prompt; these results do not describe every model configuration or establish general model failure.

The user approved these decisions on 25 October 2026, and they were implemented within the scope above. Simulated tests passed; the limited real evaluation found non-conforming language selection for its tested configuration. No alternative prompt was promoted.

## Project context reported by the user

- A mobile personal assistant based on an LLM.
- Android is the first planned platform; iOS and web remain to be evaluated.
- A Python learning project involving agentic integration and workflows.
- The user wants to participate actively and follow the work closely.
- The coordinator primarily handles frontend work.
- The user prefers faster implementation, with explanations focused on critical steps such as workflows, tool calls, and LLM integration. The project remains hands-on and educational.
- The coordinator translates requests into bounded tasks for Luna Sviluppo; Luna Commit handles requested local commits with English subjects. Do not activate the full team for every task.

This context does not add product requirements beyond the ideas and decisions attributed to the user above.

## Architectural hypotheses and current implementation

Earlier hypotheses included Flutter, FastAPI/Pydantic, SQLite, a replaceable model provider, and a low-cost local-first start. The user later asked to begin preparing a FastAPI layer. The first stateless HTTP endpoint is implemented; Flutter, SQLite, and a final provider strategy remain open.

The backend includes an asynchronous event-drafting workflow, validated `update_event_draft` tool calls, demo/Ollama/Hugging Face provider adapters, an Italian/English message catalog, a CLI, and a stateful FastAPI HTTP/SSE API backed by PostgreSQL. Provider profiles apply to the API; the CLI still selects Ollama through its own options. Event creation, notifications, and mobile UI remain unimplemented. Historical notes about `LocalizedText`, disabled streaming, or “no API yet” describe earlier states.

## Model provider profiles approved on 25 October 2026

- Keep the deterministic demo, local Ollama model, and remote Hugging Face Inference Providers as three built-in choices.
- Store the built-in provider profiles and the single active profile in PostgreSQL; the FastAPI admin endpoints list the choices and switch the active profile.
- Keep provider credentials outside the database. Hugging Face uses `HF_TOKEN` from local environment configuration; the local admin API remains unauthenticated and must stay bound to localhost.
- Start with Hugging Face as the first remote adapter. Amazon Bedrock remains a possible later adapter if an AWS deployment or specific model requirement justifies it; this implementation does not rule it out.

## Initial Hugging Face model selected on 26 October 2026

- Use `Qwen/Qwen3-8B` as the initial Hugging Face Inference Providers profile. It matches the local Qwen3 8B family, making a local-versus-hosted provider comparison more direct.
- The current official Hugging Face Inference Providers catalog marks the Nscale route for this model as tool-compatible.
- Keep Demo as the initially active profile so a fresh setup cannot make remote model calls accidentally.

## Open questions

- How should Kairos turn its philosophy into concrete behavior and features?
- What tone and product implications should express that philosophy? These are proposals to discuss, not user decisions.
- What are the boundaries of the educational project, agents, and workflows?
- When should iOS and web be evaluated relative to Android?
- For events, which fields beyond date and time are needed? How should missing details other than reminder time be handled? The 31 October example has no actual year, duration, or location.
- How should multiple reminders be defined and changed?
- Which essential information belongs in personal context, and how is it updated? Consent and data handling are unspecified.
- How can language selection be improved without semantic regressions? The current real-model evidence is limited to the stated model and configuration.
- Is guided onboarding part of the first version, and which choices should it offer?
- Are guardrails future work, or should a coordinator proposal be considered for the first version? Specific behaviors remain undefined.
- How should feedback usefulness be assessed, and who can review items filtered by an agent?
