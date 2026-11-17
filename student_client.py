import argparse
import json
import student_auth
import time
import random
import FreeSimpleGUI as sg


# --- Constants  ---
GRID_SIZE = 10
GAME_LOOP_TIMEOUT_MS = 100  # This is in milliseconds

CLIENT_ASSET_CONFIG = {
    'hq': {'size': 5, 'count': 1},
    'warehouse': {'size': 3, 'count': 2},
    'store': {'size': 2, 'count': 3}
}

# --- Helper Functions  ---


def handle_api_error(response):
    """A helper to parse and print API errors from JSON or raw text."""
    try:
        # Try to parse the JSON and get the specific error message
        error_json = response.json()
        error_message = error_json.get("error", response.text)
        print(f"Error: {response.status_code} - {error_message}")
    except:
        # Fallback for non-JSON responses
        print(f"Error: {response.status_code} - {response.text}")


def handle_command_line():
    """A helper to parse command-line arguments and options."""

    parser = argparse.ArgumentParser(description="Supply Chain Showdown Client")

    # Add global arguments to the main parser
    parser.add_argument("--team-id", required=False, help="Your unique team identifier")
    parser.add_argument("--opponent-id", required=False, help="Opponent unique team identifier")
    parser.add_argument("--server-url", required=False,
                        help="Base URL of the game server (e.g., http://localhost:8080). Defaults to value in client_config.json if not provided.")

    subparsers = parser.add_subparsers(dest="action",
                                       help="Action to perform (for testing purposes). If omitted, client runs in tournament mode.")

    # Subcommand for 'join'
    join_parser = subparsers.add_parser("join", help="Join a game")
    join_parser.add_argument("--game-id", help="The ID of the game to join (optional, server may assign)")
    join_parser.add_argument("--opponent-id",
                             help="Team ID of your opponent (required for 'join' in tournament mode, ignored in dev mode)")

    # Subcommand for 'place-assets'
    place_assets_parser = subparsers.add_parser("place-assets", help="Place your assets on the grid")
    place_assets_parser.add_argument("--game-id", required=True, help="The ID of the game to interact with")
    place_assets_parser.add_argument("--placements-file",
                                     help="Path to a JSON file containing asset placement data. If not provided, your logic decides.")

    # Subcommand for 'hack'
    hack_parser = subparsers.add_parser("hack", help="Perform a hack on an opponent's cell")
    hack_parser.add_argument("--game-id", required=True, help="The ID of the game to interact with")
    hack_parser.add_argument("--coords",
                             help="Coordinate string for the 'hack' action (e.g., 'C5'). If not provided, your logic decides.")

    # Subcommand for 'status'
    status_parser = subparsers.add_parser("status", help="Get the current game status")
    status_parser.add_argument("--game-id", required=True, help="The ID of the game to interact with")

    # Parse arguments
    args = parser.parse_args()

    # If an action is specified, team-id is required.
    if args.action and not args.team_id:
        parser.error(f"--team-id is required for the '{args.action}' action.")

    return args


def decide_hack_coordinates(opponent_grid_view=None, locally_hacked=None):
    """Week 1 strategy: choose a random cell that has never been hacked.

    The server's grid uses '.' for unknown, '~' for Block, '*' for Breach.
    locally_hacked protects against delays before the grid refreshes.
    """
    locally_hacked = locally_hacked or set()
    available = []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            coord = f"{chr(ord('A') + row)}{col + 1}"
            if coord in locally_hacked:
                continue
            if opponent_grid_view is not None:
                if opponent_grid_view[row][col] != '.':
                    continue
            available.append(coord)
    return random.choice(available) if available else None


def decide_asset_placement():
    """Determines where in grid to place assets and returns a dictionary."""

    # Students: This is where you generate random asset locations.
    # For now, return something valid.
    return {
        "hq": [["B2", "C2", "D2", "E2", "F2"]],
        "warehouse": [["E8", "E9", "E10"], ["H4", "I4", "J4"]],
        "store": [["G6", "G7"], ["A8", "A9"], ["C4", "D4"]]
    }


# --- API Interaction Stubs ---


def do_join(server_url, team_id, opponent_id=None):
    """POST /join; return Game ID or None."""
    url = f"{server_url.rstrip('/')}/join"
    payload = {"team_id": team_id}
    if opponent_id:
        payload["opponent_id"] = opponent_id
    try:
        response = student_auth.post(url, data=payload)
        if response.status_code in (200, 201):
            data = response.json()
            return data.get("game_id")
        handle_api_error(response)
    except Exception as exc:
        print(f"Could not join game: {exc}")
    return None


def do_place_assets(server_url, game_id, team_id, placements_data=None):
    """POST /{game_id}/place-assets; return True only on success."""
    if placements_data is None:
        placements_data = decide_asset_placement()
    url = f"{server_url.rstrip('/')}/{game_id}/place-assets"
    payload = {"team_id": team_id, "assets": placements_data}
    try:
        response = student_auth.post(url, data=payload)
        if response.status_code in (200, 201):
            print("Assets placed successfully.")
            return True
        handle_api_error(response)
    except Exception as exc:
        print(f"Could not place assets: {exc}")
    return False


