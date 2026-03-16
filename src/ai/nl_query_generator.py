"""
Natural Language Query Generator
Converts natural language questions into SQL queries using OpenAI GPT-4o
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class NLQueryGenerator:
    """Generate SQL queries from natural language using LLM"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    def get_table_schema(self, db):
        """
        Get database schema information for context
        
        Args:
            db: DatabaseConnection instance
            
        Returns:
            str: Formatted schema information
        """
        schema_query = """
        SELECT 
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name IN ('voyage_performance', 'dq_alerts')
        ORDER BY table_name, ordinal_position
        """
        
        try:
            schema_rows = db.execute_query(schema_query)
            
            # Format schema for LLM
            schema_text = "Database Schema:\n\n"
            current_table = None
            
            for row in schema_rows:
                if row['table_name'] != current_table:
                    current_table = row['table_name']
                    schema_text += f"\nTable: {current_table}\n"
                    schema_text += "-" * 50 + "\n"
                
                nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                schema_text += f"  {row['column_name']}: {row['data_type']} ({nullable})\n"
            
            return schema_text
        
        except Exception as e:
            print(f"Error getting schema: {e}")
            return "Schema information unavailable"
    
    def generate_sql(self, user_question, schema_context):
        """
        Generate SQL query from natural language question
        
        Args:
            user_question (str): User's question in natural language
            schema_context (str): Database schema information
            
        Returns:
            dict: Contains 'sql' query and 'explanation'
        """
        
        system_prompt = """You are an expert SQL query generator for a maritime voyage performance database.

Your task is to convert natural language questions into accurate PostgreSQL queries.

IMPORTANT RULES:
1. Generate ONLY valid PostgreSQL syntax
2. Use proper table and column names from the schema
3. Include appropriate WHERE clauses, JOINs, GROUP BY, ORDER BY as needed
4. Always use meaningful column aliases
5. Limit results to 100 rows unless specifically asked otherwise
6. Use LIMIT for top N queries
7. Handle date/time comparisons properly using PostgreSQL date functions
8. Return only executable SQL - no explanations in the SQL itself

Return your response in this exact JSON format:
{
    "sql": "SELECT ... FROM ... WHERE ...",
    "explanation": "Brief explanation of what the query does"
}

Available tables and their common use cases:
- voyage_performance: Main table with voyage data (vessel names, dates, distances, fuel consumption, cargo)
- dq_alerts: Data quality alerts and anomalies detected in voyage data
"""

        user_prompt = f"""{schema_context}

User Question: {user_question}

Generate a SQL query to answer this question. Return ONLY valid JSON with 'sql' and 'explanation' fields."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            
            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
            
            return result
        
        except Exception as e:
            print(f"Error generating SQL: {e}")
            return {
                "sql": None,
                "explanation": f"Error: {str(e)}"
            }


# Test function
if __name__ == "__main__":
    from db.connection import DatabaseConnection
    
    # Test the generator
    db = DatabaseConnection()
    db.connect()
    
    generator = NLQueryGenerator()
    schema = generator.get_table_schema(db)
    
    test_question = "What are the top 5 vessels by total fuel consumption?"
    
    print(f"Question: {test_question}\n")
    
    result = generator.generate_sql(test_question, schema)
    
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Explanation: {result['explanation']}\n")
    
    # Execute the query
    try:
        results = db.query_to_dataframe(result['sql'])
        print("Results:")
        print(results)
    except Exception as e:
        print(f"Error executing query: {e}")
    
    db.close()
