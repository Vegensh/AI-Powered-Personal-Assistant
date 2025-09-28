from datetime import datetime, timedelta, timezone
import pytz
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def help_command():
    print("Available commands:")
    print("  today   - Show your daily plan")
    print("  add     - Add a new event")
    print("  list    - List your events for today with numbers")
    print("  delete  - Delete an event by its number (usage: delete 2)")
    print("  exit    - Quit the assistant")
    print("  help    - Show this help message")

def input_date():
    while True:
        date_str = input("Enter date (YYYY-MM-DD): ")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            print("Invalid date format. Please enter as YYYY-MM-DD.")

def input_time():
    while True:
        time_str = input("Enter time (HH:MM, 24hr): ")
        try:
            datetime.strptime(time_str, "%H:%M")
            return time_str
        except ValueError:
            print("Invalid time format. Please enter as HH:MM (24hr).")

def get_todays_events(service):
    tz = pytz.timezone('Asia/Kolkata')  # Change to your timezone if needed

    now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    timeMin = today_start.isoformat()
    timeMax = today_end.isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=timeMin,
        timeMax=timeMax,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])

    meal_times = {
        "Breakfast": tz.localize(datetime.combine(today_start.date(), datetime.strptime("07:00", "%H:%M").time())),
        "Lunch": tz.localize(datetime.combine(today_start.date(), datetime.strptime("13:00", "%H:%M").time())),
        "Dinner": tz.localize(datetime.combine(today_start.date(), datetime.strptime("20:00", "%H:%M").time())),
    }

    event_hours = []
    parsed_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        try:
            event_dt = datetime.fromisoformat(start)
            parsed_events.append(("Event: " + event.get('summary', 'No Title'), event_dt))
            event_hours.append(event_dt.hour)
        except Exception:
            continue

    adjusted_meals = {}
    for meal, dt in meal_times.items():
        if dt.hour in event_hours:
            dt = dt + timedelta(hours=1)
        adjusted_meals[meal] = dt

    schedule = [
        ("Breakfast", adjusted_meals["Breakfast"]),
        ("Lunch", adjusted_meals["Lunch"]),
        ("Dinner", adjusted_meals["Dinner"])
    ] + parsed_events

    schedule_sorted = sorted(schedule, key=lambda x: x[1])

    print("Today's plan:")
    for name, time in schedule_sorted:
        print(f"- {name} at {time.strftime('%I:%M %p %Z')}")

def add_event(service):
    title = input("Event title: ")
    date_str = input_date()
    time_str = input_time()
    duration_str = input("Duration in minutes (default 60): ").strip()
    try:
        duration_minutes = int(duration_str) if duration_str else 60
    except ValueError:
        duration_minutes = 60

    try:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        event = {
            'summary': title,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event added: {created_event.get('htmlLink', 'Success')}")
    except Exception as e:
        print("Failed to add event. Please check your input format.")
        print(e)

def list_events(service):
    tz = pytz.timezone('Asia/Kolkata')  # Use your timezone if different

    now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    timeMin = today_start.isoformat()
    timeMax = today_end.isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=timeMin,
        timeMax=timeMax,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])

    if not events:
        print("No events found for today.")
        return []

    print("Today's events:")
    for i, event in enumerate(events, start=1):
        start = event["start"].get("dateTime", event["start"].get("date"))
        try:
            event_time = datetime.fromisoformat(start).strftime("%I:%M %p")
        except Exception:
            event_time = start
        summary = event.get("summary", "No Title")
        print(f"{i}. {summary} at {event_time}")
    return events

def delete_event(service, events, number_str):
    try:
        number = int(number_str)
        if number < 1 or number > len(events):
            print("Invalid event number.")
            return
        event_id = events[number - 1]["id"]
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        print("Event deleted successfully.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        print("Failed to delete event:", e)

def command_loop(service):
    print("Welcome to your AI assistant. Type 'help' for commands.")
    events_cache = []
    while True:
        cmd = input("Enter command: ").strip().lower()
        if cmd == 'help':
            help_command()
        elif cmd == 'today':
            get_todays_events(service)
        elif cmd == 'add':
            add_event(service)
        elif cmd == 'list':
            events_cache = list_events(service)
        elif cmd.startswith('delete'):
            parts = cmd.split()
            if len(parts) == 2:
                delete_event(service, events_cache, parts[1])
                events_cache = list_events(service)
            else:
                print("Usage: delete <event_number>")
        elif cmd == 'exit':
            print("Goodbye.")
            break
        else:
            print("Unknown command. Type 'help' for available commands.")

def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow().isoformat() + "Z"
        print("Getting the upcoming 10 events")
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
        else:
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                summary = event.get("summary", "No Title")
                print(f"{start}: {summary}")

        print("\n")

        command_loop(service)

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()
