import tkinter as tk
from tkinter import font, messagebox, simpledialog
import subprocess
import sys
import json
import os
import requests
import webbrowser   # NEW: for opening news links

# ------------------- REMINDERS WINDOW ------------------- #
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
        tk.Button(btn_frame, text="Add",
                  command=self.add_reminder, bg="#00adb5", fg="white", width=10).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Delete",
                  command=self.delete_reminder, bg="#ff5722", fg="white", width=10).grid(row=0, column=1, padx=5)

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
        idx = selection[0]
        reminders = self.get_all_reminders()
        reminders.pop(idx)
        self.save_reminders(reminders)
        self.load_reminders()

# ------------------- NOTES WINDOW ------------------- #
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
        text = self.textbox.get("1.0", tk.END)
        try:
            with open("notes.txt", "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Notes", "Notes saved!")
        except:
            messagebox.showerror("Error", "Could not save notes.")

    def load_notes(self):
        if os.path.exists("notes.txt"):
            try:
                with open("notes.txt", "r", encoding="utf-8") as f:
                    notes = f.read()
                self.textbox.delete("1.0", tk.END)
                self.textbox.insert("1.0", notes)
            except:
                messagebox.showerror("Error", "Could not load notes.")
        else:
            self.textbox.delete("1.0", tk.END)
            self.textbox.insert("1.0", "")

# ------------------- WEATHER WINDOW ------------------- #
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

        self.api_key = "1efd250cd8ab53a92d1faf7eccbfb560"  # <-- Your OpenWeatherMap API key

    def get_weather(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name.")
            return
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
            response = requests.get(url)
            data = response.json()
            if data.get("cod") != 200:
                messagebox.showerror("Error", data.get("message", "Unable to get weather."))
                return
            weather = data["weather"][0]["description"].title()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            report = (
                f"City: {city}\n"
                f"Weather: {weather}\n"
                f"Temperature: {temp}°C\n"
                f"Feels Like: {feels_like}°C\n"
                f"Humidity: {humidity}%\n"
                f"Wind Speed: {wind_speed} m/s"
            )
            self.result_label.config(text=report)
        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch weather: {e}")

# ------------------- NEWS WINDOW ------------------- #
class NewsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("News Headlines")
        self.geometry("600x400")
        self.configure(bg="#222831")

        self.font_header = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_normal = font.Font(family="Helvetica", size=11)
        self.news_api_key = "2f8126d7ec754d839a66ed954343ccef"  # <-- Your NewsAPI.org API key

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
            resp = requests.get(url)
            data = resp.json()
            self.news_list.delete(0, tk.END)
            self.news_links = []
            if data.get("status") != "ok":
                messagebox.showerror("Error", data.get("message", "Failed to fetch news."))
                return
            articles = data.get("articles", [])
            if not articles:
                self.news_list.insert(tk.END, f"No news found for '{country.upper()}' right now.")
                return
            for article in articles:
                headline = article.get("title", "No title")
                source = article.get("source", {}).get("name", "")
                display = headline if not source else f"{headline} ({source})"
                self.news_list.insert(tk.END, display)
                self.news_links.append(article.get("url", ""))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch news: {e}")

    def open_link(self, event):
        idxs = self.news_list.curselection()
        if not idxs:
            return
        link = self.news_links[idxs[0]]
        if link:
            webbrowser.open(link)

# ------------------- MAIN PERSONAL ASSISTANT ------------------- #
class PersonalAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Assistant")
        self.configure(bg="#222831")

        window_width = 500
        window_height = 500
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.resizable(False, False)

        self.header_font = font.Font(family="Helvetica", size=20, weight="bold")
        self.button_font = font.Font(family="Helvetica", size=12, weight="bold")

        header = tk.Label(self, text="Personal Assistant", font=self.header_font, fg="#00ffd5", bg="#222831")
        header.pack(pady=(20, 10))

        btn_frame = tk.Frame(self, bg="#393e46")
        btn_frame.pack(pady=(0, 20), fill="x", padx=40)

        btn_params = {
            "master": btn_frame,
            "font": self.button_font,
            "fg": "white",
            "bg": "#00adb5",
            "activebackground": "#007f8e",
            "activeforeground": "white",
            "bd": 0,
            "relief": "flat",
            "cursor": "hand2",
            "width": 18,
            "height": 2
        }

        calendar_btn = tk.Button(text="Open Calendar Assistant", command=self.open_calendar, **btn_params)
        reminders_btn = tk.Button(text="Reminders / To-Do", command=self.reminders_feature, **btn_params)
        notes_btn = tk.Button(text="Notes / Journal", command=self.notes_feature, **btn_params)
        weather_btn = tk.Button(text="Weather", command=self.weather_feature, **btn_params)
        news_btn = tk.Button(text="News Headlines", command=self.news_feature, **btn_params)

        calendar_btn.grid(row=0, column=0, padx=10, pady=10, columnspan=2)
        reminders_btn.grid(row=1, column=0, padx=10, pady=10, columnspan=2)
        notes_btn.grid(row=2, column=0, padx=10, pady=10, columnspan=2)
        weather_btn.grid(row=3, column=0, padx=10, pady=10, columnspan=2)
        news_btn.grid(row=4, column=0, padx=10, pady=10, columnspan=2)

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

# ------------------- MAIN ENTRY ------------------- #
if __name__ == "__main__":
    app = PersonalAssistant()
    app.mainloop()