def do_hack(server_url, game_id, team_id, coords=None):
    """POST /{game_id}/hack; return response JSON or None."""
    if coords is None:
        coords = decide_hack_coordinates()
    if not coords:
        print("No unused coordinates remain.")
        return None
    url = f"{server_url.rstrip('/')}/{game_id}/hack"
    payload = {"team_id": team_id, "coords": coords}
    try:
        response = student_auth.post(url, data=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"Hack {coords}: {result}")
            return result
        handle_api_error(response)
    except Exception as exc:
        print(f"Could not hack {coords}: {exc}")
    return None


def do_get_status(server_url, game_id, team_id):
    """GET /{game_id}/status with team_id query parameter."""
    url = f"{server_url.rstrip('/')}/{game_id}/status"
    try:
        response = student_auth.get(url, params={"team_id": team_id})
        if response.status_code == 200:
            return response.json()
        handle_api_error(response)
    except Exception as exc:
        print(f"Could not get status: {exc}")
    return None


def display_grid(grid):
    """Format the server's 10x10 opponent_grid_view as a readable grid."""
    if not grid or len(grid) != GRID_SIZE:
        return "Waiting for grid data..."
    lines = ["    " + " ".join(f"{i:>2}" for i in range(1, 11))]
    for row_index, row in enumerate(grid):
        lines.append(f"{chr(65 + row_index)}   " + " ".join(f"{cell:>2}" for cell in row))
    return "\n".join(lines)


