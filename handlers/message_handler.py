import json
import os
from groq import Groq
from database.db import (
    get_all_restaurants,
    get_menu_by_restaurant,
    get_menu_item_by_id,
    get_available_rider,
    save_order,
    save_user_address,
    get_user_address,
    save_message,
    get_conversation_history,
    clear_conversation_history
)

from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# In-memory session store
user_sessions = {}

# ── TOOLS DEFINITION ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_restaurants",
            "description": "Get all available restaurants the user can order from",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Get the menu for a specific restaurant by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "integer",
                        "description": "The ID of the restaurant"
                    }
                },
                "required": ["restaurant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a menu item to the user's cart",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "The ID of the menu item to add"
                    }
                },
                "required": ["item_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_cart",
            "description": "View the current items in the user's cart",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_cart",
            "description": "Clear all items from the user's cart",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rider_offer",
            "description": "Get the initial delivery fee offer from an available rider",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "negotiate_rider_fee",
            "description": "User makes a counteroffer to the rider for the delivery fee. The rider will accept, reject, or counter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "offered_amount": {
                        "type": "number",
                        "description": "The amount the user is offering for delivery in Naira"
                    }
                },
                "required": ["offered_amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place the final order after delivery fee is agreed upon",
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_address": {
                        "type": "string",
                        "description": "The delivery address provided by the user"
                    },
                    "agreed_delivery_fee": {
                        "type": "number",
                        "description": "The final agreed delivery fee in Naira"
                    }
                },
                "required": ["delivery_address", "agreed_delivery_fee"]
            }
        }
    }
]


# ── TOOL EXECUTION ────────────────────────────────────────────────────────────

