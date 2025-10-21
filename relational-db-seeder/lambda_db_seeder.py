import psycopg2
import os

def handler(event, context):
    db_host = os.environ['DB_HOST']
    db_user = os.environ['DB_USER']
    db_pass = os.environ['DB_PASS']
    db_port = os.environ['DB_PORT']
    db_name = os.environ['DB_NAME']
    sql_file_path = os.path.join(os.path.dirname(__file__), "01_create_tables.sql")

    print(f"Connecting to {db_host}...")

    try:
        conn = psycopg2.connect(
            dbname=db_name,
            port=db_port,
            host=db_host,
            user=db_user,
            password=db_pass
        )
        cur = conn.cursor()

        with open(sql_file_path, 'r') as f:
            sql_commands = f.read()

        print("Running SQL script...")
        cur.execute(sql_commands)
        conn.commit()

        print("Tables created successfully!")

        cur.close()
        conn.close()

        return {"status": "ok", "message": "Tables created successfully"}

    except Exception as e:
        print("Error executing SQL:", str(e))
        return {"status": "error", "message": str(e)}