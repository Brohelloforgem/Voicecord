import os
import sys
import json
import time
import requests
import websocket # This should be the 'websocket-client' library
import threading # For handling heartbeats
from keep_alive import keep_alive # Assuming this is correctly defined elsewhere

# --- Configuration ---
status = "dnd" # online/dnd/idle

GUILD_ID = 550389429567750155 # Replace with your target Guild ID
CHANNEL_ID = 1287816051760824457 # Replace with your target Voice Channel ID
SELF_MUTE = False
SELF_DEAF = False

# --- Token and User Info Retrieval ---
usertoken = os.getenv("TOKEN")
if not usertoken:
  print("[ERROR] Please add a Discord user token as an environment variable named 'TOKEN'.")
  sys.exit()

headers = {"Authorization": usertoken, "Content-Type": "application/json"}

# Validate token and get user info
try:
  validate_response = requests.get('https://canary.discordapp.com/api/v9/users/@me', headers=headers)
  validate_response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
  userinfo = validate_response.json()
  username = userinfo.get("username", "Unknown")
  discriminator = userinfo.get("discriminator", "0000")
  userid = userinfo.get("id", "Unknown")
except requests.exceptions.RequestException as e:
  print(f"[ERROR] Failed to validate token or fetch user info: {e}")
  print("Your token might be invalid or there's a network issue. Please check it again.")
  sys.exit()

# --- Heartbeat Thread Function ---
def send_heartbeat(ws, interval):
    """Sends heartbeat payloads to the Discord Gateway to keep the connection alive."""
    # Discord Gateway expects op:1 (heartbeat)
    payload = {"op": 1, "d": None}
    while not ws.closed:
        try:
            ws.send(json.dumps(payload))
            # print(f"[DEBUG] Sent heartbeat. Next in {interval / 1000:.1f} seconds.")
            time.sleep(interval / 1000)
        except websocket.WebSocketConnectionClosedException:
            print("[INFO] Heartbeat thread detected WebSocket connection closed.")
            break
        except Exception as e:
            print(f"[ERROR] Heartbeat thread encountered an error: {e}")
            break

# --- Main Joiner Function ---
def joiner(token, status):
    """
    Connects to the Discord Gateway, authenticates, and joins a voice channel.
    Handles basic WebSocket operations and starts a heartbeat thread.
    """
    ws = None # Initialize ws to None
    heartbeat_thread = None # Initialize heartbeat_thread to None
    try:
        # Initialize WebSocket client. This *should* work without arguments for websocket-client.
        ws = websocket.WebSocket()
        print("[INFO] Attempting to connect to Discord Gateway...")
        ws.connect('wss://gateway.discord.gg/?v=9&encoding=json')
        print("[INFO] Connected to Discord Gateway.")

        # Receive the 'Hello' payload from Discord
        start_payload = json.loads(ws.recv())
        heartbeat_interval = start_payload['d']['heartbeat_interval']
        print(f"[INFO] Received heartbeat interval: {heartbeat_interval} ms")

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=send_heartbeat, args=(ws, heartbeat_interval))
        heartbeat_thread.daemon = True # Allow the main program to exit even if thread is running
        heartbeat_thread.start()

        # Send Identify payload for authentication
        auth_payload = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "Windows 10",
                    "$browser": "Google Chrome",
                    "$device": "Windows"
                },
                "presence": {
                    "status": status,
                    "afk": False
                }
            }
        }
        ws.send(json.dumps(auth_payload))
        print("[INFO] Sent Identify payload.")

        # Send Voice State Update payload to join VC
        vc_payload = {
            "op": 4,
            "d": {
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "self_mute": SELF_MUTE,
                "self_deaf": SELF_DEAF
            }
        }
        ws.send(json.dumps(vc_payload))
        print(f"[INFO] Sent Voice State Update to join Guild ID: {GUILD_ID}, Channel ID: {CHANNEL_ID}.")

        # Keep connection alive and process incoming messages (optional, for basic listening)
        while not ws.closed:
            try:
                message = ws.recv()
                # print(f"[DEBUG] Received: {message[:100]}...") # Print first 100 chars
                # You can add logic here to process Discord Gateway events
            except websocket.WebSocketConnectionClosedException:
                print("[INFO] WebSocket connection closed by Discord or client.")
                break
            except Exception as e:
                print(f"[ERROR] Error receiving message: {e}")
                break

    except websocket.WebSocketException as e:
        print(f"[ERROR] WebSocket error: {e}. This might be due to an invalid URL or network issue.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred in joiner: {e}")
    finally:
        if ws and not ws.closed:
            print("[INFO] Closing WebSocket connection.")
            ws.close()
        if heartbeat_thread and heartbeat_thread.is_alive():
            print("[INFO] Stopping heartbeat thread.")
            # No explicit stop, rely on ws.closed or main program exit


def run_joiner():
  os.system("clear" if os.name == "posix" else "cls") # Clears terminal (for Windows or Linux/macOS)
  print(f"Logged in as {username}#{discriminator} (ID: {userid}).")
  print("Starting Discord Voice Channel Joiner...")
  while True:
    joiner(usertoken, status)
    print("[INFO] Reconnecting in 30 seconds...")
    time.sleep(30) # Reconnects every 30 seconds

# --- Application Entry Point ---
# 'keep_alive()' is assumed to be a function that keeps the script running on services like Replit.
keep_alive()
run_joiner()
