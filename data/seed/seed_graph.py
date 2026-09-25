"""
Seed the Neo4j knowledge graph with business entities and relationships.
Run after docker-compose up:
  python data/seed/seed_graph.py
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase

NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "cortexflow_dev")


QUERIES = [
    # ── Region nodes ──────────────────────────────────────────────────────────
    "MERGE (r:Region {name: 'Kerala'}) SET r.country = 'India', r.zone = 'South India'",
    "MERGE (r:Region {name: 'Karnataka'}) SET r.country = 'India', r.zone = 'South India'",
    "MERGE (r:Region {name: 'Tamil Nadu'}) SET r.country = 'India', r.zone = 'South India'",
    "MERGE (r:Region {name: 'Telangana'}) SET r.country = 'India', r.zone = 'South India'",

    # ── Category nodes ────────────────────────────────────────────────────────
    "MERGE (c:Category {name: 'Electronics'}) SET c.margin = 0.22",
    "MERGE (c:Category {name: 'Software'}) SET c.margin = 0.68",
    "MERGE (c:Category {name: 'Networking'}) SET c.margin = 0.31",

    # ── Supplier nodes ────────────────────────────────────────────────────────
    "MERGE (s:Supplier {name: 'Dell Technologies'}) SET s.country = 'USA'",
    "MERGE (s:Supplier {name: 'Microsoft'}) SET s.country = 'USA'",
    "MERGE (s:Supplier {name: 'Cisco Systems'}) SET s.country = 'USA'",
    "MERGE (s:Supplier {name: 'LocalTech Solutions'}) SET s.country = 'India', s.note = 'Competitor in Kerala market'",

    # ── Product nodes ─────────────────────────────────────────────────────────
    "MERGE (p:Product {id: 1, name: 'Enterprise Server Pro'}) SET p.price = 250000",
    "MERGE (p:Product {id: 2, name: 'Workstation Elite'}) SET p.price = 85000",
    "MERGE (p:Product {id: 3, name: 'Cloud Platform'}) SET p.price = 15000",
    "MERGE (p:Product {id: 4, name: 'Security Suite'}) SET p.price = 8000",
    "MERGE (p:Product {id: 5, name: 'Network Switch 48-Port'}) SET p.price = 45000",

    # ── Customer nodes ────────────────────────────────────────────────────────
    "MERGE (c:Customer {id: 'KOCHI001'}) SET c.name = 'Kochi Tech Solutions', c.churn_risk = 'HIGH'",
    "MERGE (c:Customer {id: 'TVM001'}) SET c.name = 'Trivandrum Enterprises', c.churn_risk = 'HIGH'",
    "MERGE (c:Customer {id: 'CLT001'}) SET c.name = 'Calicut Systems', c.churn_risk = 'MEDIUM'",
    "MERGE (c:Customer {id: 'BLR001'}) SET c.name = 'Bangalore Software Co', c.churn_risk = 'LOW'",
    "MERGE (c:Customer {id: 'MYS001'}) SET c.name = 'Mysore Technologies', c.churn_risk = 'LOW'",

    # ── Product → Category ────────────────────────────────────────────────────
    """MATCH (p:Product {id: 1}) MATCH (c:Category {name: 'Electronics'})
       MERGE (p)-[:BELONGS_TO]->(c)""",
    """MATCH (p:Product {id: 2}) MATCH (c:Category {name: 'Electronics'})
       MERGE (p)-[:BELONGS_TO]->(c)""",
    """MATCH (p:Product {id: 3}) MATCH (c:Category {name: 'Software'})
       MERGE (p)-[:BELONGS_TO]->(c)""",
    """MATCH (p:Product {id: 4}) MATCH (c:Category {name: 'Software'})
       MERGE (p)-[:BELONGS_TO]->(c)""",
    """MATCH (p:Product {id: 5}) MATCH (c:Category {name: 'Networking'})
       MERGE (p)-[:BELONGS_TO]->(c)""",

    # ── Product → Supplier ────────────────────────────────────────────────────
    """MATCH (p:Product {id: 1}) MATCH (s:Supplier {name: 'Dell Technologies'})
       MERGE (p)-[:SUPPLIED_BY]->(s)""",
    """MATCH (p:Product {id: 3}) MATCH (s:Supplier {name: 'Microsoft'})
       MERGE (p)-[:SUPPLIED_BY]->(s)""",
    """MATCH (p:Product {id: 5}) MATCH (s:Supplier {name: 'Cisco Systems'})
       MERGE (p)-[:SUPPLIED_BY]->(s)""",

    # ── Customer → Region ─────────────────────────────────────────────────────
    """MATCH (c:Customer {id: 'KOCHI001'}) MATCH (r:Region {name: 'Kerala'})
       MERGE (c)-[:LOCATED_IN]->(r)""",
    """MATCH (c:Customer {id: 'TVM001'}) MATCH (r:Region {name: 'Kerala'})
       MERGE (c)-[:LOCATED_IN]->(r)""",
    """MATCH (c:Customer {id: 'CLT001'}) MATCH (r:Region {name: 'Kerala'})
       MERGE (c)-[:LOCATED_IN]->(r)""",
    """MATCH (c:Customer {id: 'BLR001'}) MATCH (r:Region {name: 'Karnataka'})
       MERGE (c)-[:LOCATED_IN]->(r)""",
    """MATCH (c:Customer {id: 'MYS001'}) MATCH (r:Region {name: 'Karnataka'})
       MERGE (c)-[:LOCATED_IN]->(r)""",

    # ── Customer → Product (purchase relationships) ───────────────────────────
    """MATCH (c:Customer {id: 'KOCHI001'}) MATCH (p:Product {id: 1})
       MERGE (c)-[:PURCHASED {quantity: 3, year: 2023, quarter: 'Q3'}]->(p)""",
    """MATCH (c:Customer {id: 'KOCHI001'}) MATCH (p:Product {id: 1})
       MERGE (c)-[:PURCHASED {quantity: 1, year: 2024, quarter: 'Q3'}]->(p)""",
    """MATCH (c:Customer {id: 'TVM001'}) MATCH (p:Product {id: 3})
       MERGE (c)-[:PURCHASED {quantity: 10, year: 2023, quarter: 'Q3'}]->(p)""",
    """MATCH (c:Customer {id: 'TVM001'}) MATCH (p:Product {id: 3})
       MERGE (c)-[:PURCHASED {quantity: 6, year: 2024, quarter: 'Q3'}]->(p)""",
    """MATCH (c:Customer {id: 'BLR001'}) MATCH (p:Product {id: 1})
       MERGE (c)-[:PURCHASED {quantity: 5, year: 2024, quarter: 'Q3'}]->(p)""",
    """MATCH (c:Customer {id: 'BLR001'}) MATCH (p:Product {id: 3})
       MERGE (c)-[:PURCHASED {quantity: 20, year: 2024, quarter: 'Q3'}]->(p)""",

    # ── Competitor relationship ───────────────────────────────────────────────
    """MATCH (s:Supplier {name: 'LocalTech Solutions'}) MATCH (r:Region {name: 'Kerala'})
       MERGE (s)-[:OPERATES_IN {since: '2024-Q2', strategy: 'price_undercutting'}]->(r)""",
]


async def main():
    print(f"Connecting to Neo4j at {NEO4J_URL}...")
    driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))

    async with driver.session() as session:
        for i, query in enumerate(QUERIES, 1):
            try:
                await session.run(query.strip())
                print(f"  ✅ [{i}/{len(QUERIES)}] {query.strip()[:60]}...")
            except Exception as e:
                print(f"  ⚠️  [{i}/{len(QUERIES)}] Error: {e}")

    await driver.close()
    print(f"\n✅ Knowledge graph seeded with {len(QUERIES)} statements.")
    print("   Open Neo4j Browser at http://localhost:7474 to explore.")
    print("   Try: MATCH (n) RETURN n LIMIT 50")


if __name__ == "__main__":
    asyncio.run(main())
