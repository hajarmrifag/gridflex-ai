"""GridFlex API and production SPA host. Run: uvicorn api.main:app."""

from pathlib import Path
from threading import BoundedSemaphore
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from . import service
from .models import OptimizeRequest, ScenarioRequest, StressRequest

app = FastAPI(
    title="GridFlex simulation API", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json"
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
compute_slots = BoundedSemaphore(2)


class BodyLimitMiddleware:
    """Bound JSON input before FastAPI reads it, including chunked requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 16_384:
                return await JSONResponse({"detail": "Request body exceeds 16 KB"}, status_code=413)(
                    scope, receive, send
                )
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


app.add_middleware(BodyLimitMiddleware)


@app.middleware("http")
async def response_headers(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    response.headers["Server-Timing"] = f"total;dur={(perf_counter() - start) * 1000:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    )
    if request.url.path == "/api/docs":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'"
        )
    return response


@app.exception_handler(ValueError)
async def invalid_input(_request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
async def infeasible(_request, _exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "The optimizer could not solve these constraints. "
            "Try disabling terminal charge restoration or reducing the horizon."
        },
    )


def compute(function, *args):
    if not compute_slots.acquire(blocking=False):
        raise HTTPException(
            503, "The simulation engine is busy. Try again shortly.", headers={"Retry-After": "2"}
        )
    try:
        return function(*args)
    finally:
        compute_slots.release()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/simulate")
def simulate(request: ScenarioRequest):
    return compute(service.simulation, request)


@app.post("/api/compare")
def compare(request: ScenarioRequest):
    return compute(service.comparison, request)


@app.post("/api/forecast")
def forecast(request: ScenarioRequest):
    return compute(service.forecast, request.profile, request.days)


@app.post("/api/optimize")
def optimize(request: OptimizeRequest):
    return compute(service.optimized, request)


@app.post("/api/stress")
def stress(request: StressRequest):
    return compute(service.stressed, request)


static = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if static.is_dir():
    app.mount("/", StaticFiles(directory=static, html=True), name="workspace")
