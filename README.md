Create app_keys.py with

```
apps = {
    "<ttn_app_name>": dict(
        ttn=dict(
            host="<ttn_app_router>",
            app_key="<ttn_app_key>",
        ),
        sms={
            "<name>": "+<number>"
        },
        telegram={

        }
    ),
}

```
