"""
PostgreSQL MCP Server — exposes database tools over HTTP.
Runs as a standalone FastAPI service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import json
import os

app = FastAPI(title="CortexFlow Database MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cortexflow:cortexflow_dev@localhost:5432/cortexflow",
)
pool: asyncpg.Pool = None


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    print("✅ MCP-Database: PostgreSQL pool ready")


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


TOOLS = [
    {
        "name": "get_schema",
        "description": "Get the complete database schema showing all tables and columns.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "query_database",
        "description": "Execute a read-only SELECT SQL query against the business database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A valid PostgreSQL SELECT statement."}
            },
            "required": ["sql"],
        },
    },
    {
        "name": "describe_table",
        "description": "Get detailed information about a specific table including sample rows.",
        "inputSchema": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
    },
    {
        "name": "get_regional_sales",
        "description": "Get sales data filtered by region, state, quarter, and year.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "quarter": {"type": "string"},
                "year": {"type": "integer"},
            },
            "required": [],
        },
    },
]


def _json_default(obj):
    """Handle non-serializable types like Decimal and datetime."""
    import decimal
    import datetime
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    return str(obj)


@app.get("/tools/list")
async def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call")
async def call_tool(request: dict):
    name = request.get("name")
    arguments = request.get("arguments", {})

    if not pool:
        return {"content": [{"type": "text", "text": "Database pool not initialized yet"}]}

    try:
        if name == "get_schema":
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                """)
                schema: dict = {}
                for row in rows:
                    t = row["table_name"]
                    if t not in schema:
                        schema[t] = []
                    schema[t].append(f"{row['column_name']} ({row['data_type']})")

                formatted = "\n".join([
                    f"Table: {t}\n  Columns: {', '.join(cols)}"
                    for t, cols in schema.items()
                ])
                return {"content": [{"type": "text", "text": formatted}]}

        elif name == "query_database":
            sql = arguments.get("sql", "")
            if not sql.strip().upper().startswith("SELECT"):
                return {"content": [{"type": "text", "text": "ERROR: Only SELECT queries are permitted."}]}
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql)
                result = [dict(row) for row in rows[:100]]
                return {"content": [{"type": "text", "text": json.dumps(result, default=_json_default, indent=2)}]}

        elif name == "describe_table":
            table_name = arguments.get("table_name")
            async with pool.acquire() as conn:
                columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = $1 AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, table_name)
                sample = await conn.fetch(f'SELECT * FROM "{table_name}" LIMIT 3')
                result = {
                    "table": table_name,
                    "columns": [dict(c) for c in columns],
                    "sample_rows": [dict(r) for r in sample],
                }
                return {"content": [{"type": "text", "text": json.dumps(result, default=_json_default, indent=2)}]}

        elif name == "get_regional_sales":
            conditions = []
            params = []
            if arguments.get("state"):
                params.append(arguments["state"])
                conditions.append(f"state = ${len(params)}")
            if arguments.get("quarter"):
                params.append(arguments["quarter"])
                conditions.append(f"quarter = ${len(params)}")
            if arguments.get("year"):
                params.append(arguments["year"])
                conditions.append(f"year = ${len(params)}")

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            sql = f"SELECT * FROM regional_sales {where} ORDER BY year DESC, quarter DESC LIMIT 100"

            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
                result = [dict(r) for r in rows]
                return {"content": [{"type": "text", "text": json.dumps(result, default=_json_default, indent=2)}]}

        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-database"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
