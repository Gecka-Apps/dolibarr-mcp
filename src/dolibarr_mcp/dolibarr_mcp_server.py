"""Professional Dolibarr MCP Server with comprehensive CRUD operations."""

import asyncio
import json
import sys
import logging
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

# Import MCP components
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent

# Import our Dolibarr components
from .config import Config
from .dolibarr_client import DolibarrClient, DolibarrAPIError
from .response_shaper import format_response, get_properties_param, TOOL_RESPONSE_CONFIG
from .analytics import (
    AnalyticsUnavailableError,
    ANALYTICS_TOOLS,
    analytics_available,
)
from .capabilities import Capabilities, MissingUserInfoPermission
from .tools import ALL_TOOLS, ALL_HANDLERS
from .tools.base import ToolContext

# HTTP transport imports
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send
import uvicorn


# Configure logging to stderr so it doesn't interfere with MCP protocol
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise in MCP communication
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)

# Create server instance
server = Server("dolibarr-mcp")

# Rights of the Dolibarr user behind the API token, resolved once at startup.
# Gates which tools are advertised and which calls are allowed.
CAPABILITIES: Capabilities | None = None

# Whether the direct SQL analytics layer is usable, resolved once at startup.
# None means "not yet checked" (annotation is skipped, e.g. in tests).
ANALYTICS_AVAILABLE: bool | None = None


def _unavailable_reason(tool_name: str) -> str | None:
    """Why *tool_name* cannot be used right now, or None if it is available.

    Two independent gates: the API user's Dolibarr rights (permission takes
    precedence, it is the more fundamental reason) and, for the SQL-backed
    analytics tools, whether the database connection is configured and reachable.
    """
    if CAPABILITIES is not None and not CAPABILITIES.is_allowed(tool_name):
        return CAPABILITIES.denial_message(tool_name)
    if tool_name in ANALYTICS_TOOLS and ANALYTICS_AVAILABLE is False:
        return (
            "analytics require a database connection; set DB_HOST, DB_NAME, "
            "DB_USER (and install the [analytics] extra)"
        )
    return None


def _annotate_unavailable(tools):
    """Flag tools that cannot be used right now, keeping them visible.

    Tools stay advertised so the agent (and user) get an explicit reason instead
    of a silent absence, but their description warns upfront. Returns copies so the
    shared registry definitions in ALL_TOOLS are never mutated.
    """
    annotated = []
    for tool in tools:
        reason = _unavailable_reason(tool.name)
        if reason:
            tool = tool.model_copy(update={"description": f"{tool.description} [UNAVAILABLE: {reason}]"})
        annotated.append(tool)
    return annotated


