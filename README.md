# ArcadeHub

ArcadeHub is a lightweight collection of classic mini-games written in Python. Each game is standalone and uses simple assets for graphics, fonts, and sound. A small local SQLite database provides cross-game features like users, friends, leaderboards, and achievements.

## Features
- Several included games: `dino.py`, `flappy.py`, `pacman.py`, `snake.py`, etc.
- Local SQLite-backed leaderboards and achievements via `db.py` and `game_zone.db`.
- Organized assets in the `Assets/` folder (images, sounds, sprites).
- Easy to run, extend, and fork.

## Requirements
- Python 3.8+
- `pygame` (or other libraries used by specific games)

Install dependencies:
```bash
pip install pygame
# or, if you provide requirements.txt:
pip install -r requirements.txt
```

## Run a Game
From the project root run the desired game script. Examples:
```bash
python dino.py
python flappy.py
python pacman.py
python snake.py
```
See the top of each game file for any additional usage notes.

## Database (leaderboards & achievements)
- The app uses SQLite. The DB file is `game_zone.db` in the project root (created/managed by `db.py`).
- Quick inspection options:
  - GUI: Open `game_zone.db` with DB Browser for SQLite.
  - CLI:
    ```bash
    sqlite3 game_zone.db
    .tables
    SELECT * FROM leaderboard LIMIT 20;
    ```
  - Python snippet:
    ```python
    import sqlite3
    conn = sqlite3.connect("game_zone.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(cur.fetchall())
    cur.execute("SELECT * FROM leaderboard LIMIT 10")
    print(cur.fetchall())
    conn.close()
    ```

## Project Structure
- Game scripts: `dino.py`, `flappy.py`, `pacman.py`, `snake.py`, `board.py`, etc.
- Database helpers: `db.py`
- Assets: `Assets/` (Bird, Cactus, Dino, ghost_images, player_images, etc.)
- Fonts: `Font/`
- Graphics: `Graphics/`
- Sound: `sfx/`, `sound/`

## Contributing
- Fork the repository and open a pull request.
- Add or improve games; keep asset licensing and attribution in mind.
- If you add new dependencies, update `requirements.txt` and this README.

## Troubleshooting
- Missing pygame error: `pip install pygame`
- Git push issues: ensure your remote is named `origin` and you’re on the correct branch:
  ```bash
  git remote -v
  git branch --show-current
  ```
- Missing database: import `db.py` or run a game to initialize `game_zone.db`.

