from fastapi import APIRouter
from backend.db.postgres import execute_query

router = APIRouter()


@router.get("/regional-summary")
async def regional_summary():
    """Regional sales summary — grouped by state, quarter, year, and product category."""
    try:
        rows = await execute_query("""
            SELECT
                state,
                quarter,
                year,
                product_category,
                SUM(revenue) as total_revenue,
                SUM(units_sold) as total_units
            FROM regional_sales
            GROUP BY state, quarter, year, product_category
            ORDER BY year DESC, quarter DESC, total_revenue DESC
            LIMIT 100
        """)
        return {"data": rows}
    except Exception as e:
        return {"error": str(e), "data": []}


@router.get("/churn-risk")
async def churn_risk():
    """Customer churn risk overview."""
    try:
        rows = await execute_query("""
            SELECT
                c.company_name,
                c.region,
                c.city,
                ch.health_score,
                ch.churn_risk,
                ch.last_order_days_ago,
                ch.revenue_trend
            FROM customer_health ch
            JOIN customers c ON c.customer_id = ch.customer_id
            ORDER BY ch.health_score ASC
        """)
        return {"data": rows}
    except Exception as e:
        return {"error": str(e), "data": []}


@router.get("/top-customers")
async def top_customers():
    """Top customers by total revenue."""
    try:
        rows = await execute_query("""
            SELECT
                c.customer_id,
                c.company_name,
                c.region,
                COUNT(o.order_id) AS order_count,
                SUM(o.total_amount) AS total_revenue
            FROM customers c
            LEFT JOIN orders o ON o.customer_id = c.customer_id
            GROUP BY c.customer_id, c.company_name, c.region
            ORDER BY total_revenue DESC NULLS LAST
            LIMIT 20
        """)
        return {"data": rows}
    except Exception as e:
        return {"error": str(e), "data": []}


@router.get("/kerala-vs-karnataka")
async def kerala_vs_karnataka():
    """Head-to-head Kerala vs Karnataka comparison for all available quarters."""
    try:
        rows = await execute_query("""
            SELECT
                state,
                quarter,
                year,
                SUM(revenue) AS total_revenue,
                SUM(units_sold) AS total_units
            FROM regional_sales
            WHERE state IN ('Kerala', 'Karnataka')
            GROUP BY state, quarter, year
            ORDER BY year DESC, quarter DESC, state
        """)
        return {"data": rows}
    except Exception as e:
        return {"error": str(e), "data": []}


@router.get("/health")
async def analytics_health():
    return {"status": "ok"}
