import aiosqlite, os
from aiogram import types
from datetime import datetime, timedelta
import aiosqlite
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "database.db")
db: aiosqlite.Connection = None
OFFSET = 3


async def init_db():
    global db
    db = await aiosqlite.connect(DB_NAME)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id BIGINT PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            buyer BOOLEAN NOT NULL DEFAULT 0,
            active_slots INTEGER NOT NULL DEFAULT 0
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            png TEXT NOT NULL,
            size TEXT,
            price TEXT NOT NULL,
            user_id BIGINT,
            description TEXT,
            channel_id BIGINT,
            message_id BIGINT,
            FOREIGN KEY (user_id) REFERENCES users (tg_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT NOT NULL,
            username TEXT,
            slot_id INTEGER NOT NULL,
            size TEXT,
            delivery TEXT,
            address TEXT,
            proof TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slot_id) REFERENCES slots (id)
        )
    """)
    await db.commit()
    print("✅ Таблицы готовы (users, slots, orders)")


async def shift_created_at():
    global db
    cursor = await db.execute("SELECT id, created_at FROM orders")
    rows = await cursor.fetchall()

    for order_id, created_at in rows:
        dt = datetime.fromisoformat(created_at)
        dt_new = dt + timedelta(hours=OFFSET)
        await db.execute(
            "UPDATE orders SET created_at = ? WHERE id = ?",
            (dt_new.strftime("%Y-%m-%d %H:%M:%S"), order_id)
        )

    await db.commit()


# ================= USERS =================

async def add_user(user):
    global db
    await db.execute(
        "INSERT OR IGNORE INTO users (tg_id, username, buyer, active_slots) VALUES (?, ?, ?, ?)",
        (user.id, user.username or "unknown", 0, 0)
    )
    await db.commit()


async def get_users():
    global db
    cursor = await db.execute("SELECT tg_id, username FROM users")
    return await cursor.fetchall()


async def mark_as_buyer(tg_id: int):
    global db
    await db.execute("UPDATE users SET buyer = 1 WHERE tg_id = ?", (tg_id,))
    await db.commit()

async def get_buyers():
    query = """
        SELECT u.tg_id, u.username,
               COUNT(o.id) AS active_slots
        FROM users u
        LEFT JOIN orders o 
            ON u.tg_id = o.user_id
            AND o.status IN ('paid', 'processing', 'shipped')
        WHERE u.buyer = 1
        GROUP BY u.tg_id, u.username
    """
    global db
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(query)
    buyers = await cursor.fetchall()
    return buyers



async def increment_slots(tg_id: int, count: int = 1):
    global db
    await db.execute(
            "UPDATE users SET active_slots = active_slots + ? WHERE tg_id = ?",
            (count, tg_id)
        )
    await db.commit()


async def decrement_slots(tg_id: int, count: int = 1):
    global db
    await db.execute(
            "UPDATE users SET active_slots = MAX(active_slots - ?, 0) WHERE tg_id = ?",
            (count, tg_id)
        )
    await db.commit()


# ================= SLOTS =================

async def add_slot(name: str, png: str, size: str, price: str, user_id: int, description: str = None):
    global db
    await db.execute(
        "INSERT INTO slots (name, png, size, price, user_id, description) VALUES (?, ?, ?, ?, ?, ?)",
        (name, png, size, price, user_id, description),
    )
    await db.commit()



async def update_slot_size(slot_id: int, new_size: str):
    global db
    cursor = await db.execute("SELECT size FROM slots WHERE id = ?", (slot_id,))
    row = await cursor.fetchone()
    if not row:
        return False

    current_sizes = row[0].split(",") if row[0] else []
    if new_size in current_sizes:
        return True

    updated_sizes = ",".join(current_sizes + [new_size]) if current_sizes else new_size
    await db.execute("UPDATE slots SET size = ? WHERE id = ?", (updated_sizes, slot_id))
    await db.commit()
    return True



async def save_slot_post(slot_id: int, channel_id: int, message_id: int):
    """сохраняем id канала и сообщения после публикации"""
    global db
    await db.execute(
        "UPDATE slots SET channel_id = ?, message_id = ? WHERE id = ?",
        (channel_id, message_id, slot_id)
    )
    await db.commit()


async def get_slots():
    global db
    cursor = await db.execute("SELECT id, name, price, user_id FROM slots")
    rows = await cursor.fetchall()
    return [
        {"id": row[0], "name": row[1], "price": row[2], "user_id": row[3]}
        for row in rows
    ]



async def get_slot(slot_id: int):
    global db
    cursor = await db.execute(
        "SELECT id, name, png, size, price, description, user_id, channel_id, message_id FROM slots WHERE id = ?",
        (slot_id,),
    )
    row = await cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "png": row[2],
            "size": row[3],
            "price": row[4],
            "description": row[5],
            "user_id": row[6],
            "channel_id": row[7],
            "message_id": row[8],
        }
    return None





async def update_slot(slot_id: int, field: str, value: str):
    global db
    await db.execute(
        f"UPDATE slots SET {field} = ? WHERE id = ?",
        (value, slot_id)
    )
    await db.commit()




async def get_user_slots(user_id: int):
    global db
    cursor = await db.execute(
        "SELECT id, name, price FROM slots WHERE user_id = ?",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [
        {"id": row[0], "name": row[1], "price": row[2]}
        for row in rows
    ]


async def delete_slot(slot_id: int):
    global db
    await db.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    await db.commit()


async def reset_slots():
    global db
    await db.execute("DELETE FROM slots")
    await db.execute("DELETE FROM sqlite_sequence WHERE name='slots'")
    await db.commit()
    print("♻️ Таблица slots очищена, ID сброшены")
# ================= ORDERS =================

async def create_order(
    user_id: int,
    slot_id: int,
    username: str | None = None,
    size: str | None = None,
    delivery: str | None = None,
    address: str | None = None,
):
    global db
    cursor = await db.execute(
        """
        INSERT INTO orders (user_id, username, slot_id, size, delivery, address, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (user_id, username, slot_id, size, delivery, address),
    )
    await increment_slots(user_id)

    await db.commit()
    return cursor.lastrowid





