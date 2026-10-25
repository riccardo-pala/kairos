# Kairos development workflow

This lightweight collaboration model was approved on 25 October 2026.

## Roles and activation

The normal setup is the coordinator plus at most one operational agent per task. The whole team is not recreated or activated for every request.

| Role | Model | Reasoning | When it is used |
| --- | --- | --- | --- |
| Coordinator | Main chat agent | Set by the chat | Answers questions, explanations, and brainstorming; defines tasks, verifies results, and explains them to the user. Handles small updates to working rules. |
| Luna Sviluppo | gpt-6-luna | Varies with task complexity | Implements authorized code tasks and prepares an educational recap of its changes. |
| Luna Commit | gpt-6-luna | Low | Creates coherent local commits only when requested. Uses concise English subjects based on staged changes only. Push requires authorization. |
| Luna Archivio | gpt-6-luna | Low | Reorganizes the idea log when a substantive update is needed or requested. |
| Luna Prodotto | gpt-6-luna | Medium | Develops proposals when substantial product work is needed or requested. |
| Luna Requisiti | gpt-6-luna | Medium | Updates requirements when functionality, scope, or evidence changes materially, or when requested. |

The separate Luna Recap role is inactive; Luna Sviluppo includes the recap, which the coordinator reviews. Other roles remain available without automatic Archivio → Prodotto → Requisiti chains.

## Work process

The coordinator handles questions, explanations, and brainstorming without delegation. Discuss exploratory requests and meaningful design choices before implementation.

For development, the coordinator gives Luna Sviluppo a short task with an objective, scope, acceptance criteria, and targeted references. The agent implements only authorized changes; scope expansions return to the coordinator. The project retains its educational focus on Python, workflows, tool calls, and LLM integration.

The recap first explains which files changed, what they do, where they are used, and which function or class starts the flow. It then walks through a concrete code example, with short real snippets explained and verified file references. Length should match the task; diagrams are included only when useful. The recap distinguishes implementation, simulated tests, real-model trials, and observed limits. The coordinator returns this explanation without starting another agent.

Ideas do not automatically activate agents or update every document. When consolidated, the Archivio role distinguishes requests, interpretations, proposals, and decisions. Prodotto relates proposals to Kairos's purpose of helping people who procrastinate act at the right moment. Requisiti keeps stable IDs and distinguishes goals, available behavior, and evidence. A proposal alone does not authorize implementation.

## Context and verification

- Read only the files and diffs relevant to the task; avoid rereading all documentation on every turn.
- Give agents only the context they need, with precise references, rather than copying the entire chat history or unrelated documents.
- Run checks appropriate to the change and do not repeat checks that passed without new changes, failures, or specific concerns.
- Avoid collateral documentation updates and extra review steps for small changes.
- Keep responses and progress updates proportional to the work, while explaining steps useful to the user's learning.
- Do not run background cycles; agents work during the chat task.

## Documentation structure

Project documentation is organized by reader purpose: `docs/usage/` explains how to start and use the module; `docs/functional/` contains the single Markdown requirements source, the derived Word copy, product proposals, and decision log; `docs/technology/` contains architecture, evaluation, and development workflow.

Keep each document focused on its audience. Put conversational history, internal rationale, discarded ideas, and unresolved product decisions only in `docs/functional/decision-log.md`; describe their resulting behavior or current status in other documents without repeating the discussion. Put startup commands in the usage guide that covers the relevant service, and link to them from the README instead of duplicating them.

The Word requirements document is generated from `docs/functional/requirements.md` by `scripts/build_functional_document.py`. Regenerate and visually verify it for substantive revisions, not every note. Any functional edits made directly in Word must be copied back to the Markdown source before regenerating.

Project documents preserve decisions beyond an agent's lifetime. New sessions should retrieve only the context needed and activate roles as required, following this lightweight model.
