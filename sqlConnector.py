import mysql.connector
import random
import slack_sdk
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
import datetime

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


def save_profile_to_db(user_id, profile):
    db = connect_to_db()
    cursor = db.cursor()

    # Upsert query: Insert new row if user_id doesn't exist, otherwise update the existing row
    query = """
    INSERT INTO user_profiles (user_id, full_name, pronouns, location, hometown, education, languages, hobbies, birthday, ask_me_about, bio)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    bio = VALUES(bio)
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
        profile.get('bio', '')
    ))

    db.commit()
    cursor.close()
    db.close()


def load_profile_from_db(user_id):
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM user_profiles WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result

def is_user_opted_in(user_id):
    """Check if the user is opted in."""
    db = connect_to_db()
    cursor = db.cursor()

    # Check if the user_id exists in the introductions table
    cursor.execute("SELECT COUNT(*) FROM introductions WHERE user_id = %s", (user_id,))
    count = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return count > 0

def opt_in_user(user_id, full_name):
    db = connect_to_db()
    cursor = db.cursor()
    intro_text = f"{full_name} has opted in!"  # Customize this message as needed
    query = """
    INSERT INTO introductions (user_id, intro_text) 
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE intro_text = VALUES(intro_text)
    """
    cursor.execute(query, (user_id, intro_text))
    db.commit()
    cursor.close()
    db.close()


def opt_out_user(user_id):
    db = connect_to_db()
    cursor = db.cursor()
    
    # Remove user from opt-in users table
    cursor.execute("DELETE FROM introductions WHERE user_id = %s", (user_id,))
    
    # Remove user from introductions
    cursor.execute("DELETE FROM introductions WHERE user_id = %s", (user_id,))
    
    db.commit()
    cursor.close()
    db.close()


def pair_users_weekly():
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch all opted-in users
    cursor.execute("SELECT user_id FROM introductions")
    users = [row["user_id"] for row in cursor.fetchall()]
    
    random.shuffle(users)
    pairs = []

    # Check for past pairs and create new pairs avoiding repeats
    while len(users) > 1:
        user1 = users.pop()
        user2 = users.pop()

        # Check for repeat pairing
        cursor.execute("""
            SELECT 1 FROM pairings 
            WHERE (user_id1 = %s AND user_id2 = %s) OR (user_id1 = %s AND user_id2 = %s)
        """, (user1, user2, user2, user1))

        if cursor.fetchone():
            users.extend([user1, user2])  # Put them back and try next
        else:
            pairs.append((user1, user2))
            # Save pair to pairings database
            cursor.execute("INSERT INTO pairings (user_id1, user_id2) VALUES (%s, %s)", (user1, user2))
            db.commit()

            # DM both users
            client.chat_postMessage(channel=user1, text=f"👋 You've been paired with <@{user2}> this week!")
            client.chat_postMessage(channel=user2, text=f"👋 You've been paired with <@{user1}> this week!")

    cursor.close()
    db.close()