@server.list_tools()
async def handle_list_tools():
    """List all available tools."""
    return _annotate_unavailable(list(ALL_TOOLS))


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle all tool calls using the DolibarrClient."""

    try:
        # Refuse calls the API user has no rights for, with an explicit reason.
        if CAPABILITIES is not None and not CAPABILITIES.is_allowed(name):
            return [TextContent(type="text", text=json.dumps({
                "error": "PermissionDenied",
                "status": 403,
                "message": CAPABILITIES.denial_message(name),
                "missing_permissions": CAPABILITIES.missing(name),
            }, separators=(",", ":")))]

        # Initialize the config and client
        config = Config()

        # Compute server-side field selection via Dolibarr ?properties= param
        properties = get_properties_param(
            TOOL_RESPONSE_CONFIG.get(name, {}).get("entity_type"),
            TOOL_RESPONSE_CONFIG.get(name, {}).get("field_set", "full"),
            [f.strip() for f in arguments["fields"].split(",") if f.strip()]
            if arguments.get("fields") else None,
        )

        async with DolibarrClient(config) as client:

            if name in ALL_HANDLERS:
                ctx = ToolContext(client=client, arguments=arguments, config=config, properties=properties)
                result = await ALL_HANDLERS[name](ctx)
            else:
                result = {"error": f"Unknown tool: {name}"}

        return format_response(
            result,
            tool_name=name,
            arguments=arguments,
            max_response_chars=config.max_response_chars,
        )

    except AnalyticsUnavailableError as e:
        return [TextContent(type="text", text=json.dumps(
            {"error": "Analytics Unavailable", "message": str(e)},
            separators=(",", ":"),
        ))]

    except DolibarrAPIError as e:
        error_payload = e.response_data or {
            "error": "Dolibarr API Error",
            "status": e.status_code or 500,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return [TextContent(type="text", text=json.dumps(error_payload, separators=(",", ":")))]

    except Exception as e:
        correlation_id = str(uuid.uuid4())
        error_result = {
            "error": "Internal Server Error",
            "status": 500,
            "message": f"Tool execution failed: {str(e)}",
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(f"Tool execution error ({correlation_id}): {e}", file=sys.stderr)
        return [TextContent(type="text", text=json.dumps(error_result, separators=(",", ":")))]


@asynccontextmanager
async def test_api_connection(config: Config | None = None):
    """Test API connection and yield client if successful."""
    created_config = False
    api_ok = False
    try:
        if config is None:
            config = Config()
            created_config = True
        
        # Check if environment variables are set
        if not config.dolibarr_url or config.dolibarr_url == "https://your-dolibarr-instance.com/api/index.php":
            print("⚠️  Warning: DOLIBARR_URL not configured in .env file", file=sys.stderr)
            print("⚠️  Using placeholder URL - API calls will fail", file=sys.stderr)
            print("📝 Please configure your .env file with valid Dolibarr credentials", file=sys.stderr)
            yield False  # Configuration incomplete
            return
            
        if not config.api_key or config.api_key == "your_dolibarr_api_key_here":
            print("⚠️  Warning: DOLIBARR_API_KEY not configured in .env file", file=sys.stderr)
            print("⚠️  API authentication will fail", file=sys.stderr)
            print("📝 Please configure your .env file with valid Dolibarr credentials", file=sys.stderr)
            yield False  # Configuration incomplete
            return
        
        async with DolibarrClient(config) as client:
            print("🧪 Testing Dolibarr API connection...", file=sys.stderr)
            result = await client.get_status()
            if 'success' in result or 'dolibarr_version' in str(result):
                print("✅ Dolibarr API connection successful", file=sys.stderr)
                print("🎯 Full CRUD operations available for all Dolibarr modules", file=sys.stderr)
                api_ok = True
            else:
                print(f"⚠️  API test returned unexpected result: {result}", file=sys.stderr)
                print("⚠️  Server will start but API calls may fail", file=sys.stderr)
                api_ok = False
    except Exception as e:
        print(f"⚠️  API test error: {e}", file=sys.stderr)
        if config is None or created_config:
            print("💡 Check your .env file configuration", file=sys.stderr)
        print("⚠️  Server will start but API calls may fail", file=sys.stderr)
        api_ok = False
    
    yield api_ok


async def _run_stdio_server(_config: Config) -> None:
    """Run the MCP server over STDIO (default)."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dolibarr-mcp",
                server_version="1.0.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


