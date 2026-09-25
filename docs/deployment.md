# Run and deploy GridFlex

The public workspace is hosted at **https://gridflex.onrender.com/**. Deployments track `main` through the repository's Render Blueprint.

## Local production preview

```bash
pip install -e ".[api]"
npm ci --prefix frontend
npm run build --prefix frontend
OMP_NUM_THREADS=1 uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The frontend is mounted if `frontend/dist` exists at server startup. Rebuild and restart after deployment updates. Vite's port 5173 is only needed for development.

## Docker

```bash
docker build -t gridflex .
docker run --rm -p 127.0.0.1:8000:8000 gridflex
```

The multi-stage image builds with Node 24, runs on Python 3.12, excludes development dependencies, and runs the API as UID 10001 rather than root. It has a health check against `/api/health`. The runtime needs no persistent writable data volume and no provider credentials. `.dockerignore` excludes local environments, browser test artifacts and Git history.

Python runtime dependencies are pinned with hashes in `requirements-api.lock`; frontend dependencies are pinned in `frontend/package-lock.json`. CI builds the image and checks its health endpoint, frontend and a simulation request.

To refresh the Python lockfile, install `uv` in your development environment and run:

```bash
uv pip compile pyproject.toml --extra api --python-version 3.11 --universal --generate-hashes --output-file requirements-api.lock --no-header
```

Review the diff and run the full checks before committing a dependency update.

## Render

The repository includes a [Render Blueprint](https://render.com/docs/blueprint-spec), `render.yaml`, for one Docker web service on the free plan. It sets port 8000, an HTTP health check and deployment after CI checks pass.

In your Render workspace, create a Blueprint from `hajarmrifag/gridflex-ai`, select `main`, and apply `render.yaml`. The linked GitHub integration must already have repository access for automatic deployments. No database, API keys or persistent disk are required.

The free plan can sleep when idle and is suitable for a public demonstration. Account resource limits still apply. Use a sized, continuously running service for workloads requiring availability guarantees.

After deployment, verify `/api/health`, load the workspace and run a scenario. The service URL appears in the Render dashboard. For rollback, redeploy a previously tested commit from Render's deploy history; no database migration is involved.

## Hosting

Use a host that supports an always-on Python web service or Docker, with TLS at its reverse proxy. Route the frontend and API through the same origin; no wildcard CORS is configured. Expose the container's port 8000 behind that proxy. Configure request-rate and connection limits at the edge if opening the service to many users. One worker and `OMP_NUM_THREADS=1` is a conservative starting point; benchmark the host before raising concurrency.

`/api/health` is liveness, not a guarantee that an optimization is feasible. The API returns 422 for invalid scientific inputs/infeasible constraints, 413 for oversized request bodies, and 503 with `Retry-After: 2` while its two compute slots are occupied. Computations and caches are bounded per process, not per user. The optimizer allows at most 20 seconds per solve and performs two solves by default.

Snapshots live in the user's browser. Clearing site data removes them. Export JSON to retain a portable record. A share link reproduces settings on the recipient's accessible app deployment; it does not expose a localhost server to the internet.

The existing Streamlit deployment and the new React/FastAPI service are separate deployment targets. Creating or pushing a feature branch does not deploy the new workspace.
