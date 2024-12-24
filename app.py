
import os
import logging
from slack_sdk import WebClient 
from slack_sdk.errors import SlackApiError

from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from flask import Flask, request, jsonify
from functions import draft_message
from dotenv import load_dotenv

load_dotenv()


SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")

print(f"SLACK_BOT_TOKEN: {SLACK_BOT_TOKEN}")

app = App(token=SLACK_BOT_TOKEN)

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)
slack_client = WebClient(token=SLACK_BOT_TOKEN)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def post_messages(channel, text, thread_ts=None):
    try:
        response = slack_client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts
        )
        logging.info(f"Message posted: {response}")
    except SlackApiError as e:
        logging.error(f"Error posting message: {e.response['error']}")

def add_reaction(channel, timestamp, reaction):
    try:
        response = slack_client.reactions_add(
            channel=channel,
            timestamp=timestamp,
            name=reaction
        )
        logging.debug(f"Reaction added: {response}")
    except SlackApiError as e:
        logging.error(f"Error adding reaction: {e.response['error']}")   

def remove_reaction(channel, timestamp, reaction):
    try:
        response = slack_client.reactions_remove(
            channel=channel,
            timestamp=timestamp,
            name=reaction
        )
        logging.debug(f"Reaction removed: {response}")
    except SlackApiError as e:
        logging.error(f"Error removing reaction: {e.response['error']}")    

def get_user_name(user_id):
    try:
        logging.debug(f"Getting user info for User ID: {user_id}")   
        response = slack_client.users_info(user=user_id)
        user_info = response.get("user", {})
        real_name = user_info.get("real_name", "Unknown Banda")
        logging.debug(f"fetched user info: {user_info}")
        return real_name
    except SlackApiError as e:
        logging.error(f"Error getting user info from {user_id}: {e.response['error']}")
        return "Unknown Banda"      

def fetched_thread_message(channel,thread_ts):
    try:
        response = slack_client.conversations_replies(
            channel=channel,    
            ts=thread_ts
        )
        messages = response.get("messages", [])

        thread_messages = []
        for message in messages:
            user_id = message.get("user", "")
            user_name = get_user_name(user_id)
            message_text = message.get("text", "")
            thread_messages.append({"user": user_name, "text": message_text})
        return thread_messages
    except SlackApiError as e:
        logging.error(f"Error fetching thread messages: {e.response['error']}") 
        return []


@app.event("app_mention")
def handle_mentions(body, say):   
    logging.info("Received app mention event")  
    text = body["event"]["text"]  
    mention = f"<@{SLACK_BOT_USER_ID}>"

    event = body['event']
    channel = event['channel']
    timestamp = event['ts']
    emoji = "🎉"
    logging.info(f"Adding reaction {emoji}")
    add_reaction(channel, timestamp, emoji)

    text = text.replace(mention, "").strip()
    logging.info(f"Processed text: {text}")

    logging.info("Drafting message response")
    response = draft_message(text, history=[])
    logging.info(f"Drafted response: {response}")

    logging.info("Posting response message")
    post_messages(channel, response, thread_ts=timestamp)
    
    thread_messages = fetched_thread_message(channel, timestamp)
    logging.info(f"Fetched thread messages: {thread_messages}")
    
    logging.info("Removing reaction")
    remove_reaction(channel, timestamp, emoji)
@app.message(".*")
def handle_message_event(body, say, logger):
    logging.info("Received message event")
    event = body['event']
    text = event['text']
    channel = event['channel']
    logger.debug(f"Received message: {text}")

    if 'thread_ts' in event:
        parent_thread_ts =  event['thread_ts']
        timestamp = event['ts']
        emoji = 'eyes'
        logging.info(f"Adding reaction {emoji}")
        add_reaction(channel, timestamp, emoji)
        
        logging.info("Fetching thread messages")
        history = fetched_thread_message(channel, parent_thread_ts)
        logging.info(f"Fetched history: {history}")
        
        logging.info("Drafting message response")
        response = draft_message(text, history)
        logging.info(f"Drafted response: {response}")

        logging.info("Posting response message")
        post_messages(channel, response, parent_thread_ts)
        
        logging.info("Removing reaction")
        remove_reaction(channel, timestamp, emoji)
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if 'challenge' in data:
        challenge = data['challenge']
        return jsonify({'challenge': challenge})
    return handler.handle(request)

@flask_app.route("/slack", methods=["GET"])
def function():
    return "OK"

if __name__ == "__main__":
    logging.info("Starting Flask APP")
    flask_app.run(host='0.0.0.0', port=5003)



# first of all your flask app should be running
# then run the command
# ngrok http 5003
# and copy the ngrok link
# https://880f-115-96-219-32.ngrok-free.app/slack/events
# and paste the ngrok link in the slack app
# https://api.slack.com/apps/A0822T0ATUK/event-subscriptions

