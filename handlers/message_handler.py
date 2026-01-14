from utils.menu import get_menu, get_item_by_number
from database.db import save_order, get_user_address, save_user_address

user_sessions = {}

def handle_incoming_message(message, sender):
    """Process incoming messages and return appropriate response"""
    
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
        
        total = sum(item['price'] for item in session['order'])
        
        order_text = "📋 *Your Order:*\n\n"
        for item in session['order']:
            order_text += f"• {item['name']} - ₦{item['price']}\n"
        order_text += f"\n*Total: ₦{total}*\n\n"
        order_text += "Type 'confirm' to continue"
        
        session['state'] = 'confirming'
        return order_text
    
    # Confirm order - NOW ASK FOR ADDRESS
    elif message == 'confirm' and session['state'] == 'confirming':
        # Check if user has saved address
        saved_address = get_user_address(sender)
        
        if saved_address:
            session['state'] = 'confirm_address'
            return f"📍 Use your saved address?\n\n{saved_address}\n\nReply 'yes' to use this address or type a new address."
        else:
            session['state'] = 'waiting_address'
            return "📍 *Please send your delivery address*\n\nInclude:\n• Street name and number\n• Area/Estate\n• Landmark (optional)\n\nExample: 15 Admiralty Way, Lekki Phase 1, Near Shoprite"
    
    # User confirms saved address
    elif message == 'yes' and session['state'] == 'confirm_address':
        saved_address = get_user_address(sender)
        session['delivery_address'] = saved_address
        return complete_order(sender, session)
    
    # User provides new address (when they have saved address)
    elif session['state'] == 'confirm_address':
        session['delivery_address'] = message
        save_user_address(sender, message)
        return complete_order(sender, session)
    
    # User provides address (first time)
    elif session['state'] == 'waiting_address':
        # Save the address
        session['delivery_address'] = message
        save_user_address(sender, message)
        return complete_order(sender, session)
    
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
- Type 'confirm' - Continue to delivery
- Type 'cancel' - Clear cart
- Type 'help' - Show this message
"""
    
    # Default response
    else:
        return "❓ I didn't understand that. Type 'help' for available commands or 'menu' to see food items."


def complete_order(sender, session):
    """Complete the order after address is provided"""
    # Calculate total
    total = sum(item['price'] for item in session['order'])
    
    # Save order to database
    order_id = save_order(
        customer_phone=sender,
        items=session['order'],
        delivery_address=session['delivery_address']
    )
    
    # Format confirmation message
    confirmation = f"""✅ *Order Confirmed!*

Order ID: #{order_id}
Total: ₦{total}

📍 Delivery Address:
{session['delivery_address']}

⏱️ Estimated delivery: 30-45 minutes
💰 Payment: Cash on Delivery

Please have exact change ready.
Thank you! 🙏

Type 'menu' to order again!"""
    
    # Clear session
    session['order'] = []
    session['state'] = 'start'
    session['delivery_address'] = None
    
    return confirmation