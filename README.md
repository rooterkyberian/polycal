# polycal

Google calendar aggregation tool.
Goal is to synchronize events from multiple calendars into one.

## Configuring Google OAuth2

https://console.cloud.google.com/apis/dashboard?pli=1

1. New project

2. Enable APIs and services

Google Calendar API

3. Create credentials

Which API are you using? Google Calendar API

What data will you be accessing? User data

Scopes:
find the required scopes in `src/polycal/services/gcal.py`

4. OAuth Client ID

App type: Desktop app

Download client secret json to `./polycal/client_secret.json`
