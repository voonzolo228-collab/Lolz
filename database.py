import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                deals_count INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                lang TEXT DEFAULT 'Русский',
                requisites TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                seller_id INTEGER,
                seller_username TEXT,
                category TEXT,
                gift_link TEXT,
                requisites TEXT,
                amount_stars INTEGER,
                description TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int, username: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute(
                    "INSERT INTO users (user_id, username) VALUES (?, ?)",
                    (user_id, username or "")
                )
                await db.commit()
                return {"user_id": user_id, "username": username, "deals_count": 0, "balance": 0, "referrals": 0, "lang": "Русский", "requisites": None}
            return {"user_id": user[0], "username": user[1], "deals_count": user[2], "balance": user[3], "referrals": user[4], "lang": user[5], "requisites": user[6] if len(user) > 6 else None}

async def set_user_requisites(user_id: int, req_data: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET requisites = ? WHERE user_id = ?", (req_data, user_id))
        await db.commit()

async def add_referral(referrer_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
        await db.commit()

async def save_deal(deal_data: dict):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO deals (deal_id, seller_id, seller_username, category, gift_link, requisites, amount_stars, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deal_data['deal_id'], deal_data['seller_id'], deal_data['seller_username'],
            deal_data['category'], deal_data['gift_link'], deal_data['requisites'],
            deal_data['amount_stars'], deal_data['description']
        ))
        await db.execute("UPDATE users SET deals_count = deals_count + 1 WHERE user_id = ?", (deal_data['seller_id'],))
        await db.commit()

async def get_deal(deal_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "deal_id": row[0], "seller_id": row[1], "seller_username": row[2],
                    "category": row[3], "gift_link": row[4], "requisites": row[5],
                    "amount_stars": row[6], "description": row[7], "status": row[8]
                }
            return None
