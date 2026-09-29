from action.base_action import type_text,hot_key, press_key
import sys

def web_search(query):
    hot_key(['ctrl','l'])

    type_text(query)

    press_key('enter')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Error: need 1 arguments: application_name", file=sys.stderr)
        sys.exit(1)
    try:
        query = sys.argv[1]
        web_search(query)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)