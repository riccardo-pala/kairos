# Event workflow prompt comparison

This is a small local-model experiment, not a production latency or quality guarantee. It compares the exact earlier prompt with the current compact candidate through the existing Ollama provider, workflow and tool registry. The corpus has six synthetic scenarios (nine turns in the baseline and candidate runs): complete event, single-field update, reminder replacement, ambiguous date, a four-turn language sequence, and prompt injection. Two warm-up calls, one per prompt, were excluded. Variant order alternated by scenario.

| Measure | Baseline | Compact candidate |
| --- | ---: | ---: |
| Prompt words / characters | 354 / 2,352 | 293 / 2,052 |
| Tool schema characters | 2,719 | 2,719 |
| Prompt tokens, mean / total | 1,189.2 / 10,703 | 1,172.0 / 10,548 |
| Paired input-token savings, mean per matching turn | — | 17.2 tokens (9 paired turns) |
| Output tokens, mean / total | 60.9 / 548 | 57.7 / 519 |
| Deterministic scenario checks passed | 2 / 6 | 3 / 6 |
| End-to-end time, mean / median | 3,288 / 3,239 ms | 3,152 / 2,975 ms |
| First text response | none in 9 turns | none in 9 turns |

The prompt is 17.2% shorter by word count and 12.8% by character count, but the measured paired input-token reduction is only 1.4% of the baseline mean. The candidate fixed the baseline's over-patching in the single-field update, but introduced a prompt-injection scenario failure by adding an unsupported 60-minute duration and omitting the user's explicit no-reminder selection. Both prompts failed to select English for the initial substantive English event and both failed the French-to-English language sequence. Therefore this candidate is not a quality-safe replacement for the baseline, despite one additional passing deterministic scenario check. The application continues to use the baseline prompt; the compact candidate is retained only for evaluation.

Manual review also found that both prompts omitted the ambiguous `03/04` date but asked for time and place instead of resolving the date ambiguity. The automatic ambiguity check only measures that the date was omitted and a clarification was requested; it does not claim the question resolved the ambiguity. The language sequence questions were in Italian throughout, including after the French input, so the model did not demonstrate the required fallback. All responses were tool-only; there was no streamed text sample to time or review.

The comparison used `qwen3:8b` on local Ollama with `think: false`, temperature 0 and seed 42 for repeatability. These are evaluation-only settings; the application continues to use the model's default inference settings. Nine turns per variant and one run are too few for statistical latency claims. End-to-end values include local request/workflow overhead and do not predict production latency. Paired multi-turn rows are matched by scenario and turn index; after divergent model behavior, later turns may have different conversational context.

The JSON report contains the exact prompt texts and SHA-256 digests, per-turn tool arguments, state, checks, Ollama counters and timings: [`qwen3-8b-prompt-comparison.json`](qwen3-8b-prompt-comparison.json). The original baseline prompt is separately preserved in [`event-v1-baseline.txt`](../prompts/event-v1-baseline.txt). A compact-only follow-up trial is in [`qwen3-8b-compact-candidate.json`](qwen3-8b-compact-candidate.json).

Re-run from `backend/` with a local Ollama service and the model already installed:

```bash
.venv/bin/python evals/run_event_prompt_benchmark.py --model qwen3:8b
```

Official protocol references: [Ollama chat API](https://docs.ollama.com/api/chat) and [Ollama API usage and metrics](https://docs.ollama.com/api/usage).
