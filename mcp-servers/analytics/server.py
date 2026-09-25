"""
Analytics MCP Server — exposes analytics and chart generation tools over HTTP.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import plotly.express as px
import json

app = FastAPI(title="CortexFlow Analytics MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOOLS = [
    {
        "name": "calculate_growth",
        "description": "Calculate percentage growth between two periods for a metric.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_value": {"type": "number"},
                "previous_value": {"type": "number"},
                "metric_name": {"type": "string"},
            },
            "required": ["current_value", "previous_value"],
        },
    },
    {
        "name": "compare_periods",
        "description": "Compare a metric across two time periods for multiple categories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "metric": {"type": "string"},
                "period1_label": {"type": "string"},
                "period2_label": {"type": "string"},
            },
            "required": ["data", "metric"],
        },
    },
    {
        "name": "generate_chart",
        "description": "Generate a Plotly chart from data. Returns chart JSON for frontend rendering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "pie"]},
                "data": {"type": "array"},
                "x_field": {"type": "string"},
                "y_field": {"type": "string"},
                "title": {"type": "string"},
                "color_field": {"type": "string"},
            },
            "required": ["chart_type", "data", "x_field", "y_field", "title"],
        },
    },
]


@app.get("/tools/list")
async def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call")
async def call_tool(request: dict):
    name = request.get("name")
    arguments = request.get("arguments", {})

    try:
        if name == "calculate_growth":
            current = float(arguments["current_value"])
            previous = float(arguments["previous_value"])
            metric = arguments.get("metric_name", "metric")

            if previous == 0:
                return {"content": [{"type": "text", "text": "Cannot calculate growth from zero baseline"}]}

            growth = ((current - previous) / previous) * 100
            direction = "increased" if growth > 0 else "decreased"

            result = {
                "metric": metric,
                "current_value": current,
                "previous_value": previous,
                "growth_percent": round(growth, 2),
                "direction": direction,
                "summary": f"{metric} {direction} by {abs(growth):.1f}%",
            }
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

        elif name == "compare_periods":
            data = arguments["data"]
            metric = arguments["metric"]
            p1 = arguments.get("period1_label", "Period 1")
            p2 = arguments.get("period2_label", "Period 2")

            comparisons = []
            for item in data:
                v1 = float(item.get("period1_value", 0))
                v2 = float(item.get("period2_value", 0))
                change = ((v2 - v1) / v1 * 100) if v1 != 0 else 0
                comparisons.append({
                    "category": item.get("category"),
                    p1: v1,
                    p2: v2,
                    "change_percent": round(change, 2),
                    "trend": "📈" if change > 0 else ("📉" if change < 0 else "➡️"),
                })

            comparisons.sort(key=lambda x: x["change_percent"])
            return {"content": [{"type": "text", "text": json.dumps(comparisons, indent=2)}]}

        elif name == "generate_chart":
            chart_type = arguments["chart_type"]
            data = arguments["data"]
            x_field = arguments["x_field"]
            y_field = arguments["y_field"]
            title = arguments["title"]
            color_field = arguments.get("color_field")

            if not data:
                return {"content": [{"type": "text", "text": "No data provided for chart"}]}

            df = pd.DataFrame(data)

            # Coerce numeric fields
            if y_field in df.columns:
                df[y_field] = pd.to_numeric(df[y_field], errors="coerce")

            if chart_type == "bar":
                fig = px.bar(df, x=x_field, y=y_field, title=title,
                             color=color_field, barmode="group")
            elif chart_type == "line":
                fig = px.line(df, x=x_field, y=y_field, title=title,
                              color=color_field, markers=True)
            elif chart_type == "pie":
                fig = px.pie(df, names=x_field, values=y_field, title=title)
            else:
                fig = px.bar(df, x=x_field, y=y_field, title=title)

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8e8f0"),
            )

            chart_json = fig.to_json()
            return {"content": [{"type": "text", "text": chart_json}]}

        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-analytics"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
