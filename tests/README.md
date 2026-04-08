# Test Suite

This directory contains project-level tests (not virtualenv dependency tests).

## Run

```bash
python -m pytest tests -q
```

## Coverage goals
- Contract checks for required endpoints and metric names.
- Repository structure checks for demo deliverables.
- Fast smoke tests that run in CI/local without requiring full Docker startup.
