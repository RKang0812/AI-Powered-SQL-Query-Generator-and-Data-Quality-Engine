"""
provides a DatabaseConnection class for managing PostgreSQL connections, executing queries, and handling results.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import pandas as pd

# loding environment variables from .env file
load_dotenv()


class DatabaseConnection:
    """Database connection manager"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'naviguard_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print("✅ Database connection established!")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("🔒 Database connection closed")
    
    def execute_query(self, query, params=None, fetch=True):
        """
        Execute SQL query
        
        Args:
            query: SQL query statement
            params: Query parameters
            fetch: Whether to return results
        """
        try:
            self.cursor.execute(query, params)
            
            if fetch:
                return self.cursor.fetchall()
            else:
                self.conn.commit()
                return self.cursor.rowcount
        except Exception as e:
            self.conn.rollback()
            print(f"❌ failed: {e}")
            raise e
    
    def execute_file(self, filepath):
        """Execute SQL file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            self.cursor.execute(sql)
            self.conn.commit()
            print(f"✅ file executed: {filepath}")
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ SQL file execution failed: {e}")
            return False
    
    def query_to_dataframe(self, query, params=None):
        """Execute query and return Pandas DataFrame"""
        try:
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        except Exception as e:
            print(f"❌ Query to DataFrame failed: {e}")
            return None
    
    def insert_dataframe(self, df, table_name, if_exists='append'):
        """
        insert Pandas DataFrame into database table
        
        Args:
            df: Pandas DataFrame
            table_name: Target table name
            if_exists: 'append', 'replace', 'fail'
        """
        try:
            df.to_sql(
                table_name, 
                self.conn, 
                if_exists=if_exists, 
                index=False,
                method='multi'
            )
            print(f"✅ Successfully inserted {len(df)} rows into table {table_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to insert data: {e}")
            return False
    
    def get_table_info(self, table_name):
        """Get table structure information"""
        query = """
        SELECT 
            column_name, 
            data_type, 
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
        """
        return self.execute_query(query, (table_name,))
    
    def count_rows(self, table_name, where_clause=None):
        """Count rows in a table"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        result = self.execute_query(query)
        return result[0]['count'] if result else 0


def test_connection():
    """Test database connection"""
    db = DatabaseConnection()
    
    if db.connect():
        # Test query
        result = db.execute_query("SELECT version();")
        print(f"\n📊 PostgreSQL version: {result[0]['version']}")
        
        # List all tables
        tables = db.execute_query("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        print(f"\n📋 Tables in the database:")
        for table in tables:
            count = db.count_rows(table['tablename'])
            print(f"   - {table['tablename']}: {count} rows")
        
        db.close()
        return True
    else:
        return False


if __name__ == "__main__":
    test_connection()
