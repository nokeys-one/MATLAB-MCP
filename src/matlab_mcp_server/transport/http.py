import logging
from ..config import Settings
from ..server import create_server

logger = logging.getLogger(__name__)


def run_http(settings: Settings):
    logger.info(
        "Starting MATLAB MCP Server in HTTP mode on %s:%s",
        settings.http_bind,
        settings.http_port,
    )
    mcp = create_server(settings)

    if not settings.http_token:
        logger.warning(
            "No HTTP token configured. Set MATLAB_MCP_HTTP_TOKEN for authentication."
        )

    mcp.run(
        transport="streamable-http",
        host=settings.http_bind,
        port=settings.http_port,
    )
