# Configuration

The Dolibarr MCP server reads configuration from environment variables. Use a
`.env` file during development or configure the variables directly in the MCP
host application that will launch the server.

| Variable | Description |
| --- | --- |
| `DOLIBARR_URL` / `DOLIBARR_SHOP_URL` | Base API URL, e.g. `https://your-dolibarr.example.com/api/index.php` (legacy configs that still export `DOLIBARR_BASE_URL` are also honoured). |
| `DOLIBARR_API_KEY` | Personal Dolibarr API token assigned to your user. |
| `LOG_LEVEL` | Optional logging level (`INFO`, `DEBUG`, `WARNING`, …). |
| `ALLOW_REF_AUTOGEN` | When `true`, the wrapper auto-generates missing `ref` values for create operations. |
| `REF_AUTOGEN_PREFIX` | Prefix used for generated references (default `AUTO`). |
| `DEBUG_MODE` | When `true`, request/response bodies are logged without secrets. |
| `MAX_RETRIES` | Retries for transient HTTP errors (default `2`). |
| `RETRY_BACKOFF_SECONDS` | Base backoff for retries (default `0.5`). |

## Example `.env`

```env
DOLIBARR_URL=https://your-dolibarr.example.com/api/index.php
DOLIBARR_API_KEY=your_api_key
LOG_LEVEL=INFO
ALLOW_REF_AUTOGEN=true
REF_AUTOGEN_PREFIX=AUTO
DEBUG_MODE=false
```

The [`Config` class](../src/dolibarr_mcp/config.py) is built with
`pydantic-settings`. It validates the values on load, applies alias support for
legacy variable names and raises a descriptive error if placeholder credentials
are detected.

## Required Dolibarr permission (capability gating)

The server is capability-aware: at startup it reads the rights of the user behind
`DOLIBARR_API_KEY` (via `GET /users/info?includepermissions=1`) and only allows
each tool if that user actually holds the matching Dolibarr permission. Tools the
user cannot use stay listed but are flagged as unavailable, and calling them
returns an explicit "permission denied" message instead of an opaque error.

Reading those rights itself requires one permission, so it is **mandatory** for
every MCP user:

> **User / Users / "Create/modify its own user info"** (`user.self.creer`)

Without it, `/users/info` returns `403`, the server cannot determine the user's
capabilities, and it refuses to start. This permission is harmless on its own
(it only lets the user edit its own profile) and does not grant access to any
business data. Administrators bypass the check entirely and get every tool.

## Testing credentials

Use the standalone helper to verify that the credentials are accepted by
Dolibarr before wiring the server into your MCP host:

```bash
python -m dolibarr_mcp.test_connection --url https://your-dolibarr.example.com/api/index.php --api-key YOUR_KEY
```
