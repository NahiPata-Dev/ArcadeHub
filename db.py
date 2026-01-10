"""Clean database helper module for game_zone.

Provides a single consistent set of helpers for users, friends,
leaderboards, and achievements. Runs lightweight migrations on import.
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "game_zone.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # base tables
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY,
            user TEXT,
            friend TEXT,
            added_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY,
            game TEXT,
            user TEXT,
            score INTEGER,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY,
            user TEXT,
            key TEXT,
            awarded_at TEXT
        )
        """
    )

    conn.commit()

    # migrations
    cur.execute("PRAGMA table_info(friends)")
    cols = [r[1] for r in cur.fetchall()]
    if "status" not in cols:
        try:
            cur.execute("ALTER TABLE friends ADD COLUMN status TEXT DEFAULT 'accepted'")
        except Exception:
            pass

    cur.execute("PRAGMA table_info(achievements)")
    acols = [r[1] for r in cur.fetchall()]
    if "reason" not in acols:
        try:
            cur.execute("ALTER TABLE achievements ADD COLUMN reason TEXT DEFAULT ''")
        except Exception:
            pass

    conn.commit()
    conn.close()


def add_user_if_not_exists(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, created_at) VALUES (?,?)", (username, datetime.utcnow().isoformat()))
        conn.commit()
    conn.close()


def add_friend(user, friend):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO friends (user, friend, added_at, status) VALUES (?,?,?,?)", (user, friend, datetime.utcnow().isoformat(), 'pending'))
    conn.commit()
    conn.close()


def get_friend_requests(user):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user FROM friends WHERE friend=? AND status='pending' ORDER BY added_at DESC", (user,))
    except sqlite3.OperationalError:
        return []
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def accept_friend_request(user, requester):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE friends SET status='accepted', added_at=? WHERE user=? AND friend=? AND status='pending'", (datetime.utcnow().isoformat(), requester, user))
        cur.execute("SELECT id FROM friends WHERE user=? AND friend=?", (user, requester))
        if not cur.fetchone():
            cur.execute("INSERT INTO friends (user, friend, added_at, status) VALUES (?,?,?,?)", (user, requester, datetime.utcnow().isoformat(), 'accepted'))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


