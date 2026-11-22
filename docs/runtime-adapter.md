# Shared runtime adapter (integration)

One configuration, one provider client, two parameter profiles. Lives in
[`src/runtime/adapter.py`](../src/runtime/adapter.py), owned by integration
(Shaurya); analysis quality validated by Anushree. No teammate builds a separate
provider client.

## Pinned runtime

| Setting | Value |
| --- | --- |
| Provider | OpenRouter (OpenAI-compatible); also DashScope / self-host |
| Endpoint | `POST https://openrouter.ai/api/v1/chat/completions` |
| Model | `qwen/qwen-2.5-72b-instruct` |
| Prompt version | `evidence-analysis-v1` (from `stopreplay_analysis.prompting`) |
| Analysis params | `temperature 0.2`, `top_p 1.0` |
| Key / base URL | `LLM_API_KEY` (+ `OPENROUTER_API_KEY` fallback), `LLM_BASE_URL`; from `.env` (gitignored), never logged |

Changing the model id is a new prompt/eval baseline — do it deliberately.
Offline work uses `mock_mode` (no key, deterministic), which reports the provider
as `deterministic_mock`.

## For analysis (Anushree)

```python
from src.runtime.adapter import build_analysis_adapter, ModelAdapter

adapter = build_analysis_adapter()                 # uses the shared default_adapter
# offline: build_analysis_adapter(ModelAdapter(mock_mode=True))
result = adapter.generate(request)                 # -> parsed dict {outcome, finding, reason}
```

- `generate(request)` returns the model's **parsed JSON dict**, keys untouched;
  the Analyzer assigns identity/scope/status and validates cross-field rules.
- `adapter.metadata` -> provider / model_version / prompt_version / parameters_json
  for `analysis_results.runtime`.

## Error taxonomy

`LLMRuntimeError(code, message)` exposes `.code`. The analysis engine maps by
exception **type** (not by reading `.code`) and replaces the message with a fixed
string via `raise ... from None`:

| Exception | `.code` | Also a | Engine (`analyze_incremental`) maps to |
| --- | --- | --- | --- |
| `ModelRefusal` (reused from analysis) | — | — | refusal |
| `ModelTimeout` | `timeout` | `TimeoutError`, `LLMRuntimeError` | timeout |
| `ProviderError` | `provider_failure` | `LLMRuntimeError` | provider_failure |
| `InvalidModelOutput` | `invalid_output` | `LLMRuntimeError` | provider_failure |

`ModelTimeout` subclasses the builtin `TimeoutError` on purpose, so the engine's
`except TimeoutError` handler maps it to `timeout`. **Exception messages never
contain provider response bodies** — the body is read only to classify.

## For the attack side (integration)

```python
from src.runtime.adapter import generate_completion
text = generate_completion("...", system_prompt="...", temperature=0.7)
```

## Validate

```sh
python3 -m unittest tests.test_runtime -v     # mocked bridge tests, no network/key
python3 -m unittest discover -s tests         # analysis + runtime
```

## Still needed before a real eval run

- Funded `OPENROUTER_API_KEY` (or `LLM_API_KEY`).
- Confirm the provider behind the slug accepts structured JSON output; the prompt
  already forbids markdown and the parser strips stray code fences.
