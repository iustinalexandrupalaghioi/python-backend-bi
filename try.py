import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_db_connection():
    try:
        url = os.getenv("DB_URL")
        connection = await asyncpg.connect(dsn=url)
        print("Database connection successful.")
        query = "SELECT NOW();"  # Simple test query
        result = await connection.fetch(query)
        print(result)
        await connection.close()
    except Exception as e:
        print(f"Database connection failed: {str(e)}")

asyncio.run(test_db_connection())
