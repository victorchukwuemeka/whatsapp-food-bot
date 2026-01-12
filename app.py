from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from handlers.message_handler import handle_incoming_message
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    
    # Create response object
    resp = MessagingResponse()
    
    # Handle the message and get response
    response_text = handle_incoming_message(incoming_msg, sender)
    
    # Send response
    msg = resp.message()
    msg.body(response_text)
    
    return str(resp)

@app.route('/')
def home():
    return "WhatsApp Food Bot is running!"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
