#imports
import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request
from slackeventsapi import SlackEventAdapter
import json

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# For connecting to the server that the bot is in
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

# Gets slack token
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

# Send a test message when the bot starts
client.chat_postMessage(channel='#test', text="Hello World!")

# Gives id of bot
BOT_ID = client.api_call("auth.test")['user_id']

#converts rich text to slack text channel
def convert_rich_text_to_slack_format(rich_text):
    formatted_text = ""
    
    for element in rich_text.get("elements", []):
        if element["type"] == "rich_text_section":
            for sub_element in element["elements"]:
                if sub_element["type"] == "text":
                    text_content = sub_element["text"]
                    style = sub_element.get("style", {})
                    
                    # Apply styles in the correct order: bold, italic, strikethrough, and inline code
                    if style.get("code"):
                        # Inline code
                        text_content = f"`{text_content}`"
                    if style.get("bold"):
                        text_content = f"*{text_content}*"
                    if style.get("italic"):
                        text_content = f"_{text_content}_"
                    if style.get("strike"):
                        # Handle spaces within strikethrough: remove leading/trailing spaces inside strikethrough marks
                        text_content = f"~{text_content.strip()}~"

                    # Ensure no double spaces are introduced around styled text
                    formatted_text += text_content + " "

                # Handle hyperlink
                elif sub_element["type"] == "link":
                    url = sub_element["url"]
                    link_text = sub_element["text"]
                    formatted_text += f"<{url}|{link_text}> "

                # Handle emoji
                elif sub_element["type"] == "emoji":
                    emoji_name = sub_element["name"]
                    formatted_text += f":{emoji_name}: "

        # Handle bulleted lists
        elif element["type"] == "rich_text_list" and element.get("style") == "bullet":
            for item in element["elements"]:
                list_item_text = item["elements"][0]["text"]
                formatted_text += f"• {list_item_text}\n"

        # Handle ordered lists
        elif element["type"] == "rich_text_list" and element.get("style") == "ordered":
            for i, item in enumerate(element["elements"], start=1):
                list_item_text = item["elements"][0]["text"]
                formatted_text += f"{i}. {list_item_text}\n"

        # Handle block quotes
        elif element["type"] == "rich_text_quote":
            quote_text = element["elements"][0]["text"]
            formatted_text += f"> {quote_text}\n"

        # Handle code blocks
        elif element["type"] == "rich_text_preformatted":
            code_text = "".join([se["text"] for se in element["elements"] if se["type"] == "text"])
            formatted_text += f"```{code_text}```\n"

    # Strip trailing space to avoid extra space at the end
    return formatted_text.strip()


# Messages user if they join the slack server
@slack_event_adapter.on("team_join")
def handle_team_join(event_data):
    user_id = event_data["event"]["user"]["id"]
    welcome_message = f"Welcome to the team, <@{user_id}>! Please introduce yourself in the Introductions text channel!"
    
    # Send a DM to the new user
    client.chat_postMessage(channel=user_id, text=welcome_message)

# Handle app_home_opened event to update the Home Tab
@slack_event_adapter.on("app_home_opened")
def update_home_tab(event_data):
    user_id = event_data["event"]["user"]

    try:
        # Define the view (Home Tab layout)
        user_info = client.users_info(user=user_id)
        full_name = user_info['user']['profile'].get('real_name', 'User')  # Get the full name or default to 'User'
        profile_picture_url = user_info['user']['profile'].get('image_192', '')  # Get the profile picture URL

        view = {
            "type": "home",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Welcome to the Viaka Bot home page!* :tada:"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":busts_in_silhouette: Profile",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*{full_name}*\nHi there!\n\nPlease make to *Update Your Profile* :pencil2:\n\n\n*Introduce yourself* to everyone! :wave:" 
                        },
                    ],
                    "accessory": {
                        "type": "image",
                        "image_url": profile_picture_url,
                        "alt_text": "User's Profile Picture"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": ":bust_in_silhouette: Your Profile"
                            },
                            "value": "update_profile",  # Value for identifying the action
                            "action_id": "update_profile_button"  # Action ID for handling
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": ":flashlight: Introduce Yourself"
                            },
                            "value": "introduce_yourself",  # Value for identifying the action
                            "action_id": "introduce_yourself_button"  # Action ID for handling
                        }
                    ]
                }
            ]
        }

        # Publish the view to the Home Tab
        client.views_publish(
            user_id=user_id,
            view=view
        )

    except slack.errors.SlackApiError as e:
        print(f"Error publishing home tab: {e.response['error']}")

