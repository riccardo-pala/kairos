# Event workflow prompt evaluation

One comparison of the baseline prompt and a compact candidate was run against local `qwen3:8b`, using six synthetic scenarios and nine turns per variant. The candidate uses 17% fewer words, but the measured mean input saving across nine paired turns was 17.2 tokens, about 1.4% of the baseline. End-to-end time differed by 136.8 ms in favor of the candidate in this single run; this sample does not establish a latency improvement. All responses were tool-only, so first-text latency was `null`.

Structural and scenario checks passed for 2/6 baseline cases and 3/6 candidate cases. This count is not a complete quality measure. The candidate regressed on prompt injection by adding an unsupported duration and ignoring the user's explicit no-reminder choice. Both prompts failed language-switch precision on the corpus, and neither asked a useful clarification for the ambiguous date. The runtime therefore continues to use the baseline prompt.

The comparison used `think: false`, temperature 0, and seed 42 for repeatability; the application leaves inference settings at the model default. Paired multi-turn rows can have different context after the model responses diverge. One run with nine turns per variant is too small for statistical latency claims and does not predict production behavior.

The [full reproducible report](../../backend/evals/results/qwen3-8b-prompt-comparison.md) contains prompt hashes, outputs, checks, metrics, limitations, and the command to rerun it.
