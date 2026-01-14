"""
Local testing script for WhatsApp Food Bot
Run this instead of using Twilio to test your bot logic
"""

from handlers.message_handler import handle_incoming_message

# Simulate a user phone number
test_user = "whatsapp:+2348012345678"


def test_conversation():
    """Simulate a complete ordering conversation"""
    
    print("=" * 60)
    print("WHATSAPP FOOD BOT - LOCAL TEST")
    print("=" * 60)
    print()
    
    # Test cases
    test_messages = [
        "menu",
        "order 1",
        "order 4",
        "checkout",
        "confirm",
        "menu",
        "help",
        "random text",
        "cancel"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"USER: {message}")
        response = handle_incoming_message(message, test_user)
        print(f"BOT: {response}")
        print("-" * 60)

def interactive_test():
    """Interactive mode - chat with the bot"""
    
    print("=" * 60)
    print("INTERACTIVE MODE - Type 'quit' to exit")
    print("=" * 60)
    print()
    
    while True:
        user_input = input("YOU: ").strip()
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
            
        response = handle_incoming_message(user_input.lower(), test_user)
        print(f"BOT: {response}\n")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Automated test (run all test cases)")
    print("2. Interactive mode (chat with bot)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_conversation()
    elif choice == "2":
        interactive_test()
    else:
        print("Invalid choice. Running automated test...")
        test_conversation()