def get_friends(user):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT friend FROM friends WHERE user=? AND status='accepted' ORDER BY added_at DESC", (user,))
    except sqlite3.OperationalError:
        cur.execute("SELECT friend FROM friends WHERE user=? ORDER BY added_at DESC", (user,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def record_score(game, user, score):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO leaderboard (game, user, score, created_at) VALUES (?,?,?,?)", (game, user, score, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    _maybe_award_achievements(user, game, score)


def get_leaderboard(game, limit=20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user, MAX(score) as score, MAX(created_at) as created_at
        FROM leaderboard
        WHERE game=?
        GROUP BY user
        ORDER BY score DESC
        LIMIT ?
        """, (game, limit))
    rows = cur.fetchall()
    conn.close()
    return [(r['user'], r['score'], r['created_at']) for r in rows]


def get_overall_leaderboard(limit=20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user, SUM(score) as total FROM leaderboard GROUP BY user ORDER BY total DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [(r['user'], r['total']) for r in rows]


def get_user_total(user):
    """Return the overall total score for a user (sum across all games)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT SUM(score) as total FROM leaderboard WHERE user=?", (user,))
    row = cur.fetchone()
    conn.close()
    return row['total'] if row and row['total'] is not None else 0


def get_user_game_total(user, game):
    """Return the total score for a user in a specific game (sum of all runs)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT SUM(score) as total FROM leaderboard WHERE user=? AND game=?", (user, game))
    row = cur.fetchone()
    conn.close()
    return row['total'] if row and row['total'] is not None else 0


def get_user_overall_by_bests(user):
    """Return overall total computed as SUM of per-game bests for `user`.
    This treats each game by the user's best score, then sums those bests.
    """
    conn = get_conn()
    cur = conn.cursor()
    # sum of MAX(score) per game for this user
    cur.execute(
        "SELECT SUM(best) as total FROM (SELECT MAX(score) as best FROM leaderboard WHERE user=? GROUP BY game)",
        (user,)
    )
    row = cur.fetchone()
    conn.close()
    return row['total'] if row and row['total'] is not None else 0


def get_overall_leaderboard_by_bests(limit=20):
    """Return overall leaderboard ordered by SUM(MAX(score) per game) desc."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user, SUM(best) as total FROM (SELECT user, game, MAX(score) as best FROM leaderboard GROUP BY user, game) GROUP BY user ORDER BY total DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return [(r['user'], r['total']) for r in rows]


def get_overall_rank_by_bests(user):
    """Return 1-based rank by overall-as-bests; returns None if user has no scores."""
    conn = get_conn()
    cur = conn.cursor()
    # check if user has any per-game records
    cur.execute("SELECT COUNT(*) as cnt FROM (SELECT MAX(score) as best FROM leaderboard WHERE user=? GROUP BY game)", (user,))
    cnt = cur.fetchone()['cnt']
    if cnt == 0:
        conn.close()
        return None
    # compute user's total (sum of bests)
    cur.execute("SELECT SUM(best) as total FROM (SELECT MAX(score) as best FROM leaderboard WHERE user=? GROUP BY game)", (user,))
    total = cur.fetchone()['total']
    cur.execute(
        "SELECT COUNT(*) as cnt FROM (SELECT user, SUM(best) as total FROM (SELECT user, game, MAX(score) as best FROM leaderboard GROUP BY user, game) GROUP BY user) WHERE total > ?",
        (total,)
    )
    higher = cur.fetchone()['cnt']
    conn.close()
    return higher + 1


def get_user_best_score(user):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(score) as best FROM leaderboard WHERE user=?", (user,))
    row = cur.fetchone()
    conn.close()
    return row['best'] if row and row['best'] is not None else 0


def get_user_best_for_game(user, game):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(score) as best FROM leaderboard WHERE user=? AND game=?", (user, game))
    row = cur.fetchone()
    conn.close()
    return row['best'] if row and row['best'] is not None else 0


def get_rank_for_game(user, game):
    """Return 1-based rank of `user` for `game` by highest score across users.
    If the user has no score for the game, returns None.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(score) as best FROM leaderboard WHERE user=? AND game=?", (user, game))
    r = cur.fetchone()
    best = r['best'] if r and r['best'] is not None else None
    if best is None:
        conn.close()
        return None
    cur.execute(
        "SELECT COUNT(*) as cnt FROM (SELECT user, MAX(score) as best FROM leaderboard WHERE game=? GROUP BY user) WHERE best > ?",
        (game, best),
    )
    cnt = cur.fetchone()['cnt']
    conn.close()
    return cnt + 1


def get_overall_rank(user):
    """Return 1-based overall rank of `user` by total score. Returns None if no score."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT SUM(score) as total FROM leaderboard WHERE user=?", (user,))
    r = cur.fetchone()
    total = r['total'] if r and r['total'] is not None else None
    if total is None:
        conn.close()
        return None
    cur.execute(
        "SELECT COUNT(*) as cnt FROM (SELECT user, SUM(score) as total FROM leaderboard GROUP BY user) WHERE total > ?",
        (total,)
    )
    cnt = cur.fetchone()['cnt']
    conn.close()
    return cnt + 1


def _maybe_award_achievements(user, game, score):
    conn = get_conn()
    cur = conn.cursor()
    # score-based achievements (common thresholds)
    score_thresholds = [500, 1000]
    for th in score_thresholds:
        if score >= th:
            _award(conn, cur, user, f"{game}_score_{th}", f"Score >= {th} in {game}")

    # play-count achievements
    cur.execute("SELECT COUNT(*) as cnt FROM leaderboard WHERE user=? AND game=?", (user, game))
    cnt = cur.fetchone()[0]
    play_thresholds = [5, 10, 25]
    for pth in play_thresholds:
        if cnt >= pth:
            _award(conn, cur, user, f"{game}_plays_{pth}", f"Played {pth} games of {game}")
    conn.commit()
    conn.close()


def _award(conn, cur, user, key, reason=""):
    cur.execute("SELECT id FROM achievements WHERE user=? AND key=?", (user, key))
    if not cur.fetchone():
        cur.execute("INSERT INTO achievements (user, key, reason, awarded_at) VALUES (?,?,?,?)", (user, key, reason, datetime.utcnow().isoformat()))


def get_user_achievements(user):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT key, reason, awarded_at FROM achievements WHERE user=? ORDER BY awarded_at DESC", (user,))
        rows = cur.fetchall()
        return [(r['key'], r['reason'], r['awarded_at']) for r in rows]
    finally:
        conn.close()


def get_user_profile(user):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT created_at FROM users WHERE username=?", (user,))
    u = cur.fetchone()
    created = u['created_at'] if u else 'unknown'
    # total: use overall-as-bests for a fair cross-game total
    total = get_user_overall_by_bests(user)
    cur.execute("SELECT COUNT(*) as plays FROM leaderboard WHERE user=?", (user,))
    s = cur.fetchone()
    plays = s['plays'] or 0
    achievements = get_user_achievements(user)
    conn.close()
    out = []
    out.append(f"Username: {user}")
    out.append(f"Joined: {created}")
    out.append(f"Total score: {total}")
    out.append(f"Total plays: {plays}")
    out.append("\nAchievements:")
    if achievements:
        for k, reason, at in achievements:
            out.append(f"- {k}: {reason} ({at})")
    else:
        out.append("- None yet")
    return "\n".join(out)


# Ensure DB exists / migrations applied when module is imported
try:
    init_db()
except Exception:
    pass


def rescan_achievements():
    """Rescan leaderboard to retroactively award achievements based on
    configured thresholds (score 500/1000, plays 5/10/25).
    This is idempotent because `_award` checks for existing awards.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user, game, MAX(score) as max_score, COUNT(*) as plays FROM leaderboard GROUP BY user, game"
    )
    rows = cur.fetchall()
    awarded = 0
    for r in rows:
        user = r["user"]
        game = r["game"]
        max_score = r["max_score"] or 0
        plays = r["plays"] or 0
        for th in (500, 1000):
            if max_score >= th:
                _award(conn, cur, user, f"{game}_score_{th}", f"Score >= {th} in {game}")
                awarded += 1
        for pth in (5, 10, 25):
            if plays >= pth:
                _award(conn, cur, user, f"{game}_plays_{pth}", f"Played {pth} games of {game}")
                awarded += 1
    conn.commit()
    conn.close()
    return awarded
