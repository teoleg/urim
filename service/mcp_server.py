"""Urim MCP server: the same pricing service as the REST API, as MCP tools.

Local:  python -m service.mcp_server          (stdio, used by .mcp.json)
Remote: mounted at /mcp by service.app          (streamable HTTP, stateless)
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from service import core

mcp = MCPServer(
    name="urim",
    version=core.VERSION,
    instructions=(
        "Prices European equity options from identified market snapshots. Never invent market data: "
        "call list_snapshots and use a snapshot_id. Never assume conventions: call list_packs, choose a "
        "pack, and tell the user which pack (and its day count and calendar) the price used."
    ),
)


@mcp.tool()
def list_packs() -> dict:
    """List the named convention packs (day count, calendar, exercise style, compounding, settlement)."""
    return core.list_packs()


@mcp.tool()
def list_snapshots() -> list[dict]:
    """List available market snapshots: snapshot_id, as_of date, underlying, and whether the data is synthetic."""
    return core.list_snapshots()


@mcp.tool()
def price_european_option(snapshot_id: str, option_type: str, strike: float, expiry: str, pack: str) -> dict:
    """Price a European equity option and return price, Greeks and full provenance.

    Args:
        snapshot_id: ID from list_snapshots. Raw market numbers are not accepted.
        option_type: "call" or "put".
        strike: strike price, > 0.
        expiry: ISO date (YYYY-MM-DD); must be a business day in the pack's calendar and after as_of.
        pack: convention pack name from list_packs. Required; there is no default.
    """
    try:
        return core.price_european_option(snapshot_id, option_type, strike, expiry, pack)
    except (core.BadRequest, core.NotFound) as exc:
        # anticipated refusals reach the model with their reason; real crashes stay generic
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
