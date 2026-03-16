"""
NaviGuard AI - Streamlit data quality monitoring dashboard for maritime voyage performance data
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# add src directory to sys.path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from db.connection import DatabaseConnection
from ai.rule_generator import RuleGenerator
from ai.anomaly_detector import AnomalyDetector
from ai.nl_query_generator import NLQueryGenerator

# page configuration
st.set_page_config(
    page_title="NaviGuard AI - Data Quality Monitoring",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .alert-critical {
        background-color: #ffebee;
        padding: 0.5rem;
        border-left: 4px solid #f44336;
    }
    .alert-high {
        background-color: #fff3e0;
        padding: 0.5rem;
        border-left: 4px solid #ff9800;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db_connection():
    """Cache the database connection"""
    db = DatabaseConnection()
    db.connect()
    return db


def show_dashboard():
    """Main dashboard"""
    st.markdown('<div class="main-header">🚢 NaviGuard AI - Maritime Data Quality Monitoring System</div>', 
                unsafe_allow_html=True)
    
    db = get_db_connection()
    
    # get dashboard summary data
    dashboard_query = "SELECT * FROM v_dq_dashboard"
    dashboard_data = db.execute_query(dashboard_query)[0]
    
    # top level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Voyage Count",
            value=f"{dashboard_data['total_voyages']:,}",
        )
    
    with col2:
        st.metric(
            label="⚠️ Total Anomalies",
            value=f"{dashboard_data['total_anomalies']:,}",
            delta=f"{dashboard_data['anomaly_percentage']}%"
        )
    
    with col3:
        st.metric(
            label="🔔 Open Alerts",
            value=f"{dashboard_data['open_alerts']:,}",
        )
    
    with col4:
        st.metric(
            label="✅ Resolved Alerts",
            value=f"{dashboard_data['resolved_alerts']:,}",
        )
    
    st.divider()
    
    # anomaly type distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Anomaly Type Distribution")
        anomaly_summary = db.query_to_dataframe("SELECT * FROM v_anomaly_summary")
        
        if not anomaly_summary.empty:
            fig = px.bar(
                anomaly_summary,
                x='anomaly_type',
                y='count',
                color='count',
                text='percentage',
                labels={'count': 'Count', 'anomaly_type': 'Anomaly Type'},
                color_continuous_scale='Reds'
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No anomaly data available")
    
    with col2:
        st.subheader("🎯 Severity Distribution of Alerts")
        severity_query = """
        SELECT severity, COUNT(*) as count
        FROM dq_alerts
        WHERE status = 'OPEN'
        GROUP BY severity
        ORDER BY 
            CASE severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END
        """
        severity_data = db.query_to_dataframe(severity_query)
        
        if not severity_data.empty:
            fig = px.pie(
                severity_data,
                values='count',
                names='severity',
                color='severity',
                color_discrete_map={
                    'CRITICAL': '#f44336',
                    'HIGH': '#ff9800',
                    'MEDIUM': '#ffc107',
                    'LOW': '#4caf50'
                }
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No alert data available")


def show_anomalies():
    """anomaly details page"""
    st.header("🔍 Anomaly Details")
    
    db = get_db_connection()
    
    # filtering options
    col1, col2 = st.columns(2)
    
    with col1:
        anomaly_types = db.execute_query(
            "SELECT DISTINCT anomaly_type FROM voyage_performance WHERE is_anomaly = TRUE"
        )
        selected_type = st.selectbox(
            "Select Anomaly Type",
            options=['All'] + [r['anomaly_type'] for r in anomaly_types]
        )
    
    with col2:
        limit = st.slider("Display Count", 10, 100, 50)
    
    # select anomalies based on filters
    if selected_type == 'All':
        query = f"""
        SELECT * FROM voyage_performance 
        WHERE is_anomaly = TRUE 
        ORDER BY voyage_id DESC 
        LIMIT {limit}
        """
    else:
        query = f"""
        SELECT * FROM voyage_performance 
        WHERE is_anomaly = TRUE AND anomaly_type = '{selected_type}'
        ORDER BY voyage_id DESC 
        LIMIT {limit}
        """
    
    anomalies_df = db.query_to_dataframe(query)
    
    if not anomalies_df.empty:
        st.dataframe(
            anomalies_df,
            use_container_width=True,
            height=400
        )
        
        # download button
        csv = anomalies_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Anomaly Data CSV",
            data=csv,
            file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No anomaly data available")


def show_alerts():
    """alert management page"""
    st.header("🔔 Data Quality Alerts")
    
    db = get_db_connection()
    
    # status filter
    status_filter = st.selectbox(
        "Alert Status",
        options=['All', 'OPEN', 'INVESTIGATING', 'RESOLVED', 'IGNORED']
    )
    
    # filter alerts based on status
    if status_filter == 'All':
        query = """
        SELECT a.*, v.vessel_name, v.departure_port, v.arrival_port
        FROM dq_alerts a
        LEFT JOIN voyage_performance v ON a.voyage_id = v.voyage_id
        ORDER BY a.created_at DESC
        LIMIT 100
        """
    else:
        query = f"""
        SELECT a.*, v.vessel_name, v.departure_port, v.arrival_port
        FROM dq_alerts a
        LEFT JOIN voyage_performance v ON a.voyage_id = v.voyage_id
        WHERE a.status = '{status_filter}'
        ORDER BY a.created_at DESC
        LIMIT 100
        """
    
    alerts_df = db.query_to_dataframe(query)
    
    if not alerts_df.empty:
        # show alerts with severity color coding
        for idx, alert in alerts_df.iterrows():
            severity_color = {
                'CRITICAL': 'alert-critical',
                'HIGH': 'alert-high',
                'MEDIUM': 'metric-card',
                'LOW': 'metric-card'
            }
            
            with st.container():
                st.markdown(f'<div class="{severity_color.get(alert["severity"], "metric-card")}">', 
                          unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.markdown(f"**🚢 {alert['vessel_name']}** (Voyage #{alert['voyage_id']})")
                    st.caption(f"{alert['departure_port']} → {alert['arrival_port']}")
                
                with col2:
                    st.markdown(f"**Issue:** {alert['issue_description']}")
                    st.caption(f"Rule: {alert['rule_violated']}")
                
                with col3:
                    st.markdown(f"**Severity:** {alert['severity']}")
                    st.caption(f"Status: {alert['status']}")
                
                # expander for AI fix suggestions
                with st.expander("🔧 AI Fix Suggestions"):
                    st.markdown("**Diagnostic Explanation:**")
                    st.write(alert['ai_explanation'])
                    
                    st.markdown("**Suggested Fix SQL:**")
                    st.code(alert['suggested_fix_sql'], language='sql')
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.divider()
    else:
        st.info("No alert data available")


def show_ai_tools():
    """AI tools page"""
    st.header("🤖 AI Data Quality Tools")
    
    db = get_db_connection()
    
    tab1, tab2 = st.tabs(["Rule Generator", "Anomaly Detector"])
    
    with tab1:
        st.subheader("📝 AI Rule Generator")
        st.write("Use AI to automatically generate data quality validation rules")
        
        num_rules = st.slider("generate rules", 5, 20, 10)
        
        if st.button("🚀 generate rules", type="primary"):
            with st.spinner("AI is generating rules..."):
                generator = RuleGenerator()
                schema = generator.get_table_schema(db)
                rules = generator.generate_validation_rules(schema, num_rules)
                
                if rules:
                    st.success(f"✅ Success! Generated {len(rules)} rules!")
                    
                    for i, rule in enumerate(rules, 1):
                        with st.expander(f"Rule {i}: {rule['rule_name']} ({rule['severity']})"):
                            st.markdown(f"**Description:** {rule['description']}")
                            st.markdown(f"**Business Impact:** {rule['business_impact']}")
                            st.code(rule['sql_check'], language='sql')
    
    with tab2:
        st.subheader("🔍 AI Anomaly Detector")
        st.write("Use AI to scan and analyze data anomalies")
        
        if st.button("🔎 Start Scan", type="primary"):
            with st.spinner("Scanning for anomalies..."):
                detector = AnomalyDetector()
                anomalies = detector.scan_for_anomalies(db)
                
                if anomalies:
                    st.success(f"✅ Scan complete! Found {len(anomalies)} types of anomalies")
                    
                    for anomaly_type, data in anomalies.items():
                        st.markdown(f"**{anomaly_type}:** {data['count']} entries")
                    
                    if st.button("📝 Create Alerts for Anomalies"):
                        with st.spinner("Creating alerts..."):
                            alerts_created = detector.create_dq_alerts(db, anomalies)
                            st.success(f"✅ Created {alerts_created} alerts!")
                else:
                    st.info("No anomalies found")


def show_nl_query():
    """Natural Language Query page"""
    st.header("💬 Natural Language SQL Query")
    
    db = get_db_connection()
    
    st.write("Ask questions about your data in plain English, and AI will generate and execute SQL queries for you.")
    
    # Example questions
    with st.expander("📖 Example Questions"):
        st.markdown("""
        - What are the top 5 vessels by total distance traveled?
        - Show me voyages with fuel consumption above average
        - Which routes had the highest average speed last month?
        - List all vessels that had anomalies in the last 7 days
        - What is the total cargo quantity by departure port?
        - Show me the most fuel-efficient voyages
        """)
    
    # User input
    user_question = st.text_area(
        "Enter your question:",
        placeholder="e.g., What were the top 5 vessels by fuel efficiency last month?",
        height=100
    )
    
    col1, col2 = st.columns([1, 5])
    
    with col1:
        execute_query = st.button("🚀 Generate & Run", type="primary")
    
    with col2:
        show_sql_only = st.checkbox("Show SQL only (don't execute)", value=False)
    
    if execute_query and user_question:
        with st.spinner("AI is analyzing your question and generating SQL..."):
            try:
                # Initialize the NL Query Generator
                nl_generator = NLQueryGenerator()
                
                # Get table schema for context
                schema = nl_generator.get_table_schema(db)
                
                # Generate SQL from natural language
                result = nl_generator.generate_sql(user_question, schema)
                
                if result and 'sql' in result:
                    st.success("✅ SQL query generated successfully!")
                    
                    # Display the generated SQL
                    st.subheader("📝 Generated SQL Query")
                    st.code(result['sql'], language='sql')
                    
                    # Display explanation if available
                    if 'explanation' in result:
                        with st.expander("💡 Query Explanation"):
                            st.write(result['explanation'])
                    
                    # Execute the query if not in "show only" mode
                    if not show_sql_only:
                        st.subheader("📊 Query Results")
                        
                        try:
                            # Execute the generated SQL
                            results_df = db.query_to_dataframe(result['sql'])
                            
                            if not results_df.empty:
                                st.dataframe(
                                    results_df,
                                    use_container_width=True,
                                    height=400
                                )
                                
                                # Show row count
                                st.caption(f"Total rows: {len(results_df)}")
                                
                                # Visualization if applicable
                                if len(results_df.columns) >= 2 and len(results_df) <= 50:
                                    st.subheader("📈 Visualization")
                                    
                                    # Determine chart type based on data
                                    numeric_cols = results_df.select_dtypes(include=['number']).columns
                                    
                                    if len(numeric_cols) >= 1:
                                        chart_type = st.selectbox(
                                            "Select chart type:",
                                            ["Bar Chart", "Line Chart", "Pie Chart"]
                                        )
                                        
                                        x_col = results_df.columns[0]
                                        y_col = numeric_cols[0] if len(numeric_cols) > 0 else results_df.columns[1]
                                        
                                        if chart_type == "Bar Chart":
                                            fig = px.bar(results_df, x=x_col, y=y_col)
                                            st.plotly_chart(fig, use_container_width=True)
                                        elif chart_type == "Line Chart":
                                            fig = px.line(results_df, x=x_col, y=y_col)
                                            st.plotly_chart(fig, use_container_width=True)
                                        elif chart_type == "Pie Chart" and len(results_df) <= 20:
                                            fig = px.pie(results_df, names=x_col, values=y_col)
                                            st.plotly_chart(fig, use_container_width=True)
                                
                                # Download button
                                csv = results_df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="📥 Download Results as CSV",
                                    data=csv,
                                    file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                            else:
                                st.info("Query executed successfully but returned no results.")
                        
                        except Exception as e:
                            st.error(f"❌ Error executing query: {str(e)}")
                            st.info("Try rephrasing your question or check the generated SQL.")
                
                else:
                    st.error("❌ Failed to generate SQL query. Please try rephrasing your question.")
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Please make sure your question is clear and related to the available data.")
    
    elif execute_query and not user_question:
        st.warning("⚠️ Please enter a question first.")


def main():
    """Main function"""
    
    # sidebar with navigation and system status
    with st.sidebar:
        
        st.title("📊 Navigation")
        page = st.radio(
            "Choose a page",
            options=["Dashboard", "Natural Language Query", "Anomalies", "Alerts", "AI Tools"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("### 📈 System Status")
        db = get_db_connection()
        
        try:
            voyage_count = db.count_rows('voyage_performance')
            alert_count = db.count_rows('dq_alerts', "status = 'OPEN'")
            
            st.metric("Voyage Data", f"{voyage_count:,}")
            st.metric("Open Alerts", f"{alert_count:,}")
            
            st.success("✅ Database connection is normal")
        except:
            st.error("❌ Database connection error")
        
        st.divider()

    
    # Main content area
    if page == "Dashboard":
        show_dashboard()
    elif page == "Natural Language Query":
        show_nl_query()
    elif page == "Anomalies":
        show_anomalies()
    elif page == "Alerts":
        show_alerts()
    elif page == "AI Tools":
        show_ai_tools()


if __name__ == "__main__":
    main()
