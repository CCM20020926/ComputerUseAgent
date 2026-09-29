---
name: add_city_to_world_clock
description: Add a city to the World Clock in the Windows Clock app. Use When the user wants to add a city to the world clock or add a timezone. DO NOT Use When the Clock app is not installed, or when the task involves alarms, timers, or stopwatch features.
---

# add_city_to_world_clock

Add a city to the World Clock section of the Windows Clock app.

## Workflow

### Step 1 — Launch the Clock app

Use the `launch_app` skill to open the Clock application:

- **English system**: search for `"Clock"`
- **Chinese system**: search for `"时钟"`

Determine the system language by observing the text on the screen (e.g. taskbar labels, window titles). If the UI contains Chinese characters, treat it as a Chinese environment; otherwise treat it as English.

### Step 2 — Click the "+" button

After the Clock app window is open, locate the **"+"** (plus) button and perform a `single_click` on it to open the "Add city" input field.

### Step 3 — Type the city name

Type the city name into the search input field using the `type_text` action.

**CRITICAL — Language matching rule:**

- If the system is in a **Chinese** environment (detected in Step 1), the city name **MUST** be typed in **Chinese** (e.g. "东京", "伦敦", "纽约").
- If the system is in an **English** environment, the city name **MUST** be typed in **English** (e.g. "Tokyo", "London", "New York").

Translate the city name to the matching language before typing if necessary.

### Step 4 — Wait for search suggestions

After typing, wait briefly (use the `wait` action with `seconds: 1`) and observe whether search suggestions appear in the dropdown list.

- **Suggestions appeared**: a matching city entry is visible → proceed to Step 5.
- **No suggestions**: no matching result is shown → execute the `call_user` action to inform the user that the city could not be found, then stop.

### Step 5 — Click the target city suggestion

Locate the correct city entry in the suggestion list and perform a `single_click` on it to select it.

### Step 6 — Click "Add" / "添加"

After selecting the city, locate the confirmation button:

- **English environment**: click **"Add"**
- **Chinese environment**: click **"添加"**

Perform a `single_click` on the button.

### Step 7 — Confirm the city was added

Observe whether the city now appears in the World Clock list:

- **City added**: the city card is visible in the list → task complete.
- **City not added**: the city did not appear → retry from Step 5.

## Notes

- The city name language **must** match the system locale. This is the most important constraint of this skill.
- If the user provides the city name in a language that does not match the detected system environment, translate it before typing.
- The Clock app must be running on the "World Clock" tab (the default tab) before starting this workflow.
