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
                "opp_amount": {"type": "number", "description": "Opportunity amount (lead value)"},
                "opp_percent": {"type": "number", "description": "Opportunity win probability (%)"},
                "opp_status": {"type": "integer", "description": "Opportunity status id (from the opportunity-status dictionary)"},
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
    Tool(
        name="get_project_contacts",
        description="List the contacts assigned to a project. Requires Dolibarr 23.0+.",
        inputSchema={
            "type": "object",
            "properties": {"project_id": {"type": "integer", "description": "Project ID"}},
            "required": ["project_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="add_project_contact",
        description="Assign a contact to a project. Requires Dolibarr 23.0+.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "Project ID"},
                "contact_id": {"type": "integer", "description": "Contact/user ID (fk_socpeople)"},
                "type_contact": {"type": "string", "description": "Role code, e.g. PROJECTLEADER or PROJECTCONTRIBUTOR"},
                "source": {"type": "string", "enum": ["internal", "external"], "description": "'internal' (Dolibarr user) or 'external' (third-party contact)"},
            },
            "required": ["project_id", "contact_id", "type_contact", "source"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="remove_project_contact",
        description="Unassign a contact from a project. Requires Dolibarr 23.0+.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "Project ID"},
                "contact_id": {"type": "integer", "description": "Contact ID"},
                "type_contact": {"type": "string", "description": "Role code used when assigning"},
            },
            "required": ["project_id", "contact_id", "type_contact"],
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


async def get_project_contacts(ctx: ToolContext):
    return await ctx.client.get_project_contacts(ctx.arguments["project_id"])


async def add_project_contact(ctx: ToolContext):
    return await ctx.client.add_project_contact(
        ctx.arguments["project_id"], ctx.arguments["contact_id"],
        ctx.arguments["type_contact"], ctx.arguments["source"],
    )


async def remove_project_contact(ctx: ToolContext):
    return await ctx.client.remove_project_contact(
        ctx.arguments["project_id"], ctx.arguments["contact_id"], ctx.arguments["type_contact"],
    )


HANDLERS = {
    "get_projects": get_projects,
    "get_project_by_id": get_project_by_id,
    "search_projects": search_projects,
    "create_project": create_project,
    "update_project": update_project,
    "delete_project": delete_project,
    "get_project_contacts": get_project_contacts,
    "add_project_contact": add_project_contact,
    "remove_project_contact": remove_project_contact,
}
