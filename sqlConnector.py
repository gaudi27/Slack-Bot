import mysql.connector
import random
import slack_sdk
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
import datetime
from slack_sdk import WebClient

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# For connecting to the server that the bot is in
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

# Gets slack token
client = slack_sdk.WebClient(token= os.environ['SLACK_TOKEN'])


def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="gaudi",
        password="WellesleY!738",
        database="slackdb"
    )


def save_profile_to_db(user_id, profile, team_id):
    db = connect_to_db()
    cursor = db.cursor()
    print(team_id)

    query = """
    INSERT INTO user_profiles (user_id, full_name, pronouns, location, hometown, education, languages, hobbies, birthday, ask_me_about, bio, team_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    full_name = VALUES(full_name),
    pronouns = VALUES(pronouns),
    location = VALUES(location),
    hometown = VALUES(hometown),
    education = VALUES(education),
    languages = VALUES(languages),
    hobbies = VALUES(hobbies),
    birthday = VALUES(birthday),
    ask_me_about = VALUES(ask_me_about),
    bio = VALUES(bio),
    team_id = VALUES(team_id)
    """
    cursor.execute(query, (
        user_id,  
        profile.get('full_name', ''),
        profile.get('pronouns', ''),
        profile.get('location', ''),
        profile.get('hometown', ''),
        profile.get('education', ''),
        profile.get('languages', ''),
        profile.get('hobbies', ''),
        profile.get('birthday', ''),
        profile.get('ask_me_about', ''),
        profile.get('bio', ''),
        team_id
    ))

    db.commit()
    cursor.close()
    db.close()


def load_profile_from_db(user_id, team_id):
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM user_profiles WHERE user_id = %s AND team_id = %s"
    cursor.execute(query, (user_id, team_id))
    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result

def is_user_opted_in(user_id, team_id):
    db = connect_to_db()
    cursor = db.cursor()

    # Check if the user_id exists in the introductions table for the specific team
    cursor.execute("SELECT COUNT(*) FROM introductions WHERE user_id = %s AND team_id = %s", (user_id, team_id))
    count = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return count > 0

def opt_in_user(user_id, team_id, full_name):
    db = connect_to_db()
    cursor = db.cursor()
    intro_text = f"{full_name} has opted in!"
    query = """
    INSERT INTO introductions (user_id, team_id, intro_text)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE intro_text = VALUES(intro_text)
    """
    cursor.execute(query, (user_id, team_id, intro_text))
    db.commit()
    cursor.close()
    db.close()


def opt_out_user(user_id, team_id):
    db = connect_to_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM introductions WHERE user_id = %s AND team_id = %s", (user_id, team_id))
    db.commit()
    cursor.close()
    db.close()



from slack_sdk import WebClient

def pair_users_weekly():
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Get unique team_ids from introductions to process each server separately
    cursor.execute("SELECT DISTINCT team_id FROM introductions")
    teams = cursor.fetchall()

    for team in teams:
        team_id = team["team_id"]

        # Fetch all opted-in users for this team
        cursor.execute("SELECT user_id FROM introductions WHERE team_id = %s", (team_id,))
        users = [row["user_id"] for row in cursor.fetchall()]

        random.shuffle(users)
        pairs = []

        while len(users) > 1:
            if len(users) == 3:
                # Pair as a trio
                user1, user2, user3 = users.pop(), users.pop(), users.pop()
                pairs.append((user1, user2, user3))
                group_dm = client.conversations_open(users=[user1, user2, user3])

                # Message with buttons for viewing each other's profiles
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":wave: You've been paired with <@{user2}> and <@{user3}> this week!"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Profile"
                                },
                                "value": user2,
                                "action_id": "view_profile_button"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Profile"
                                },
                                "value": user3,
                                "action_id": "view_profile_button"
                            }
                        ]
                    }
                ]

                client.chat_postMessage(channel=group_dm["channel"]["id"], blocks=blocks)

            else:
                # Pair as a duo
                user1, user2 = users.pop(), users.pop()
                pairs.append((user1, user2))
                group_dm = client.conversations_open(users=[user1, user2])

                # Message with buttons for viewing each other's profiles
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":wave: You've been paired with <@{user1}> and <@{user2}> this week!"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Profile"
                                },
                                "value": user1,
                                "action_id": "view_profile_button"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Profile"
                                },
                                "value": user2,
                                "action_id": "view_profile_button"
                            }
                        ]
                    }
                ]

                client.chat_postMessage(channel=group_dm["channel"]["id"], blocks=blocks)

        # Remove paired users from introductions table for this team
        for pair in pairs:
            for user in pair:
                cursor.execute("DELETE FROM introductions WHERE user_id = %s AND team_id = %s", (user, team_id))

    db.commit()
    cursor.close()
    db.close()




