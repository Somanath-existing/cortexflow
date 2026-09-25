from backend.core.config import settings

# Lazy driver — initialized on first use, not at import time
_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import AsyncGraphDatabase
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_url,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


class GraphRAG:
    """Graph-enhanced RAG using Neo4j knowledge graph."""

    async def find_related_entities(self, entity_name: str, depth: int = 2) -> list[dict]:
        """Find all entities related to a given entity up to specified depth."""
        query = """
        MATCH path = (start)-[*1..$depth]-(related)
        WHERE start.name CONTAINS $name OR start.id = $name
        RETURN
            start.name AS source,
            [r IN relationships(path) | type(r)] AS relationship_types,
            related.name AS related_entity,
            labels(related) AS entity_types
        LIMIT 50
        """
        driver = _get_driver()
        async with driver.session() as session:
            result = await session.run(query, name=entity_name, depth=depth)
            return [dict(record) async for record in result]

    async def get_revenue_graph(self, region: str = None) -> dict:
        """Get subgraph of entities related to revenue in a region."""
        query = """
        MATCH (r:Region)<-[:LOCATED_IN]-(c:Customer)
        -[:PURCHASED]->(p:Product)
        WHERE ($region IS NULL OR r.name CONTAINS $region)
        RETURN
            r.name AS region,
            c.name AS customer,
            p.name AS product,
            count(*) AS purchase_count
        ORDER BY purchase_count DESC
        LIMIT 20
        """
        driver = _get_driver()
        async with driver.session() as session:
            result = await session.run(query, region=region)
            records = [dict(record) async for record in result]

        return {
            "region": region,
            "entity_relationships": records,
            "graph_summary": self._summarize_graph(records),
        }

    def _summarize_graph(self, records: list[dict]) -> str:
        if not records:
            return "No graph data found"
        customers = list(set(r.get("customer") for r in records if r.get("customer")))
        products = list(set(r.get("product") for r in records if r.get("product")))
        return (
            f"Found {len(records)} entity relationships. "
            f"Key customers: {', '.join(customers[:3])}. "
            f"Key products: {', '.join(products[:3])}."
        )

    async def find_customer_relationships(self, customer_id: str) -> list[dict]:
        """Find a customer's full relationship graph."""
        query = """
        MATCH (c:Customer {id: $customer_id})
        OPTIONAL MATCH (c)-[:PURCHASED]->(p:Product)
        RETURN
            c.name AS customer,
            collect(DISTINCT p.name) AS products
        """
        driver = _get_driver()
        async with driver.session() as session:
            result = await session.run(query, customer_id=customer_id)
            return [dict(record) async for record in result]


graph_rag = GraphRAG()