async def get_users_with_orders():
    query = """
        SELECT u.tg_id, u.username, u.buyer,
               COUNT(o.id) as active_slots
        FROM users u
        LEFT JOIN orders o
            ON u.tg_id = o.user_id
           AND o.status IN ('paid', 'processing', 'shipped')
        GROUP BY u.tg_id, u.username, u.buyer
    """
    global db
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(query)
    return await cursor.fetchall()


async def get_order_user(order_id: int):
    global db
    cursor = await db.execute(
        """
        SELECT o.user_id, s.name
        FROM orders o
        JOIN slots s ON o.slot_id = s.id
        WHERE o.id = ?
        """,
        (order_id,)
    )
    return await cursor.fetchone()


async def update_order_address(order_id: int, address: str):
    global db
    await db.execute("UPDATE orders SET address = ? WHERE id = ?", (address, order_id))
    await db.commit()

async def get_all_users():
    global db
    cursor = await db.execute(
        "SELECT tg_id, username, buyer, active_slots FROM users"
    )
    rows = await cursor.fetchall()
    return [
        {
            "tg_id": row[0],
            "username": row[1],
            "buyer": bool(row[2]),
            "active_slots": row[3],
        }
        for row in rows
    ]




async def get_all_orders_history():
    global db
    cursor = await db.execute(
        """
        SELECT o.id, u.username, s.name, o.size, o.status, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.tg_id
        JOIN slots s ON o.slot_id = s.id
        ORDER BY o.created_at DESC
        """
    )
    return await cursor.fetchall()



async def update_order_status(order_id: int, status: str):
    global db
    await db.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (status, order_id)
    )
    await db.commit()


async def add_order_proof(order_id: int, proof_file_id: str):
    global db
    await db.execute(
        "UPDATE orders SET proof = ? WHERE id = ?",
        (proof_file_id, order_id)
    )
    await db.commit()


async def get_user_orders(user_id: int):
    global db
    cursor = await db.execute(
        "SELECT id, slot_id, size, address, status FROM orders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    return await cursor.fetchall()



async def get_all_orders():
    global db
    cursor = await db.execute(
        """
        SELECT o.id, u.username, s.name, o.status, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.tg_id
        JOIN slots s ON o.slot_id = s.id
        WHERE o.status IN ('paid', 'processing', 'shipped')
        ORDER BY o.created_at DESC
        """
    )
    return await cursor.fetchall()


async def get_order(order_id: int) -> dict | None:
    query = """
        SELECT o.id, o.user_id, o.username, o.size, o.delivery, o.address, o.status,
               o.proof, o.slot_id, s.name AS slot_name, s.price
        FROM orders o
        JOIN slots s ON o.slot_id = s.id
        WHERE o.id = ?
    """
    global db
    cursor = await db.execute(query, (order_id,))
    row = await cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "size": row[3],
            "delivery": row[4],
            "address": row[5],
            "status": row[6],
            "proof": row[7],
            "slot_id": row[8],
            "slot_name": row[9],
            "price": row[10]
        }
    return None

