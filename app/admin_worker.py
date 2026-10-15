"""Sequential Telegram sender for confirmed miniapp broadcasts."""
import asyncio, logging
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from . import admin_db as adb
log=logging.getLogger(__name__)

async def broadcast_loop(bot):
    while True:
        try:
            with adb.connection() as c:
                rows=[dict(x) for x in c.execute('''SELECT d.id,d.recipient,d.broadcast_id,b.body,b.media_file_id FROM mini_delivery d JOIN mini_broadcasts b ON b.id=d.broadcast_id WHERE d.status='pending' AND b.state='queued' ORDER BY d.id LIMIT 20''')]
            for r in rows:
                try:
                    if r['media_file_id'] and len(r['body'])<=1024:
                        await bot.send_photo(r['recipient'],r['media_file_id'],caption=r['body'])
                    else:
                        if r['media_file_id']:await bot.send_photo(r['recipient'],r['media_file_id'])
                        await bot.send_message(r['recipient'],r['body'])
                    status='sent';error=None
                except TelegramRetryAfter as e:
                    await asyncio.sleep(min(e.retry_after,120));continue
                except Exception as e:
                    status='failed';error=str(e)[:500]
                with adb.connection() as c:
                    c.execute('UPDATE mini_delivery SET status=?,error=? WHERE id=?',(status,error,r['id']))
                    c.execute('''UPDATE mini_broadcasts SET sent=(SELECT COUNT(*) FROM mini_delivery WHERE broadcast_id=? AND status='sent'),failed=(SELECT COUNT(*) FROM mini_delivery WHERE broadcast_id=? AND status='failed') WHERE id=?''',(r['broadcast_id'],r['broadcast_id'],r['broadcast_id']))
                await asyncio.sleep(.08)
            with adb.connection() as c:
                c.execute('''UPDATE mini_broadcasts SET state='done' WHERE state='queued' AND NOT EXISTS (SELECT 1 FROM mini_delivery WHERE broadcast_id=mini_broadcasts.id AND status='pending')''')
        except Exception:
            log.exception('Broadcast worker')
        await asyncio.sleep(3)
