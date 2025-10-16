import datetime
import os
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(SCRIPT_DIR, 'token.json')
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, 'credentials.json')


def get_calendar_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_console()
        # Save the credentials for the next run
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def list_events(max_results=10):
    """Lists the next events on the user's calendar."""
    service = get_calendar_service()
    if service:
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return {"events": "No upcoming events found."}

        # Collects the start and name of the next events into a list
        event_summaries = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_summaries.append(f"{start} {event['summary']}")
        return {"events": "\n".join(event_summaries)}

def add_event(summary, start_time, end_time, location=None, description=None, attendees=None):
    """Adds an event to the user's calendar."""
    service = get_calendar_service()
    if service:
        event = {
            'summary': summary,
            'location': location if location else '',
            'description': description if description else '',
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Los_Angeles',
            },
            'attendees': attendees if attendees else [],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return {"status": "Event created", "link": event.get('htmlLink')}

def update_event(event_id, summary, start_time, end_time, location=None, description=None, attendees=None):
    """Updates an event on the user's calendar."""
    service = get_calendar_service()
    if service:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        event['summary'] = summary
        event['location'] = location if location else ''
        event['description'] = description if description else ''
        event['start']['dateTime'] = start_time
        event['end']['dateTime'] = end_time
        event['attendees'] = attendees if attendees else []

        updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
        return {"status": "Event updated", "link": updated_event.get('htmlLink')}

def delete_event(event_id):
    """Deletes an event from the user's calendar."""
    service = get_calendar_service()
    if service:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"status": "Event deleted"}

def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "list_events",
                "description": "Lists upcoming events from the user's primary Google Calendar, ordered by start time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "The maximum number of events to return.",
                        }
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_event",
                "description": "Adds a new event to the user's primary Google Calendar. Requires a summary (title), start time, and end time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "The summary or title of the event."},
                        "location": {"type": "string", "description": "The location of the event."},
                        "description": {"type": "string", "description": "A description of the event."},
                        "start_time": {"type": "string", "description": "The start time of the event in ISO 8601 format (e.g., '2025-08-31T10:00:00-07:00')."},
                        "end_time": {"type": "string", "description": "The end time of the event in ISO 8601 format (e.g., '2025-08-31T11:00:00-07:00')."},
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "A list of attendee email addresses.",
                        },
                    },
                    "required": ["summary", "start_time", "end_time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_event",
                "description": "Updates an existing event on the user's primary Google Calendar. Requires the event ID and the new details for the event.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "The ID of a given event to update."}, 
                        "summary": {"type": "string", "description": "The new summary or title of the event."},
                        "location": {"type": "string", "description": "The new location of the event."},
                        "description": {"type": "string", "description": "The new description of the event."},
                        "start_time": {"type": "string", "description": "The new start time of the event in ISO 8601 format."},
                        "end_time": {"type": "string", "description": "The new end time of the event in ISO 8601 format."},
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The new list of attendee email addresses.",
                        },
                    },
                    "required": ["event_id", "summary", "start_time", "end_time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_event",
                "description": "Deletes an event from the user's primary Google Calendar, given an event ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "The ID of the event to delete."} 
                    },
                    "required": ["event_id"],
                },
            },
        }
    ]
