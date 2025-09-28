🧑‍💻 Personal Assistant 

A desktop-based AI-powered personal assistant built with Python (Tkinter GUI).
This project integrates multiple productivity tools into one place — a calendar assistant, reminders, notes, weather updates, news headlines, and AI-assisted Gmail email sending.

🚀 Features
📅 AI Calendar Assistant (calendar_gui.py)

Connects with Google Calendar API

Add, list, or delete events with a user-friendly GUI

Auto-schedules meals (Breakfast, Lunch, Dinner) around existing events

View daily and custom-date plans with conflict resolution

🧾 Full Personal Assistant (Full_personal_assistant.py)

All-in-one desktop app with:

Calendar Integration → Opens the calendar assistant

Reminders / To-Do List → Save, delete, and persist reminders in JSON

Notes / Journal → Write and save notes in a simple editor

Weather Updates → Fetch real-time weather via OpenWeather API

News Headlines → Fetch top headlines by country using NewsAPI

AI Email Sender → Draft professional emails using Gemini AI (Google Generative AI) and send via Gmail API

📧 Gmail AI Email Sender (send_gmail.py)

Command-line tool for sending polished, AI-formatted Gmail messages

Uses Gemini AI to rewrite short drafts into complete professional emails

Sends emails via the Gmail API

🛠️ Tech Stack

Python 3.x

Tkinter (GUI)

Google APIs: Calendar, Gmail

Gemini AI API for email drafting

OpenWeather API for weather updates

NewsAPI for headlines

File storage: JSON (reminders.json), TXT (notes.txt), pickle (token.pickle)
