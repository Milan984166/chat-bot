from flask import Flask, get_flashed_messages, render_template, request, redirect, url_for, flash, jsonify, session
from functools import wraps
from datetime import timedelta
from pprint import pprint
from datetime import datetime

import openai
import os
import mysql.connector
import bcrypt
import json
import time



mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="chat_bot"
)

mycursor = mydb.cursor()

app = Flask(__name__)
app.secret_key = app.secret_key = os.urandom(24)  # Change this to a secure random key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Set session expiration to 30 minutes

# Set your OpenAI API key
openai.api_key = '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'


# Placeholder list of users (username, password)
users = [("milan", "12345")]


def create_user(username, password):

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor = mydb.cursor()
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
    mydb.commit()
    user_id = cursor.lastrowid
    cursor.close()

    topic = 'New Chat'
    message = '[]'

    if user_id is not None and topic and message:
        insert_query = "INSERT INTO user_chats (user_id, topic, message) VALUES (%s, %s, %s)"
        data = (user_id, topic, message)
        mycursor.execute(insert_query, data)
        mydb.commit()

def get_user(username):

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    return user

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode())
    # return bcrypt.checkpw(password.encode('utf-8'), hashed_password.decode('utf-8'))


# Placeholder function for login authentication
# def login(username, password):
#     for user, pwd in users:
#         if user == username and pwd == password:
#             return True
#     return False

# def signup(username, password):
#     users.append((username, password))
    

@app.route("/")\

def index():
    if 'username' in session:
        return redirect(url_for("chat"))  # Redirect to chat page if already logged in
    return render_template('login.html')

@app.route("/signup", methods=["GET", "POST"])

def signup():

    if 'username' in session:
        return redirect(url_for("chat"))  # Redirect to chat page if already logged in
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        error_messages = []

        if get_user(username):
            error_messages.append("Username already exists. Please choose a different one.")
            # return redirect(url_for("signup"))  # Redirect back to signup page with error message
        
        if password != confirm_password:
            error_messages.append("Passwords do not match. Please try again.")
            # return redirect(url_for("signup"))  # Redirect back to signup page with error message
        
        if error_messages:
            for error in error_messages:
                flash(error, "error")
            return redirect(url_for("signup"))  # Redirect back to signup page with error messages
        
        create_user(username, password)
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
        
    return render_template("signup.html")

def get_latest_chat_id(user_id):
    
    select_query = "SELECT id FROM user_chats WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1"
    mycursor.execute(select_query, (user_id,))
    latest_chat = mycursor.fetchone()
    # mycursor.close()
    # mydb.close()
    # pprint('abc')
    # pprint(latest_chat[0])
    if latest_chat:
        return latest_chat[0]
    return None

@app.route("/login", methods=["GET", "POST"])
def login():

    if 'username' in session:
        return redirect(url_for("chat"))  # Redirect to chat page if already logged in
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = get_user(username)
        
        if user and verify_password(password, user['password']):
            session["username"] = username
            # select_query = "SELECT * FROM users WHERE username = %s"
            # mycursor.execute(select_query, (username,))
            # user_data = mycursor.fetchone()  # Assuming one user per username

            return redirect(url_for("chat"))
        else:
            flash("Invalid username or password. Please try again.", "error")

    return render_template("login.html")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function



def get_user_id():
    username = session.get("username")
    select_query = "SELECT id FROM users WHERE username = %s"
    mycursor.execute(select_query, (username,))
    user_data = mycursor.fetchone()  # Assuming one user per username
    if user_data:
        return user_data[0]  # Assuming the first column is the user ID
    return None

@app.route("/new-chat", methods=["GET"])
def new_chat():
    if request.method == "GET":
        user_id = get_user_id()  # Implement this to get the user's ID
        topic = 'New Chat'
        message = '[]'

        if user_id is not None and topic and message:
            insert_query = "INSERT INTO user_chats (user_id, topic, message) VALUES (%s, %s, %s)"
            data = (user_id, topic, message)
            mycursor.execute(insert_query, data)
            mydb.commit()
            # pprint('test')
            return redirect(url_for("chat"))

    # this part needs to be updated
    # pprint('test2')
    return redirect(url_for("chat"))

def get_latest_user_chat(user_id):
    select_query = "SELECT topic, message FROM user_chats WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1"
    mycursor.execute(select_query, (user_id,))
    chat_data = mycursor.fetchone()
    # pprint(chat_data)
    if chat_data:
        topic, message = chat_data
        return {"topic": topic, "message": message}
    else:
        return {"topic": "", "message": ""}

def get_previous_user_chats(user_id):
    select_query = "SELECT id, topic, message FROM user_chats WHERE user_id = %s ORDER BY timestamp DESC"  # Limit to 100 previous chats
    mycursor.execute(select_query, (user_id,))
    chat_data = mycursor.fetchall()
    chat_list = [{"id": id, "topic": topic, "message": message} for id, topic, message in chat_data]
    return chat_list


