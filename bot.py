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
#client.chat_postMessage(channel='#test', text="Hello World!")

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
                    # Check if "url" and "text" are available
                    url = sub_element.get("url", "")
                    link_text = sub_element.get("text", "")
                    if link_text:
                        formatted_text += f"<{url}|{link_text}> "  # Use link text if available
                    else:
                        formatted_text += f"<{url}|{url}> "  # Fallback to URL if no text is provided

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
# Simulated persistent storage for user profiles (in a real application, use a database)
user_profiles = {}

# Handle app_home_opened event to update the Home Tab
@slack_event_adapter.on("app_home_opened")
def update_home_tab(event_data):
    user_id = event_data["event"]["user"]

    try:
        # Get user profile info from Slack (full name and profile picture)
        user_info = client.users_info(user=user_id)
        full_name = user_info['user']['profile'].get('real_name', 'User')  # Get the full name or default to 'User'
        profile_picture_url = user_info['user']['profile'].get('image_192', '')  # Get the profile picture URL

        # Check if the user has a custom profile saved, otherwise use the default message
        profile = user_profiles.get(user_id, {
            "full_name": full_name,
            "bio": "Hi there!\nPlease make sure to *Update Your Profile* :pencil2:\n\n\n*Introduce yourself* to everyone! :wave:"
        })

        # Define the Home Tab layout
       # Define the Home Tab layout
        profile_blocks = [
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*{profile['full_name']}*\n{profile['bio']}"
                    },
                ],
                "accessory": {
                    "type": "image",
                    "image_url": profile_picture_url,
                    "alt_text": "User's Profile Picture"
                }
            }
        ]

        # Add fields only if they are present in the profile
        optional_fields = [
            ("Pronouns", "pronouns"),
            (":round_pushpin: Location", "location"),
            (":house: Hometown", "hometown"),
            (":school: Education", "education"),
            (":speech_balloon: Languages", "languages"),
            (":clapper: Hobbies", "hobbies"),
            (":birthday: Birthday", "birthday"),
            (":bulb: Ask me About", "ask_me_about"),
        ]

        for field_label, field_key in optional_fields:
            field_value = profile.get(field_key)
            if field_value:
                profile_blocks.append({
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*{field_label}:* {field_value}"
                        }
                    ]
                })

        view = {
            "type": "home",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Welcome to the Viaka Bot home page!* :tada: Please see the *About* tab for any questions. :thinking_face: "
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
                }
            ] + profile_blocks + [
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": ":bust_in_silhouette: Your Profile"
                            },
                            "value": "update_profile",
                            "action_id": "update_profile_button"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": ":flashlight: Introduce Yourself"
                            },
                            "value": "introduce_yourself",
                            "action_id": "introduce_yourself_button"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": ":warning: Reset Profile"
                            },
                            "value": "reset_profile",
                            "action_id": "reset_profile_button"
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

    # Check the type of event
    if data["type"] == "block_actions":
        user_id = data["user"]["id"]
        action_id = data["actions"][0]["action_id"]

        # Handle the profile button interaction
        if action_id == "update_profile_button":
            # Open a new modal where users can create their profile
            profile_modal_view = {
                "type": "modal",
                "callback_id": "profile_creation_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Create Your Profile"
                },
                "submit": {  # Add a submit button to the modal
                    "type": "plain_text",
                    "text": "Submit"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "bio_input",
                        "element": {
                            "type": "plain_text_input",
                            "multiline": True,
                            "action_id": "bio",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "Small blurb about yourself"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":notebook: Bio"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "full_name_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "full_name",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. George Audi"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":speech_balloon: Full Name"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "pronouns_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "pronouns",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. He/him, She/her, They/them"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Pronouns"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "location_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "location",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. New York"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":round_pushpin: Where you are located (optional)"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "hometown_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "hometown",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. New York"
                            },
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":house: Where you are from"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "education_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "education",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. Boston University"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":school: Education"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "languages_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "languages",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. English, Spanish, Arabic"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":speech_balloon: What languages do you speak?"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "hobbies_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "hobbies",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. Golf, Reading, Movies"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":clapper: Hobbies"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "birthday_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "birthday",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "e.g. July 27th, 2004"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":birthday: Birthday"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "ask_me_about_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "ask_me_about",
                            "placeholder" : {
                                "type": "plain_text",
                                "text": "Highlight what makes you excited!"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": ":bulb: Ask me About"
                        },
                        "optional": True
                    }
                ]
            }

            # Open the profile creation modal
            client.views_open(
                trigger_id=data["trigger_id"],
                view=profile_modal_view
            )



        elif action_id == "reset_profile_button":
            # Reset the user's profile to the default message
            # Open a confirmation modal for resetting the profile
            confirmation_modal_view = {
                "type": "modal",
                "callback_id": "reset_profile_confirmation_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Confirm Reset Profile"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Are you sure you want to reset your profile? This action cannot be undone."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Yes, Reset"
                                },
                                "style": "danger",
                                "value": "confirm_reset",
                                "action_id": "confirm_reset_button"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Cancel"
                                },
                                "value": "cancel_reset",
                                "action_id": "cancel_reset_button"
                            }
                        ]
                    }
                ]
            }


            # Open the confirmation modal
            client.views_open(
                trigger_id=data["trigger_id"],
                view=confirmation_modal_view
            )

         # Handle confirmation from the modal
        elif action_id == "confirm_reset_button":
            if user_id in user_profiles:
                del user_profiles[user_id]  # Remove the custom profile

            # Update the home tab after resetting
            update_home_tab({"event": {"user": user_id}})

        elif action_id == "introduce_yourself_button":
            # Existing "Introduce Yourself" button functionality
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

        # Check if the submission is from the profile creation modal
        # Handle modal submissions
        if data["view"]["callback_id"] == "profile_creation_modal":
            # Extract user inputs, initializing empty values for optional fields
            full_name = data["view"]["state"]["values"].get("full_name_input", {}).get("full_name", {}).get("value", "")
            bio = data["view"]["state"]["values"].get("bio_input", {}).get("bio", {}).get("value", "")
            pronouns = data["view"]["state"]["values"].get("pronouns_input", {}).get("pronouns", {}).get("value", "")
            location = data["view"]["state"]["values"].get("location_input", {}).get("location", {}).get("value", "")
            hometown = data["view"]["state"]["values"].get("hometown_input", {}).get("hometown", {}).get("value", "")
            education = data["view"]["state"]["values"].get("education_input", {}).get("education", {}).get("value", "")
            languages = data["view"]["state"]["values"].get("languages_input", {}).get("languages", {}).get("value", "")
            hobbies = data["view"]["state"]["values"].get("hobbies_input", {}).get("hobbies", {}).get("value", "")
            birthday = data["view"]["state"]["values"].get("birthday_input", {}).get("birthday", {}).get("value", "")
            ask_me_about = data["view"]["state"]["values"].get("ask_me_about_input", {}).get("ask_me_about", {}).get("value", "")

            # Store the profile in our simulated storage only if the field is not empty
            user_profiles[user_id] = {
                "full_name": full_name if full_name else None,
                "bio": bio if bio else None,
                "pronouns": pronouns if pronouns else None,
                "location": location if location else None,
                "hometown": hometown if hometown else None,
                "education": education if education else None,
                "languages": languages if languages else None,
                "hobbies": hobbies if hobbies else None,
                "birthday": birthday if birthday else None,
                "ask_me_about": ask_me_about if ask_me_about else None,
            }

            # Update the Home Tab to reflect the new profile information
            update_home_tab({"event": {"user": user_id}})

        elif data["view"]["callback_id"] == "introduce_yourself_modal":
            # Existing "Introduce Yourself" submission handling (no changes)
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
                    # Get user profile information to fetch the profile picture URL
                    user_info = client.users_info(user=user_id)
                    profile_pic_url = user_info["user"]["profile"].get("image_48")  # You can adjust the size as needed

                    # Create a message with blocks
                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*New Introduction from <@{user_id}>:*\n\n{introduction}"
                            },
                            "accessory": {
                                "type": "image",
                                "image_url": profile_pic_url,
                                "alt_text": f"{user_info['user']['real_name']}'s profile picture"  # Alt text for accessibility
                            }
                        }
                    ]

                    client.chat_postMessage(
                        channel=selected_channel,
                        blocks=blocks
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
