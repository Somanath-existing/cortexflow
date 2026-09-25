from neo4j import AsyncGraphDatabase
from backend.core.config import settings

driver = None


async def init_neo4j():
    global driver
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_url,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    print("✅ Neo4j connected")


async def execute_cypher(query: str, params: dict = None) -> list[dict]:
    async with driver.session() as session:
        result = await session.run(query, params or {})
        return [dict(record) async for record in result]


async def seed_knowledge_graph():
    """Seeds the knowledge graph with business entities."""
    queries = [
        """
        MERGE (c:Customer {id: 'ALFKI', name: 'Alfreds Futterkiste'})
        SET c.region = 'Germany', c.segment = 'Enterprise'
        """,
        """
        MERGE (c:Customer {id: 'KOCHI001', name: 'Kochi Tech Solutions'})
        SET c.region = 'Kerala', c.segment = 'Enterprise'
        """,
        """
        MERGE (c:Customer {id: 'TVM001', name: 'Trivandrum Enterprises'})
        SET c.region = 'Kerala', c.segment = 'SMB'
        """,
        """
        MERGE (p:Product {id: 1, name: 'Chai'})
        SET p.category = 'Beverages', p.unit_price = 18.00
        """,
        """
        MERGE (p:Product {id: 2, name: 'Enterprise Server'})
        SET p.category = 'Electronics', p.unit_price = 250000.00
        """,
        """
        MERGE (p:Product {id: 3, name: 'Cloud Platform'})
        SET p.category = 'Software', p.unit_price = 15000.00
        """,
        """
        MERGE (r:Region {name: 'Kerala', country: 'India'})
        SET r.zone = 'South India'
        """,
        """
        MERGE (r:Region {name: 'Karnataka', country: 'India'})
        SET r.zone = 'South India'
        """,
        """
        MATCH (c:Customer {id: 'KOCHI001'})
        MATCH (p:Product {id: 2})
        MERGE (c)-[:PURCHASED {quantity: 5, date: '2023-07-15'}]->(p)
        """,
        """
        MATCH (c:Customer {id: 'TVM001'})
        MATCH (p:Product {id: 3})
        MERGE (c)-[:PURCHASED {quantity: 10, date: '2023-08-01'}]->(p)
        """,
        """
        MATCH (c:Customer {id: 'KOCHI001'})
        MATCH (r:Region {name: 'Kerala'})
        MERGE (c)-[:LOCATED_IN]->(r)
        """,
        """
        MATCH (c:Customer {id: 'TVM001'})
        MATCH (r:Region {name: 'Kerala'})
        MERGE (c)-[:LOCATED_IN]->(r)
        """,
    ]
    for q in queries:
        await execute_cypher(q)
    print("✅ Neo4j knowledge graph seeded")
