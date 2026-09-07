# sample-service

A deliberately small service used as a fixed workspace for eval control prompts.

It exposes two entry points, `run()` and `health()`. Configuration lives in a module-level
`cfg` dict: the port defaults to 8080 and debug is off.

Clients that recieve a health response should treat a missing `ok` key as a failure.

## Running

    python src/app.py
