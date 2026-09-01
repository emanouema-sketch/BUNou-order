import sqlite3
import os
from datetime import datetime

import config

_ALLOWED_PRODUCT_FIELDS = {"name", "description", "price", "stock", "photo_file_id", "active"}
_ALLOWED_SELLER_FIELDS = {"name", "commission_percent", "active"}
_ALLOWED_ORDER_FIELDS = {
    "buyer_name", "phone", "seller_code", "discount_code", "discount_amount",
    "items_text", "subtotal", "shipping_method", "shipping_cost", "shipping_cod",
    "total", "province", "city", "address", "status", "stage",
    "abandoned_notified", "receipt_file_id",
}


def get_conn():
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        price INTEGER NOT NULL,
        stock INTEGER DEFAULT 0,
        photo_file_id TEXT,
        active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sellers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        chat_id INTEGER,
        code TEXT UNIQUE NOT NULL,
        commission_percent REAL NOT NULL DEFAULT 0,
        active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS discount_codes(
        code TEXT PRIMARY KEY,
        percent INTEGER NOT NULL,
        seller_code TEXT,
        active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_chat_id INTEGER,
        customer_username TEXT,
        buyer_name TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        seller_code TEXT,
        discount_code TEXT,
        discount_amount INTEGER DEFAULT 0,
        items_text TEXT DEFAULT '',
        subtotal INTEGER DEFAULT 0,
        shipping_method TEXT,
        shipping_cost INTEGER DEFAULT 0,
        shipping_cod INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        province TEXT,
        city TEXT,
        address TEXT,
        status TEXT DEFAULT 'cart',
        stage TEXT DEFAULT 'انتخاب محصول',
        abandoned_notified INTEGER DEFAULT 0,
        receipt_file_id TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        qty INTEGER,
        price_each INTEGER
    )""")

    conn.commit()

    c.execute("SELECT COUNT(*) AS n FROM products")
    if c.fetchone()["n"] == 0:
        demo = [
            ("سرم ویتامین C", "روشن‌کننده و آنتی‌اکسیدان", 420000, 25, None, 1),
            ("کرم مرطوب‌کننده گلاب", "مناسب پوست حساس", 285000, 30, None, 1),
            ("رژ لب مخملی", "ماندگاری بالا، رنگ رز", 165000, 40, None, 1),
            ("ماسک مو آرگان", "ترمیم‌کننده موهای آسیب‌دیده", 210000, 20, None, 1),
            ("تونر ضدجوش", "تنظیم‌کننده چربی پوست", 190000, 22, None, 1),
            ("کرم ضدآفتاب SPF50", "بدون چربی، ضد آب", 245000, 18, None, 1),
            ("عطر جیبی یاس", "رایحه ماندگار و ملایم", 330000, 15, None, 1),
            ("شامپو بدن بادام", "نرم‌کننده و معطر", 175000, 28, None, 1),
        ]
        c.executemany(
            "INSERT INTO products(name, description, price, stock, photo_file_id, active) VALUES (?,?,?,?,?,?)",
            demo,
        )

    c.execute("SELECT COUNT(*) AS n FROM sellers")
    if c.fetchone()["n"] == 0:
        demo_sellers = [
            ("نگار احمدی", None, "NEGAR", 10, 1),
            ("پریسا کریمی", None, "PARISA", 12, 1),
            ("مهسا رضایی", None, "MAHSA", 8, 1),
        ]
        c.executemany(
            "INSERT INTO sellers(name, chat_id, code, commission_percent, active) VALUES (?,?,?,?,?)",
            demo_sellers,
        )
    conn.commit()
    conn.close()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ==================== PRODUCTS ====================
def list_products(active_only=False):
    conn = get_conn()
    q = "SELECT * FROM products"
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY id"
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows


def get_product(product_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return row


def add_product(name, price, stock=0, description=""):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO products(name, description, price, stock, active) VALUES (?,?,?,?,1)",
        (name, description, price, stock),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def remove_product(product_id):
    conn = get_conn()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


def update_product_field(product_id, field, value):
    if field not in _ALLOWED_PRODUCT_FIELDS:
        raise ValueError(f"invalid field: {field}")
    conn = get_conn()
    conn.execute(f"UPDATE products SET {field}=? WHERE id=?", (value, product_id))
    conn.commit()
    conn.close()


def toggle_product_active(product_id):
    conn = get_conn()
    conn.execute("UPDATE products SET active = 1 - active WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


# ==================== SELLERS (فروشنده‌ها) ====================
def list_sellers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM sellers ORDER BY id").fetchall()
    conn.close()
    return rows


def get_seller_by_code(code):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sellers WHERE code=?", (code.upper(),)).fetchone()
    conn.close()
    return row


def get_seller_by_chat_id(chat_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sellers WHERE chat_id=? AND active=1", (chat_id,)).fetchone()
    conn.close()
    return row


def add_seller(name, code, commission_percent):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sellers(name, code, commission_percent, active) VALUES (?,?,?,1)",
        (name, code.upper(), commission_percent),
    )
    conn.commit()
    conn.close()


def remove_seller(seller_id):
    conn = get_conn()
    conn.execute("DELETE FROM sellers WHERE id=?", (seller_id,))
    conn.commit()
    conn.close()


def update_seller_field(seller_id, field, value):
    if field not in _ALLOWED_SELLER_FIELDS:
        raise ValueError(f"invalid field: {field}")
    conn = get_conn()
    conn.execute(f"UPDATE sellers SET {field}=? WHERE id=?", (value, seller_id))
    conn.commit()
    conn.close()


def toggle_seller_active(seller_id):
    conn = get_conn()
    conn.execute("UPDATE sellers SET active = 1 - active WHERE id=?", (seller_id,))
    conn.commit()
    conn.close()


def bind_seller_chat_id(code, chat_id):
    conn = get_conn()
    conn.execute("UPDATE sellers SET chat_id=? WHERE code=?", (chat_id, code.upper()))
    conn.commit()
    conn.close()


# ==================== DISCOUNT CODES ====================
def get_discount(code):
    conn = get_conn()
    row = conn.execute("SELECT * FROM discount_codes WHERE code=? AND active=1", (code.upper(),)).fetchone()
    conn.close()
    return row


def list_discounts():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM discount_codes ORDER BY code").fetchall()
    conn.close()
    return rows


def add_discount(code, percent, seller_code=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO discount_codes(code, percent, seller_code, active) VALUES (?,?,?,1)",
        (code.upper(), percent, seller_code.upper() if seller_code else None),
    )
    conn.commit()
    conn.close()


def remove_discount(code):
    conn = get_conn()
    conn.execute("DELETE FROM discount_codes WHERE code=?", (code.upper(),))
    conn.commit()
    conn.close()


def toggle_discount(code):
    conn = get_conn()
    conn.execute("UPDATE discount_codes SET active = 1 - active WHERE code=?", (code.upper(),))
    conn.commit()
    conn.close()


# ==================== ORDERS ====================
def create_draft_order(customer_chat_id, customer_username):
    conn = get_conn()
    now = _now()
    cur = conn.execute(
        """INSERT INTO orders(customer_chat_id, customer_username, status, stage, created_at, updated_at)
           VALUES (?,?,?,?,?,?)""",
        (customer_chat_id, customer_username, "cart", "انتخاب محصول", now, now),
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def update_order(order_id, **fields):
    if not fields:
        return
    bad = set(fields) - _ALLOWED_ORDER_FIELDS
    if bad:
        raise ValueError(f"invalid order fields: {bad}")
    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [order_id]
    conn = get_conn()
    conn.execute(f"UPDATE orders SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()


def get_order(order_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row


def finalize_items(order_id, items):
    """items: لیستی از دیکشنری‌های {product_id, name, qty, price}"""
    conn = get_conn()
    conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
    for it in items:
        conn.execute(
            "INSERT INTO order_items(order_id, product_id, product_name, qty, price_each) VALUES (?,?,?,?,?)",
            (order_id, it.get("product_id"), it["name"], it["qty"], it["price"]),
        )
    conn.commit()
    conn.close()


def attach_receipt(order_id, file_id):
    update_order(order_id, receipt_file_id=file_id, status="waiting_review", stage="در انتظار بررسی فیش")


def set_status(order_id, status):
    update_order(order_id, status=status)


def mark_abandoned_notified(order_id):
    update_order(order_id, abandoned_notified=1, status="abandoned")


def seller_orders(seller_code, status=None, limit=20):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM orders WHERE seller_code=? AND status=? ORDER BY id DESC LIMIT ?",
            (seller_code.upper(), status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM orders WHERE seller_code=? ORDER BY id DESC LIMIT ?",
            (seller_code.upper(), limit),
        ).fetchall()
    conn.close()
    return rows


def orders_by_status(status, limit=30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)
    ).fetchall()
    conn.close()
    return rows


def search_order(order_id):
    return get_order(order_id)


# ==================== REPORTS ====================
def stats_today():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    confirmed_today = conn.execute(
        "SELECT * FROM orders WHERE status='confirmed' AND created_at LIKE ?", (today + "%",)
    ).fetchall()
    pending_payment = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE status IN ('cart','pending_payment')").fetchone()["n"]
    abandoned = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE status='abandoned'").fetchone()["n"]
    confirmed_total = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE status='confirmed'").fetchone()["n"]
    conn.close()
    return {
        "today_order_count": len(confirmed_today),
        "today_sales": sum(o["total"] for o in confirmed_today),
        "pending_payment": pending_payment,
        "abandoned": abandoned,
        "confirmed_total": confirmed_total,
    }


def stats_overall():
    conn = get_conn()
    confirmed = conn.execute("SELECT * FROM orders WHERE status='confirmed'").fetchall()
    total_toman = sum(o["total"] for o in confirmed)

    seller_totals = {}
    for o in confirmed:
        if o["seller_code"]:
            seller_totals[o["seller_code"]] = seller_totals.get(o["seller_code"], 0) + o["subtotal"]
    top_seller_code = max(seller_totals, key=seller_totals.get) if seller_totals else None
    top_seller = get_seller_by_code(top_seller_code) if top_seller_code else None

    top_product = conn.execute(
        """SELECT oi.product_name AS name, SUM(oi.qty) AS qty
           FROM order_items oi JOIN orders o ON o.id = oi.order_id
           WHERE o.status='confirmed'
           GROUP BY oi.product_name ORDER BY qty DESC LIMIT 1"""
    ).fetchone()
    conn.close()

    return {
        "order_count": len(confirmed),
        "total_toman": total_toman,
        "top_seller_name": top_seller["name"] if top_seller else None,
        "top_seller_code": top_seller_code,
        "top_seller_amount": seller_totals.get(top_seller_code, 0) if top_seller_code else 0,
        "top_product_name": top_product["name"] if top_product else None,
        "top_product_qty": top_product["qty"] if top_product else 0,
    }


def seller_stats(seller_code):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE seller_code=? AND status='confirmed'", (seller_code.upper(),)
    ).fetchall()
    conn.close()
    seller = get_seller_by_code(seller_code)
    subtotal_sum = sum(o["subtotal"] for o in rows)
    rate = seller["commission_percent"] if seller else 0
    return {
        "order_count": len(rows),
        "sales_total": subtotal_sum,
        "commission_rate": rate,
        "commission_total": round(subtotal_sum * rate / 100),
    }
