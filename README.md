# Kairos

Kairos is a personal assistant project intended to help people who procrastinate turn intentions into concrete next steps. Android is the first planned platform; Italian and English are the initial languages.

The current Python backend prepares event drafts through a multi-turn workflow. It includes a CLI and a local HTTP API with PostgreSQL-backed sessions. The database stores only the current workflow state, not a chat transcript. Event creation, notifications, voice input, and the mobile app are not implemented.

See [Start and use the module](docs/usage/module-guide.md) for the CLI and API, and [Local infrastructure setup](docs/usage/local-infrastructure.md) for Docker, PostgreSQL, and optional Ollama or Hugging Face configuration.

With the local Compose stack running, open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the developer playground. It uses the existing API and is intended for localhost development only.

## Documentation

- [Start and use the module](docs/usage/module-guide.md): Python setup, CLI, and HTTP API usage.
- [Local infrastructure setup](docs/usage/local-infrastructure.md): Docker Compose, PostgreSQL, and optional model-provider configuration.
- [Functional requirements](docs/functional/requirements.md) and [product proposals](docs/functional/product-proposals.md).
- [Technology documentation](docs/technology/architecture.md): backend design, workflow, API, model integration, and prompt evaluation.

```text
docs/
├── usage/       # Module setup and use, plus local infrastructure
├── functional/  # Requirements and product proposals
└── technology/  # Architecture, stack, and evaluation
```

The English functional requirements in Markdown are the source for the stakeholder Word document in `docs/functional/`. Regenerate it with `python scripts/build_functional_document.py` and review its rendered pages after substantive changes; the builder requires `python-docx`, separate from the backend dependencies.
