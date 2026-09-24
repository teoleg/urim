"""Urim REST API (FastAPI) with the MCP server mounted at /mcp.

Local: uvicorn service.app:app --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from service import core
from service.mcp_server import mcp

LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*", "127.0.0.1", "localhost"]


def allowed_hosts() -> list[str]:
    """Hosts the MCP endpoint answers for (DNS-rebinding protection stays on)."""
    hosts = list(LOCAL_HOSTS)
    for var in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        if os.environ.get(var):
            hosts.append(os.environ[var])
    hosts += [h.strip() for h in os.environ.get("URIM_ALLOWED_HOSTS", "").split(",") if h.strip()]
    return hosts


mcp_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,  # serverless: no session state between invocations
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts(),
        allowed_origins=[f"https://{h}" for h in allowed_hosts() if "*" not in h]
        + ["http://127.0.0.1:*", "http://localhost:*"],
    ),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(mcp_app):  # starts the MCP session manager
        yield


app = FastAPI(title="Urim pricing service", version=core.VERSION, lifespan=lifespan)


class PriceRequest(BaseModel):
    snapshot_id: str = Field(description="ID from GET /snapshots; raw market numbers are not accepted")
    option_type: str = Field(pattern="^(call|put)$")
    strike: float = Field(gt=0)
    expiry: str = Field(description="ISO date, business day in the pack's calendar")
    pack: str = Field(description="convention pack name from GET /packs; required, no default")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **core.service_info()}


@app.get("/packs")
def packs() -> dict:
    return core.list_packs()


@app.get("/snapshots")
def snapshots() -> list[dict]:
    return core.list_snapshots()


@app.post("/price")
def price(req: PriceRequest) -> dict:
    try:
        return core.price_european_option(req.snapshot_id, req.option_type, req.strike, req.expiry, req.pack)
    except core.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except core.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


app.mount("/", mcp_app)  # after the REST routes, so they take precedence; serves /mcp
