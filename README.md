# Kairos

Kairos is a personal assistant project intended to help people who procrastinate turn intentions into concrete next steps. Android is the first planned platform; Italian and English are the initial languages.

The current Python backend can prepare an event draft through a multi-turn workflow. It includes a CLI and a first stateless HTTP API. Drafts are held in memory by the client; event storage, notifications, voice input, and the mobile app are not implemented. The grocery-list idea is outside the first proof of concept.

## Documentation

- [Start and use the module](docs/usage/module-guide.md): environment setup, CLI, HTTP API, and Ollama configuration.
- [Functional requirements](docs/functional/requirements.md), [product proposals](docs/functional/product-proposals.md), and [decision log](docs/functional/decision-log.md).
- [Technology documentation](docs/technology/architecture.md): backend design, workflow, API, model integration, and prompt evaluation.
- [Development workflow](docs/technology/development-workflow.md): repository collaboration and documentation conventions.

```text
docs/
├── usage/       # How to install, start, and use the module
├── functional/  # Requirements, proposals, and product decisions
└── technology/  # Architecture, stack, evaluation, and development workflow
```

The English functional requirements in Markdown are the source for the stakeholder Word document in `docs/functional/`. Regenerate it with `python scripts/build_functional_document.py` and review its rendered pages after substantive changes; the builder requires `python-docx`, separate from the backend dependencies.
