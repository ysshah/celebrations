from base64 import b64decode
from os import environ
import json
import pickle

from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.cloud import storage

TOKEN_FILE = '/tmp/token.pickle'
credentials = service_account.Credentials.from_service_account_info(
    json.loads(b64decode(environ['SERVICE_ACCOUNT_INFO'])))

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/contacts.readonly',
]

def _blob():
  return storage.Client(project=environ['PROJECT'],
                        credentials=credentials).bucket(environ['BUCKET']).blob('token.pickle')

def _get_creds():
  _blob().download_to_filename(TOKEN_FILE)
  with open(TOKEN_FILE, 'rb') as token:
    return pickle.load(token)

def _save_creds(creds):
  with open(TOKEN_FILE, 'wb') as token:
    pickle.dump(creds, token)
  print(f'Uploading {TOKEN_FILE}')
  _blob().upload_from_filename(TOKEN_FILE)

def get_credentials():
  creds = _get_creds()
  if not creds.valid and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    _save_creds(creds)
  elif not creds.valid:
    raise RuntimeError('Unable to refresh credentials')
  return creds
