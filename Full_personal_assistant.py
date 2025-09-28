import tkinter as tk
from tkinter import font, messagebox, simpledialog
import subprocess
import sys
import json
import os
import requests
import webbrowser
import pickle
import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.generativeai as genai   # Gemini API

# ==== CONFIG ====
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
GEMINI_API_KEY = "AIzaSyA0V1wo0eKnGwyfXHFf01R3N3G8w2ysKTQ"

# ---------------- Gmail API ---------------- #
def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                messagebox.showerror("Error", "Missing credentials.json for Gmail API.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    try:
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        messagebox.showerror("Error", f"Gmail service error: {e}")
        return None

def ai_format_email(subject, user_draft):
    """Send subject + draft to Gemini API and get polished email text."""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are an expert email writer. "
            "Given the subject and a short user note, rewrite them into a complete, polite, professional email "
            "with a greeting, clear body, and closing. "
            "Preserve meaning and ensure it matches the subject context.\n\n"
            f"Subject: {subject}\n"
            f"User Note: {user_draft}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        messagebox.showwarning("AI Error", f"Gemini API error: {e}")
        return f"Subject: {subject}\n\nHello,\n\n{user_draft}\n\nBest regards,\nYour Personal Assistant"

def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email(to_email, subject, user_draft):
    service = get_gmail_service()
    if not service:
        return
    final_body = ai_format_email(subject, user_draft)
    message = create_message("me", to_email, subject, final_body)
    try:
        service.users().messages().send(userId="me", body=message).execute()
        messagebox.showinfo("Success", f"Email sent to {to_email}\n\nContent:\n\n{final_body}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send email: {e}")

# ---------------- REMINDERS ---------------- #
class RemindersWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Reminders / To-Do List")
        self.geometry("400x400")
        self.configure(bg="#222831")
        self.font_header = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=11)
        tk.Label(self, text="Reminders", font=self.font_header, fg="#00ffd5", bg="#222831").pack(pady=10)
        self.reminder_list = tk.Listbox(self, font=self.font_normal, width=40, height=12)
        self.reminder_list.pack(pady=5)
        btn_frame = tk.Frame(self, bg="#222831")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_reminder, bg="#00adb5", fg="white", width=10).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_reminder, bg="#ff5722", fg="white", width=10).grid(row=0, column=1, padx=5)
        self.load_reminders()

    def load_reminders(self):
        self.reminder_list.delete(0, tk.END)
        if os.path.exists("reminders.json"):
            try:
                with open("reminders.json", "r") as f:
                    data = json.load(f)
                for item in data:
                    display_text = f"{item['text']}   ({item['due']})" if item['due'] else item['text']
                    self.reminder_list.insert(tk.END, display_text)
            except:
                messagebox.showerror("Error", "Could not load reminders.")

    def save_reminders(self, reminders):
        try:
            with open("reminders.json", "w") as f:
                json.dump(reminders, f, indent=4)
        except:
            messagebox.showerror("Error", "Could not save reminders.")

    def get_all_reminders(self):
        if os.path.exists("reminders.json"):
            try:
                with open("reminders.json", "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def add_reminder(self):
        text = simpledialog.askstring("Add Reminder", "Enter the reminder text:")
        if not text:
            return
        due = simpledialog.askstring("Add Reminder", "Enter due date/time (optional):")
        reminders = self.get_all_reminders()
        reminders.append({"text": text, "due": due})
        self.save_reminders(reminders)
        self.load_reminders()

    def delete_reminder(self):
        selection = self.reminder_list.curselection()
        if not selection:
            messagebox.showinfo("Delete Reminder", "Please select a reminder to delete.")
            return
        reminders = self.get_all_reminders()
        reminders.pop(selection[0])
        self.save_reminders(reminders)
        self.load_reminders()

# ---------------- NOTES ---------------- #
class NotesWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Notes / Journal")
        self.geometry("500x400")
        self.configure(bg="#222831")
        self.font_header = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Consolas", size=11)
        tk.Label(self, text="Your Notes / Journal", font=self.font_header, fg="#00ffd5", bg="#222831").pack(pady=10)
        self.textbox = tk.Text(self, font=self.font_normal, width=60, height=18, bg="#eeeeee", fg="#222831")
        self.textbox.pack(padx=12, pady=5, fill="both", expand=True)
        btn_frame = tk.Frame(self, bg="#222831")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Save", command=self.save_notes, bg="#00adb5", fg="white", width=10).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Load", command=self.load_notes, bg="#393e46", fg="white", width=10).grid(row=0, column=1, padx=5)
        self.load_notes()

    def save_notes(self):
        try:
            with open("notes.txt", "w", encoding="utf-8") as f:
                f.write(self.textbox.get("1.0", tk.END))
            messagebox.showinfo("Notes", "Notes saved!")
        except:
            messagebox.showerror("Error", "Could not save notes.")

    def load_notes(self):
        if os.path.exists("notes.txt"):
            try:
                with open("notes.txt", "r", encoding="utf-8") as f:
                    self.textbox.delete("1.0", tk.END)
                    self.textbox.insert("1.0", f.read())
            except:
                messagebox.showerror("Error", "Could not load notes.")

# ---------------- WEATHER ---------------- #
class WeatherWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Weather")
        self.geometry("400x300")
        self.configure(bg="#222831")
        self.font_header = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=11)
        tk.Label(self, text="Weather Information", font=self.font_header, fg="#00ffd5", bg="#222831").pack(pady=10)
        self.city_entry = tk.Entry(self, font=self.font_normal, width=25)
        self.city_entry.pack(pady=5)
        self.city_entry.insert(0, "Enter city name")
        tk.Button(self, text="Get Weather", command=self.get_weather, bg="#00adb5", fg="white", width=15).pack(pady=5)
        self.result_label = tk.Label(self, text="", font=self.font_normal, fg="white", bg="#222831", justify="left")
        self.result_label.pack(pady=10)
        self.api_key = "1efd250cd8ab53a92d1faf7eccbfb560"

    def get_weather(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name.")
            return
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
            data = requests.get(url).json()
            if data.get("cod") != 200:
                messagebox.showerror("Error", data.get("message", "Unable to get weather."))
                return
            report = (
                f"City: {city}\n"
                f"Weather: {data['weather'][0]['description'].title()}\n"
                f"Temperature: {data['main']['temp']}°C\n"
                f"Feels Like: {data['main']['feels_like']}°C\n"
                f"Humidity: {data['main']['humidity']}%\n"
                f"Wind Speed: {data['wind']['speed']} m/s"
            )
            self.result_label.config(text=report)
        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch weather: {e}")

# ---------------- NEWS ---------------- #
class NewsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("News Headlines")
        self.geometry("600x400")
        self.configure(bg="#222831")
        self.font_header = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=11)
        self.news_api_key = "2f8126d7ec754d839a66ed954343ccef"
        tk.Label(self, text="Top News Headlines", font=self.font_header, fg="#00ffd5", bg="#222831").pack(pady=10)
        search_frame = tk.Frame(self, bg="#222831")
        search_frame.pack()
        self.country_var = tk.StringVar(value="in")
        tk.Label(search_frame, text="Country code:", font=self.font_normal, fg="white", bg="#222831").grid(row=0, column=0)
        self.country_entry = tk.Entry(search_frame, textvariable=self.country_var, font=self.font_normal, width=6)
        self.country_entry.grid(row=0, column=1)
        tk.Button(search_frame, text="Get Headlines", command=self.get_headlines, bg="#00adb5", fg="white", width=15).grid(row=0, column=2, padx=10)
        self.news_list = tk.Listbox(self, font=self.font_normal, width=80, height=15, cursor="hand2")
        self.news_list.pack(padx=10, pady=10)
        self.news_links = []
        self.news_list.bind("<Double-Button-1>", self.open_link)
        self.get_headlines()

    def get_headlines(self):
        country = self.country_var.get().strip().lower()
        url = f"https://newsapi.org/v2/top-headlines?country={country}&pageSize=20&apiKey={self.news_api_key}"
        try:
            data = requests.get(url).json()
            self.news_list.delete(0, tk.END)
            self.news_links = []
            if data.get("status") != "ok":
                messagebox.showerror("Error", data.get("message", "Failed to fetch news."))
                return
            articles = data.get("articles", [])
            if not articles:
                self.news_list.insert(tk.END, f"No news found for '{country.upper()}'.")
                return
            for article in articles:
                title = article.get("title", "No title")
                source = article.get("source", {}).get("name", "")
                self.news_list.insert(tk.END, f"{title} ({source})" if source else title)
                self.news_links.append(article.get("url", ""))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch news: {e}")

    def open_link(self, event):
        idxs = self.news_list.curselection()
        if idxs:
            url = self.news_links[idxs[0]]
            if url:
                webbrowser.open(url)

