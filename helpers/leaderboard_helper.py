import math

class LeaderboardHelper:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    def get_xp_for_level(self, level):
        """Standard formula: 5 * (lvl^2) + (50 * lvl) + 100"""
        return 5 * (level**2) + (50 * level) + 100

    async def get_user_rank(self, user_id):
        """Fetches level, xp, and calculates position (rank) in the server."""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Get user stats
                await cur.execute("SELECT xp, level FROM leveling WHERE user_id = %s", (user_id,))
                user_data = await cur.fetchone()
                
                if not user_data:
                    return None

                # Calculate Rank (Position) by counting how many people have more XP
                await cur.execute("SELECT COUNT(*) + 1 as rank FROM leveling WHERE xp > %s", (user_data['xp'],))
                rank_data = await cur.fetchone()
                
                user_data['rank'] = rank_data['rank']
                return user_data

    async def get_top_10(self):
        """Fetches the top 10 players sorted by XP."""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT user_id, xp, level FROM leveling ORDER BY xp DESC LIMIT 10")
                return await cur.fetchall()