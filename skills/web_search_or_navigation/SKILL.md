---
name: web_search_or_navigation
description: Perform a web search or web navigation in the browser's address bar. Use When you need to perform a web search or navigate to a URL in the browser, and the browser's address bar is currently visible. DO NOT Use When the address bar is NOT visible or not focused, or when no web search is needed.
---

# web_search

Perform a web search by typing a query into the browser's address bar and submitting it.

## Workflow

### Step 1 — Run the search script

Execute the `run_script` action with the following arguments to type the search query into the address bar and press Enter:

```
action: run_script
arguments:
  skill_name: "web_search_or_navigation"
  script_name: "web_search.py"
  script_args: ["<search_query>"]
```

- `skill_name` must be `"web_search"`
- `script_name` must be `"web_search.py"`
- `script_args` must be a list containing exactly one element: the search query as specified by the user (e.g. `["Python tutorial"]`, `["latest news"]`)

### Step 2 — Check search results

Observe whether the search results page has loaded:

- **Results loaded**: the page shows search results → Continue to complete the task.
- **Results not loaded**: the page did not navigate or shows an error → execute the `call_user` action to inform the user that the search could not be completed.

## Notes

- Pass the search query exactly as specified by the user; do not translate or rephrase it.
- The `script_args` parameter must always be a list, even for a single argument.
- This skill assumes the browser's address bar is already visible and focused. If the address bar is not visible, do NOT use this skill.
