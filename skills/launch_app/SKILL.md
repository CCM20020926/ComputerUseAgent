---
name: launch_app
description: Search and launch a local application on Windows via the Start Menu.  Use When the target application icon or window is NOT visible on the current screen,  and the user needs to open a local application.  DO NOT Use When the target application icon or window is already visible on the screen (interact with it directly instead), or when no application needs to be launched.
---

# launch_app

Search and launch a local application on Windows via the Start Menu.

## Workflow

### Step 1 — Run the search script

Execute the `run_script` action with the following arguments to open the Windows Start Menu and search for the target application:

```
action: run_script
arguments:
  skill_name: "launch_app"
  script_name: "search_app.py"
  script_args: ["<application_name>"]
```

- `skill_name` must be `"launch_app"`
- `script_name` must be `"search_app.py"`
- `script_args` must be a list containing exactly one element: the target application name as specified by the user (e.g. `["Notepad"]`, `["Chrome"]`)

### Step 2 — Check search results

Observe whether the target application appears in the search results:

- **Found**: the application icon or entry is visible → proceed to Step 3.
- **Not found**: no matching result is shown → execute the `call_user` action to inform the user that the application could not be found, then stop.

### Step 3 — Click "Open"

Locate the **"Open"** button in the search results panel and execute a `single_click` action on it to launch the application.

### Step 4 — Confirm launch

Verify:

- Application window appeared → Continue to complete the task.
- Application did not launch → Try to launch the target application again.

## Notes

- Pass the application name exactly as specified by the user; do not translate or substitute it.
- The `script_args` parameter must always be a list, even for a single argument.
