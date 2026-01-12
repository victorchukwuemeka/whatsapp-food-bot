# Simple menu (expand this as needed)
MENU = [
    {'id': 1, 'name': 'Jollof Rice', 'price': 2000, 'category': 'Main'},
    {'id': 2, 'name': 'Fried Rice', 'price': 2000, 'category': 'Main'},
    {'id': 3, 'name': 'Chicken & Chips', 'price': 2500, 'category': 'Main'},
    {'id': 4, 'name': 'Peppered Chicken', 'price': 1500, 'category': 'Sides'},
    {'id': 5, 'name': 'Meat Pie', 'price': 500, 'category': 'Snacks'},
    {'id': 6, 'name': 'Soft Drink', 'price': 300, 'category': 'Drinks'},
]

def get_menu():
    """Return formatted menu string"""
    menu_text = "🍽️ *MENU*\n\n"
    
    for item in MENU:
        menu_text += f"{item['id']}. {item['name']} - ₦{item['price']}\n"
    
    menu_text += "\n💬 Type 'order [number]' to add to cart\nExample: order 1"
    
    return menu_text

def get_item_by_number(item_num):
    """Get menu item by number"""
    for item in MENU:
        if item['id'] == item_num:
            return item
    return None
