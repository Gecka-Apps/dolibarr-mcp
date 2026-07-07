"""Project tools: search, CRUD, and listing."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, escape_sqlfilter, extract_list_kwargs

TOOLS: list[Tool] = [
    Tool(
        name="get_projects",
        description=(
            "Get a paginated list of projects from Dolibarr, optionally filtered by status. "
            "Use this for overviews or when you need to iterate through project pages. "
            "Do not use this to search for a project by name or reference (use search_projects instead)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of projects to return (default: 20)",
                    "default": 20,
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination (default: 1)",
                    "default": 1,
                },
                "status": {
                    "type": "integer",
                    "description": "Project status filter (e.g. 0=draft, 1=open, 2=closed)",
                    "default": 1,
                },
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_project_by_id",
        description=(
            "Get the details of exactly one project by numeric ID. "
            "Use this only when you already know the internal Dolibarr project_id. "
            "Do not pass project reference here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Exact numeric Dolibarr project ID.",
                },
                **DETAIL_PARAMS,
            },
            "required": ["project_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="search_projects",
        description=(
            "Search projects by reference or title. Use this when you have a partial or full project ref/title "
            "and need to find matching projects without loading full project lists."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for project ref or title",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 20,
                },
                "fields": LIST_PARAMS["fields"],
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_project",
        description="Create a new project",
        inputSchema={
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Project reference (optional, if Dolibarr auto-generates)",
                },
                "title": {"type": "string", "description": "Project title"},
                "description": {
                    "type": "string",
                    "description": "Project description",
                },
                "socid": {
                    "type": "integer",
                    "description": "Linked customer ID (thirdparty)",
                },
                "status": {
                    "type": "integer",
                    "description": "Project status (e.g. 1=open)",
                    "default": 1,
                },
            },
            "required": ["title"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_project",
        description="Update an existing project",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Project ID to update",
                },
                "title": {"type": "string", "description": "Project title"},
                "description": {
                    "type": "string",
                    "description": "Project description",
                },
                "status": {
                    "type": "integer",
                    "description": "Project status",
                },
            },
            "required": ["project_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_project",
        description="Delete a project",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Project ID to delete",
                }
            },
            "required": ["project_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_projects(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_projects(**lk, status=ctx.arguments.get("status"), properties=ctx.properties)


async def get_project_by_id(ctx: ToolContext):
    return await ctx.client.get_project_by_id(ctx.arguments["project_id"])


async def search_projects(ctx: ToolContext):
    query = escape_sqlfilter(ctx.arguments["query"])
    limit = ctx.arguments.get("limit", 20)
    sqlfilters = f"((t.ref:like:'%{query}%') OR (t.title:like:'%{query}%'))"
    return await ctx.client.search_projects(sqlfilters=sqlfilters, limit=limit, properties=ctx.properties)


async def create_project(ctx: ToolContext):
    return await ctx.client.create_project(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_project(ctx: ToolContext):
    args = dict(ctx.arguments)
    project_id = args.pop("project_id")
    return await ctx.client.update_project(project_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_project(ctx: ToolContext):
    return await ctx.client.delete_project(ctx.arguments["project_id"])


HANDLERS = {
    "get_projects": get_projects,
    "get_project_by_id": get_project_by_id,
    "search_projects": search_projects,
    "create_project": create_project,
    "update_project": update_project,
    "delete_project": delete_project,
}
