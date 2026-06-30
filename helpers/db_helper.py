import aiomysql
import os
import asyncio

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Initializes the MariaDB connection pool."""
        try:
            self.pool = await aiomysql.create_pool(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT', 3306)),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASS'),
                db=os.getenv('DB_NAME', 'discord_bot'),
                autocommit=True,
                minsize=1,
                maxsize=10
            )
            print("✅ MariaDB Connection Pool established.")
        except Exception as e:
            print(f"❌ Failed to connect to MariaDB: {e}")

    async def execute(self, query, *args):
        """Executes a query (INSERT, UPDATE, DELETE)."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return cur

    async def fetchrow(self, query, *args):
        """Fetches a single row as a dictionary."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchone()

    async def fetch(self, query, *args):
        """Fetches multiple rows as a list of dictionaries."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchall()