"""
Automatically generate data quality verification rules using the OpenAI API
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()


class RuleGenerator:
    """AI-driven data quality rule generator"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')
    
    def get_table_schema(self, db_connection, table_name='voyage_performance'):
        """Get table schema information"""
        schema_info = db_connection.get_table_info(table_name)
        
        schema_text = f"Table: {table_name}\nColumns:\n"
        for col in schema_info:
            schema_text += f"  - {col['column_name']} ({col['data_type']})"
            if col['is_nullable'] == 'NO':
                schema_text += " NOT NULL"
            schema_text += "\n"
        
        return schema_text
    
    def generate_validation_rules(self, table_schema, num_rules=10):
        """
        Use AI to generate data quality validation rules
        
        Args:
            table_schema: Table schema description
            num_rules: Number of rules to generate
        """
        
        prompt = f"""You are a data quality expert for the shipping industry. 
Given the following database table schema for voyage performance tracking:

{table_schema}

Generate {num_rules} critical data quality validation rules specific to shipping operations.

For each rule, provide:
1. rule_name: A short descriptive name
2. description: What the rule checks
3. sql_check: A PostgreSQL query that returns rows violating this rule
4. severity: LOW, MEDIUM, HIGH, or CRITICAL
5. business_impact: Why this rule matters

Focus on shipping-specific logic such as:
- Time continuity (arrival > departure)
- Physical limits (speed, fuel consumption)
- Geographic validity (latitude/longitude ranges)
- Business logic (cargo consistency, ballast conditions)
- Data completeness and format

Return ONLY a valid JSON array of rules, no additional text.

Example format:
[
  {{
    "rule_name": "Time Sequence Validation",
    "description": "Arrival time must be after departure time",
    "sql_check": "SELECT * FROM voyage_performance WHERE arrival_at <= departure_at",
    "severity": "CRITICAL",
    "business_impact": "Invalid time sequences indicate data entry errors or system clock issues"
  }}
]
"""
        
        try:
            print("🤖 Generating validation rules with AI...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data quality expert specializing in maritime shipping operations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            rules_text = response.choices[0].message.content.strip()
            
            # clean up markdown formatting if present
            if rules_text.startswith("```json"):
                rules_text = rules_text[7:]
            if rules_text.startswith("```"):
                rules_text = rules_text[3:]
            if rules_text.endswith("```"):
                rules_text = rules_text[:-3]
            
            rules = json.loads(rules_text.strip())
            
            print(f"✅ Successfully generated {len(rules)} validation rules")
            return rules
            
        except Exception as e:
            print(f"❌ Failed to generate rules: {e}")
            return []
    
    def validate_data_with_rules(self, db_connection, rules):
        """
        Use the generated rules to validate data
        
        Returns:
            violations: List of violation records
        """
        violations = []
        
        print(f"\n🔍 Starting to execute {len(rules)} validation rules...\n")
        
        for i, rule in enumerate(rules, 1):
            try:
                # Execute validation SQL
                result = db_connection.execute_query(rule['sql_check'])
                
                if result and len(result) > 0:
                    violation = {
                        'rule': rule,
                        'violation_count': len(result),
                        'sample_records': result[:5]  # Only take the first 5 samples
                    }
                    violations.append(violation)
                    
                    print(f"⚠️  Rule {i}: {rule['rule_name']}")
                    print(f"   Severity: {rule['severity']}")
                    print(f"   Violation Count: {len(result)}")
                    print(f"   Description: {rule['description']}\n")
                else:
                    print(f"✅ Rule {i}: {rule['rule_name']} - No violations")
            
            except Exception as e:
                print(f"❌ Rule {i} execution failed: {e}")
        
        return violations
    
    def save_rules_to_file(self, rules, filepath='data/processed/validation_rules.json'):
        """Save rules to a file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
            print(f"💾 Rules saved to: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to save rules: {e}")
            return False
    
    def load_rules_from_file(self, filepath='data/processed/validation_rules.json'):
        """Load rules from a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            print(f"📂 Loaded {len(rules)} rules from file")
            return rules
        except Exception as e:
            print(f"❌ Failed to load rules: {e}")
            return []


if __name__ == "__main__":
    from src.db.connection import DatabaseConnection
    
    # test the rule generator
    db = DatabaseConnection()
    if db.connect():
        generator = RuleGenerator()
        
        # get table schema
        schema = generator.get_table_schema(db)
        print("📋 Table Schema:")
        print(schema)
        
        # generate rules
        rules = generator.generate_validation_rules(schema, num_rules=10)
        
        if rules:
            # save rules
            generator.save_rules_to_file(rules)
            
            # execute rules and get violations
            violations = generator.validate_data_with_rules(db, rules)
            
            print(f"\n📊 Validation Summary:")
            print(f"   Total Rules: {len(rules)}")
            print(f"   Violations Found: {len(violations)} Types")
        
        db.close()
