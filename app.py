import logging
import os
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

import pymysql
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FreshCart")

app = FastAPI(title="FreshCart / Online Super Market", version="2.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "freshcart-production-super-secret-key-2026"),
    max_age=86400 * 7,  # 7 days session
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Register Decimal adapter for SQLite
sqlite3.register_adapter(Decimal, lambda d: float(d))


def _sqlite_placeholders(sql: str) -> str:
    return sql.replace("%s", "?")


class SQLiteCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql: str, params: tuple | list | None = None):
        clean_params = tuple(float(p) if isinstance(p, Decimal) else p for p in (params or ()))
        self._cursor.execute(_sqlite_placeholders(sql), clean_params)
        return self

    def executemany(self, sql: str, seq_of_params):
        clean_seq = [
            tuple(float(p) if isinstance(p, Decimal) else p for p in params)
            for params in seq_of_params
        ]
        self._cursor.executemany(_sqlite_placeholders(sql), clean_seq)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(row) for row in rows]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount


class SQLiteConnection:
    def __init__(self, database_path: str):
        self._conn = sqlite3.connect(database_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def cursor(self):
        return SQLiteCursor(self._conn.cursor())

    def close(self):
        try:
            self._conn.commit()
        except Exception:
            pass
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def ensure_sqlite_schema(database_path: str):
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_account (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            dob DATE,
            mobile VARCHAR(30),
            address TEXT,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seller (
            seller_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(100) NOT NULL,
            password VARCHAR(255) NOT NULL,
            shop_name VARCHAR(150) NOT NULL,
            gst_no VARCHAR(50),
            shop_address TEXT,
            mobile VARCHAR(30),
            email VARCHAR(255) NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS admin (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS category (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name VARCHAR(100) NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS product (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name VARCHAR(150) NOT NULL,
            brand_name VARCHAR(150),
            description TEXT,
            photo VARCHAR(255),
            price DECIMAL(10, 2) NOT NULL,
            stock INTEGER NOT NULL DEFAULT 50,
            status VARCHAR(30) NOT NULL DEFAULT 'Active',
            created_on DATETIME,
            category_id INTEGER,
            seller_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE SET NULL,
            FOREIGN KEY (seller_id) REFERENCES seller(seller_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS cart (
            cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            UNIQUE (user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES user_account(user_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            shipping_address TEXT NOT NULL,
            phone VARCHAR(30) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'Pending',
            created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_account(user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            seller_id INTEGER,
            qty INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'Pending',
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(product_id),
            FOREIGN KEY (seller_id) REFERENCES seller(seller_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            seller_id INTEGER,
            comment TEXT,
            rating INTEGER NOT NULL,
            created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_account(user_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE,
            FOREIGN KEY (seller_id) REFERENCES seller(seller_id) ON DELETE SET NULL
        );
        """
    )
    # Check for missing columns in product
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(product)")
    cols = [r[1] for r in cur.fetchall()]
    if "stock" not in cols:
        conn.execute("ALTER TABLE product ADD COLUMN stock INTEGER NOT NULL DEFAULT 50")
    if "status" not in cols:
        conn.execute("ALTER TABLE product ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'Active'")
    if "created_on" not in cols:
        conn.execute("ALTER TABLE product ADD COLUMN created_on DATETIME")

    # Default categories
    default_cats = [
        "Fresh Fruits & Vegetables",
        "Dairy, Bakery & Eggs",
        "Pantry & Cooking Essentials",
        "Snacks, Beverages & Instant Food",
        "Household & Personal Care",
    ]
    for cat in default_cats:
        conn.execute("INSERT OR IGNORE INTO category (category_name) VALUES (?)", (cat,))

    conn.execute(
        "INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)",
        ("admin", "admin123"),
    )
    conn.commit()
    conn.close()


def get_db():
    db_engine = os.getenv("DB_ENGINE", "mysql").strip().lower()
    if db_engine == "mysql":
        try:
            return pymysql.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "online_supermarket"),
                port=int(os.getenv("DB_PORT", "3305")),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                connect_timeout=3,
            )
        except (pymysql.MySQLError, RuntimeError) as e:
            logger.debug(f"MySQL unavailable, falling back to SQLite: {e}")

    sqlite_path = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "app.db"))
    ensure_sqlite_schema(sqlite_path)
    return SQLiteConnection(sqlite_path)


# Authentication & Session Safety Helpers
def get_current_user(request: Request) -> dict | None:
    u = request.session.get("user")
    if isinstance(u, dict) and u.get("user_id"):
        return u
    return None


def get_current_seller(request: Request) -> dict | None:
    s = request.session.get("seller")
    if isinstance(s, dict) and s.get("seller_id"):
        return s
    return None


def get_current_admin(request: Request) -> dict | None:
    a = request.session.get("admin")
    if isinstance(a, dict) and a.get("admin_id"):
        return a
    return None


def logged_in(request: Request, role: str) -> bool:
    if role == "user":
        return get_current_user(request) is not None
    if role == "seller":
        return get_current_seller(request) is not None
    if role == "admin":
        return get_current_admin(request) is not None
    return False


def verify_password(stored_password: str | None, provided_password: str) -> bool:
    if not stored_password:
        return False
    if stored_password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return check_password_hash(stored_password, provided_password)
    return stored_password == provided_password


def flash(request: Request, message: str):
    request.session.setdefault("_flash", []).append(message)


def pop_flash(request: Request) -> list[str]:
    return request.session.pop("_flash", [])


def get_cart_count(request: Request) -> int:
    guest_cart = request.session.get("guest_cart", {})
    guest_count = sum(int(q) for q in guest_cart.values() if str(q).isdigit())
    user = get_current_user(request)
    if not user:
        return guest_count
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(qty) AS total FROM cart WHERE user_id = %s", (user["user_id"],))
            row = cur.fetchone()
            db_total = int(row["total"] or 0) if row else 0
            return db_total + guest_count
    except Exception:
        return guest_count
    finally:
        try:
            conn.close()
        except Exception:
            pass


def render_template(request: Request, template_name: str, **context: Any):
    context.setdefault("messages", pop_flash(request))
    context["current_user"] = get_current_user(request)
    context["current_seller"] = get_current_seller(request)
    context["current_admin"] = get_current_admin(request)
    context["cart_count"] = get_cart_count(request)
    context["url_for"] = lambda endpoint, **values: (
        f"/static/{values.get('filename', '')}"
        if endpoint == "static"
        else str(request.url_for(endpoint, **values))
    )
    return templates.TemplateResponse(request=request, name=template_name, context=context)


def redirect(request: Request, endpoint: str, status_code: int = 303, **kwargs: Any):
    return RedirectResponse(
        url=str(request.url_for(endpoint, **kwargs)),
        status_code=status_code,
    )


def merge_guest_cart_to_db(cur, user_id: int, request: Request):
    guest_cart = request.session.pop("guest_cart", None)
    if not guest_cart:
        return
    for pid_str, qty in guest_cart.items():
        if not str(pid_str).isdigit():
            continue
        pid = int(pid_str)
        cur.execute("SELECT stock FROM product WHERE product_id = %s AND status = 'Active'", (pid,))
        prod = cur.fetchone()
        if not prod:
            continue
        stock = prod.get("stock") if prod.get("stock") is not None else 999
        if stock <= 0:
            continue
        cur.execute("SELECT cart_id, qty FROM cart WHERE user_id = %s AND product_id = %s", (user_id, pid))
        existing = cur.fetchone()
        if existing:
            new_qty = min(existing["qty"] + int(qty), stock)
            cur.execute("UPDATE cart SET qty = %s WHERE cart_id = %s", (new_qty, existing["cart_id"]))
        else:
            add_qty = min(int(qty), stock)
            cur.execute("INSERT INTO cart (user_id, product_id, qty) VALUES (%s, %s, %s)", (user_id, pid, add_qty))


def fetch_guest_cart_summary(cur, guest_cart: dict):
    if not guest_cart:
        return [], 0, 0, 0
    prod_ids = [int(pid) for pid in guest_cart.keys() if str(pid).isdigit()]
    if not prod_ids:
        return [], 0, 0, 0
    placeholders = ", ".join(["%s"] * len(prod_ids))
    cur.execute(
        f"""
        SELECT p.product_id, p.product_name, p.photo, p.price, p.stock, p.brand_name, c.category_name
        FROM product p
        LEFT JOIN category c ON p.category_id = c.category_id
        WHERE p.product_id IN ({placeholders})
        """,
        tuple(prod_ids),
    )
    products = cur.fetchall()
    items = []
    for p in products:
        pid = str(p["product_id"])
        qty = int(guest_cart.get(pid, 1))
        items.append({
            "cart_id": p["product_id"],
            "product_id": p["product_id"],
            "qty": qty,
            "product_name": p["product_name"],
            "photo": p["photo"],
            "price": p["price"],
            "stock": p["stock"],
            "brand_name": p["brand_name"],
            "category_name": p["category_name"],
            "is_guest": True,
        })
    subtotal = sum(float(item["price"]) * int(item["qty"]) for item in items)
    delivery = 0 if not items or subtotal >= 499 else 49
    total = subtotal + delivery
    return items, subtotal, delivery, total


def fetch_cart_summary(cur, user_id: int):
    cur.execute(
        """
        SELECT c.cart_id, c.product_id, c.qty, p.product_name, p.photo,
               p.price, p.stock, p.brand_name, c2.category_name
        FROM cart c
        JOIN product p ON c.product_id = p.product_id
        LEFT JOIN category c2 ON p.category_id = c2.category_id
        WHERE c.user_id = %s
        ORDER BY c.cart_id DESC
        """,
        (user_id,),
    )
    items = cur.fetchall()
    subtotal = sum(float(item["price"]) * int(item["qty"]) for item in items)
    delivery = 0 if not items or subtotal >= 499 else 49
    total = subtotal + delivery
    return items, subtotal, delivery, total


# Customer / Public Routes
@app.get("/", name="start")
@app.get("/index", name="index")
async def index(request: Request):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.*, c.category_name, s.shop_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                LEFT JOIN seller s ON p.seller_id = s.seller_id
                WHERE p.status = 'Active'
                ORDER BY p.product_id DESC
                """
            )
            products = cur.fetchall()
            cur.execute("SELECT * FROM category ORDER BY category_name")
            categories = cur.fetchall()
        return render_template(
            request, "index.html", products=products, categories=categories
        )
    finally:
        conn.close()


@app.get("/products", name="products")
async def products_catalog(
    request: Request,
    q: str | None = None,
    category_id: int | None = None,
    sort: str = "newest",
):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM category ORDER BY category_name")
            categories = cur.fetchall()

            conditions = ["p.status = 'Active'"]
            params: list[Any] = []

            if category_id:
                conditions.append("p.category_id = %s")
                params.append(category_id)

            if q and q.strip():
                clean_q = f"%{q.strip()}%"
                conditions.append("(p.product_name LIKE %s OR p.brand_name LIKE %s OR p.description LIKE %s)")
                params.extend([clean_q, clean_q, clean_q])

            order_clause = "p.product_id DESC"
            if sort == "price_asc":
                order_clause = "p.price ASC"
            elif sort == "price_desc":
                order_clause = "p.price DESC"

            where_sql = " AND ".join(conditions)
            sql = f"""
                SELECT p.*, c.category_name, s.shop_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                LEFT JOIN seller s ON p.seller_id = s.seller_id
                WHERE {where_sql}
                ORDER BY {order_clause}
            """
            cur.execute(sql, tuple(params))
            product_list = cur.fetchall()

        return render_template(
            request,
            "products.html",
            products=product_list,
            categories=categories,
            selected_category=category_id,
            query=q,
            sort=sort,
        )
    finally:
        conn.close()


@app.get("/categories", name="categories")
async def categories_redirect(request: Request):
    return redirect(request, "products", 302)


@app.get("/product/{product_id:int}", name="product_details")
async def product_details(request: Request, product_id: int):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.*, c.category_name, s.shop_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                LEFT JOIN seller s ON p.seller_id = s.seller_id
                WHERE p.product_id = %s
                """,
                (product_id,),
            )
            product = cur.fetchone()
            if not product:
                flash(request, "Product not found")
                return redirect(request, "products")

            # Fetch customer reviews
            cur.execute(
                """
                SELECT f.*, u.first_name, u.last_name
                FROM feedback f
                JOIN user_account u ON f.user_id = u.user_id
                WHERE f.product_id = %s
                ORDER BY f.feedback_id DESC
                LIMIT 10
                """,
                (product_id,),
            )
            reviews = cur.fetchall()

            # Related products
            cur.execute(
                """
                SELECT p.*, c.category_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                WHERE p.category_id = %s AND p.product_id != %s AND p.status = 'Active'
                LIMIT 4
                """,
                (product["category_id"], product_id),
            )
            related_products = cur.fetchall()

        return render_template(
            request,
            "product_details.html",
            product=product,
            reviews=reviews,
            related_products=related_products,
        )
    finally:
        conn.close()


# Cart Routes
@app.get("/cart", name="cart")
async def view_cart(request: Request):
    user = get_current_user(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if user:
                merge_guest_cart_to_db(cur, user["user_id"], request)
                cart_items, subtotal, delivery, total = fetch_cart_summary(cur, user["user_id"])
            else:
                guest_cart = request.session.get("guest_cart", {})
                cart_items, subtotal, delivery, total = fetch_guest_cart_summary(cur, guest_cart)
        return render_template(
            request,
            "cart.html",
            cart_items=cart_items,
            subtotal=subtotal,
            delivery=delivery,
            total=total,
        )
    finally:
        conn.close()


@app.get("/add_to_cart/{product_id:int}", name="add_to_cart")
async def add_to_cart(request: Request, product_id: int, qty: int = 1):
    quantity = max(1, qty)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT stock, status, product_name FROM product WHERE product_id = %s", (product_id,))
            prod = cur.fetchone()
            if not prod or prod.get("status") != "Active":
                flash(request, "This item is currently unavailable")
                return redirect(request, "products")

            stock = prod.get("stock") if prod.get("stock") is not None else 999
            if stock <= 0:
                flash(request, f"'{prod['product_name']}' is out of stock")
                return redirect(request, "products")

            user = get_current_user(request)
            if user:
                cur.execute(
                    "SELECT cart_id, qty FROM cart WHERE user_id = %s AND product_id = %s",
                    (user["user_id"], product_id),
                )
                existing = cur.fetchone()
                if existing:
                    new_qty = min(existing["qty"] + quantity, stock)
                    cur.execute("UPDATE cart SET qty = %s WHERE cart_id = %s", (new_qty, existing["cart_id"]))
                else:
                    add_qty = min(quantity, stock)
                    cur.execute(
                        "INSERT INTO cart (user_id, product_id, qty) VALUES (%s, %s, %s)",
                        (user["user_id"], product_id, add_qty),
                    )
            else:
                guest_cart = dict(request.session.get("guest_cart", {}))
                pid_str = str(product_id)
                current_qty = int(guest_cart.get(pid_str, 0))
                guest_cart[pid_str] = min(current_qty + quantity, stock)
                request.session["guest_cart"] = guest_cart

        flash(request, f"Added {prod['product_name']} to cart")
        return redirect(request, "cart")
    finally:
        conn.close()


@app.post("/cart/update/{cart_id:int}", name="update_cart")
async def update_cart(request: Request, cart_id: int):
    user = get_current_user(request)
    form = await request.form()
    try:
        quantity = max(1, int(form.get("qty", 1)))
    except (TypeError, ValueError):
        quantity = 1

    conn = get_db()
    try:
        with conn.cursor() as cur:
            if user:
                cur.execute(
                    """
                    SELECT c.cart_id, p.stock, p.product_name
                    FROM cart c JOIN product p ON c.product_id = p.product_id
                    WHERE c.cart_id = %s AND c.user_id = %s
                    """,
                    (cart_id, user["user_id"]),
                )
                row = cur.fetchone()
                if row:
                    stock = row.get("stock") if row.get("stock") is not None else 999
                    final_qty = min(quantity, stock)
                    cur.execute(
                        "UPDATE cart SET qty = %s WHERE cart_id = %s AND user_id = %s",
                        (final_qty, cart_id, user["user_id"]),
                    )
                    if quantity > stock:
                        flash(request, f"Adjusted to available stock ({stock} units) for {row['product_name']}")
                    else:
                        flash(request, "Cart updated")
            else:
                guest_cart = dict(request.session.get("guest_cart", {}))
                pid_str = str(cart_id)
                if pid_str in guest_cart:
                    cur.execute("SELECT stock, product_name FROM product WHERE product_id = %s", (cart_id,))
                    row = cur.fetchone()
                    stock = row.get("stock") if row and row.get("stock") is not None else 999
                    final_qty = min(quantity, stock)
                    guest_cart[pid_str] = final_qty
                    request.session["guest_cart"] = guest_cart
                    flash(request, "Cart updated")
        return redirect(request, "cart")
    finally:
        conn.close()


@app.post("/cart/remove/{cart_id:int}", name="remove_from_cart")
async def remove_from_cart(request: Request, cart_id: int):
    user = get_current_user(request)
    if user:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cart WHERE cart_id = %s AND user_id = %s", (cart_id, user["user_id"]))
            flash(request, "Item removed from cart")
        finally:
            conn.close()
    else:
        guest_cart = dict(request.session.get("guest_cart", {}))
        pid_str = str(cart_id)
        if pid_str in guest_cart:
            del guest_cart[pid_str]
            request.session["guest_cart"] = guest_cart
            flash(request, "Item removed from cart")
    return redirect(request, "cart")


# Checkout & Orders
@app.get("/checkout", name="checkout")
@app.get("/checkout/{product_id:int}", name="checkout_product")
async def checkout(request: Request, product_id: int | None = None, qty: int = 1):
    user = get_current_user(request)
    if not user:
        flash(request, "Please sign in to proceed with checkout")
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            if product_id is not None:
                quantity = max(1, qty)
                cur.execute("SELECT cart_id FROM cart WHERE user_id = %s AND product_id = %s", (user["user_id"], product_id))
                existing = cur.fetchone()
                if not existing:
                    cur.execute(
                        "INSERT INTO cart (user_id, product_id, qty) VALUES (%s, %s, %s)",
                        (user["user_id"], product_id, quantity),
                    )
                else:
                    cur.execute(
                        "UPDATE cart SET qty = %s WHERE cart_id = %s",
                        (quantity, existing["cart_id"]),
                    )

            cart_items, subtotal, delivery, total = fetch_cart_summary(cur, user["user_id"])
            if not cart_items:
                flash(request, "Your cart is empty. Add some products before checkout.")
                return redirect(request, "products")

        return render_template(
            request,
            "checkout.html",
            cart_items=cart_items,
            subtotal=subtotal,
            delivery=delivery,
            total=total,
            user=user,
        )
    finally:
        conn.close()


@app.post("/place_order", name="place_order")
async def place_order(request: Request):
    user = get_current_user(request)
    if not user:
        return redirect(request, "login", 302)

    form = await request.form()
    shipping_address = str(form.get("shipping_address") or "").strip()
    phone = str(form.get("phone") or "").strip()

    if not shipping_address or not phone:
        flash(request, "Shipping address and phone number are required")
        return redirect(request, "checkout")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.*, p.price, p.seller_id, p.stock, p.product_name
                FROM cart c
                JOIN product p ON c.product_id = p.product_id
                WHERE c.user_id = %s
                """,
                (user["user_id"],),
            )
            items = cur.fetchall()
            if not items:
                flash(request, "Your cart is empty")
                return redirect(request, "products")

            # Validate stock and calculate total
            subtotal = sum(float(item["price"]) * int(item["qty"]) for item in items)
            delivery = 0 if subtotal >= 499 else 49
            total = subtotal + delivery

            cur.execute(
                """
                INSERT INTO orders (user_id, total, shipping_address, phone, status, created_on)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (user["user_id"], total, shipping_address, phone, "Pending"),
            )
            order_id = cur.lastrowid

            for item in items:
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, seller_id, qty, price, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (order_id, item["product_id"], item["seller_id"], item["qty"], item["price"], "Pending"),
                )
                # Decrement stock safely
                cur.execute(
                    "UPDATE product SET stock = CASE WHEN stock - %s < 0 THEN 0 ELSE stock - %s END WHERE product_id = %s",
                    (item["qty"], item["qty"], item["product_id"]),
                )

            # Clear cart
            cur.execute("DELETE FROM cart WHERE user_id = %s", (user["user_id"],))

        flash(request, f"Order #{order_id} placed successfully! Cash on Delivery confirmed.")
        return redirect(request, "my_orders")
    finally:
        conn.close()


@app.get("/my_orders", name="my_orders")
@app.get("/orders", name="orders")
async def my_orders(request: Request):
    user = get_current_user(request)
    if not user:
        flash(request, "Please sign in to view your order history")
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM orders WHERE user_id = %s ORDER BY order_id DESC",
                (user["user_id"],),
            )
            orders = cur.fetchall()
            order_items = {}
            for o in orders:
                cur.execute(
                    """
                    SELECT oi.*, p.product_name, p.brand_name, p.photo, s.shop_name
                    FROM order_items oi
                    JOIN product p ON oi.product_id = p.product_id
                    LEFT JOIN seller s ON oi.seller_id = s.seller_id
                    WHERE oi.order_id = %s
                    """,
                    (o["order_id"],),
                )
                order_items[o["order_id"]] = cur.fetchall()

        return render_template(
            request, "orders.html", orders=orders, order_items=order_items
        )
    finally:
        conn.close()


@app.api_route("/profile", methods=["GET", "POST"], name="profile")
async def user_profile(request: Request):
    user = get_current_user(request)
    if not user:
        flash(request, "Please sign in to access your profile")
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            if request.method == "POST":
                form = await request.form()
                action = form.get("action")
                if action == "update_profile":
                    first_name = str(form.get("first_name") or "").strip()
                    last_name = str(form.get("last_name") or "").strip()
                    mobile = str(form.get("mobile") or "").strip()
                    address = str(form.get("address") or "").strip()

                    cur.execute(
                        """
                        UPDATE user_account
                        SET first_name = %s, last_name = %s, mobile = %s, address = %s
                        WHERE user_id = %s
                        """,
                        (first_name, last_name, mobile, address, user["user_id"]),
                    )
                    user["first_name"] = first_name
                    user["last_name"] = last_name
                    user["mobile"] = mobile
                    user["address"] = address
                    request.session["user"] = user
                    flash(request, "Profile details updated successfully")
                    return redirect(request, "profile")

                elif action == "change_password":
                    current_pw = str(form.get("current_password") or "")
                    new_pw = str(form.get("new_password") or "")
                    confirm_pw = str(form.get("confirm_password") or "")

                    cur.execute("SELECT password FROM user_account WHERE user_id = %s", (user["user_id"],))
                    row = cur.fetchone()
                    if not row or not verify_password(row["password"], current_pw):
                        flash(request, "Current password is incorrect")
                        return redirect(request, "profile")

                    if len(new_pw) < 6:
                        flash(request, "New password must be at least 6 characters")
                        return redirect(request, "profile")

                    if new_pw != confirm_pw:
                        flash(request, "New passwords do not match")
                        return redirect(request, "profile")

                    cur.execute(
                        "UPDATE user_account SET password = %s WHERE user_id = %s",
                        (generate_password_hash(new_pw), user["user_id"]),
                    )
                    flash(request, "Password updated successfully")
                    return redirect(request, "profile")

            # Fetch refreshed details
            cur.execute("SELECT * FROM user_account WHERE user_id = %s", (user["user_id"],))
            db_user = cur.fetchone() or user
            cur.execute("SELECT COUNT(*) AS total FROM orders WHERE user_id = %s", (user["user_id"],))
            order_count = cur.fetchone()["total"]

        return render_template(
            request, "profile.html", user=db_user, order_count=order_count
        )
    finally:
        conn.close()


@app.api_route("/feedback/{product_id:int}", methods=["GET", "POST"], name="feedback")
async def submit_feedback(request: Request, product_id: int):
    user = get_current_user(request)
    if not user:
        flash(request, "Please sign in to write a review")
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM product WHERE product_id = %s", (product_id,))
            product = cur.fetchone()
            if not product:
                flash(request, "Product not found")
                return redirect(request, "products")

            if request.method == "POST":
                form = await request.form()
                try:
                    rating = max(1, min(5, int(form.get("rating", 5))))
                except ValueError:
                    rating = 5
                comment = str(form.get("comment") or "").strip()

                cur.execute(
                    """
                    INSERT INTO feedback (user_id, product_id, seller_id, comment, rating, created_on)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user["user_id"], product_id, product.get("seller_id"), comment, rating),
                )
                flash(request, "Thank you! Your feedback has been recorded.")
                return redirect(request, "product_details", product_id=product_id)

        return render_template(request, "feedback.html", product=product)
    finally:
        conn.close()


@app.get("/user", name="user")
@app.get("/user_dashboard", name="user_dashboard")
async def user_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cart_items, subtotal, delivery, total = fetch_cart_summary(cur, user["user_id"])
            cur.execute(
                "SELECT * FROM orders WHERE user_id = %s ORDER BY order_id DESC LIMIT 5",
                (user["user_id"],),
            )
            orders = cur.fetchall()
            cur.execute(
                """
                SELECT p.*, c.category_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                WHERE p.status = 'Active'
                ORDER BY p.product_id DESC
                LIMIT 4
                """
            )
            products = cur.fetchall()

        return render_template(
            request,
            "user_dashboard.html",
            cart_items=cart_items,
            user_name=user.get("first_name", "Customer"),
            orders=orders,
            products=products,
            cart_total=total,
        )
    finally:
        conn.close()


# Authentication (Register, Login, Logout)
@app.api_route("/register", methods=["GET", "POST"], name="register")
async def register(request: Request):
    if request.method == "POST":
        form = await request.form()
        email = str(form.get("email") or "").strip().lower()
        password = str(form.get("password") or "")
        first_name = str(form.get("first_name") or "").strip()
        last_name = str(form.get("last_name") or "").strip()
        dob = form.get("dob")
        mobile = str(form.get("mobile") or "").strip()
        address = str(form.get("address") or "").strip()

        if not email or not password or not first_name:
            flash(request, "First name, email and password are required")
            return render_template(request, "register.html")

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM user_account WHERE email = %s", (email,))
                if cur.fetchone():
                    flash(request, "An account with this email already exists. Please login.")
                    return render_template(request, "register.html")

                cur.execute(
                    """
                    INSERT INTO user_account
                    (first_name, last_name, dob, mobile, address, email, password)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (first_name, last_name, dob or None, mobile, address, email, generate_password_hash(password)),
                )
            flash(request, "Registration successful! Please sign in with your credentials.")
            return redirect(request, "login")
        except (sqlite3.IntegrityError, pymysql.IntegrityError):
            flash(request, "An account with this email already exists. Please login.")
            return render_template(request, "register.html")
        finally:
            conn.close()

    return render_template(request, "register.html")


@app.api_route("/seller_register", methods=["GET", "POST"], name="seller_register")
@app.api_route("/seller-register", methods=["GET", "POST"], name="seller_register_alias")
async def seller_register(request: Request):
    if request.method == "POST":
        form = await request.form()
        email = str(form.get("email") or "").strip().lower()
        username = str(form.get("username") or "").strip()
        password = str(form.get("password") or "")
        shop_name = str(form.get("shop_name") or "").strip()
        gst_no = str(form.get("gst_no") or "").strip()
        shop_address = str(form.get("shop_address") or "").strip()
        mobile = str(form.get("mobile") or "").strip()

        if not email or not password or not shop_name:
            flash(request, "Shop name, email and password are required")
            return render_template(request, "seller-register.html")

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT seller_id FROM seller WHERE email = %s OR username = %s", (email, username))
                if cur.fetchone():
                    flash(request, "A seller account with this email or username already exists. Please sign in.")
                    return render_template(request, "seller-register.html")

                cur.execute(
                    """
                    INSERT INTO seller
                    (username, password, shop_name, gst_no, shop_address, mobile, email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (username, generate_password_hash(password), shop_name, gst_no or None, shop_address, mobile, email),
                )
            flash(request, "Seller account registered! Please sign in to access your Seller Hub.")
            return redirect(request, "login")
        except (sqlite3.IntegrityError, pymysql.IntegrityError):
            flash(request, "Seller details already exist. Please check your username and email.")
            return render_template(request, "seller-register.html")
        finally:
            conn.close()

    return render_template(request, "seller-register.html")


@app.api_route("/login", methods=["GET", "POST"], name="login")
async def login(request: Request):
    if request.method == "POST":
        form = await request.form()
        role = str(form.get("role") or "user").strip().lower()
        identifier = str(form.get("email") or "").strip()
        password = str(form.get("password") or "")

        conn = get_db()
        try:
            with conn.cursor() as cur:
                if role == "user":
                    cur.execute("SELECT * FROM user_account WHERE email = %s", (identifier.lower(),))
                    user = cur.fetchone()
                    if user and verify_password(user.get("password"), password):
                        # Safe session storing JSON-serializable primitives only
                        request.session["user"] = {
                            "user_id": int(user["user_id"]),
                            "first_name": str(user["first_name"] or ""),
                            "last_name": str(user["last_name"] or ""),
                            "email": str(user["email"] or ""),
                            "mobile": str(user.get("mobile") or ""),
                            "address": str(user.get("address") or ""),
                        }
                        request.session["user_id"] = int(user["user_id"])
                        request.session["role"] = "user"
                        merge_guest_cart_to_db(cur, int(user["user_id"]), request)
                        flash(request, f"Welcome back, {user['first_name']}!")
                        return redirect(request, "products")
                    flash(request, "Invalid customer email or password")

                elif role == "seller":
                    cur.execute(
                        "SELECT * FROM seller WHERE email = %s OR username = %s",
                        (identifier.lower(), identifier),
                    )
                    seller = cur.fetchone()
                    if seller and verify_password(seller.get("password"), password):
                        request.session["seller"] = {
                            "seller_id": int(seller["seller_id"]),
                            "username": str(seller["username"] or ""),
                            "shop_name": str(seller["shop_name"] or ""),
                            "email": str(seller["email"] or ""),
                            "mobile": str(seller.get("mobile") or ""),
                            "shop_address": str(seller.get("shop_address") or ""),
                            "gst_no": str(seller.get("gst_no") or ""),
                        }
                        request.session["seller_id"] = int(seller["seller_id"])
                        request.session["role"] = "seller"
                        flash(request, f"Welcome, {seller['shop_name']}!")
                        return redirect(request, "seller_dashboard")
                    flash(request, "Invalid seller credentials")

                elif role == "admin":
                    cur.execute("SELECT * FROM admin WHERE username = %s", (identifier,))
                    admin = cur.fetchone()
                    if admin and verify_password(admin.get("password"), password):
                        request.session["admin"] = {
                            "admin_id": int(admin["admin_id"]),
                            "username": str(admin["username"] or ""),
                        }
                        request.session["admin_id"] = int(admin["admin_id"])
                        request.session["role"] = "admin"
                        flash(request, "Admin panel authenticated")
                        return redirect(request, "admin_dashboard")
                    flash(request, "Invalid admin credentials")
        finally:
            conn.close()

    return render_template(request, "login.html")


@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    flash(request, "You have been signed out.")
    return redirect(request, "start")


# Seller Hub & Management
@app.get("/seller", name="seller_dashboard")
@app.get("/seller_dashboard", name="seller_dashboard_alias")
async def seller_dashboard(request: Request):
    seller = get_current_seller(request)
    if not seller:
        flash(request, "Please sign in as a seller")
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            sid = seller["seller_id"]
            # Seller's products
            cur.execute(
                """
                SELECT p.*, c.category_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                WHERE p.seller_id = %s
                ORDER BY p.product_id DESC
                """,
                (sid,),
            )
            products = cur.fetchall()

            # Categories
            cur.execute("SELECT * FROM category ORDER BY category_name")
            categories = cur.fetchall()

            # Customer orders for this seller's products
            cur.execute(
                """
                SELECT oi.*, o.shipping_address, o.phone, o.created_on,
                       u.first_name, u.last_name,
                       p.product_name, p.photo
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                JOIN product p ON oi.product_id = p.product_id
                LEFT JOIN user_account u ON o.user_id = u.user_id
                WHERE oi.seller_id = %s
                ORDER BY oi.order_item_id DESC
                """,
                (sid,),
            )
            seller_orders = cur.fetchall()

            product_count = len(products)
            inventory_value = sum(float(p["price"]) * int(p.get("stock") or 0) for p in products)
            order_count = len(seller_orders)
            pending_orders_count = sum(1 for o in seller_orders if o.get("status") in ["Pending", "Processing"])

        return render_template(
            request,
            "seller_dashboard.html",
            seller=seller,
            products=products,
            categories=categories,
            seller_orders=seller_orders,
            product_count=product_count,
            inventory_value=inventory_value,
            order_count=order_count,
            pending_orders_count=pending_orders_count,
        )
    finally:
        conn.close()


@app.post("/seller/products/create", name="create_product")
async def create_product(request: Request):
    seller = get_current_seller(request)
    if not seller:
        return redirect(request, "login", 302)

    form = await request.form()
    product_name = str(form.get("product_name") or "").strip()
    brand_name = str(form.get("brand_name") or "").strip()
    description = str(form.get("description") or "").strip()
    price_text = str(form.get("price") or "").strip()
    stock_text = str(form.get("stock") or "50").strip()
    category_text = str(form.get("category_id") or "").strip()
    status = str(form.get("status") or "Active").strip()
    upload = form.get("product_image")

    if not product_name or not description:
        flash(request, "Product name and description are required")
        return redirect(request, "seller_dashboard")

    try:
        price = float(Decimal(price_text))
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        flash(request, "Please enter a valid positive price")
        return redirect(request, "seller_dashboard")

    try:
        stock = max(0, int(stock_text))
    except ValueError:
        stock = 50

    category_id = int(category_text) if category_text.isdigit() else None

    photo_name = None
    if upload and getattr(upload, "filename", None):
        filename = str(upload.filename).strip()
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in ALLOWED_IMAGE_EXTENSIONS:
                data = await upload.read()
                if len(data) <= MAX_IMAGE_BYTES:
                    safe = secure_filename(Path(filename).stem) or "product"
                    photo_name = f"{uuid4().hex}_{safe}{ext}"
                    Path(UPLOAD_FOLDER, photo_name).write_bytes(data)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product
                (product_name, brand_name, description, photo, price, stock, status, category_id, seller_id, created_on)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (
                    product_name,
                    brand_name or None,
                    description,
                    photo_name,
                    price,
                    stock,
                    status,
                    category_id,
                    seller["seller_id"],
                ),
            )
        flash(request, f"Product '{product_name}' published successfully")
        return redirect(request, "seller_dashboard")
    finally:
        conn.close()


@app.get("/seller/products/edit/{product_id:int}", name="edit_product_page")
async def edit_product_page(request: Request, product_id: int):
    seller = get_current_seller(request)
    if not seller:
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM product WHERE product_id = %s AND seller_id = %s", (product_id, seller["seller_id"]))
            product = cur.fetchone()
            if not product:
                flash(request, "Product not found or access denied")
                return redirect(request, "seller_dashboard")

            cur.execute("SELECT * FROM category ORDER BY category_name")
            categories = cur.fetchall()

        return render_template(
            request, "seller_product_edit.html", product=product, categories=categories
        )
    finally:
        conn.close()


@app.post("/seller/products/edit/{product_id:int}", name="update_product")
async def update_product(request: Request, product_id: int):
    seller = get_current_seller(request)
    if not seller:
        return redirect(request, "login", 302)

    form = await request.form()
    product_name = str(form.get("product_name") or "").strip()
    brand_name = str(form.get("brand_name") or "").strip()
    description = str(form.get("description") or "").strip()
    price_text = str(form.get("price") or "").strip()
    stock_text = str(form.get("stock") or "50").strip()
    category_text = str(form.get("category_id") or "").strip()
    status = str(form.get("status") or "Active").strip()
    upload = form.get("product_image")

    try:
        price = float(Decimal(price_text))
    except (InvalidOperation, ValueError):
        flash(request, "Invalid price")
        return redirect(request, "edit_product_page", product_id=product_id)

    try:
        stock = max(0, int(stock_text))
    except ValueError:
        stock = 50

    category_id = int(category_text) if category_text.isdigit() else None

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT photo FROM product WHERE product_id = %s AND seller_id = %s", (product_id, seller["seller_id"]))
            existing = cur.fetchone()
            if not existing:
                flash(request, "Product not found")
                return redirect(request, "seller_dashboard")

            photo_name = existing.get("photo")
            if upload and getattr(upload, "filename", None):
                filename = str(upload.filename).strip()
                if filename:
                    ext = Path(filename).suffix.lower()
                    if ext in ALLOWED_IMAGE_EXTENSIONS:
                        data = await upload.read()
                        if len(data) <= MAX_IMAGE_BYTES:
                            safe = secure_filename(Path(filename).stem) or "product"
                            photo_name = f"{uuid4().hex}_{safe}{ext}"
                            Path(UPLOAD_FOLDER, photo_name).write_bytes(data)

            cur.execute(
                """
                UPDATE product
                SET product_name = %s, brand_name = %s, description = %s,
                    photo = %s, price = %s, stock = %s, status = %s, category_id = %s
                WHERE product_id = %s AND seller_id = %s
                """,
                (
                    product_name,
                    brand_name or None,
                    description,
                    photo_name,
                    price,
                    stock,
                    status,
                    category_id,
                    product_id,
                    seller["seller_id"],
                ),
            )
        flash(request, f"Product '{product_name}' updated successfully")
        return redirect(request, "seller_dashboard")
    finally:
        conn.close()


@app.post("/seller/products/delete/{product_id:int}", name="delete_product")
async def delete_product(request: Request, product_id: int):
    seller = get_current_seller(request)
    if not seller:
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM product WHERE product_id = %s AND seller_id = %s",
                (product_id, seller["seller_id"]),
            )
        flash(request, "Product deleted from your catalog")
        return redirect(request, "seller_dashboard")
    finally:
        conn.close()


@app.post("/seller/orders/status/{order_item_id:int}", name="update_order_status")
async def update_order_status(request: Request, order_item_id: int):
    seller = get_current_seller(request)
    if not seller:
        return redirect(request, "login", 302)

    form = await request.form()
    new_status = str(form.get("status") or "Pending").strip()
    valid_statuses = {"Pending", "Processing", "Shipped", "Delivered", "Cancelled"}
    if new_status not in valid_statuses:
        new_status = "Pending"

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE order_items SET status = %s WHERE order_item_id = %s AND seller_id = %s",
                (new_status, order_item_id, seller["seller_id"]),
            )
        flash(request, f"Order item #{order_item_id} marked as {new_status}")
        return redirect(request, "seller_dashboard")
    finally:
        conn.close()


# Admin Routes
@app.get("/admin", name="admin_dashboard")
@app.get("/admin/sellers", name="admin_sellers")
@app.get("/admin/users", name="admin_users")
@app.get("/admin/products", name="admin_products")
@app.get("/admin/feedbacks", name="admin_feedbacks")
async def admin_dashboard(request: Request):
    if not logged_in(request, "admin"):
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM seller")
            seller_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM user_account")
            user_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM product")
            product_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM feedback")
            feedback_count = cur.fetchone()["total"]

            cur.execute("SELECT * FROM seller ORDER BY seller_id DESC LIMIT 15")
            sellers = cur.fetchall()
            cur.execute("SELECT * FROM user_account ORDER BY user_id DESC LIMIT 15")
            users = cur.fetchall()
            cur.execute(
                """
                SELECT p.*, c.category_name, s.shop_name
                FROM product p
                LEFT JOIN category c ON p.category_id = c.category_id
                LEFT JOIN seller s ON p.seller_id = s.seller_id
                ORDER BY p.product_id DESC
                LIMIT 20
                """
            )
            products = cur.fetchall()
            cur.execute(
                """
                SELECT f.*, u.first_name, p.product_name, s.shop_name
                FROM feedback f
                LEFT JOIN user_account u ON f.user_id = u.user_id
                LEFT JOIN product p ON f.product_id = p.product_id
                LEFT JOIN seller s ON f.seller_id = s.seller_id
                ORDER BY f.feedback_id DESC
                LIMIT 20
                """
            )
            feedbacks = cur.fetchall()

        return render_template(
            request,
            "admin_dashboard.html",
            sellers=sellers,
            users=users,
            products=products,
            feedbacks=feedbacks,
            seller_count=seller_count,
            user_count=user_count,
            product_count=product_count,
            feedback_count=feedback_count,
            active_section={
                "/admin/sellers": "sellers",
                "/admin/users": "users",
                "/admin/products": "products",
                "/admin/feedbacks": "feedbacks",
            }.get(request.url.path, "dashboard"),
        )
    finally:
        conn.close()


@app.post("/admin/products/delete/{product_id:int}", name="admin_delete_product")
async def admin_delete_product(request: Request, product_id: int):
    if not logged_in(request, "admin"):
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM product WHERE product_id = %s", (product_id,))
        flash(request, f"Product #{product_id} removed by administrator")
        return redirect(request, "admin_products")
    finally:
        conn.close()


@app.post("/admin/feedbacks/delete/{feedback_id:int}", name="admin_delete_feedback")
async def admin_delete_feedback(request: Request, feedback_id: int):
    if not logged_in(request, "admin"):
        return redirect(request, "login", 302)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE feedback_id = %s", (feedback_id,))
        flash(request, f"Feedback #{feedback_id} removed by administrator")
        return redirect(request, "admin_feedbacks")
    finally:
        conn.close()


# Health Check
@app.get("/api/health", name="health")
async def health():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            ok = cur.fetchone()["ok"] == 1
        return {"status": "ok", "database": "ok" if ok else "degraded"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "degraded", "error": str(e)})
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
