# CortexFlow

**MCP-Powered Autonomous Enterprise Data Worker**

CortexFlow is a multi-agent system that answers complex business questions by autonomously planning, querying databases, searching documents, traversing a knowledge graph, and synthesising everything into a cited answer.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│   Planner   │  Creates a 2-5 step research plan using Groq LLM
└──────┬──────┘
       │  conditional routing (LangGraph)
       ▼
┌─────────────┐     ┌─────────────────────────────────────────┐
│  SQL Agent  │────▶│  Database MCP Server (port 8001)        │
└─────────────┘     │  Tools: get_schema, query_database,     │
       │            │         describe_table, get_regional_sales│
┌─────────────┐     └─────────────────────────────────────────┘
│ Researcher  │────▶┌─────────────────────────────────────────┐
└─────────────┘     │  Knowledge MCP Server (port 8002)       │
       │            │  Tools: search_documents, get_document, │
┌─────────────┐     │         find_policy                     │
│   Critic    │     └─────────────────────────────────────────┘
└─────────────┘     ┌─────────────────────────────────────────┐
       │            │  Analytics MCP Server (port 8003)       │
┌─────────────┐     │  Tools: calculate_growth, compare_periods│
│  Responder  │     │         generate_chart                  │
└──────┬──────┘     └─────────────────────────────────────────┘
       │
       ▼
  Final Answer + Sources + Chart
```

### Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq (llama-3.3-70b-versatile) |
| Agent framework | LangGraph |
| Tool protocol | MCP (custom HTTP servers) |
| Vector database | Qdrant |
| Relational database | PostgreSQL + pgvector |
| Knowledge graph | Neo4j |
| Cache | Redis |
| Backend | FastAPI + Python 3.11 |
| Frontend | Next.js 14 + TypeScript + Tailwind |
| Infra | Docker Compose (local) / AWS ECS (prod) |

---

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 18+
- A free Groq API key from [console.groq.com](https://console.groq.com)

### 1. Clone and configure

```bash
git clone https://github.com/yourname/cortexflow.git
cd cortexflow
cp .env.example .env
# Edit .env and set GROQ_API_KEY=gsk_...
```

### 2. Start all services

```bash
docker-compose up -d
```

This starts: PostgreSQL, Neo4j, Qdrant, Redis, the FastAPI backend, the Next.js frontend, and all three MCP servers.

Wait ~30 seconds for all services to be healthy.

### 3. Seed the knowledge graph and documents

```bash
# Install local Python deps for seeding (or run inside the backend container)
pip install neo4j sentence-transformers qdrant-client

# Seed the Neo4j knowledge graph
python data/seed/seed_graph.py