def display_own_grid(assets, last_opponent_move, opponent_attacks):
    """Show placement and any opponent attacks observed in status updates."""
    cells = [['.' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    symbols = {'hq': 'H', 'warehouse': 'W', 'store': 'S'}
    for asset_type, buildings in assets.items():
        for building in buildings:
            for coord in building:
                row, col = ord(coord[0]) - 65, int(coord[1:]) - 1
                cells[row][col] = symbols[asset_type]
    if last_opponent_move and last_opponent_move.get('coords'):
        opponent_attacks.add(last_opponent_move['coords'])
    for coord in opponent_attacks:
        row, col = ord(coord[0]) - 65, int(coord[1:]) - 1
        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            cells[row][col] = 'X' if cells[row][col] != '.' else '~'
    return display_grid(cells)


# --- Main Execution Logic ---


def main():

    # Call helper function to parse command-line arguments
    args = handle_command_line()

    # Students, when you run this program, you will do it in one of two ways:
    #
    # During development:
    #    python student_client.py --team-id TEAMID
    #
    # During a tournament:
    #    python student_client.py --team-id TEAMID --opponent-id OPPONENTID
    #
    # Note, however, that there are several other options that can appear on the command line.
    # Ignore these -- they are for use by the instructor only.
    #
    # The code below handles those other options, if they are present.
    # YOUR code for the game loop goes in the "else" near the bottom of the file.

    # Determine server_url: command-line > config file > error
    server_url = args.server_url
    config_file_name = "client_config.json"

    if not server_url:
        try:
            with open(config_file_name, 'r') as f:
                config = json.load(f)
                server_url = config.get("server_url")
        except FileNotFoundError:
            print(f"Client Error: '{config_file_name}' not found. Please provide --server-url or create the config file.")
            return
        except json.JSONDecodeError:
            print(f"Client Error: Invalid JSON in '{config_file_name}'.")
            return
        
    if not server_url:
        print("Client Error: Server URL not provided via --server-url or found in client_config.json.")
        return

    # Dispatch based on action or default to tournament mode
    if args.action == 'join':
        game_id = do_join(server_url, args.team_id, args.opponent_id)
        if game_id:
            print(f"Client: Successfully joined game with ID: {game_id}")
        else:
            print("Client: Failed to join game.")
    elif args.action == 'place-assets':
        if not args.game_id:
            print("Client Error: --game-id is required for 'place-assets' action.")
            return
        placements_data = None
        if args.placements_file:
            try:
                with open(args.placements_file, 'r') as f:
                    placements_data = json.load(f)
            except FileNotFoundError:
                print(f"Client Error: Placements file '{args.placements_file}' not found.")
                return
            except json.JSONDecodeError:
                print(f"Client Error: Invalid JSON in placements file '{args.placements_file}'.")
                return
        do_place_assets(server_url, args.game_id, args.team_id, placements_data)
    elif args.action == 'hack':
        if not args.game_id:
            print("Client Error: --game-id is required for 'hack' action.")
            return
        do_hack(server_url, args.game_id, args.team_id, args.coords)
    elif args.action == 'status':
        if not args.game_id:
            print("Client Error: --game-id is required for 'status' action.")
            return
        do_get_status(server_url, args.game_id, args.team_id)
    else:
        if not args.team_id:
            print("A Team ID must be supplied to play the game.")
            return

        # Call join and placement exactly once. Do not run multiple clients for
        # the same team simultaneously.
        game_id = do_join(server_url, args.team_id, args.opponent_id)
        if not game_id:
            print("Could not start: join failed.")
            return
        assets = decide_asset_placement()
        if not do_place_assets(server_url, game_id, args.team_id, assets):
            print("Could not start: asset placement failed.")
            return

        # Simple Week 1 dashboard. Replace / expand this in Week 2.
        layout = [
            [sg.Text("THE BEAN COUNTERATTACK", font=("Arial", 18, "bold"))],
            [sg.Text(f"Team: {args.team_id}   |   Game: {game_id}")],
            [sg.Text("Game status: Waiting", key="-STATE-", size=(55, 1))],
            [sg.Text("Damage: $0 / $750,000", key="-DAMAGE-", size=(55, 1))],
            [sg.ProgressBar(750000, orientation="h", size=(40, 12), key="-PROGRESS-")],
            [sg.Text("Turns: 0   Penalties: $0   Goofs: 0", key="-STATS-")],
            [
                sg.Column([[sg.Text("Our Assets (H / W / S)")],
                           [sg.Multiline(display_grid(None), size=(40, 14), font=("Courier", 11),
                                         disabled=True, key="-OWN-")]]),
                sg.Column([[sg.Text("Opponent Grid (. unknown, ~ block, * breach)")],
                           [sg.Multiline(display_grid(None), size=(40, 14), font=("Courier", 11),
                                         disabled=True, key="-OPP-")]])
            ],
            [sg.Text("Last hack: none", key="-LAST-HACK-", size=(90, 1))],
            [sg.Text("Opponent's last move: none", key="-OPP-MOVE-", size=(90, 1))],
            [sg.Button("Exit Game", key="-EXIT-")]
        ]
        window = sg.Window("The Bean Counterattack | Supply Chain Showdown", layout, finalize=True)
        locally_hacked = set()
        opponent_attacks = set()
        last_hack_text = "none"
        previous_status = None
        next_poll = 0.0
        finished = False

        # The window.read loop keeps the GUI responsive. Status polling happens
        # every 2 seconds without blocking GUI events with time.sleep().
        while True:
            event, _ = window.read(timeout=GAME_LOOP_TIMEOUT_MS)
            if event in (sg.WIN_CLOSED, "-EXIT-"):
                break
            if finished or time.monotonic() < next_poll:
                continue
            next_poll = time.monotonic() + 2.0
            status = do_get_status(server_url, game_id, args.team_id)
            if status is None:
                # Transient error: try again, not a blind attack.
                continue
            previous_status = status
            state = status.get('game_state', 'unknown')
            my_turn = status.get('is_your_turn', False)
            stats = status.get('your_stats') or {}
            damage = float(stats.get('total_damage_inflicted', 0))
            penalties = float(stats.get('penalties', 0))
            net_damage = max(0, damage - penalties)
            opponent_grid = status.get('opponent_grid_view')
            opponent_move = status.get('last_opponent_move')
            window['-STATE-'].update(f"Game status: {state} | " +
                                    ('Your turn' if my_turn else "Opponent's turn"))
            window['-DAMAGE-'].update(f"Net damage: ${net_damage:,.0f} / $750,000")
            window['-PROGRESS-'].update(current_count=min(750000, int(net_damage)))
            window['-STATS-'].update(
                f"Turns (server): {status.get('turn_count', 0)}   "
                f"Penalties: ${penalties:,.0f}   Goofs: {stats.get('goof_count', 0)}"
            )
            window['-OWN-'].update(display_own_grid(assets, opponent_move, opponent_attacks))
            window['-OPP-'].update(display_grid(opponent_grid))
            window['-LAST-HACK-'].update(f"Last hack: {last_hack_text}")
            if opponent_move:
                window['-OPP-MOVE-'].update(
                    f"Opponent's last move: {opponent_move.get('coords')} "
                    f"({opponent_move.get('result')})"
                )
            if state == 'finished':
                winner = status.get('winner')
                window['-STATE-'].update(f"GAME OVER | Winner: {winner}")
                finished = True
                continue
            if state == 'active' and my_turn and not stats.get('on_autoplay', False):
                coord = decide_hack_coordinates(opponent_grid, locally_hacked)
                if coord is not None:
                    result = do_hack(server_url, game_id, args.team_id, coord)
                    if result is not None:
                        locally_hacked.add(coord)
                        last_hack_text = (f"{coord}: {result.get('result', '?')} "
                                          f"(${result.get('damage_inflicted', 0):,})")
                        window['-LAST-HACK-'].update(f"Last hack: {last_hack_text}")
        window.close()


if __name__ == "__main__":
    main()
