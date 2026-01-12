from utils.menu import get_menu, get_item_by_number
from database.db import save_order

# Simple state management (use database for production)
user_sessions = {}

def handle_incoming_message(message, sender):
    """Process incoming messages and return appropriate response"""
    
    # Initialize user session if new
    if sender not in user_sessions:
        user_sessions[sender] = {'state': 'start', 'order': []}
    
    session = user_sessions[sender]
    
    # Menu command
    if message in ['menu', 'start', 'hi', 'hello']:
        session['state'] = 'browsing'
        return get_menu()
    
    # Order command
    elif message.startswith('order'):
        try:
            # Extract item number: "order 1" or "order 3"
            item_num = int(message.split()[1])
            item = get_item_by_number(item_num)
            
            if item:
                session['order'].append(item)
                return f"✅ Added {item['name']} (₦{item['price']}) to your order!\n\nType 'checkout' to complete or 'menu' to continue ordering."
            else:
                return "❌ Invalid item number. Type 'menu' to see available items."
        except:
            return "❌ Please use format: 'order 1' (where 1 is item number)"
    
    # Checkout command
    elif message == 'checkout':
        if len(session['order']) == 0:
            return "🛒 Your cart is empty! Type 'menu' to start ordering."
        
        # Calculate total
        total = sum(item['price'] for item in session['order'])
        
        # Format order summary
        order_text = "📋 *Your Order:*\n\n"
        for item in session['order']:
            order_text += f"• {item['name']} - ₦{item['price']}\n"
        order_text += f"\n*Total: ₦{total}*\n\n"
        order_text += "Type 'confirm' to place order or 'cancel' to clear cart."
        
        session['state'] = 'confirming'
        return order_text
    
    # Confirm order
    elif message == 'confirm' and session['state'] == 'confirming':
        # Save order to database
        order_id = save_order(sender, session['order'])
        
        # Clear session
        session['order'] = []
        session['state'] = 'start'
        
        return f"✅ *Order Confirmed!*\n\nOrder ID: #{order_id}\n\nYour food will be delivered in 30-45 minutes.\n\nType 'menu' to order again!"
    
    # Cancel order
    elif message == 'cancel':
        session['order'] = []
        session['state'] = 'start'
        return "❌ Order cancelled. Type 'menu' to start a new order."
    
    # Help command
    elif message == 'help':
        return """
🤖 *How to Use:*

- Type 'menu' - View available items
- Type 'order [number]' - Add item to cart
  Example: order 1
- Type 'checkout' - View cart
- Type 'confirm' - Place order
- Type 'cancel' - Clear cart
- Type 'help' - Show this message
"""
    
    # Default response
    else:
        return "❓ I didn't understand that. Type 'help' for available commands or 'menu' to see food items."
