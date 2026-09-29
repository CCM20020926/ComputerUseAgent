import time
import os

import pyautogui
import pyperclip
import subprocess
from memory_manager import memory_manager

pyautogui.FAILSAFE = False

ACTION_SPACE = {}
ACTION_SCHEMA = {}

def register(name=None):
    def decorate(cls):
        nonlocal name
        if name is None:
            name = cls.__name__
        ACTION_SPACE[name] = cls
        ACTION_SCHEMA[name] = cls.__doc__
        return cls
    return decorate


# ──────────────────────────── Mouse Actions ────────────────────────────


@register()
def single_click(x, y):
    """
    {
        "name": "single_click",
        "description": "Perform a single left click at the specified (x, y) screen coordinate.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "The x-coordinate of the screen position to click."
                },
                "y": {
                    "type": "integer",
                    "description": "The y-coordinate of the screen position to click."
                }
            },
            "required": ["x", "y"]
        }
    }
    """
    pyautogui.click(x, y, button="left")


@register()
def double_click(x, y):
    """
    {
        "name": "double_click",
        "description": "Perform a double left click at the specified (x, y) screen coordinate.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "The x-coordinate of the screen position to click."
                },
                "y": {
                    "type": "integer",
                    "description": "The y-coordinate of the screen position to click."
                }
            },
            "required": ["x", "y"]
        }
    }
    """
    pyautogui.doubleClick(x, y)


@register()
def triple_click(x, y):
    """
    {
        "name": "triple_click",
        "description": "Perform a triple click at the specified (x, y) screen coordinate. Typically used to select an entire line of text.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "The x-coordinate of the screen position to click."
                },
                "y": {
                    "type": "integer",
                    "description": "The y-coordinate of the screen position to click."
                }
            },
            "required": ["x", "y"]
        }
    }
    """
    pyautogui.tripleClick(x, y)


@register()
def right_click(x, y):
    """
    {
        "name": "right_click",
        "description": "Perform a right mouse click at the specified (x, y) screen coordinate.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "The x-coordinate of the screen position to click."
                },
                "y": {
                    "type": "integer",
                    "description": "The y-coordinate of the screen position to click."
                }
            },
            "required": ["x", "y"]
        }
    }
    """
    pyautogui.rightClick(x, y)


@register()
def move_to(x, y):
    """
    {
        "name": "move_to",
        "description": "Move the mouse cursor to the specified (x, y) screen coordinate without clicking.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "The x-coordinate of the target screen position."
                },
                "y": {
                    "type": "integer",
                    "description": "The y-coordinate of the target screen position."
                }
            },
            "required": ["x", "y"]
        }
    }
    """
    pyautogui.moveTo(x, y)


@register()
def drag_to(x, y, duration=0.5):
    """
    {
        "name": "drag_to",
        "description": "Drag the mouse from the current position to the specified (x, y) screen coordinate while holding the left mouse button.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "The x-coordinate of the target screen position."
                },
                "y": {
                    "type": "integer",
                    "description": "The y-coordinate of the target screen position."
                },
                "duration": {
                    "type": "number",
                    "description": "The duration of the drag motion in seconds. Defaults to 0.5."
                }
            },
            "required": ["x", "y"]
        }
    }
    """
    pyautogui.dragTo(x, y, duration=duration)


@register()
def scroll(clicks, x=None, y=None):
    """
    {
        "name": "scroll",
        "description": "Scroll the mouse wheel at the specified position. Positive values scroll up, negative values scroll down.",
        "parameters": {
            "type": "object",
            "properties": {
                "clicks": {
                    "type": "integer",
                    "description": "Number of scroll clicks. Positive to scroll up, negative to scroll down."
                },
                "x": {
                    "type": "integer",
                    "description": "Optional x-coordinate where the scroll should occur. Defaults to current mouse position."
                },
                "y": {
                    "type": "integer",
                    "description": "Optional y-coordinate where the scroll should occur. Defaults to current mouse position."
                }
            },
            "required": ["clicks"]
        }
    }
    """
    pyautogui.scroll(clicks, x=x, y=y)


# ──────────────────────────── Keyboard Actions ─────────────────────────


@register()
def type_text(text, interval=0.05):
    """
    {
        "name": "type_text",
        "description": "Type the given text string at the current cursor position. Uses clipboard paste to support Unicode characters.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text string to type."
                },
                "interval": {
                    "type": "number",
                    "description": "Interval between each keystroke in seconds. Defaults to 0.05."
                }
            },
            "required": ["text"]
        }
    }
    """
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


@register()
def press_key(key):
    """
    {
        "name": "press_key",
        "description": "Press and release a single keyboard key.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key to press, e.g. 'enter', 'tab', 'escape', 'backspace', 'space', 'up', 'down', 'left', 'right'."
                }
            },
            "required": ["key"]
        }
    }
    """
    pyautogui.press(key)


@register()
def key_down(key):
    """
    {
        "name": "key_down",
        "description": "Press a keyboard key down without releasing it. Must be paired with a subsequent key_up call.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key to press down, e.g. 'shift', 'ctrl', 'alt'."
                }
            },
            "required": ["key"]
        }
    }
    """
    pyautogui.keyDown(key)


@register()
def key_up(key):
    """
    {
        "name": "key_up",
        "description": "Release a keyboard key that was previously pressed down with key_down.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key to release, e.g. 'shift', 'ctrl', 'alt'."
                }
            },
            "required": ["key"]
        }
    }
    """
    pyautogui.keyUp(key)


