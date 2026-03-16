"""
using AI to automatically detect data anomalies in voyage performance data and generate fix suggestions
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()


class AnomalyDetector:
    """AI-driven anomaly detector"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')
    
    def scan_for_anomalies(self, db_connection):
        """
        Using AI to automatically scan for data anomalies
        """
        # Execute basic anomaly scanning SQL
        scan_queries = {
            "time_inconsistency": """
                SELECT voyage_id, vessel_name, departure_at, arrival_at,
                       EXTRACT(EPOCH FROM (arrival_at - departure_at))/3600 as duration_hours
                FROM voyage_performance 
                WHERE arrival_at <= departure_at
            """,
            
            "zero_fuel_with_distance": """
                SELECT voyage_id, vessel_name, distance_nm, heavy_fuel_oil_cons
                FROM voyage_performance 
                WHERE distance_nm > 0 AND heavy_fuel_oil_cons = 0
            """,
            
            "excessive_speed": """
                SELECT voyage_id, vessel_name, avg_speed_knots, vessel_type
                FROM voyage_performance 
                WHERE avg_speed_knots > 30
            """,
            
            "negative_values": """
                SELECT voyage_id, vessel_name, distance_nm, heavy_fuel_oil_cons, cargo_qty_mt
                FROM voyage_performance 
                WHERE distance_nm < 0 OR heavy_fuel_oil_cons < 0 OR cargo_qty_mt < 0
            """,
            
            "ballast_with_cargo": """
                SELECT voyage_id, vessel_name, is_ballast, cargo_qty_mt
                FROM voyage_performance 
                WHERE is_ballast = TRUE AND cargo_qty_mt > 0
            """,
            
            "invalid_coordinates": """
                SELECT voyage_id, vessel_name, 
                       departure_lat, departure_lon, arrival_lat, arrival_lon
                FROM voyage_performance 
                WHERE ABS(departure_lat) > 90 OR ABS(arrival_lat) > 90
                   OR ABS(departure_lon) > 180 OR ABS(arrival_lon) > 180
            """
        }
        
        all_anomalies = {}
        
        print("🔍 Starting to scan for data anomalies...\n")
        
        for anomaly_type, query in scan_queries.items():
            try:
                results = db_connection.execute_query(query)
                if results and len(results) > 0:
                    all_anomalies[anomaly_type] = {
                        'count': len(results),
                        'samples': results[:10]  # 前10条
                    }
                    print(f"⚠️  Found {anomaly_type}: {len(results)} rows")
                else:
                    print(f"✅ {anomaly_type}: No anomalies found")
            except Exception as e:
                print(f"❌ Failed to scan {anomaly_type}: {e}")
        
        return all_anomalies
    
    def generate_fix_suggestions(self, anomaly_record):
        """
        Using AI to generate fix suggestions
        
        Args:
            anomaly_record: Anomaly record (dict)
        """
        
        prompt = f"""You are a data quality expert for shipping operations.

An anomaly has been detected in the voyage performance data:

{json.dumps(anomaly_record, indent=2, default=str)}

Please analyze this anomaly and provide:

1. root_cause: The most likely cause of this data quality issue
2. suggested_fix_sql: A PostgreSQL UPDATE statement to fix this specific record
3. explanation: A clear explanation of what went wrong and how the fix works
4. prevention_tips: How to prevent this type of error in the future

Return ONLY a valid JSON object with these fields, no additional text.

Example:
{{
  "root_cause": "Time zone conversion error or manual data entry mistake",
  "suggested_fix_sql": "UPDATE voyage_performance SET departure_at = '2024-01-15 08:00:00', arrival_at = '2024-01-20 14:30:00' WHERE voyage_id = 123;",
  "explanation": "The arrival time is before departure time. Most likely the dates were swapped during entry.",
  "prevention_tips": "Implement automatic time sequence validation at data entry point"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data quality expert specializing in shipping operations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            fix_text = response.choices[0].message.content.strip()
            
            # 清理markdown标记
            if fix_text.startswith("```json"):
                fix_text = fix_text[7:]
            if fix_text.startswith("```"):
                fix_text = fix_text[3:]
            if fix_text.endswith("```"):
                fix_text = fix_text[:-3]
            
            fix_suggestion = json.loads(fix_text.strip())
            return fix_suggestion
            
        except Exception as e:
            print(f"❌ Failed to generate fix suggestions: {e}")
            return None
    
    def create_dq_alerts(self, db_connection, anomalies):
        """
        Create data quality alerts for detected anomalies
        """
        alerts_created = 0
        
        print("\n📝 Creating data quality alerts...\n")
        
        for anomaly_type, data in anomalies.items():
            for record in data['samples'][:5]:  # Only create alerts for the first 5 records
                try:
                    # Use AI to generate fix suggestions
                    fix_suggestion = self.generate_fix_suggestions(dict(record))
                    
                    if fix_suggestion:
                        # Insert alert record
                        insert_query = """
                        INSERT INTO dq_alerts 
                        (voyage_id, severity, issue_description, rule_violated, 
                         suggested_fix_sql, ai_explanation)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        
                        # configure severity based on anomaly type
                        severity_map = {
                            'time_inconsistency': 'CRITICAL',
                            'zero_fuel_with_distance': 'HIGH',
                            'excessive_speed': 'MEDIUM',
                            'negative_values': 'CRITICAL',
                            'ballast_with_cargo': 'HIGH',
                            'invalid_coordinates': 'CRITICAL'
                        }
                        
                        db_connection.execute_query(
                            insert_query,
                            (
                                record['voyage_id'],
                                severity_map.get(anomaly_type, 'MEDIUM'),
                                fix_suggestion.get('root_cause', 'Unknown issue'),
                                anomaly_type,
                                fix_suggestion.get('suggested_fix_sql', ''),
                                fix_suggestion.get('explanation', '')
                            ),
                            fetch=False
                        )
                        
                        alerts_created += 1
                        print(f"✅ created alert for voyage_id={record['voyage_id']} ({anomaly_type})")
                
                except Exception as e:
                    print(f"❌ fail to create alert for voyage_id={record['voyage_id']}: {e}")
        
        print(f"\n📊 created {alerts_created} alerts")
        return alerts_created


if __name__ == "__main__":
    from src.db.connection import DatabaseConnection
    
    # test the anomaly detector
    db = DatabaseConnection()
    if db.connect():
        detector = AnomalyDetector()
        
        # scan for anomalies
        anomalies = detector.scan_for_anomalies(db)
        
        if anomalies:
            print(f"\nfound anomalies: {len(anomalies)} types")
            
            # create data quality alerts
            detector.create_dq_alerts(db, anomalies)
        
        db.close()
