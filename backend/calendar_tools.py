from typing import List, Optional
from .oauth import get_google_calendar_service

def get_availability(start: str, end: str) -> bool:
    """Check if the time slot is available."""
    service = get_google_calendar_service()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return len(events) == 0

def create_event(summary: str, start: str, end: str, attendees: Optional[List[str]] = None, description: str = "") -> dict:
    service = get_google_calendar_service()
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start, 'timeZone': 'UTC'},
        'end': {'dateTime': end, 'timeZone': 'UTC'},
    }
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

def update_event(event_id: str, new_values: dict) -> dict:
    service = get_google_calendar_service()
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    event.update(new_values)
    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    return updated_event

def delete_event(event_id: str):
    service = get_google_calendar_service()
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    return True

def list_events(start_time_str: str, end_time_str: str):
    """Lists events from the primary calendar within the specified time range."""
    service = get_google_calendar_service()

    # Ensure timestamps are in RFC3339 format (what Google API expects)
    # Add 'Z' for UTC if no timezone is specified.
    if 'Z' not in start_time_str and '+' not in start_time_str and '-' not in start_time_str[10:]:
        start_time_str += 'Z'
    if 'Z' not in end_time_str and '+' not in end_time_str and '-' not in end_time_str[10:]:
        end_time_str += 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_time_str,
        timeMax=end_time_str,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])
