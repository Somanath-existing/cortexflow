-- CortexFlow Seed Database
-- Simplified Northwind + Regional Sales Data for demo

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(100),
    contact_name VARCHAR(100),
    country VARCHAR(50),
    city VARCHAR(50),
    region VARCHAR(50)
);

INSERT INTO customers (customer_id, company_name, contact_name, country, city, region) VALUES
('KOCHI001', 'Kochi Tech Solutions', 'Arun Kumar', 'India', 'Kochi', 'Kerala'),
('TVM001',   'Trivandrum Enterprises', 'Priya Nair', 'India', 'Trivandrum', 'Kerala'),
('CLT001',   'Calicut Systems', 'Rajan Menon', 'India', 'Calicut', 'Kerala'),
('BLR001',   'Bangalore Software Co', 'Suresh Rao', 'India', 'Bangalore', 'Karnataka'),
('MYS001',   'Mysore Technologies', 'Deepa Gowda', 'India', 'Mysore', 'Karnataka'),
('CHN001',   'Chennai Innovations', 'Venkat Kumar', 'India', 'Chennai', 'Tamil Nadu'),
('HYD001',   'Hyderabad Systems', 'Krishnamurti', 'India', 'Hyderabad', 'Telangana'),
('ALFKI',    'Alfreds Futterkiste', 'Maria Anders', 'Germany', 'Berlin', NULL)
ON CONFLICT (customer_id) DO NOTHING;

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(100),
    unit_price DECIMAL(10,2),
    units_in_stock INTEGER
);

INSERT INTO products (product_name, category, unit_price, units_in_stock) VALUES
('Enterprise Server Pro', 'Electronics', 250000.00, 50),
('Workstation Elite', 'Electronics', 85000.00, 120),
('Network Switch 48-Port', 'Electronics', 45000.00, 200),
('Cloud Platform (per seat/month)', 'Software', 15000.00, 9999),
('Security Suite (per seat/month)', 'Software', 8000.00, 9999),
('Analytics Platform (per seat/month)', 'Software', 25000.00, 9999),
('UPS 3KVA', 'Electronics', 32000.00, 80),
('Fiber Optic Cable (100m)', 'Networking', 12000.00, 500);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(10) REFERENCES customers(customer_id),
    order_date DATE,
    shipped_date DATE,
    total_amount DECIMAL(12,2)
);

INSERT INTO orders (customer_id, order_date, shipped_date, total_amount) VALUES
('KOCHI001', '2023-07-10', '2023-07-15', 750000.00),
('KOCHI001', '2023-08-05', '2023-08-12', 500000.00),
('KOCHI001', '2023-09-20', '2023-09-28', 312000.00),
('KOCHI001', '2024-07-08', '2024-07-20', 250000.00),
('KOCHI001', '2024-08-15', NULL,          180000.00),
('TVM001',   '2023-07-22', '2023-07-30', 198000.00),
('TVM001',   '2023-08-18', '2023-08-25', 165000.00),
('TVM001',   '2024-07-30', NULL,          120000.00),
('CLT001',   '2023-09-05', '2023-09-12', 95000.00),
('CLT001',   '2024-08-20', NULL,          65000.00),
('BLR001',   '2023-07-15', '2023-07-22', 421000.00),
('BLR001',   '2023-08-10', '2023-08-18', 398000.00),
('BLR001',   '2024-07-25', '2024-08-02', 445000.00),
('MYS001',   '2023-09-10', '2023-09-18', 210000.00),
('MYS001',   '2024-08-05', '2024-08-15', 235000.00);

-- Regional sales summary table (key demo table)
CREATE TABLE IF NOT EXISTS regional_sales (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100),
    state VARCHAR(100),
    quarter VARCHAR(10),
    year INTEGER,
    revenue DECIMAL(12,2),
    units_sold INTEGER,
    product_category VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO regional_sales (region, state, quarter, year, revenue, units_sold, product_category) VALUES
-- Kerala Electronics: Q3 decline
('South India', 'Kerala', 'Q3', 2023, 312000.00, 1560, 'Electronics'),
('South India', 'Kerala', 'Q3', 2024, 245000.00, 1230, 'Electronics'),
-- Kerala Software: slight decline
('South India', 'Kerala', 'Q3', 2023, 198000.00, 990,  'Software'),
('South India', 'Kerala', 'Q3', 2024, 189000.00, 945,  'Software'),
-- Kerala Networking: moderate decline
('South India', 'Kerala', 'Q3', 2023, 85000.00,  425,  'Networking'),
('South India', 'Kerala', 'Q3', 2024, 61000.00,  305,  'Networking'),
-- Karnataka Electronics: growing
('South India', 'Karnataka', 'Q3', 2023, 398000.00, 1990, 'Electronics'),
('South India', 'Karnataka', 'Q3', 2024, 421000.00, 2105, 'Electronics'),
-- Karnataka Software: growing
('South India', 'Karnataka', 'Q3', 2023, 256000.00, 1280, 'Software'),
('South India', 'Karnataka', 'Q3', 2024, 312000.00, 1560, 'Software'),
-- Tamil Nadu: stable
('South India', 'Tamil Nadu', 'Q3', 2023, 280000.00, 1400, 'Electronics'),
('South India', 'Tamil Nadu', 'Q3', 2024, 295000.00, 1475, 'Electronics'),
-- Q2 data for context
('South India', 'Kerala', 'Q2', 2023, 290000.00, 1450, 'Electronics'),
('South India', 'Kerala', 'Q2', 2024, 275000.00, 1375, 'Electronics'),
('South India', 'Kerala', 'Q1', 2024, 320000.00, 1600, 'Electronics'),
('South India', 'Kerala', 'Q4', 2023, 380000.00, 1900, 'Electronics');

-- Customer health scores
CREATE TABLE IF NOT EXISTS customer_health (
    customer_id VARCHAR(10) REFERENCES customers(customer_id),
    health_score DECIMAL(5,2),
    churn_risk VARCHAR(20),
    last_order_days_ago INTEGER,
    revenue_trend VARCHAR(20),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO customer_health (customer_id, health_score, churn_risk, last_order_days_ago, revenue_trend) VALUES
('KOCHI001', 52.0, 'HIGH',   45, 'DECLINING'),
('TVM001',   48.5, 'HIGH',   67, 'DECLINING'),
('CLT001',   61.0, 'MEDIUM', 38, 'FLAT'),
('BLR001',   88.5, 'LOW',    12, 'GROWING'),
('MYS001',   79.0, 'LOW',    22, 'STABLE'),
('CHN001',   74.5, 'LOW',    18, 'STABLE'),
('HYD001',   65.0, 'MEDIUM', 35, 'FLAT')
ON CONFLICT DO NOTHING;

-- Document embeddings table for pgvector
CREATE TABLE IF NOT EXISTS document_embeddings (
    id BIGSERIAL PRIMARY KEY,
    doc_id VARCHAR(255),
    content TEXT,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS document_embeddings_hnsw
ON document_embeddings USING hnsw (embedding vector_cosine_ops);
