from action.base_action import type_text,hot_key, wait
import sys

def search_app(application_name):
    # 1. Press win
    hot_key(['win'])

    # 2. Wait for the search bar to appear
    wait(seconds=0.5)

    # 3. Type the application name
    type_text(application_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Error: need 1 arguments: application_name", file=sys.stderr)
        sys.exit(1)
    try:
        application_name = sys.argv[1]
        search_app(application_name)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)