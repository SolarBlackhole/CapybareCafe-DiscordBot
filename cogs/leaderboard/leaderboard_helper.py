import math

class LeaderboardHelper:
    def __init__(self, db_pool):
        self.db_pool = db_pool

        def calculate_level(self, xp):
            return math.floor(xp / 100)
        
        async def add_xp(self, user_id, xp):
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO leveling (user_id, xp) VALUES (%s, %s) "
                        "ON DUPLICATE KEY UPDATE xp = xp + VALUES(xp)", 
                        (user_id, xp, xp)
                    )
                    await cur.execute("SELECT xp FROM leveling WHERE user_id = %s", (user_id,))
                    return await cur.fetchone()
        
        async def get_leaderboard(self, limit=10):
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT user_id, xp FROM leveling ORDER BY xp DESC LIMIT %s", 
                        (limit,)
                    )
                    return await cur.fetchall()
                
        async def get_user_xp(self, user_id):
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT xp FROM leveling WHERE user_id = %s", (user_id,))
                    result = await cur.fetchone()
                    return result[0] if result else 0
                
