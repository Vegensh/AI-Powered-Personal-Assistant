from __future__ import absolute_import, print_function
import os.path
import base64
import pickle
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import google.generativeai as genai  # Gemini API

# ==== CONFIG ====
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
GEMINI_API_KEY = "Your API Key"  # Your Gemini API key

# ---------------- Gmail API Authentication ---------------- #
def get_gmail_service():
    """Authenticate and return a Gmail API service instance."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"Error creating Gmail service: {e}")
        return None

# ---------------- Gemini AI Formatter ---------------- #
def ai_format_email(subject, user_draft):
    """Use Gemini API to rewrite the subject + note into a professional email."""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are an expert email writer. "
            "Given the subject and a short user note, rewrite them into a complete, polite, professional email "
            "with a greeting, clear body, and closing. "
            "Preserve the meaning and ensure it matches the subject context.\n\n"
            f"Subject: {subject}\n"
            f"User Note: {user_draft}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠ Gemini API error: {e}")
        # Fallback to a simple format if AI fails
        return f"Subject: {subject}\n\nHello,\n\n{user_draft}\n\nBest regards,\nYour Personal Assistant"

# ---------------- Gmail Email Creation ---------------- #
def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

# ---------------- Gmail Send Email ---------------- #
def send_email(to_email, subject, user_draft):
    service = get_gmail_service()
    if not service:
        print("Failed to initialize Gmail service.")
        return

    final_body = ai_format_email(subject, user_draft)  # AI formats with full context
    message = create_message("me", to_email, subject, final_body)

    try:
        sent = service.users().messages().send(userId="me", body=message).execute()
        print(f"✅ Email sent successfully to {to_email}")
        print("\n------ Email Content Sent ------\n")
        print(final_body)
    except Exception as e:
        print(f"❌ An error occurred: {e}")

# ---------------- Main ---------------- #
if __name__ == '__main__':
    recipient = input("Enter recipient Gmail address: ").strip()
    subject = input("Enter email subject: ").strip()
    note = input("Enter your short note (no greeting needed): ").strip()

    send_email(recipient, subject, note)