@register()
def hot_key(keys: list[str]):
    """
    {
        "name": "hot_key",
        "description": "Press a combination of keys simultaneously (hotkey / keyboard shortcut).",
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of keys to press together, e.g. ['ctrl', 'c'] for copy, ['alt', 'tab'] for window switch."
                }
            },
            "required": ["keys"]
        }
    }
    """
    pyautogui.hotkey(*keys)


# ──────────────────────────── Screenshot ───────────────────────────────


@register()
def screenshot(region=None):
    """
    {
        "name": "screenshot",
        "description": "Take a screenshot of the entire screen or a specified region. Returns a PIL Image object.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Optional screenshot region as [left, top, width, height]. If omitted, captures the full screen."
                }
            },
            "required": []
        }
    }
    """
    if region:
        return pyautogui.screenshot(region=tuple(region))
    return pyautogui.screenshot()


# ──────────────────────────── Clipboard ────────────────────────────────


@register()
def copy_selected_text():
    """
    {
        "name": "copy_selected_text",
        "description": "Copy the currently selected text to the clipboard by pressing Ctrl+C. Returns the clipboard content as a string.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    """
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.1)
    return pyperclip.paste()


@register()
def paste_text(text=None):
    """
    {
        "name": "paste_text",
        "description": "Paste text from the clipboard at the current cursor position. If text is provided, it is first copied to the clipboard before pasting.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Optional text to place into the clipboard before pasting. If omitted, pastes the current clipboard content."
                }
            },
            "required": []
        }
    }
    """
    if text is not None:
        pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


# ──────────────────────────── System ───────────────────────────────────


@register()
def switch_window():
    """
    {
        "name": "switch_window",
        "description": "Switch to the next window by pressing Alt+Tab.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    """
    pyautogui.hotkey("alt", "tab")


@register()
def wait(seconds):
    """
    {
        "name": "wait",
        "description": "Pause execution for a specified number of seconds, waiting for the environment to update.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "Number of seconds to wait."
                }
            },
            "required": ["seconds"]
        }
    }
    """
    time.sleep(seconds)


# ──────────────────────────── Control Flow ─────────────────────────────


@register()
def finish(reason):
    """
    {
        "name": "finish",
        "description": "Signal that the current task is complete. This is a control-flow action, not a GUI operation.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "A brief explanation of why the task is considered finished."
                }
            },
            "required": ["reason"]
        }
    }
    """
    pass


@register()
def error_env(message):
    """
    {
        "name": "error_env",
        "description": "Report an environment error or unexpected state encountered during task execution. This is a control-flow action, not a GUI operation.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Description of the environment error."
                }
            },
            "required": ["message"]
        }
    }
    """
    pass


@register()
def call_user(message):
    """
    {
        "name": "call_user",
        "description": "Pause the agent and ask the user for help or clarification. This is a control-flow action, not a GUI operation.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message or question to present to the user."
                }
            },
            "required": ["message"]
        }
    }
    """
    pass


@register()
def do_nothing():
    """
    {
        "name": "do_nothing",
        "description": "Perform no operation. Used when the agent determines that no action is needed in the current step.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    """
    pass

@register()
def run_script(skill_name, script_name, script_args):
    """
    {
        "name": "run_script",
        "description": "Run a script within a specific skill",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The name of the skill directory, e.g. 'launch_app'."
                },
                "script_name": {
                    "type": "string",
                    "description": "The name of the script file to run, e.g. 'search_app.py'."
                },
                "script_args": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of arguments to pass to the script, e.g. ['Notepad']."
                }
            },
            "required": ["skill_name", "script_name", "script_args"]
        }
    }
    """

    script_path = os.path.join(
        'skills',
        skill_name,
        script_name
    )

    try:
        result = subprocess.run(
            ["python", script_path] + script_args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False
        )
        if result.returncode != 0:
            err_msg = f"Error: {result.stderr.strip()}"
            print(err_msg)
            return err_msg
        return result.stdout.strip()
    except Exception as e:
        return f"Exception happened: {str(e)}"

@register()
def search_memory(category, query):
    """
    {
        "name": "search_memory",
        "description": "Search long-term memory for previously stored user preferences or local environment configurations. Returns up to 5 most relevant memory entries.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["preference", "local_config"],
                    "description": "The category of memory to search. 'preference' for user habits and tool preferences; 'local_config' for local file paths and environment settings."
                },
                "query": {
                    "type": "string",
                    "description": "The search query describing what information to retrieve, e.g. 'preferred office software' or 'documents folder path'."
                }
            },
            "required": ["category", "query"]
        }
    }
    """
    return memory_manager.search(category, query)


@register()
def load_skill(skill_name):
    """
    {
        "name": "load_skill",
        "description": "Load the detailed workflow documentation (SKILL.md) for a specific skill. Use this action when you determine that a skill is needed to accomplish the current task.",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The name of the skill to load, e.g. 'launch_app'."
                }
            },
            "required": ["skill_name"]
        }
    }
    """
    skill_path = os.path.join('skills', skill_name, 'SKILL.md')
    try:
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Strip YAML frontmatter (--- ... ---)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content
    
    except FileNotFoundError:
        return f"Error: skill '{skill_name}' not found at {skill_path}"
    except Exception as e:
        return f"Error loading skill: {str(e)}"
