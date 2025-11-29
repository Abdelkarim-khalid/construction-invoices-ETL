from sqlalchemy import create_engine, inspect, text
from database import DATABASE_URL

def check_database():
    print(f"Checking database at: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    print(f"\nFound {len(tables)} tables:")
    
    for table in tables:
        print(f"\n📋 Table: {table}")
        columns = inspector.get_columns(table)
        # Print columns
        col_names = [col['name'] for col in columns]
        print(f"   Columns: {', '.join(col_names)}")
        
        # Print first 5 rows
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table} LIMIT 5"))
            rows = result.fetchall()
            if rows:
                print("   DATA (First 5 rows):")
                for row in rows:
                    print(f"   -> {row}")
            else:
                print("   -> [Empty Table]")

if __name__ == "__main__":
    check_database()
