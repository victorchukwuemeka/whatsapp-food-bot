import sqlite3
import json
from datetime import datetime

DB_NAME = 'orders.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Orders table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            delivery_address TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User addresses table (for saved addresses)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_addresses (
            customer_phone TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_order(customer_phone, items, delivery_address):
    """Save order to database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    total = sum(item['price'] for item in items)
    items_json = json.dumps(items)
    
    c.execute('''
        INSERT INTO orders (customer_phone, items, total, delivery_address)
        VALUES (?, ?, ?, ?)
    ''', (customer_phone, items_json, total, delivery_address))
    
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return order_id

def save_user_address(customer_phone, address):
    """Save or update user's address"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO user_addresses (customer_phone, address, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (customer_phone, address))
    
    conn.commit()
    conn.close()

def get_user_address(customer_phone):
    """Get user's saved address"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        SELECT address FROM user_addresses WHERE customer_phone = ?
    ''', (customer_phone,))
    
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None

# Initialize database on import
init_db()
