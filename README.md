# polycal

Google calendar aggregation tool.

Synchronize events from multiple calendars into one.

**One-way** synchronization only! don't expect edits of target calendar to be synchronized back - in fact they will get overwritten during next sync.

## Example config

`./.polycal/polycal`

```
sources:
  - id: example@gmail.com
    transforms:
      - type: SkipByTitle
        kwargs:
          titles:
            - "Not important"
  - id: workemail@example.com
    transforms:
      - type: ReplaceTitle
        kwargs:
          repl: "work"
      - type: Merge
        kwargs:
          elipsis: "15m"
  - id: 123@group.calendar.google.com
    transforms:
      - type: ReplaceTitle
        kwargs:
          pattern: "^(.*)$"
          repl: 'Other|\1'
      - type: SetAttr
        kwargs:
          busy: !!bool false

target:
  id: target123@group.calendar.google.com
```

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
