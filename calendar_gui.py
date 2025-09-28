import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, font
from datetime import datetime, timedelta, timezone
import pytz
import os.path
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def find_next_free_time(default_time, events, duration_minutes=30):
    meal_time = default_time
    meal_end = meal_time + timedelta(minutes=duration_minutes)
    while True:
        latest_overlap_end = None
        for ev_start, ev_end in events:
            if (meal_time < ev_end) and (meal_end > ev_start):
                if not latest_overlap_end or ev_end > latest_overlap_end:
                    latest_overlap_end = ev_end
        if latest_overlap_end:
            meal_time = latest_overlap_end + timedelta(minutes=5)
            meal_end = meal_time + timedelta(minutes=duration_minutes)
        else:
            break
    return meal_time

class AddEventDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Title:").grid(row=0)
        tk.Label(master, text="Date (YYYY-MM-DD):").grid(row=1)
        tk.Label(master, text="Start Time (HH:MM 24hr):").grid(row=2)
        tk.Label(master, text="Duration (minutes):").grid(row=3)

        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master)
        self.e3 = tk.Entry(master)
        self.e4 = tk.Entry(master)

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        self.e4.grid(row=3, column=1)
        self.e4.insert(0, "60")
        return self.e1

    def apply(self):
        self.result = (
            self.e1.get().strip(),
            self.e2.get().strip(),
            self.e3.get().strip(),
            self.e4.get().strip()
        )

