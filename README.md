# AI-Powered SQL Query Generator and Data Quality Engine

An intelligent business intelligence system that combines natural language processing with automated data quality monitoring. Users can query databases in plain English while AI automatically detects anomalies and generates validation rules.
[▶ Watch the Demo](demo.mp4)

## Overview

This project demonstrates LLM integration in data engineering workflows. It converts natural language questions into SQL queries, automates data quality checks, and provides interactive dashboards for business analytics.

Built for product performance analysis scenarios with complete pipeline coverage: data generation, ETL processing, quality validation, and visualization.

## Features

**Natural Language SQL Generator**
- Converts English questions to optimized PostgreSQL queries
- Schema-aware query construction with business logic validation
- Automated result visualization with Plotly charts
- Query explanation and downloadable results

**AI Rule Generator**
- Analyzes database schema to create validation rules
- Generates business-logic-aware SQL checks
- Configurable severity levels and impact assessment

**Automated Anomaly Detection**
- Scans data across 7 quality dimensions
- Creates severity-classified alerts with AI diagnostics
- Generates SQL fix scripts with remediation guidance

**Interactive Dashboard**
- Real-time data quality metrics
- Alert management with status tracking
- Anomaly distribution analysis
- CSV export functionality

## Tech Stack

- **Database**: PostgreSQL 15+
- **Backend**: Python 3.11+
- **AI Model**: OpenAI GPT-4o
- **UI Framework**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Synthetic Data**: Faker

## Requirements

- Python 3.11 or higher
- PostgreSQL 15+
- OpenAI API key

## Installation

```bash
git clone https://github.com/yourusername/ai-data-analytics.git
cd ai-data-analytics

python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

## Configuration

Create `.env` file:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=analytics_db
DB_USER=your_username
DB_PASSWORD=your_password

OPENAI_API_KEY=your_api_key
```

## Database Setup

```bash
# Initialize schema
psql -U your_username -d analytics_db -f src/db/init.sql

# Generate synthetic data (1000 records, 15% anomalies)
python data/generate_data.py

# Import data
psql -U your_username -d analytics_db
\copy voyage_performance FROM 'data/raw/voyage_performance.csv' CSV HEADER;
```

## Running

```bash
streamlit run app.py
```

Access at `http://localhost:8501`

## Project Structure

```
ai-data-analytics/
├── data/
│   ├── raw/                    # Generated datasets
│   ├── processed/              # Cleaned data
│   └── generate_data.py        # Synthetic data generator
├── src/
│   ├── db/
│   │   ├── init.sql           # Database schema
│   │   └── connection.py      # PostgreSQL wrapper
│   ├── ai/
│   │   ├── nl_query_generator.py    # Natural language to SQL
│   │   ├── rule_generator.py        # Validation rule creation
│   │   └── anomaly_detector.py      # Anomaly detection engine
│   └── validators/
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   └── 02_model_testing.ipynb
├── config/
│   └── business_config.py
├── app.py                     # Streamlit entry point
├── requirements.txt
└── .env.example
```

## Usage Examples

**Natural Language Query**
```
Input: "What are the top 5 vessels by fuel efficiency?"

Generated SQL:
SELECT vessel_name, 
       SUM(distance_nm) / NULLIF(SUM(heavy_fuel_oil_cons), 0) as efficiency
FROM voyage_performance
WHERE heavy_fuel_oil_cons > 0
GROUP BY vessel_name
ORDER BY efficiency DESC
LIMIT 5;

Output: Interactive table + bar chart + CSV download
```

**AI Rule Generation**
```
Dashboard → AI Tools → Generate 10 Rules
→ Analyzes schema → Creates validation checks → Displays SQL
```

**Anomaly Detection**
```
Dashboard → AI Tools → Start Scan
→ Executes rules → Flags anomalies → Creates alerts with fix suggestions
```

## Data Schema

**voyage_performance**

| Column | Type | Description |
|--------|------|-------------|
| voyage_id | SERIAL | Primary key |
| vessel_name | VARCHAR | Ship identifier |
| departure_at | TIMESTAMP | Departure time |
| arrival_at | TIMESTAMP | Arrival time |
| distance_nm | NUMERIC | Distance (nautical miles) |
| avg_speed_knots | NUMERIC | Average speed |
| heavy_fuel_oil_cons | NUMERIC | Fuel consumption (tons) |
| cargo_qty_mt | NUMERIC | Cargo weight (tons) |
| is_ballast | BOOLEAN | Empty voyage flag |
| is_anomaly | BOOLEAN | Quality flag |
| anomaly_type | VARCHAR | Anomaly category |

**dq_alerts**

| Column | Type | Description |
|--------|------|-------------|
| alert_id | SERIAL | Primary key |
| voyage_id | INTEGER | Foreign key |
| severity | VARCHAR | CRITICAL/HIGH/MEDIUM/LOW |
| issue_description | TEXT | Problem summary |
| suggested_fix_sql | TEXT | AI-generated fix |
| ai_explanation | TEXT | Root cause analysis |
| status | VARCHAR | OPEN/INVESTIGATING/RESOLVED/IGNORED |

## Anomaly Detection Categories

- Time sequence violations
- Zero fuel consumption with distance traveled
- Speed exceeding physical limits
- Negative values in measurements
- Coordinate range errors
- Business logic conflicts
- Fuel consumption outliers

## Development

```bash
# Test database connection
python src/db/connection.py

# Test NL query generator
python src/ai/nl_query_generator.py

# Test rule generator
python src/ai/rule_generator.py
