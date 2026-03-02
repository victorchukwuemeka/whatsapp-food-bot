import sqlite3
import json
from datetime import datetime

DB_NAME = 'orders.db'

def init_db():
    """Initialize database with all tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # ── EXISTING TABLES (unchanged) ──────────────────────────────────────────

    # User addresses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_addresses (
            customer_phone TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── NEW TABLES ────────────────────────────────────────────────────────────

    # Restaurants table
    c.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            area TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Menu items table (linked to restaurant)
    c.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT DEFAULT 'General',
            is_available INTEGER DEFAULT 1,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    ''')

    # Riders table
    c.execute('''
        CREATE TABLE IF NOT EXISTS riders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            area TEXT NOT NULL,
            base_fee REAL NOT NULL,
            min_fee REAL NOT NULL,          -- floor price, never go below this
            is_available INTEGER DEFAULT 1,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Orders table (updated to include restaurant + rider info)
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            restaurant_id INTEGER,
            rider_id INTEGER,
            items TEXT NOT NULL,            -- JSON
            food_total REAL NOT NULL,       -- fixed restaurant price
            delivery_fee REAL DEFAULT 0,    -- negotiated rider fee
            total REAL NOT NULL,            -- food_total + delivery_fee
            delivery_address TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY (rider_id) REFERENCES riders(id)
        )
    ''')

    # Conversation history table (needed for agentic memory)
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            role TEXT NOT NULL,             -- 'user' or 'assistant'
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully")


# ── RESTAURANT FUNCTIONS ──────────────────────────────────────────────────────

def register_restaurant(name, phone, area, description=""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO restaurants (name, phone, area, description)
            VALUES (?, ?, ?, ?)
        ''', (name, phone, area, description))
        restaurant_id = c.lastrowid
        conn.commit()
        return restaurant_id
    except sqlite3.IntegrityError:
        return None  # phone already registered
    finally:
        conn.close()

def get_all_restaurants():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, area, description FROM restaurants WHERE is_active = 1')
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'area': r[2], 'description': r[3]} for r in rows]

def get_restaurant_by_id(restaurant_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'phone': row[2], 'area': row[3], 'description': row[4]}
    return None


# ── MENU FUNCTIONS ────────────────────────────────────────────────────────────

def add_menu_item(restaurant_id, name, price, category="General"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO menu_items (restaurant_id, name, price, category)
        VALUES (?, ?, ?, ?)
    ''', (restaurant_id, name, price, category))
    conn.commit()
    conn.close()

def get_menu_by_restaurant(restaurant_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT id, name, price, category
        FROM menu_items
        WHERE restaurant_id = ? AND is_available = 1
    ''', (restaurant_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'price': r[2], 'category': r[3]} for r in rows]

def get_menu_item_by_id(item_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, price, restaurant_id FROM menu_items WHERE id = ?', (item_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'price': row[2], 'restaurant_id': row[3]}
    return None


# ── RIDER FUNCTIONS ───────────────────────────────────────────────────────────

def get_available_rider(area=None):
    """Get an available rider, optionally filtered by area"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if area:
        c.execute('''
            SELECT id, name, phone, base_fee, min_fee
            FROM riders WHERE is_available = 1 AND area = ?
            LIMIT 1
        ''', (area,))
    else:
        c.execute('''
            SELECT id, name, phone, base_fee, min_fee
            FROM riders WHERE is_available = 1 LIMIT 1
        ''')
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'phone': row[2], 'base_fee': row[3], 'min_fee': row[4]}
    return None

def register_rider(name, phone, area, base_fee, min_fee):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO riders (name, phone, area, base_fee, min_fee)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, phone, area, base_fee, min_fee))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


# ── ORDER FUNCTIONS ───────────────────────────────────────────────────────────

def save_order(customer_phone, items, delivery_address, restaurant_id=None, rider_id=None, delivery_fee=0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    food_total = sum(item['price'] for item in items)
    total = food_total + delivery_fee
    items_json = json.dumps(items)

    c.execute('''
        INSERT INTO orders (customer_phone, restaurant_id, rider_id, items, food_total, delivery_fee, total, delivery_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_phone, restaurant_id, rider_id, items_json, food_total, delivery_fee, total, delivery_address))

    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id


# ── ADDRESS FUNCTIONS (unchanged) ─────────────────────────────────────────────

def save_user_address(customer_phone, address):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO user_addresses (customer_phone, address, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (customer_phone, address))
    conn.commit()
    conn.close()

def get_user_address(customer_phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT address FROM user_addresses WHERE customer_phone = ?', (customer_phone,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


# ── CONVERSATION HISTORY (for agentic memory) ─────────────────────────────────

def save_message(customer_phone, role, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO conversations (customer_phone, role, message)
        VALUES (?, ?, ?)
    ''', (customer_phone, role, message))
    conn.commit()
    conn.close()

def get_conversation_history(customer_phone, limit=20):
    """Get last N messages for a user (for LLM context)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT role, message FROM conversations
        WHERE customer_phone = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (customer_phone, limit))
    rows = c.fetchall()
    conn.close()
    # Return in chronological order for LLM
    return [{'role': r[0], 'content': r[1]} for r in reversed(rows)]

def clear_conversation_history(customer_phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM conversations WHERE customer_phone = ?', (customer_phone,))
    conn.commit()
    conn.close()


# ── SEED DATA (for testing) ───────────────────────────────────────────────────

def seed_test_data():
    """Add sample restaurant, menu, and rider for testing"""
    # Register a test restaurant
    r_id = register_restaurant(
        name="Mama Tee Kitchen",
        phone="2348100000001",
        area="Lekki",
        description="Home-cooked Nigerian meals"
    )
    if r_id:
        add_menu_item(r_id, "Jollof Rice + Chicken", 2500, "Rice Dishes")
        add_menu_item(r_id, "Fried Rice + Fish", 2800, "Rice Dishes")
        add_menu_item(r_id, "Egusi Soup + Eba", 2000, "Soups")
        add_menu_item(r_id, "Pepper Soup (Goat)", 3000, "Soups")
        add_menu_item(r_id, "Shawarma", 1500, "Snacks")
        print(f"Test restaurant seeded with ID {r_id}")

    # Register a test rider
    rider_id = register_rider(
        name="Emeka",
        phone="2348100000002",
        area="Lekki",
        base_fee=800,   # starts at ₦800
        min_fee=400     # won't go below ₦400
    )
    if rider_id:
        print(f"Test rider seeded with ID {rider_id}")


# Initialize on import
init_db()