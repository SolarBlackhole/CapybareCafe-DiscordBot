class RoleHelper:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def add_role_to_menu(self, message_id, role_id, label, style):
        """Saves a button configuration to the database."""
        query = """
        INSERT INTO role_menus (message_id, role_id, label, style)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE label = VALUES(label), style = VALUES(style)
        """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (message_id, role_id, label, style))

    async def remove_role_from_menu(self, message_id, role_id):
        """Removes a specific button from a menu."""
        query = "DELETE FROM role_menus WHERE message_id = %s AND role_id = %s"
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (message_id, role_id))

    async def get_menu_roles(self, message_id):
        """Fetches all buttons associated with a specific message."""
        query = "SELECT role_id, label, style FROM role_menus WHERE message_id = %s"
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (message_id,))
                return await cur.fetchall()

    async def get_all_menu_ids(self):
        """Gets every message ID that acts as a role menu."""
        query = "SELECT DISTINCT message_id FROM role_menus"
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                result = await cur.fetchall()
                return [row[0] for row in result]
