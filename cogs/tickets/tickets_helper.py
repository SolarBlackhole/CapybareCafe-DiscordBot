import chat_exporter
import io

class TicketHelper:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def create_ticket_record(self, user_id, channel_id):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO tickets (user_id, channel_id, status) VALUES (%s, %s, 'open')", 
                    (user_id, channel_id)
                )
    
    async def close_ticket_record(self, channel_id):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE tickets SET status = 'closed' WHERE channel_id = %s", 
                    (channel_id,)
                )
    
    async def generate_transcript(self, channel_id):
        transcript = await chat_exporter.export(channel_id)
        if transcript is None:
            return None
    
        return discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{channel_id}.html"
        )