def execute_tool(tool_name, tool_args, sender):
    session = user_sessions.get(sender, {'cart': [], 'restaurant_id': None, 'rider': None})
    user_sessions[sender] = session

    if tool_name == "list_restaurants":
        restaurants = get_all_restaurants()
        if not restaurants:
            return "No restaurants are currently available."
        result = "Available restaurants:\n\n"
        for r in restaurants:
            result += f"ID {r['id']} - {r['name']} ({r['area']})\n"
            if r['description']:
                result += f"  {r['description']}\n"
        result += "\nTell me which restaurant you want to order from."
        return result

    elif tool_name == "get_menu":
        restaurant_id = tool_args.get("restaurant_id")
        items = get_menu_by_restaurant(restaurant_id)
        if not items:
            return "This restaurant has no menu items available right now."
        session['restaurant_id'] = restaurant_id
        result = "Menu:\n\n"
        categories = {}
        for item in items:
            cat = item['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        for cat, cat_items in categories.items():
            result += f"{cat}:\n"
            for item in cat_items:
                result += f"  [{item['id']}] {item['name']} - N{item['price']}\n"
        result += "\nTell me what you want to add to your cart by item number."
        return result

    elif tool_name == "add_to_cart":
        item_id = tool_args.get("item_id")
        item = get_menu_item_by_id(item_id)
        if not item:
            return f"Item {item_id} not found. Check the menu and try again."
        session['cart'].append(item)
        return f"Added {item['name']} (N{item['price']}) to your cart. Cart has {len(session['cart'])} item(s)."

    elif tool_name == "view_cart":
        cart = session.get('cart', [])
        if not cart:
            return "Your cart is empty."
        result = "Your cart:\n\n"
        total = 0
        for item in cart:
            result += f"  {item['name']} - N{item['price']}\n"
            total += item['price']
        result += f"\nFood total: N{total}"
        return result

    elif tool_name == "clear_cart":
        session['cart'] = []
        session['restaurant_id'] = None
        session['rider'] = None
        return "Cart cleared."

    elif tool_name == "get_rider_offer":
        rider = get_available_rider()
        if not rider:
            return "No riders are available right now. Try again in a few minutes."
        session['rider'] = rider
        return (
            f"Rider {rider['name']} is available.\n"
            f"Delivery fee: N{rider['base_fee']}\n\n"
            f"You can make a counteroffer if you want a lower price."
        )

    elif tool_name == "negotiate_rider_fee":
        offered_amount = tool_args.get("offered_amount")
        rider = session.get('rider')
        if not rider:
            return "No rider assigned yet. Ask for a rider first."

        min_fee = rider['min_fee']
        base_fee = rider['base_fee']

        if offered_amount >= base_fee:
            session['agreed_fee'] = offered_amount
            return f"Rider accepted. Delivery fee: N{offered_amount}. Ready to place your order."

        elif offered_amount >= min_fee:
            # rider accepts but acts reluctant
            session['agreed_fee'] = offered_amount
            return f"Rider agreed to N{offered_amount}. That is the lowest he can go. Ready to place your order."

        else:
            # rider counters at min_fee
            counter = min_fee
            return (
                f"Rider cannot go that low. "
                f"The lowest he can do is N{counter}. Do you accept?"
            )

    elif tool_name == "place_order":
        cart = session.get('cart', [])
        if not cart:
            return "Your cart is empty. Add items before placing an order."

        delivery_address = tool_args.get("delivery_address")
        agreed_fee = tool_args.get("agreed_delivery_fee", session.get('agreed_fee', 0))
        rider = session.get('rider')
        restaurant_id = session.get('restaurant_id')

        # Save address for future orders
        save_user_address(sender, delivery_address)

        order_id = save_order(
            customer_phone=sender,
            items=cart,
            delivery_address=delivery_address,
            restaurant_id=restaurant_id,
            rider_id=rider['id'] if rider else None,
            delivery_fee=agreed_fee
        )

        food_total = sum(item['price'] for item in cart)
        grand_total = food_total + agreed_fee

        # Clear session after order
        session['cart'] = []
        session['restaurant_id'] = None
        session['rider'] = None
        session['agreed_fee'] = None
        clear_conversation_history(sender)

        return (
            f"Order confirmed.\n\n"
            f"Order ID: #{order_id}\n"
            f"Food total: N{food_total}\n"
            f"Delivery fee: N{agreed_fee}\n"
            f"Grand total: N{grand_total}\n\n"
            f"Delivery address: {delivery_address}\n"
            f"Estimated delivery: 30-45 minutes\n"
            f"Payment: Cash on delivery"
        )

    return "Unknown tool called."


# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Brida, an agentic WhatsApp food ordering assistant.

You have access to the following actions. To call an action, respond ONLY with a JSON object in this exact format:
{"action": "action_name", "params": {}}

Available actions:
- list_restaurants — show available restaurants. params: {}
- get_menu — show menu for a restaurant. params: {"restaurant_id": <int>}
- add_to_cart — add item to cart. params: {"item_id": <int>}
- view_cart — show current cart. params: {}
- clear_cart — empty the cart. params: {}
- get_rider_offer — get delivery fee offer from rider. params: {}
- negotiate_rider_fee — user makes counteroffer. params: {"offered_amount": <float>}
- place_order — finalize order. params: {"delivery_address": "<string>", "agreed_delivery_fee": <float>}
- respond — send a plain text message to the user. params: {"message": "<string>"}

Rules:
- Always call an action by responding with JSON only. No extra text.
- Food prices are FIXED. Never negotiate food prices.
- Only the delivery fee can be negotiated.
- Be concise. This is WhatsApp.
- When user greets, call list_restaurants immediately.
- After cart is ready, call get_rider_offer, then negotiate, then place_order.
- When you have a final message for the user, use the respond action.
"""


def handle_incoming_message(message, sender):
    if sender not in user_sessions:
        user_sessions[sender] = {'cart': [], 'restaurant_id': None, 'rider': None, 'agreed_fee': None}

    save_message(sender, "user", message)
    history = get_conversation_history(sender, limit=20)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    max_iterations = 6
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.2
        )

        raw = response.choices[0].message.content.strip()

        try:
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            action = parsed.get("action")
            params = parsed.get("params", {})

            if action == "respond":
                final = params.get("message", "")
                save_message(sender, "assistant", final)
                return final

            tool_result = execute_tool(action, params, sender)

            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": f"Action result: {tool_result}. Now use the respond action to show this EXACT result to the user word for word. Do not summarize it."})
        except Exception as e:
            print(f"Error: {e}")
            print(f"Raw response was: {raw}")
            save_message(sender, "assistant", raw)
            return raw
        
    print(f"Max iterations reached. Last raw response: {raw}")
    return "Something went wrong. Please try again."











   