# ---------------- EMAIL ---------------- #
class EmailWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("AI Email Sender")
        self.geometry("500x300")
        self.configure(bg="#222831")
        self.font_header = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=11)
        tk.Label(self, text="Send an AI-Powered Email", font=self.font_header, fg="#00ffd5", bg="#222831").pack(pady=10)
        tk.Label(self, text="Recipient Email:", bg="#222831", fg="white", font=self.font_normal).pack()
        self.recipient_entry = tk.Entry(self, font=self.font_normal, width=40)
        self.recipient_entry.pack(pady=5)
        tk.Label(self, text="Subject:", bg="#222831", fg="white", font=self.font_normal).pack()
        self.subject_entry = tk.Entry(self, font=self.font_normal, width=40)
        self.subject_entry.pack(pady=5)
        tk.Label(self, text="Short Note:", bg="#222831", fg="white", font=self.font_normal).pack()
        self.body_entry = tk.Text(self, font=self.font_normal, width=45, height=5)
        self.body_entry.pack(pady=5)
        tk.Button(self, text="Send Email", command=self.send_ai_email, bg="#00adb5", fg="white", width=15).pack(pady=10)

    def send_ai_email(self):
        to_email = self.recipient_entry.get().strip()
        subject = self.subject_entry.get().strip()
        note = self.body_entry.get("1.0", tk.END).strip()
        if not to_email or not subject or not note:
            messagebox.showerror("Error", "Please fill all fields.")
            return
        send_email(to_email, subject, note)

