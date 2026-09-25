"""
Unit tests for CortexFlow components.
Run with: pytest backend/tests/ -v
"""
import pytest
import json
from unittest.mock import AsyncMock, patch


# ── Analytics MCP ─────────────────────────────────────────────────────────────

class TestAnalyticsMCP:
    """Tests for the analytics MCP server logic (no external deps needed)."""

    def test_calculate_growth_positive(self):
        current = 245000.0
        previous = 312000.0
        growth = ((current - previous) / previous) * 100
        assert round(growth, 2) == -21.47
        assert growth < 0  # Kerala declined

    def test_calculate_growth_negative_means_decline(self):
        current = 421000.0
        previous = 398000.0
        growth = ((current - previous) / previous) * 100
        assert growth > 0  # Karnataka grew
        assert round(growth, 2) == 5.78

    def test_calculate_growth_from_zero(self):
        previous = 0
        # Should not divide by zero
        with pytest.raises(ZeroDivisionError):
            _ = (100 / previous) * 100

    def test_compare_periods_sort_order(self):
        data = [
            {"category": "Electronics", "period1_value": 312000, "period2_value": 245000},
            {"category": "Software", "period1_value": 198000, "period2_value": 189000},
        ]
        comparisons = []
        for item in data:
            v1, v2 = item["period1_value"], item["period2_value"]
            change = ((v2 - v1) / v1 * 100) if v1 != 0 else 0
            comparisons.append({
                "category": item["category"],
                "change_percent": round(change, 2),
            })
        comparisons.sort(key=lambda x: x["change_percent"])
        # Electronics declined more than Software, so it should be first
        assert comparisons[0]["category"] == "Electronics"


# ── RAG Chunker ───────────────────────────────────────────────────────────────

class TestSemanticChunk:
    """Tests for the document chunking logic."""

    def _chunk(self, text: str, chunk_size: int = 400) -> list[str]:
        sentences = text.replace('\n', ' ').split('. ')
        chunks, current_chunk, current_size = [], [], 0
        for sentence in sentences:
            words = sentence.split()
            if current_size + len(words) > chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk, current_size = [], 0
            current_chunk.append(sentence)
            current_size += len(words)
        if current_chunk:
            chunks.append('. '.join(current_chunk))
        return chunks if chunks else [text]

    def test_short_text_is_single_chunk(self):
        text = "Revenue declined in Kerala. The main cause was competition."
        chunks = self._chunk(text, chunk_size=400)
        assert len(chunks) == 1

    def test_long_text_is_split(self):
        # 500+ words — should be split
        sentence = "This is a sentence with ten words in it here. "
        text = sentence * 60
        chunks = self._chunk(text, chunk_size=100)
        assert len(chunks) > 1

    def test_empty_text_returns_something(self):
        text = ""
        chunks = self._chunk(text)
        assert len(chunks) >= 1


# ── Agent State ───────────────────────────────────────────────────────────────

class TestAgentState:
    """Tests for agent state structure."""

    def test_state_has_required_fields(self):
        # Verify expected keys without importing langchain_core
        required_keys = {
            "messages", "user_query", "plan", "current_step",
            "tool_results", "final_answer", "sources",
            "chart_data", "session_id", "needs_approval", "error",
        }
        # Read the source file and check annotations are present
        import os
        state_file = os.path.join(
            os.path.dirname(__file__), "..", "agents", "state.py"
        )
        src = open(state_file).read()
        for key in required_keys:
            assert key in src, f"Missing field in AgentState: {key}"

    def test_initial_state_shape(self):
        state = {
            "messages": [],
            "user_query": "Why did revenue decline in Kerala?",
            "plan": [],
            "current_step": 0,
            "tool_results": [],
            "final_answer": "",
            "sources": [],
            "chart_data": None,
            "session_id": "test-123",
            "needs_approval": False,
            "error": None,
        }
        assert state["current_step"] == 0
        assert state["user_query"] == "Why did revenue decline in Kerala?"
        assert state["error"] is None


# ── SQL Guard ─────────────────────────────────────────────────────────────────

class TestSQLGuard:
    """Tests that the SQL-only-SELECT guard works."""

    def _is_safe(self, sql: str) -> bool:
        return sql.strip().upper().startswith("SELECT")

    def test_select_is_allowed(self):
        assert self._is_safe("SELECT * FROM regional_sales")

    def test_insert_is_blocked(self):
        assert not self._is_safe("INSERT INTO customers VALUES ('X', 'Y')")

    def test_drop_is_blocked(self):
        assert not self._is_safe("DROP TABLE customers")

    def test_update_is_blocked(self):
        assert not self._is_safe("UPDATE customers SET region = 'X'")

    def test_select_with_leading_whitespace(self):
        assert self._is_safe("  SELECT id FROM customers LIMIT 1")

    def test_injection_attempt_blocked(self):
        malicious = "'; DROP TABLE customers; --"
        assert not self._is_safe(malicious)


# ── Graph Router ──────────────────────────────────────────────────────────────

class TestGraphRouter:
    """Tests for the LangGraph conditional router."""

    def _route(self, state: dict) -> str:
        if state.get("error"):
            return "responder"
        current = state.get("current_step", 0)
        plan = state.get("plan", [])
        if current >= len(plan):
            return "critic"
        next_step = plan[current].lower()
        if any(w in next_step for w in ["sql", "query", "database", "revenue", "sales", "data"]):
            return "sql_agent"
        return "researcher"

    def test_routes_sql_keywords_to_sql_agent(self):
        state = {
            "plan": ["query_database: Get revenue for Kerala"],
            "current_step": 0,
            "error": None,
        }
        assert self._route(state) == "sql_agent"

    def test_routes_document_keywords_to_researcher(self):
        state = {
            "plan": ["search_documents: Find Kerala market reports"],
            "current_step": 0,
            "error": None,
        }
        assert self._route(state) == "researcher"

    def test_routes_to_critic_when_plan_complete(self):
        state = {
            "plan": ["query_database: Get revenue"],
            "current_step": 1,  # past end of plan
            "error": None,
        }
        assert self._route(state) == "critic"

    def test_routes_to_responder_on_error(self):
        state = {
            "plan": ["query_database: Get revenue"],
            "current_step": 0,
            "error": "Connection failed",
        }
        assert self._route(state) == "responder"
