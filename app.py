import streamlit as st
import subprocess
import sys
import os
import json
import requests
import pickle
import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.generativeai as genai

# ==== CONFIG ====

REMINDERS_FILE = "reminders.json"
NOTES_FILE = "notes.txt"
CREDENTIALS_FILE = "credentials.json"
TOKEN_PICKLE = "token.pickle"

OPENWEATHERMAP_API_KEY = "Your API Key"
NEWS_API_KEY = "Your API Key"
GEMINI_API_KEY = "Your API Key"

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

genai.configure(api_key=GEMINI_API_KEY)

# ---------------- Gmail API & Gemini AI ----------------

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                st.error(f"Missing {CREDENTIALS_FILE} for Gmail API authentication.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Gmail API service error: {e}")
        return None

def ai_format_email(subject, user_note):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are an expert email writer. "
            "Given this subject and a short user note, "
            "rewrite them into a complete, polite, professional email with greeting, "
            "clear body, and closing. Preserve meaning and ensure it matches the subject context.\n\n"
            f"Subject: {subject}\n"
            f"User Note: {user_note}"
        )
        response = model.generate_content(prompt=prompt)
        return response.text.strip()
    except Exception as e:
        st.warning(f"Gemini API error: {e}, fallback to plain format.")
        return f"Subject: {subject}\n\nHello,\n\n{user_note}\n\nBest regards,\nYour Personal Assistant"

def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email(to, subject, user_note):
    service = get_gmail_service()
    if not service:
        st.error("Failed to initialize Gmail API service.")
        return
    final_body = ai_format_email(subject, user_note)
    message = create_message("me", to, subject, final_body)
    try:
        service.users().messages().send(userId="me", body=message).execute()
        st.success(f"Email sent successfully to {to}")
        st.text_area("Email content sent:", value=final_body, height=300)
    except Exception as e:
        st.error(f"Failed to send email: {e}")

# ---------------- Reminders ----------------

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r") as f:
                return json.load(f)
        except:
            st.error("Failed to load reminders file.")
    return []

def save_reminders(reminders):
    try:
        with open(REMINDERS_FILE, "w") as f:
            json.dump(reminders, f, indent=4)
    except:
        st.error("Failed to save reminders file.")

# ---------------- Notes ----------------

def load_notes():
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except:
            st.error("Failed to load notes file.")
    return ""

def save_notes(text):
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            f.write(text)
    except:
        st.error("Failed to save notes file.")

# ---------------- Weather ----------------

def get_weather(city):
    if not city:
        return None
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            desc = data['weather'][0]['description'].capitalize()
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            wind = data['wind']['speed']
            return f"{desc} | Temp: {temp}°C | Humidity: {humidity}% | Wind Speed: {wind} m/s"
        else:
            return None
    except Exception as e:
        st.error(f"Weather API error: {e}")
        return None

# ---------------- News ----------------

def get_news(country_code):
    if not country_code:
        return None
    try:
        url = f"https://newsapi.org/v2/top-headlines?country={country_code}&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("articles", [])
        else:
            return None
    except Exception as e:
        st.error(f"News API error: {e}")
        return None

# ---------------- Streamlit UI ----------------

st.title("Full Personal Assistant (Streamlit Edition)")

tabs = st.tabs(["Calendar", "Reminders", "Notes", "Weather", "News", "AI Email"])

with tabs[0]:
    st.header("Calendar Assistant")
    if st.button("Open Calendar GUI"):
        try:
            subprocess.Popen([sys.executable, "calendar_gui.py"])
            st.success("Calendar GUI opened.")
        except Exception as e:
            st.error(f"Failed to open Calendar GUI: {e}")

with tabs[1]:
    st.header("Reminders To-Do List")
    reminders = load_reminders()
    for i, reminder in enumerate(reminders):
        col1, col2 = st.columns([8, 1])
        col1.write(f"{reminder['text']}" + (f" (Due: {reminder['due']})" if reminder.get('due') else ""))
        if col2.button("Delete", key=f"del{i}"):
            reminders.pop(i)
            save_reminders(reminders)
            st.experimental_rerun()
    text = st.text_input("Add new reminder text")
    due = st.text_input("Add new reminder due date/time (optional)")
    if st.button("Add Reminder"):
        if text.strip():
            reminders.append({"text": text.strip(), "due": due.strip() if due.strip() else None})
            save_reminders(reminders)
            st.success("Reminder added!")
            st.experimental_rerun()

with tabs[2]:
    st.header("Notes Journal")
    notes_text = load_notes()
    new_notes = st.text_area("Your notes:", value=notes_text, height=300)
    if st.button("Save Notes"):
        save_notes(new_notes)
        st.success("Notes saved!")

with tabs[3]:
    st.header("Weather Information")
    city = st.text_input("Enter city name")
    if st.button("Get Weather"):
        weather = get_weather(city.strip())
        if weather:
            st.write(weather)
        else:
            st.error("City not found or API error.")

with tabs[4]:
    st.header("Top News Headlines")
    country = st.text_input("Enter 2-letter country code (e.g., us, in, gb)")
    if st.button("Get News"):
        articles = get_news(country.strip().lower())
        if articles is None:
            st.error("Failed to fetch news. Check API key and country code.")
        elif len(articles) == 0:
            st.info("No news found for this country.")
        else:
            for art in articles:
                st.markdown(f"### [{art['title']}]({art['url']})")
                if art.get('description'):
                    st.write(art['description'])
                st.write("---")

with tabs[5]:
    st.header("AI Powered Email Sender")
    recipient = st.text_input("Recipient Gmail address")
    subject = st.text_input("Subject")
    user_note = st.text_area("Type a short note (AI will format the email)")

    if st.button("Send Email"):
        if not recipient.strip() or not subject.strip() or not user_note.strip():
            st.warning("Please fill in all the fields.")
        else:
            send_email(recipient.strip(), subject.strip(), user_note.strip())

