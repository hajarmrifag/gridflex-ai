# Contributing

Use Python 3.11 or newer and Node 24. Follow the setup in the README, then create a branch for your change.

Keep simulation logic in `src/`, request validation in `api/models.py`, and orchestration in `api/service.py`. The frontend consumes API results; it must not implement a second version of the scientific model.

For numerical changes, add a regression that checks the underlying invariant: energy conservation, battery constraints, chronological evaluation or an optimization bound. Document changes to assumptions and regenerate affected research outputs.

Before opening a pull request, run:

```bash
pytest
ruff check .
npm run format:check --prefix frontend
npm run build --prefix frontend
cd frontend && npm test
```

The browser suite requires Chromium (`npx playwright install chromium`). CI also builds and smoke-tests the production container. Describe the behavior change and validation in the pull request. Include screenshots when changing the interface.

Do not commit credentials, local environments, build output or private datasets. Preserve the attribution and licensing of bundled public data.
