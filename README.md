# DS-STAR Iterative Agent

Minimal-but-real DS-STAR-style iterative data-science agent with a pluggable LLM adapter system and a CLI. The repo structure mirrors DS-STAR agent roles to make the paper easy to follow.

## Installation

```bash
pip install -e .
```

Optional extras:

```bash
pip install -e ".[dev,xlsx,dotenv,rich]"
```

## Run with mock provider

```bash
python -m dsstar run --question "Create a python script that writes hello.txt" --provider mock
```

## Run with OpenAI

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
python -m dsstar run --question "Summarize the dataset" --provider openai
```

If `OPENAI_API_KEY` is missing, DS-STAR falls back to the mock provider with a warning.

## Run with Gemini

```bash
export GEMINI_API_KEY="..."
export GEMINI_MODEL="gemini-1.5-flash"
python -m dsstar run --question "Summarize the dataset" --provider gemini
```

If `GEMINI_API_KEY` is missing, DS-STAR falls back to the mock provider with a warning.

## Local provider (planned GPU support)

The `local` provider is a stub adapter for future GPU/local inference (vLLM/Ollama/Transformers).
It currently raises a friendly error. Environment variables such as `LOCAL_LLM_ENDPOINT` or
`LOCAL_LLM_MODEL` are reserved for future integration.

## Run artifacts

Each run writes to `./runs/<timestamp>/`:

- `run_metadata.json`: provider/model/question/files metadata
- `descriptions.json`: file inspection output
- `plan.json`: evolving plan steps
- `round_XX_prompt.txt`: prompt per round (coder prompts)
- `round_XX_code.py`: generated script per round
- `round_XX_exec.json`: execution stdout/stderr/exit_code/duration
- `final_answer.md`: final answer text
