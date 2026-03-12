"""Entry point for Open Brain MCP Server.

Usage:
    # Local (stdio) - for Claude CLI
    uv run python -m openbrain

    # Streamable HTTP - for Azure Container Apps
    uv run python -m openbrain --transport streamable-http --host 0.0.0.0 --port 8000
"""

import argparse
import logging
import os


def main():
    parser = argparse.ArgumentParser(description="Open Brain MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument("--path", default="/mcp", help="MCP endpoint path (default: /mcp)")
    args = parser.parse_args()

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("openbrain")

    from openbrain.mcp_server import mcp

    if args.transport == "streamable-http":
        logger.info(
            f"Starting Open Brain MCP Server ({args.transport}) on {args.host}:{args.port}{args.path}"
        )
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path,
            stateless_http=True,
        )
    else:
        logger.info("Starting Open Brain MCP Server (stdio)")
        mcp.run()


if __name__ == "__main__":
    main()
