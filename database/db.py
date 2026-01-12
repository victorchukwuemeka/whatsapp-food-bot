import sqlite3
import json
from datetime import datetime

DB_NAME = 'orders.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_order(customer_phone, items):
    """Save order to database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    total = sum(item['price'] for item in items)
    items_json = json.dumps(items)
    
    c.execute('''
        INSERT INTO orders (customer_phone, items, total)
        VALUES (?, ?, ?)
    ''', (customer_phone, items_json, total))
    
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return order_id

# Initialize database on import
init_db()
