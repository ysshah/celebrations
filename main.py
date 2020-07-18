import service

def main():
  calendar_events = {event['summary']: event for event in service.calendar_events()}
  people_events = service.people_events()
  for summary, data in people_events.items():
    if summary in calendar_events:
      print('Already in calendar:', summary)
      service.validate(calendar_events[summary], *data)
    else:
      service.insert(summary, *data)
  for summary, event in calendar_events.items():
    if summary not in people_events:
      print('Deleting:', summary)
      service.delete(event['id'])

if __name__ == "__main__":
  main()
