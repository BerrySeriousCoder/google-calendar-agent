import datetime
from typing import List, Optional
from googleapiclient.discovery import Resource

def get_availability(service: Resource, start: str, end: str) -> bool:
    """Check if the time slot is available."""
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return len(events) == 0

def create_event(service: Resource, summary: str, start: str, end: str, attendees: Optional[List[str]] = None, description: str = "") -> dict:
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

def update_event(service: Resource, event_id: str, new_values: dict) -> dict:
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    event.update(new_values)
    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    return updated_event

def delete_event(service, event_id):
    """Deletes an event from the primary calendar."""
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return f"Event with ID {event_id} deleted successfully."
    except Exception as e:
        return f"An error occurred: {e}"

def search_events(service, query: str, max_results: int = 10):
    """Searches for events matching the query."""
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    try:
        events_result = service.events().list(
            calendarId='primary',
            q=query,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        if not events:
            return f"No upcoming events found matching query: '{query}'"
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append(f"ID: {event['id']}, Summary: {event['summary']}, Start: {start}")
        return "\n".join(event_list)
    except Exception as e:
        return f"An error occurred while searching for events: {e}"

def list_events(service: Resource, start_time_str: str, end_time_str: str):
    """Lists events from the primary calendar within the specified time range."""
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