# ---------------- MAIN APP ---------------- #
class PersonalAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Assistant")
        self.configure(bg="#222831")
        self.geometry("500x550")
        self.header_font = font.Font(family="Helvetica", size=20, weight="bold")
        self.button_font = font.Font(family="Helvetica", size=12, weight="bold")
        tk.Label(self, text="Personal Assistant", font=self.header_font, fg="#00ffd5", bg="#222831").pack(pady=(20, 10))
        btn_frame = tk.Frame(self, bg="#393e46")
        btn_frame.pack(pady=(0, 20), fill="x", padx=40)
        btn_params = {
            "master": btn_frame, "font": self.button_font, "fg": "white",
            "bg": "#00adb5", "activebackground": "#007f8e", "activeforeground": "white",
            "bd": 0, "relief": "flat", "cursor": "hand2", "width": 20, "height": 2
        }
        tk.Button(text="Open Calendar Assistant", command=self.open_calendar, **btn_params).grid(row=0, column=0, pady=5)
        tk.Button(text="Reminders / To-Do", command=self.reminders_feature, **btn_params).grid(row=1, column=0, pady=5)
        tk.Button(text="Notes / Journal", command=self.notes_feature, **btn_params).grid(row=2, column=0, pady=5)
        tk.Button(text="Weather", command=self.weather_feature, **btn_params).grid(row=3, column=0, pady=5)
        tk.Button(text="News Headlines", command=self.news_feature, **btn_params).grid(row=4, column=0, pady=5)
        tk.Button(text="AI Email", command=self.email_feature, **btn_params).grid(row=5, column=0, pady=5)

    def open_calendar(self):
        try:
            subprocess.Popen([sys.executable, "calendar_gui.py"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Calendar Assistant: {e}")

    def reminders_feature(self):
        RemindersWindow(self)

    def notes_feature(self):
        NotesWindow(self)

    def weather_feature(self):
        WeatherWindow(self)

    def news_feature(self):
        NewsWindow(self)

    def email_feature(self):
        EmailWindow(self)

# ---------------- RUN APP ---------------- #
if __name__ == "__main__":
    app = PersonalAssistant()
    app.mainloop()

