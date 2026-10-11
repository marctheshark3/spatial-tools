# Contributing

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run python scripts/evaluate.py
```

Include a small synthetic reproduction and an independent expected result when
changing geometry behavior. Preserve strict parsing and conservative outcomes.
Document the assumptions behind a result and distinguish runtime correctness from
model behavior. Do not upload private scenes or agent transcripts.

Keep schema version 1 backward compatible; an incompatible contract needs a new
version. The skill should guide the agent to reliable tools and fresh observations,
without embedding the runtime implementation into its instructions.

Contributions are provided under the project's Apache-2.0 license. Keep third-party
notices with any reused material and describe its provenance.