@app.route("/chat")
@login_required
def chat():

    chat_id = request.args.get('id')
    if chat_id:
        update_query = "UPDATE user_chats SET timestamp = CURRENT_TIMESTAMP WHERE id = %s"
        mycursor.execute(update_query, (chat_id,))
        mydb.commit()
    username = session["username"]
    user_id = get_user_id()
    latest_chat_id = get_latest_chat_id(user_id)  # Fetch the latest chat ID for the user
    session['latest_chat_id'] = latest_chat_id

    select_query = "SELECT topic, message FROM user_chats WHERE user_id = %s AND id = %s"
    mycursor.execute(select_query, (user_id, latest_chat_id))
    latest_chat_messages = mycursor.fetchone()
    
    message_json = json.loads(latest_chat_messages[1])
    # pprint(message_json)
    
    # latest_chat_messages[1]

    latest_message = get_latest_user_chat(user_id)
    previous_chats = get_previous_user_chats(user_id)
    # pprint(latest_message)
    # pprint(latest_chat_id)

    return render_template('chat.html', username=username, latest_message=latest_message, previous_chats=previous_chats, latest_chat_id=latest_chat_id, message_json=message_json)

def insert_chat_data(user_id, topic, user_message, bot_response):
    current_time = datetime.now()
    formatted_time = current_time.strftime("%I:%M %p")
    chat_data = {"topic": topic, "user_message": user_message, "bot_response": bot_response, "time": formatted_time }
    insert_query = "INSERT INTO user_chats (user_id, message) VALUES (%s, %s)"
    mycursor.execute(insert_query, (user_id, json.dumps(chat_data)))
    mydb.commit()

def update_chat_data(user_id, user_message, bot_response):
    latest_chat_id = session.get("latest_chat_id")
    select_query = "SELECT topic, message FROM user_chats WHERE user_id = %s AND id = %s"
    mycursor.execute(select_query, (user_id, latest_chat_id))
    latest_chat_messages = mycursor.fetchone()

    previous_data = json.loads(latest_chat_messages[1])
    current_time = datetime.now()
    formatted_time = current_time.strftime("%I:%M %p")
    new_data = {"user_message": user_message, "bot_response" : bot_response, "time": formatted_time }
    
    # conversation = previous_data.get("conversation", [])
    previous_data.append(new_data)
    # pprint(previous_data)
    # previous_data["conversation"] = conversation
    
    update_query = "UPDATE user_chats SET message = %s, timestamp = CURRENT_TIMESTAMP WHERE id = %s"
    mycursor.execute(update_query, (json.dumps(previous_data), latest_chat_id))
    mydb.commit()

@app.route("/get", methods=["POST"])
def chat_response():
    msg = request.json["msg"]
    user_id = get_user_id()
    response = get_bot_response(msg, user_id)
    return jsonify({"response": response})

def load_text_from_file(filename, prompt_list):
    try:
        with open(filename, "r") as file:
            text = file.read()
        # Append the loaded text to the prompt list
        prompt_list.append(f'\nHuman: {text}')
    except Exception as e:
        print('Error loading text from file:', e)

def get_bot_response(message, user_id):

    prompt_list = [
        'You are a tourist guide chatbot and will answer as a tourist guide chatbot',
        '\nHuman: What time is it?',
        '\nAI: I have no idea, I\'m a tourist guide chatbot!'
    ]

    def update_list(message, pl):
        pl.append(message)

    def create_prompt(message, pl):
        p_message = f'\nHuman: {message}'
        update_list(p_message, pl)
        prompt = ''.join(pl)
        return prompt

    def get_api_response(prompt):
        text = None
        
        try:
            response = openai.Completion.create(
                model='text-davinci-003',
                prompt=prompt,
                temperature=0.2,
                max_tokens=200,
                top_p=1,
                frequency_penalty=0.2,
                presence_penalty=0.2,
                stop=[' Human:', ' AI:']
            )

            choices = response.get('choices')[0]
            text = choices.get('text')

        except Exception as e:
            print('ERROR:', e)

        return text

    def get_bot_response(message, pl):
        prompt = create_prompt(message, pl)
        bot_response = get_api_response(prompt)

        if bot_response:
            update_list(bot_response, pl)
            pos = bot_response.find('\nAI: ')
            bot_response = bot_response[pos + 5:]
        else:
            bot_response = 'Something went wrong...'

        update_chat_data(user_id, message, bot_response)
        return bot_response

    load_text_from_file("static/chat-data.txt", prompt_list)

    return get_bot_response(message, prompt_list)

@app.route("/edit-chat-topic", methods=["POST"])
def edit_chat_topic():
    chat_id = request.form.get("chat_id")
    new_title = request.form.get("new_title")

    # Assuming you have a database connection established
    # Update the chat topic with the new title
    update_query = "UPDATE user_chats SET topic = %s WHERE id = %s"
    mycursor.execute(update_query, (new_title, chat_id))
    mydb.commit()

    return jsonify({"message": "Chat topic updated successfully"})

@app.route("/delete-chat", methods=["GET"])
def delete_chat():
    chat_id = request.args.get("chat_id")

    # Assuming you have a database connection established
    # Update the chat topic with the new title
    delete_query = "DELETE FROM user_chats WHERE id = %s"
    mycursor.execute(delete_query, (chat_id,))
    mydb.commit()

    return jsonify({"message": "Chat deleted Successfully"})


@app.route("/logout")
def logout():
    session.clear()
    # Clear any user session data or authentication status
    # You can implement session management or other authentication methods here
    flash("Logged Out Successfully!", "success")
    return redirect(url_for("index"))



if __name__ == '__main__':
    app.debug = True
    app.run()
