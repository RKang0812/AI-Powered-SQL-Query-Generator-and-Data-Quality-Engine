-- ================================================
-- NaviGuard AI - init.sql
-- ================================================

-- delete existing tables if they exist
DROP TABLE IF EXISTS dq_alerts CASCADE;
DROP TABLE IF EXISTS voyage_performance CASCADE;

-- ================================================
-- 1. voyage_performance sheet
-- ================================================
CREATE TABLE voyage_performance (
    voyage_id SERIAL PRIMARY KEY,
    vessel_name VARCHAR(100) NOT NULL,
    vessel_type VARCHAR(50),
    
    -- departure port information
    departure_port VARCHAR(100),
    departure_lat NUMERIC(10, 6),
    departure_lon NUMERIC(10, 6),
    departure_at TIMESTAMP NOT NULL,
    
    -- arrival port information
    arrival_port VARCHAR(100),
    arrival_lat NUMERIC(10, 6),
    arrival_lon NUMERIC(10, 6),
    arrival_at TIMESTAMP NOT NULL,
    
    -- voyage performance metrics
    distance_nm NUMERIC(10, 2),  -- voyage distance (nautical miles)
    avg_speed_knots NUMERIC(5, 2),  -- average speed (knots)
    heavy_fuel_oil_cons NUMERIC(10, 2),  -- heavy fuel oil consumption (tons)
    cargo_qty_mt NUMERIC(10, 2),  -- cargo quantity (tons)
    is_ballast BOOLEAN DEFAULT FALSE,  -- is ballast
    
    -- data quality flags
    is_anomaly BOOLEAN DEFAULT FALSE,
    anomaly_type VARCHAR(100),
    
    -- audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- create indexes to improve query performance
CREATE INDEX idx_departure_at ON voyage_performance(departure_at);
CREATE INDEX idx_arrival_at ON voyage_performance(arrival_at);
CREATE INDEX idx_vessel_name ON voyage_performance(vessel_name);
CREATE INDEX idx_is_anomaly ON voyage_performance(is_anomaly);

-- ================================================
-- 2. data quality alerts table
-- ================================================
CREATE TABLE dq_alerts (
    alert_id SERIAL PRIMARY KEY,
    voyage_id INTEGER REFERENCES voyage_performance(voyage_id) ON DELETE CASCADE,
    table_name VARCHAR(50) DEFAULT 'voyage_performance',
    
    -- issue description
    severity VARCHAR(20) CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    issue_description TEXT NOT NULL,
    rule_violated TEXT,
    
    -- AI generated fix suggestions
    suggested_fix_sql TEXT,
    ai_explanation TEXT,
    
    -- status tracking
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'IGNORED')),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    
    -- audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- create indexes
CREATE INDEX idx_alert_voyage_id ON dq_alerts(voyage_id);
CREATE INDEX idx_alert_status ON dq_alerts(status);
CREATE INDEX idx_alert_severity ON dq_alerts(severity);

-- ================================================
-- 3. create view - anomaly summary
-- ================================================
CREATE OR REPLACE VIEW v_anomaly_summary AS
SELECT 
    anomaly_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM voyage_performance WHERE is_anomaly = TRUE), 2) as percentage
FROM voyage_performance
WHERE is_anomaly = TRUE
GROUP BY anomaly_type
ORDER BY count DESC;

-- ================================================
-- 4. create view - data quality dashboard
-- ================================================
CREATE OR REPLACE VIEW v_dq_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM voyage_performance) as total_voyages,
    (SELECT COUNT(*) FROM voyage_performance WHERE is_anomaly = TRUE) as total_anomalies,
    (SELECT COUNT(*) FROM dq_alerts WHERE status = 'OPEN') as open_alerts,
    (SELECT COUNT(*) FROM dq_alerts WHERE status = 'RESOLVED') as resolved_alerts,
    ROUND(
        (SELECT COUNT(*) FROM voyage_performance WHERE is_anomaly = TRUE) * 100.0 / 
        NULLIF((SELECT COUNT(*) FROM voyage_performance), 0), 
        2
    ) as anomaly_percentage;

-- ================================================
-- 5. create trigger - automatically update updated_at
-- ================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_voyage_performance_updated_at 
    BEFORE UPDATE ON voyage_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dq_alerts_updated_at 
    BEFORE UPDATE ON dq_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- hint to user
-- ================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Database initialization completed!';
    RAISE NOTICE '   - Tables: voyage_performance, dq_alerts';
    RAISE NOTICE '   - Views: v_anomaly_summary, v_dq_dashboard';
    RAISE NOTICE '   - Triggers: automatically update timestamps';
END $$;