# Handle button interactions and modal submissions
@app.route("/slack/actions", methods=["POST"])
def slack_actions():
    payload = request.form["payload"]
    data = json.loads(payload)

    # Debug: Print the entire payload to check its structure
    print("Payload received:", data)

    # Check the type of event
    if data["type"] == "block_actions":
        user_id = data["user"]["id"]
        action_id = data["actions"][0]["action_id"]

        if action_id == "update_profile_button":
            # Redirect to profile update page (you can implement this)
            client.chat_postMessage(channel=user_id, text="Please update your profile at: [Profile Update Form Link]")

        elif action_id == "introduce_yourself_button":
            # Get the list of channels to populate the dropdown
            channels_response = client.conversations_list()
            channels = channels_response['channels']
            channel_options = [
                {
                    "text": {
                        "type": "plain_text",
                        "text": channel['name']
                    },
                    "value": channel['id']
                }
                for channel in channels if not channel['is_private']  # Filter for public channels only
            ]


            # Open a modal for the user to type their introduction
            modal_view = {
                "type": "modal",
                "callback_id": "introduce_yourself_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Introduce Yourself"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "introduction_input",
                        "element": {
                            "type": "rich_text_input"  # Use rich_text_input for rich text editing
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Tell us about yourself!"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "channel_select",
                        "element": {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a channel"
                            },
                            "options": channel_options
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Select the channel to send your introduction"
                        }
                    }
                ],
                "submit": {
                    "type": "plain_text",
                    "text": "Send"
                }
            }


            # Open the modal
            client.views_open(
                trigger_id=data["trigger_id"],
                view=modal_view
            )

    elif data["type"] == "view_submission":
        # Debug: Print the entire payload to check its structure
        print("View Submission Payload:", json.dumps(data, indent=2))  # Pretty-print the payload

        # Handle modal submissions
        user_id = data["user"]["id"]

        # Initialize variables to store introduction and selected channel
        introduction = None
        selected_channel = None
        
        # Accessing the introduction input
        introduction_block = data["view"]["state"]["values"].get("introduction_input", {}).get("Cq4Y/")
        if introduction_block:
            # Access the rich text value
            rich_text_value = introduction_block.get("rich_text_value", {})
            if "elements" in rich_text_value:
                # Convert the rich text elements to plain text
                introduction = convert_rich_text_to_slack_format(rich_text_value)
        
        # Accessing the selected channel
        selected_channel_block = data["view"]["state"]["values"].get("channel_select", {}).get("5YFoV")
        if selected_channel_block:
            selected_channel = selected_channel_block["selected_option"]["value"]

        # Debug: Print the user ID and introduction
        print(f"User ID: {user_id}")
        print(f"Introduction: {introduction}")
        print(f"Selected Channel ID: {selected_channel}")

        # Send the introduction to the selected channel
        if introduction and selected_channel:
            try:
                client.chat_postMessage(
                channel=selected_channel, 
                text=f"New Introduction from <@{user_id}>: {introduction}",
                unfurl_links=False
                )
                print("Introduction sent to the selected channel.")
            except slack.errors.SlackApiError as e:
                print(f"Error sending message to the channel: {e.response['error']}")
        else:
            print("Introduction or channel selection is missing.")

    return "", 200


#ngrok testing
if __name__ == "__main__":
    app.run(debug=True, port=5002)