class _UrlTokenMiddleware:
    """Require a shared secret as the first path segment, then strip it.

    Requests that do not match return 404 (not 401) to avoid leaking the
    existence of a valid endpoint to scanners.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.prefix = f"/{token}"
        self.prefix_bytes = self.prefix.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path != self.prefix and not path.startswith(self.prefix + "/"):
            await Response(status_code=404)(scope, receive, send)
            return

        new_scope = dict(scope)
        new_scope["path"] = path[len(self.prefix):] or "/"
        raw_path = scope.get("raw_path")
        if raw_path:
            if raw_path.startswith(self.prefix_bytes):
                new_scope["raw_path"] = raw_path[len(self.prefix_bytes):] or b"/"
        await self.app(new_scope, receive, send)


def _build_http_app(session_manager: StreamableHTTPSessionManager) -> Starlette:
    """Create Starlette app that forwards to the StreamableHTTP session manager."""

    class ASGIEndpoint:
        """Lightweight adapter so Route treats our handler as an ASGI app."""

        def __init__(self, handler):
            self.handler = handler

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            await self.handler(scope, receive, send)

    async def options_handler(request):
        """Lightweight CORS-friendly response for preflight requests."""
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )

    async def lifespan(app):
        async with session_manager.run():
            yield

    async def asgi_handler(scope, receive, send):
        """Adapter to call the StreamableHTTPSessionManager with ASGI signature."""
        await session_manager.handle_request(scope, receive, send)

    asgi_endpoint = ASGIEndpoint(asgi_handler)

    app = Starlette(
        routes=[
            Route("/", asgi_endpoint, methods=["GET", "POST", "DELETE"]),
            Route("/{path:path}", asgi_endpoint, methods=["GET", "POST", "DELETE"]),
            Route("/", options_handler, methods=["OPTIONS"]),
            Route("/{path:path}", options_handler, methods=["OPTIONS"]),
        ],
        lifespan=lifespan,
    )

    # Allow cross-origin requests from MCP-enabled web UIs and dashboards.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    return app


async def _run_http_server(config: Config) -> None:
    """Run the MCP server over HTTP (StreamableHTTP)."""
    session_manager = StreamableHTTPSessionManager(server, json_response=False, stateless=False)
    app = _build_http_app(session_manager)
    if config.mcp_url_token:
        app = _UrlTokenMiddleware(app, config.mcp_url_token)
        print("🔒 URL token auth enabled — requests must include the secret path prefix", file=sys.stderr)
    print(
        f"🌐 Starting MCP HTTP server on {config.mcp_http_host}:{config.mcp_http_port}",
        file=sys.stderr,
    )
    uvicorn_config = uvicorn.Config(
        app,
        host=config.mcp_http_host,
        port=config.mcp_http_port,
        log_level=config.log_level.lower(),
        loop="asyncio",
        access_log=False,
    )
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()


async def main():
    """Run the Dolibarr MCP server."""
    config = Config()

    # Test API connection but don't fail if it's not working
    async with test_api_connection(config) as api_ok:
        if not api_ok:
            print("⚠️  Starting server without valid API connection", file=sys.stderr)
            print("📝 Configure your .env file to enable API functionality", file=sys.stderr)
        else:
            print("✅ API connection validated", file=sys.stderr)

    # Discover the API user's rights so tools are gated to what it can actually do.
    global CAPABILITIES
    if api_ok:
        try:
            print("🧪 Discovering Dolibarr user permissions...", file=sys.stderr)
            async with DolibarrClient(config) as client:
                CAPABILITIES = await Capabilities.fetch(client)
            scope = "administrator (all tools)" if CAPABILITIES.admin else f"{len(CAPABILITIES.rights)} modules"
            print(f"✅ Permissions resolved: {scope}", file=sys.stderr)
        except MissingUserInfoPermission as e:
            print(f"❌ {e}", file=sys.stderr)
            print("📝 Grant that permission to the MCP user in Dolibarr, then restart.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Could not resolve user permissions: {e}", file=sys.stderr)
            print("⚠️  Refusing to start without a capability check.", file=sys.stderr)
            sys.exit(1)

    # Test database connection for analytics; advertise the tools only if it works.
    global ANALYTICS_AVAILABLE
    if config.db_available:
        try:
            from .analytics import _get_connection
            print("🧪 Testing database connection...", file=sys.stderr)
            conn = await _get_connection(config)
            conn.close()
            ANALYTICS_AVAILABLE = True
            print("✅ Database connection successful", file=sys.stderr)
            print("📊 Analytics tools available (top sellers, sales summary, low stock)", file=sys.stderr)
        except Exception as e:
            ANALYTICS_AVAILABLE = False
            print(f"⚠️  Database connection failed: {e}", file=sys.stderr)
            print("⚠️  Analytics tools disabled, but API tools remain available", file=sys.stderr)
    else:
        ANALYTICS_AVAILABLE = False
        print("ℹ️  Database not configured — analytics tools disabled", file=sys.stderr)
        print("📝 Set DB_HOST, DB_NAME, DB_USER, DB_PASSWORD to enable analytics", file=sys.stderr)

    # Run server regardless of API/DB status
    print("🚀 Starting Dolibarr MCP server...", file=sys.stderr)
    print("✅ Server ready", file=sys.stderr)

    try:
        if config.mcp_transport == "http":
            await _run_http_server(config)
        else:
            await _run_stdio_server(config)
    except Exception as e:
        print(f"💥 Server error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server startup error: {e}", file=sys.stderr)
        sys.exit(1)