class CalendarApp(tk.Tk):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.title("AI Calendar Assistant")
        window_width = 600
        window_height = 600
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.resizable(False, False)

        self.header_font = font.Font(family="Helvetica", size=20, weight="bold")
        self.button_font = font.Font(family="Helvetica", size=12, weight="bold")
        self.output_font = font.Font(family="Consolas", size=11)
        self.configure(bg="#222831")

        header = tk.Label(self, text="AI Calendar Assistant", font=self.header_font, fg="#00ffd5", bg="#222831")
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
            "width": 15,
            "height": 2
        }
        btn_today = tk.Button(text="Today's Plan", command=self.show_todays_plan, **btn_params)
        btn_add = tk.Button(text="Add Event", command=self.add_event_gui, **btn_params)
        btn_list = tk.Button(text="List Events", command=self.list_events_gui, **btn_params)
        btn_delete = tk.Button(text="Delete Event", command=self.delete_event_gui, **btn_params)
        btn_pick = tk.Button(text="Pick Date", command=self.choose_date_gui, **btn_params)
        btn_help = tk.Button(text="Help", command=self.show_help, **btn_params)
        btn_today.grid(row=0, column=0, padx=10, pady=10)
        btn_add.grid(row=0, column=1, padx=10, pady=10)
        btn_list.grid(row=1, column=0, padx=10, pady=10)
        btn_delete.grid(row=1, column=1, padx=10, pady=10)
        btn_pick.grid(row=2, column=0, padx=10, pady=10)
        btn_help.grid(row=2, column=1, padx=10, pady=10)

        self.output = scrolledtext.ScrolledText(self, width=70, height=20, font=self.output_font,
                                                bg="#eeeeee", fg="#222831", relief="sunken", bd=2)
        self.output.pack(padx=20, pady=10, fill="both", expand=True)
        self.events_cache = []
        self.cache_date = None

    def show_output(self, text):
        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, text)

    def show_help(self):
        help_text = (
            "Available actions:\n"
            "Today's Plan - Smart schedule of meals and events for today\n"
            "Add Event - Add a new event to Google Calendar\n"
            "List Events - List today's events for delete\n"
            "Delete Event - Delete an event by its number from last shown event list\n"
            "Pick Date - View & delete events on any chosen date\n"
            "Help - Show this help message\n"
            "Exit - Close the application\n"
        )
        self.show_output(help_text)

    def get_plan_msg(self, date_obj):
        try:
            tz = pytz.timezone('Asia/Kolkata')
            day_start = tz.localize(datetime.combine(date_obj, datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            timeMin = day_start.isoformat()
            timeMax = day_end.isoformat()
            results = self.service.events().list(
                calendarId="primary",
                timeMin=timeMin,
                timeMax=timeMax,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = results.get("items", [])
            event_periods = []
            event_descript = []
            for event in events:
                start = event['start'].get('dateTime')
                end = event['end'].get('dateTime')
                summary = event.get('summary', 'No Title')
                if start and end:
                    sdt = datetime.fromisoformat(start)
                    edt = datetime.fromisoformat(end)
                    event_periods.append( (sdt, edt) )
                    event_descript.append( ("Event: " + summary, sdt) )
            meal_starts = {
                "Breakfast": tz.localize(datetime.combine(date_obj, datetime.strptime("07:00", "%H:%M").time())),
                "Lunch": tz.localize(datetime.combine(date_obj, datetime.strptime("13:00", "%H:%M").time())),
                "Dinner": tz.localize(datetime.combine(date_obj, datetime.strptime("20:00", "%H:%M").time())),
            }
            adjusted_meals = {}
            for meal, start_time in meal_starts.items():
                adjusted_meal_time = find_next_free_time(start_time, event_periods, duration_minutes=30)
                adjusted_meals[meal] = adjusted_meal_time
            schedule = [
                ("Breakfast", adjusted_meals["Breakfast"]),
                ("Lunch", adjusted_meals["Lunch"]),
                ("Dinner", adjusted_meals["Dinner"])
            ] + event_descript
            schedule_sorted = sorted(schedule, key=lambda x: x[1])
            lines = [f"Plan for {date_obj.strftime('%Y-%m-%d')}:\n"]
            for name, time in schedule_sorted:
                lines.append(f"- {name} at {time.strftime('%I:%M %p %Z')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving plan: {e}"

    def show_todays_plan(self):
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz)
        today = now.date()
        msg = self.get_plan_msg(today)
        events_msg, events = self.list_events_msg(today, return_list=True)
        self.events_cache = events
        self.cache_date = today
        self.show_output(msg + "\n\n" + events_msg)

    def choose_date_gui(self):
        date_str = simpledialog.askstring("Pick Date", "Enter date (YYYY-MM-DD):")
        if not date_str:
            return
        if not re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            messagebox.showerror("Pick Date", "Invalid date format. Please use YYYY-MM-DD.")
            return
        try:
            chosen_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            messagebox.showerror("Pick Date", "Invalid date.")
            return
        plan_msg = self.get_plan_msg(chosen_date)
        events_msg, events = self.list_events_msg(chosen_date, return_list=True)
        self.events_cache = events
        self.cache_date = chosen_date
        self.show_output(plan_msg + "\n\n" + events_msg)

    def list_events_gui(self):
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz)
        today = now.date()
        msg, events = self.list_events_msg(today, return_list=True)
        self.show_output(msg)
        self.events_cache = events
        self.cache_date = today

    def list_events_msg(self, date_obj, return_list=False):
        try:
            tz = pytz.timezone('Asia/Kolkata')
            start_dt = tz.localize(datetime.combine(date_obj, datetime.min.time()))
            end_dt = start_dt + timedelta(days=1)
            timeMin = start_dt.isoformat()
            timeMax = end_dt.isoformat()
            results = self.service.events().list(
                calendarId="primary",
                timeMin=timeMin,
                timeMax=timeMax,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = results.get("items", [])
            if not events:
                msg = f"No events found for {date_obj.strftime('%Y-%m-%d')}."
                return (msg, []) if return_list else msg
            lines = [f"Events for {date_obj.strftime('%Y-%m-%d')}:\n"]
            for i, event in enumerate(events, start=1):
                start = event["start"].get("dateTime", event["start"].get("date"))
                try:
                    event_time = datetime.fromisoformat(start).strftime("%I:%M %p")
                except Exception:
                    event_time = start
                summary = event.get("summary", "No Title")
                lines.append(f"{i}. {summary} at {event_time}")
            return ( "\n".join(lines), events ) if return_list else "\n".join(lines)
        except Exception as e:
            msg = f"Failed to list events: {e}"
            return (msg, []) if return_list else msg

    def delete_event_gui(self):
        if not self.events_cache:
            messagebox.showinfo("Delete Event", "No events cached. Use 'List Events', 'Today's Plan', or 'Pick Date' first.")
            return
        number_str = simpledialog.askstring("Delete Event", "Enter the event number to delete:")
        if number_str is None:
            return
        try:
            number = int(number_str)
            if number < 1 or number > len(self.events_cache):
                messagebox.showerror("Delete Event", "Invalid event number.")
                return
            event_id = self.events_cache[number - 1]["id"]
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            messagebox.showinfo("Delete Event", "Event deleted successfully.")
            # Refresh cache and output after delete
            date_to_refresh = self.cache_date if self.cache_date else datetime.now().date()
            plan_msg = self.get_plan_msg(date_to_refresh)
            events_msg, events = self.list_events_msg(date_to_refresh, return_list=True)
            self.events_cache = events
            self.cache_date = date_to_refresh
            self.show_output(plan_msg + "\n\n" + events_msg)
        except ValueError:
            messagebox.showerror("Delete Event", "Please enter a valid number.")
        except Exception as e:
            messagebox.showerror("Delete Event", f"Failed: {e}")

    def add_event_gui(self):
        dlg = AddEventDialog(self, title="Add Event")
        if dlg.result:
            title, date_str, time_str, duration_str = dlg.result
            if not title or not date_str or not time_str:
                messagebox.showerror("Add Event", "All fields are required.")
                return
            try:
                start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            except Exception:
                messagebox.showerror("Add Event", "Invalid date or time format.")
                return
            try:
                duration = int(duration_str) if duration_str.isdigit() else 60
            except Exception:
                duration = 60
            end_dt = start_dt + timedelta(minutes=duration)
            try:
                event = {
                    'summary': title,
                    'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
                    'end':   {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
                }
                created_event = self.service.events().insert(calendarId='primary', body=event).execute()
                messagebox.showinfo("Add Event", f"Event added: {created_event.get('htmlLink', 'Success')}")
            except Exception as e:
                messagebox.showerror("Add Event", f"Failed to add event: {e}")

def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print("Failed to refresh token:", e)
                creds = None
        if not creds or not creds.valid:
            if os.path.exists("token.json"):
                os.remove("token.json")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token_file:
                token_file.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        app = CalendarApp(service)
        app.show_help()
        app.mainloop()
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()
