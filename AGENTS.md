# Repository Guidelines

## Process Improvements
- Always review existing modules in `app/` to understand domain-specific utilities before introducing new helpers.
- Prefer reusing shared services located in `app/services/` and shared utilities in `app/utils/` when implementing new features.
- Document any new environment variables in `README.md` and reflect them in configuration loaders under `app/config.py`.

## Systemic Adjustments
- When touching retrieval or ingestion logic, ensure that both `app/retrieval.py` and `app/ingest.py` continue to respect the same interface contracts exposed through the service layer.
- Use structured logging utilities defined in `app/logging_config.py` for new background jobs or CLI scripts.
- Keep schema updates synchronized between `app/schemas.py` and any corresponding data store adapters within `app/store/`.

## Testing & QA
- Run the relevant unit or integration tests prior to committing changes; add new tests under `app/tests/` when new functionality is introduced.
- Validate prompts located in `app/prompting.py` with sample conversations to confirm expected behavior.
