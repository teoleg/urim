"""REST + MCP service: same guardrails, same numbers as the engine."""
import asyncio
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import Client

from service.app import app
from service.mcp_server import mcp

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = json.loads((ROOT / "tests" / "golden" / "expected" / "SYN-EQ-2026-09-24.json").read_text())
REQ = {"snapshot_id": "SYN-EQ-2026-09-24", "option_type": "call", "strike": 100.0,
       "expiry": "2027-09-24", "pack": "EQ-EURO-US-v1"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --- REST --------------------------------------------------------------------------------

def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["service"] == "urim" and "commit" in body


def test_lists(client):
    assert "EQ-EURO-US-v1" in client.get("/packs").json()
    ids = {s["snapshot_id"] for s in client.get("/snapshots").json()}
    assert {"SYN-EQ-2026-09-24", "SYN-EQ-2026-09-24-Q0"} <= ids


def test_price_matches_golden_and_carries_provenance(client):
    body = client.post("/price", json=REQ).json()
    assert body["price"] == pytest.approx(GOLDEN["results"]["call-atm-1y"]["price"], rel=1e-12)
    assert body["snapshot_id"] == "SYN-EQ-2026-09-24" and body["as_of"] == "2026-09-24"
    assert body["conventions"]["day_count"] == "ACT/365F" and body["synthetic_data"] is True
    assert body["service"]["service"] == "urim"


@pytest.mark.parametrize("change,status,fragment", [
    ({"pack": None}, 422, ""),                               # pack is required by the schema
    ({"pack": "NOPE"}, 422, "unknown convention pack"),
    ({"snapshot_id": "NOPE"}, 404, "unknown snapshot_id"),
    ({"snapshot_id": "../../pyproject"}, 422, "invalid snapshot_id"),
    ({"expiry": "2026-12-26"}, 422, "not a business day"),
    ({"expiry": "2026-09-01"}, 422, "after snapshot"),
    ({"option_type": "straddle"}, 422, ""),
    ({"strike": -1}, 422, ""),
])
def test_price_refusals(client, change, status, fragment):
    body = {**REQ, **change}
    if body["pack"] is None:
        del body["pack"]
    r = client.post("/price", json=body)
    assert r.status_code == status, r.text
    assert fragment in r.text


def test_unknown_path_reports_what_the_app_received(client):
    """Hosting/routing problems must be diagnosable: a 404 echoes the path the app saw."""
    r = client.get("/api/index/health")
    assert r.status_code == 404 and r.json()["path"] == "/api/index/health"


def test_unknown_snapshot_404_keeps_its_reason(client):
    r = client.post("/price", json={**REQ, "snapshot_id": "NOPE"})
    assert r.status_code == 404 and "unknown snapshot_id" in r.json()["detail"]


def test_raw_market_numbers_are_not_accepted(client):
    """Extra fields like spot/vol are ignored: prices come only from the identified snapshot."""
    a = client.post("/price", json=REQ).json()
    b = client.post("/price", json={**REQ, "spot": 1.0, "vol": 5.0}).json()
    assert a["price"] == b["price"]


# --- MCP in-process ------------------------------------------------------------------------

def _structured(result):
    data = result.structured_content or json.loads(result.content[0].text)
    return data.get("result", data)


def test_mcp_tools_in_process():
    async def go():
        async with Client(mcp) as c:
            tools = {t.name for t in (await c.list_tools()).tools}
            ok = await c.call_tool("price_european_option", REQ)
            bad = await c.call_tool("price_european_option", {**REQ, "pack": "NOPE"})
            return tools, ok, bad

    tools, ok, bad = asyncio.run(go())
    assert tools == {"list_packs", "list_snapshots", "price_european_option"}
    assert not ok.is_error
    assert _structured(ok)["price"] == pytest.approx(GOLDEN["results"]["call-atm-1y"]["price"], rel=1e-12)
    assert bad.is_error and "unknown convention pack" in bad.content[0].text


# --- MCP over real HTTP (uvicorn), incl. host checks ----------------------------------------

@pytest.fixture(scope="module")
def server_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "service.app:app", "--port", str(port)],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(150):
        try:
            if httpx.get(f"{url}/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def test_rest_over_http(server_url):
    r = httpx.post(f"{server_url}/price", json=REQ, timeout=30)
    assert r.status_code == 200 and r.json()["snapshot_id"] == "SYN-EQ-2026-09-24"


def test_mcp_over_http(server_url):
    async def go():
        async with Client(f"{server_url}/mcp") as c:
            return await c.call_tool("price_european_option", REQ)

    result = asyncio.run(go())
    assert not result.is_error
    assert _structured(result)["snapshot_id"] == "SYN-EQ-2026-09-24"


def test_smoke_script_against_live_server(server_url):
    proc = subprocess.run([sys.executable, "tools/smoke.py", server_url, "--expect-commit", "unknown"],
                          cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SMOKE: PASS" in proc.stdout


def test_smoke_script_fails_on_wrong_commit(server_url):
    proc = subprocess.run([sys.executable, "tools/smoke.py", server_url, "--expect-commit", "deadbeef"],
                          cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 1 and "FAIL  health" in proc.stdout


def test_mcp_stdio_server_as_configured_in_mcp_json():
    """Launch exactly what .mcp.json launches, from a different working directory."""
    from mcp import StdioServerParameters

    cfg = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["urim"]
    command = cfg["command"].replace("${CLAUDE_PROJECT_DIR:-.}", str(ROOT))
    params = StdioServerParameters(command=command, args=cfg["args"], cwd="/tmp")

    async def go():
        async with Client(params) as c:
            return await c.call_tool("list_packs", {})

    result = asyncio.run(go())
    assert not result.is_error and "EQ-EURO-US-v1" in result.content[0].text


def test_mcp_rejects_foreign_host_header(server_url):
    r = httpx.post(f"{server_url}/mcp",
                   headers={"Host": "evil.example", "Accept": "application/json, text/event-stream",
                            "Content-Type": "application/json"},
                   json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, timeout=30)
    assert r.status_code in (400, 403, 421), r.status_code