# Index the sample documents into Qdrant
python data/seed/seed_documents.py
```

### 4. Open the UI

```
http://localhost:3000
```

---

## Demo Queries

Run these in order to showcase all capabilities:

### Query 1 — SQL Agent + Analytics
> "Compare Kerala vs Karnataka revenue in Q3 2024 vs Q3 2023"

Shows: Planner breaking the task into SQL steps → SQL Agent querying `regional_sales` → Responder citing numbers.

### Query 2 — SQL + RAG combined (the killer demo)
> "Why did revenue decline in Kerala last quarter?"

Shows: SQL Agent fetching the 21.5% decline numbers → Researcher finding the Kerala Q3 2024 analysis report → Answer combines data + business context with citations.

### Query 3 — Graph RAG
> "Which product categories are most at risk in Kerala?"

Shows: Graph traversal (Customer → Product → Category) + SQL validation → multi-source synthesised answer.

### Query 4 — Customer analysis
> "Which customers have the highest churn risk?"

Shows: SQL Agent querying `customer_health` table → Researcher finding relevant policies → Executive-style recommendation.

---

## Project Structure

```
cortexflow/
├── docker-compose.yml
├── .env.example
│
├── backend/                    # FastAPI + LangGraph agents
│   ├── agents/
│   │   ├── graph.py            # LangGraph definition + routing
│   │   ├── state.py            # Shared AgentState TypedDict
│   │   ├── planner.py          # Creates research plan
│   │   ├── sql_agent.py        # Queries PostgreSQL via MCP
│   │   ├── researcher.py       # Searches documents via MCP
│   │   ├── critic.py           # Validates evidence sufficiency
│   │   └── responder.py        # Synthesises final answer
│   ├── mcp/
│   │   └── client.py           # HTTP client for MCP servers
│   ├── rag/
│   │   ├── indexer.py          # Document chunking + Qdrant indexing
│   │   └── graph_rag.py        # Neo4j graph queries
│   ├── db/
│   │   ├── postgres.py         # Async SQLAlchemy
│   │   └── neo4j.py            # Async Neo4j driver
│   ├── api/
│   │   └── routes/
│   │       ├── chat.py         # WebSocket streaming endpoint
│   │       ├── documents.py    # Document upload
│   │       └── analytics.py    # Dashboard data
│   ├── core/
│   │   ├── config.py           # Pydantic settings
│   │   └── llm.py              # Groq LLM factory + rate limiter
│   └── tests/
│       └── test_cortexflow.py  # Unit tests
│
├── mcp-servers/                # Standalone MCP servers (HTTP)
│   ├── database/               # PostgreSQL tools
│   ├── knowledge/              # Qdrant vector search tools
│   └── analytics/              # Plotly chart + growth calc tools
│
├── frontend/                   # Next.js 14 UI
│   └── src/
│       ├── app/                # App router pages
│       ├── components/
│       │   ├── ChatInterface.tsx   # Main chat UI
│       │   ├── AgentTrace.tsx      # Live reasoning sidebar
│       │   ├── ChartDisplay.tsx    # Plotly chart renderer
│       │   └── SourceCitations.tsx # Source attribution
│       └── lib/
│           ├── websocket.ts    # WS connection factory + types
│           └── api.ts          # REST API helpers
│
├── data/
│   ├── seed/
│   │   ├── northwind.sql       # PostgreSQL schema + sample data
│   │   ├── seed_graph.py       # Neo4j knowledge graph seeder
│   │   └── seed_documents.py   # Qdrant document indexer
│   └── documents/              # Sample business documents
│       ├── reports/
│       ├── policies/
│       └── product_docs/
│
└── infra/
    └── terraform/              # AWS ECS + RDS + ElastiCache
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key | `gsk_...` |
| `GROQ_MODEL` | Primary model | `llama-3.3-70b-versatile` |
| `GROQ_FAST_MODEL` | Fast routing model | `llama-3.1-8b-instant` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql://...` |
| `NEO4J_URL` | Neo4j bolt URL | `bolt://neo4j:7687` |
| `QDRANT_URL` | Qdrant HTTP URL | `http://qdrant:6333` |
| `REDIS_URL` | Redis URL | `redis://redis:6379` |

---

## LLM Routing

| Agent | Model | Temperature | Reason |
|-------|-------|-------------|--------|
| Planner | llama-3.3-70b-versatile | 0.1 | Needs reasoning |
| SQL Agent | llama-3.3-70b-versatile | 0.0 | Needs determinism |
| Researcher | llama-3.3-70b-versatile | 0.1 | Needs comprehension |
| Critic | llama-3.3-70b-versatile | 0.1 | Needs evaluation |
| Responder | llama-3.3-70b-versatile | 0.1 | Needs synthesis |

A built-in `InMemoryRateLimiter` keeps the system within Groq's free-tier limits (30 req/min).

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Tests cover: SQL guard (SELECT-only), graph router logic, agent state shape, chunker, analytics calculations — all without external service dependencies.

---

## AWS Deployment

```bash
cd infra/terraform
terraform init
terraform apply \
  -var="db_password=your_password" \
  -var="groq_api_key=gsk_..." \
  -var="aws_region=ap-south-1"
```

Then push images via the GitHub Actions pipeline (see `.github/workflows/deploy.yml`).

---

## MCP Server Design

Each MCP server is a standalone FastAPI service exposing two endpoints:

- `GET /tools/list` — returns tool definitions (name, description, schema)
- `POST /tools/call` — executes a tool and returns `{ content: [{ type, text }] }`

This is a simplified HTTP implementation of the MCP protocol. The backend `MCPClientManager` (`backend/mcp/client.py`) calls these endpoints. Swapping any server for an official MCP implementation requires only updating the URL in config.
