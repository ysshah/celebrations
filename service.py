from os import environ
import sys
from copy import deepcopy
from datetime import datetime

from googleapiclient.discovery import build

from auth import get_credentials

credentials = get_credentials()
PEOPLE_SERVICE = build('people', 'v1', credentials=credentials)
CALENDAR_SERVICE = build('calendar', 'v3', credentials=credentials)
CALENDAR_ID = environ['CALENDAR_ID']
DRY_RUN = len(sys.argv) > 1 and sys.argv[1] == '--dry-run'

def _get_connections():
  return PEOPLE_SERVICE.people().connections().list(
      resourceName='people/me',
      personFields='names,birthdays,events,addresses,phoneNumbers',
      pageSize=2000).execute()['connections']

def _get_name(connection):
  return connection['names'][0]['displayName']

def _indian(connection):
  for address in connection.get('addresses', []):
    if address['type'] == 'home' and 'country' in address and address['country'] in {'India', 'IN'}:
      return True
  return False

def _parse(events, event, connection):
  if 'type' not in event or event['type'] == 'anniversary':
    name = _get_name(connection)
    event_type = event.get('type', 'birthday')
    if 'date' not in event:
      raise RuntimeError(f'{name} does not have a formatted date for their {event_type}')
    events[f"{name}'s {event_type}"] = (name, event_type, event['date'], _indian(connection))

def _set_reminders(event, indian):
  event['reminders'] = {
    'useDefault': False,
    'overrides': [{
      # 12h 30m before midnight if Indian
      'minutes': 750 if indian else 0,
      'method': 'popup',
    }],
  }

def people_events():
  events = {}
  for connection in _get_connections():
    for event_type in ['birthdays', 'events']:
      if event_type in connection:
        _parse(events, connection[event_type][0], connection)
  return events

def execute(http_request):
  if not DRY_RUN:
    http_request.execute()

def calendar_events():
  return CALENDAR_SERVICE.events().list(calendarId=CALENDAR_ID, maxResults=2500).execute().get('items', [])

def get_instances(eventId):
  return CALENDAR_SERVICE.events().instances(calendarId=CALENDAR_ID, eventId=eventId).execute().get('items', [])

def validate(event, name, event_type, event_date, indian):
  updated = deepcopy(event)
  _set_reminders(updated, indian)
  if updated != event:
    print('Updating', event['summary'])
    return execute(CALENDAR_SERVICE.events().update(calendarId=CALENDAR_ID, eventId=updated['id'], body=updated))

def delete(eventId):
  return execute(CALENDAR_SERVICE.events().delete(calendarId=CALENDAR_ID, eventId=eventId))

def update_instance(instance):
  return CALENDAR_SERVICE.events().update(calendarId=CALENDAR_ID, eventId=instance['id'], body=instance).execute()

def insert(summary, name, event_type, event_date, indian):
  date = f'{datetime.now().year}-{event_date["month"]:02}-{event_date["day"]:02}'
  print(f'Inserting "{summary}" [indian = {indian}] at {date}')
  body = {
    'summary': summary,
    'start': { 'date': date, 'timeZone': 'America/Los_Angeles' },
    'end': { 'date': date, 'timeZone': 'America/Los_Angeles' },
    'recurrence': ['RRULE:FREQ=YEARLY'],
  }
  if 'year' in event_date:
    body['description'] = str(event_date['year'])
  _set_reminders(body, indian)
  execute(CALENDAR_SERVICE.events().insert(calendarId=CALENDAR_ID, body=body))

if __name__ == '__main__':
  names_without_birthdays = [_get_name(c) for c in _get_connections() if 'birthdays' not in c]
  print(len(names_without_birthdays), 'contacts without birthdays:')
  for name in names_without_birthdays:
    print('-', name)
