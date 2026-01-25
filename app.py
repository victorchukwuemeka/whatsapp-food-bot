from flask import Flask, request, jsonify
from handlers.message_handler import handle_incoming_message
from dotenv import load_dotenv
import os
import requests 


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


#where i want to handle the webhook verification
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode ==  "subscribe" and token == VERIFY_TOKEN :
        return challenge, 200 
    else:
        print("Webhook verification failed!")
        return "Forbidden", 403




@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    try:
        
        data = request.get_json()
        print(f"Received webhook: {data}")
        
        entry = data.get('entry', [])
        if not entry:
            return jsonify({'status': 'ok'}), 200
        
        changes = entry[0].get('changes', [])
        if not changes:
            return jsonify({'status': 'ok'}), 200
        
        value = changes[0].get('value', {})
        
        # Check if it contains a message
        if 'messages' in value:
            messages = value['messages']
            message = messages[0]
            
            # Get sender phone number
            sender = message.get('from')
            
            # Get message text
            if message.get('type') == 'text':
                incoming_msg = message['text']['body'].strip().lower()
                
                print(f" From: {sender}")
                print(f" Message: {incoming_msg}")
                
                # Process the message
                response_text = handle_incoming_message(incoming_msg, sender)
                
                # Send response back
                send_whatsapp_message(sender, response_text)
            
            # Handle other message types (images, locations, etc.)
            elif message.get('type') == 'location':
                # User shared location
                location = message['location']
                latitude = location.get('latitude')
                longitude = location.get('longitude')
                address = location.get('address', '')
                
                # You can handle location here
                response_text = f"📍 Location received: {address}"
                send_whatsapp_message(sender, response_text)
            
            else:
                # Unsupported message type
                print(f"ℹ Unsupported message type: {message.get('type')}")
        
        # Check if it's a status update (message delivered, read, etc.)
        elif 'statuses' in value:
            # Message status update (delivered, read, sent, failed)
            statuses = value['statuses']
            status = statuses[0]
            print(f" Status update: {status.get('status')} for message {status.get('id')}")
        
        return jsonify({'status': 'ok'}), 200
    except  Exception as e :
        print(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def send_whatsapp_message(to, message):
    """Send WhatsApp message via Meta Cloud API"""
    
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Split long messages (WhatsApp has 4096 character limit)
    max_length = 4096
    if len(message) > max_length:
        # Send in chunks
        chunks = [message[i:i+max_length] for i in range(0, len(message), max_length)]
        for chunk in chunks:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": chunk
                }
            }
            response = requests.post(url, headers=headers, json=payload)
            print(f"📤 Sent message chunk: {response.status_code}")
    else:
        # Send single message
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                print(f"✅ Message sent successfully to {to}")
            else:
                print(f"❌ Failed to send message: {response.status_code}")
                print(f"Response: {response_data}")
            
            return response
        
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None

@app.route('/')
def home():
    return "WhatsApp Food Bot is running!"

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'phone_number_id': PHONE_NUMBER_ID,
        'webhook_configured': True
    }), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)


