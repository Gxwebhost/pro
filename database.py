import os

def get_webhook(discUser):
    # Example: return the same webhook URL from env for all users
    return os.getenv("DISCORD_WEBHOOK_URL")
