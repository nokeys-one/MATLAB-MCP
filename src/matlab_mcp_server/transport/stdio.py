import logging
from ..config import Settings
from ..server import create_server

logger = logging.getLogger(__name__)


def run_stdio(settings: Settings):
    logger.info("Starting MATLAB MCP Server in stdio mode")
    mcp = create_server(settings)
    mcp.run(transport="stdio")
