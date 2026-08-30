import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "bunou.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS vendors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        commission_rate REAL NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS discount_codes(
        code TEXT PRIMARY KEY,
        percent INTEGER NOT NULL,
        vendor_code TEXT,
        active INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        phone TEXT,
        items_text TEXT,
        subtotal INTEGER,
        vendor_code TEXT,
        discount_code TEXT,
        discount_amount INTEGER,
        shipping_method TEXT,
        shipping_cost INTEGER,
        shipping_cod INTEGER DEFAULT 0,
        total INTEGER,
        province TEXT,
        city TEXT,
        address TEXT,
        status TEXT DEFAULT 'awaiting_receipt',
        receipt_file_id TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_name TEXT,
        qty INTEGER,
        price_each INTEGER
    )""")
    conn.commit()

    # seed demo data only if empty, so it matches the website
    c.execute("SELECT COUNT(*) AS n FROM products")
    if c.fetchone()["n"] == 0:
        demo_products = [
            ("سرم ویتامین C", 420000, "روشن‌کننده و آنتی‌اکسیدان"),
            ("کرم مرطوب‌کننده گلاب", 285000, "مناسب پوست حساس"),
            ("رژ لب مخملی", 165000, "ماندگاری بالا، رنگ رز"),
            ("ماسک مو آرگان", 210000, "ترمیم‌کننده موهای آسیب‌دیده"),
            ("تونر ضدجوش", 190000, "تنظیم‌کننده چربی پوست"),
            ("کرم ضدآفتاب SPF50", 245000, "بدون چربی، ضد آب"),
            ("عطر جیبی یاس", 330000, "رایحه ماندگار و ملایم"),
            ("شامپو بدن بادام", 175000, "نرم‌کننده و معطر"),
        ]
        c.executemany("INSERT INTO products(name, price, description) VALUES (?,?,?)", demo_products)

    c.execute("SELECT COUNT(*) AS n FROM vendors")
    if c.fetchone()["n"] == 0:
        demo_vendors = [
            ("نگار احمدی", "NEGAR", 10),
            ("پریسا کریمی", "PARISA", 12),
            ("مهسا رضایی", "MAHSA", 8),
        ]
        c.executemany("INSERT INTO vendors(name, code, commission_rate) VALUES (?,?,?)", demo_vendors)
    conn.commit()
    conn.close()


# ---------- products ----------
def list_products():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return rows


def get_product(product_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return row


def add_product(name, price, description=""):
    conn = get_conn()
    conn.execute("INSERT INTO products(name, price, description) VALUES (?,?,?)", (name, price, description))
    conn.commit()
    conn.close()


def remove_product(product_id):
    conn = get_conn()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


def update_price(product_id, new_price):
    conn = get_conn()
    conn.execute("UPDATE products SET price=? WHERE id=?", (new_price, product_id))
    conn.commit()
    conn.close()


# ---------- vendors (= فروشنده‌ها) ----------
def list_vendors():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM vendors ORDER BY id").fetchall()
    conn.close()
    return rows


def get_vendor_by_code(code):
    conn = get_conn()
    row = conn.execute("SELECT * FROM vendors WHERE code=?", (code.upper(),)).fetchone()
    conn.close()
    return row


def add_vendor(name, code, commission_rate):
    conn = get_conn()
    conn.execute("INSERT INTO vendors(name, code, commission_rate) VALUES (?,?,?)", (name, code.upper(), commission_rate))
    conn.commit()
    conn.close()


def set_commission(code, new_rate):
    conn = get_conn()
    conn.execute("UPDATE vendors SET commission_rate=? WHERE code=?", (new_rate, code.upper()))
    conn.commit()
    conn.close()


# ---------- discount codes ----------
def get_discount(code):
    conn = get_conn()
    row = conn.execute("SELECT * FROM discount_codes WHERE code=? AND active=1", (code.upper(),)).fetchone()
    conn.close()
    return row


def add_discount(code, percent, vendor_code=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO discount_codes(code, percent, vendor_code, active) VALUES (?,?,?,1)",
        (code.upper(), percent, vendor_code),
    )
    conn.commit()
    conn.close()


def deactivate_discount(code):
    conn = get_conn()
    conn.execute("UPDATE discount_codes SET active=0 WHERE code=?", (code.upper(),))
    conn.commit()
    conn.close()


# ---------- orders ----------
def create_order(data):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO orders(user_id, username, phone, items_text, subtotal, vendor_code, discount_code,
           discount_amount, shipping_method, shipping_cost, shipping_cod, total, province, city, address,
           status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data["user_id"], data["username"], data.get("phone", ""), data["items_text"], data["subtotal"],
            data.get("vendor_code"), data.get("discount_code"), data.get("discount_amount", 0),
            data["shipping_method"], data["shipping_cost"], int(data.get("shipping_cod", False)),
            data["total"], data["province"], data["city"], data["address"],
            "awaiting_receipt", datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    order_id = cur.lastrowid
    for item in data.get("items", []):
        conn.execute(
            "INSERT INTO order_items(order_id, product_name, qty, price_each) VALUES (?,?,?,?)",
            (order_id, item["name"], item["qty"], item["price"]),
        )
    conn.commit()
    conn.close()
    return order_id


def attach_receipt(order_id, file_id):
    conn = get_conn()
    conn.execute("UPDATE orders SET receipt_file_id=?, status='pending_review' WHERE id=?", (file_id, order_id))
    conn.commit()
    conn.close()


def set_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()


def get_order(order_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row


def pending_orders():
    """Carts that were created (card info shown) but never got a receipt / never got resolved."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE status='awaiting_receipt' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def vendor_orders(vendor_code):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE vendor_code=? AND status='confirmed' ORDER BY id DESC", (vendor_code.upper(),)
    ).fetchall()
    conn.close()
    return rows


def get_stats():
    conn = get_conn()
    confirmed = conn.execute("SELECT * FROM orders WHERE status='confirmed'").fetchall()
    count = len(confirmed)
    total_toman = sum(o["total"] for o in confirmed)

    # top vendor by attributed sales (subtotal of orders using their code)
    vendor_totals = {}
    for o in confirmed:
        if o["vendor_code"]:
            vendor_totals[o["vendor_code"]] = vendor_totals.get(o["vendor_code"], 0) + o["subtotal"]
    top_vendor_code, top_vendor_amount = (None, 0)
    if vendor_totals:
        top_vendor_code = max(vendor_totals, key=vendor_totals.get)
        top_vendor_amount = vendor_totals[top_vendor_code]
    top_vendor_row = get_vendor_by_code(top_vendor_code) if top_vendor_code else None

    # top product by quantity sold, across confirmed orders only
    rows = conn.execute(
        """SELECT oi.product_name AS name, SUM(oi.qty) AS qty
           FROM order_items oi JOIN orders o ON o.id = oi.order_id
           WHERE o.status='confirmed'
           GROUP BY oi.product_name ORDER BY qty DESC LIMIT 1"""
    ).fetchone()
    conn.close()

    return {
        "order_count": count,
        "total_toman": total_toman,
        "top_vendor_name": top_vendor_row["name"] if top_vendor_row else None,
        "top_vendor_code": top_vendor_code,
        "top_vendor_amount": top_vendor_amount,
        "top_product_name": rows["name"] if rows else None,
        "top_product_qty": rows["qty"] if rows else 0,
    }
