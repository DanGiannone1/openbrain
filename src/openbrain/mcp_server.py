"""FastMCP server instance for Open Brain."""

from fastmcp import FastMCP
from openbrain.tools.tools import register_tools

mcp = FastMCP("Open Brain")
register_tools(mcp)
