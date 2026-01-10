import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from db import (
    init_db,
    add_user_if_not_exists,
    record_score,
    get_leaderboard,
    get_overall_leaderboard,
    add_friend,
    get_friends,
    get_user_profile,
    get_user_achievements,
    get_friend_requests,
    accept_friend_request,
    get_user_best_for_game,
    get_rank_for_game,
    get_overall_rank,
    get_user_overall_by_bests,
    get_overall_leaderboard_by_bests,
    get_overall_rank_by_bests,
)

ROOT = os.path.dirname(os.path.abspath(__file__))

GAMES = [
    ("Snake", "snake.py"),
    ("Pacman", "pacman.py"),
    ("Flappy", "flappy.py"),
    ("Dino", "dino.py"),
]


class GameZoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Game Zone")
        self.geometry("900x600")
        init_db()
        self.username = simpledialog.askstring("Profile", "Enter your username:") or "guest"
        add_user_if_not_exists(self.username)
        self.create_widgets()

    def create_widgets(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.games_frame = ttk.Frame(self.nb)
        self.friends_frame = ttk.Frame(self.nb)
        self.leaderboard_frame = ttk.Frame(self.nb)
        self.profile_frame = ttk.Frame(self.nb)

        self.nb.add(self.games_frame, text="Games")
        self.nb.add(self.friends_frame, text="Friends")
        self.nb.add(self.leaderboard_frame, text="Leaderboards")
        self.nb.add(self.profile_frame, text="Profile")

        self.build_games_tab()
        self.build_friends_tab()
        self.build_leaderboard_tab()
        self.build_profile_tab()

        # bind tab change for auto-refresh behavior
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self._auto_refresh_id = None
        self._leaderboard_mode = 'game'

    def build_games_tab(self):
        frm = self.games_frame
        ttk.Label(frm, text=f"Logged in as: {self.username}", font=(None, 12)).pack(pady=6)
        grid = ttk.Frame(frm)
        grid.pack(padx=10, pady=10)
        for i, (label, script) in enumerate(GAMES):
            b = ttk.Button(grid, text=label, width=20, command=lambda s=script, g=label: self.launch_game(s, g))
            b.grid(row=i // 2, column=i % 2, padx=10, pady=8)

    def launch_game(self, script, game_name):
        path = os.path.join(ROOT, script)
        if not os.path.exists(path):
            messagebox.showerror("Missing", f"Game script not found: {script}")
            return
        try:
            # pass the logged-in username and request auto-recording
            subprocess.Popen([sys.executable, path, "--user", self.username, "--auto-record"], cwd=ROOT)
            messagebox.showinfo("Launched", f"Launched {game_name}. Scores will be recorded automatically when the game ends.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_friends_tab(self):
        frm = self.friends_frame
        toolbar = ttk.Frame(frm)
        toolbar.pack(fill=tk.X, pady=6)
        ttk.Button(toolbar, text="Add Friend", command=self.add_friend_dialog).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_friends).pack(side=tk.LEFT)

        content = ttk.Frame(frm)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        ttk.Label(left, text='Friends').pack(anchor=tk.W)
        self.friends_list = tk.Listbox(left)
        self.friends_list.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(content)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(right, text='Requests').pack(anchor=tk.W)
        self.requests_list = tk.Listbox(right, height=8)
        self.requests_list.pack()
        ttk.Button(right, text='Accept Selected', command=self.accept_selected_request).pack(pady=6)

        self.refresh_friends()
        self.refresh_friend_requests()

    def add_friend_dialog(self):
        friend = simpledialog.askstring("Add Friend", "Friend's username:")
        if friend:
            add_friend(self.username, friend)
            messagebox.showinfo('Friend Request', f'Request sent to {friend}')
            self.refresh_friend_requests()

    def refresh_friend_requests(self):
        self.requests_list.delete(0, tk.END)
        try:
            for r in get_friend_requests(self.username):
                self.requests_list.insert(tk.END, r)
        except Exception:
            pass

    def accept_selected_request(self):
        sel = None
        try:
            sel = self.requests_list.get(self.requests_list.curselection())
        except Exception:
            return
        if sel:
            accept_friend_request(self.username, sel)
            messagebox.showinfo('Friend', f'You are now friends with {sel}')
            self.refresh_friend_requests()
            self.refresh_friends()

    def refresh_friends(self):
        self.friends_list.delete(0, tk.END)
        sel_game = self.game_choice.get() if hasattr(self, 'game_choice') else None
        for f in get_friends(self.username):
            try:
                from db import get_user_overall_by_bests, get_user_best_for_game
                overall = get_user_overall_by_bests(f)
                # build per-game bests for all known games (consistent with overall-by-bests)
                per_game_totals = [(g, get_user_best_for_game(f, g)) for g, _ in GAMES]
            except Exception:
                overall = 0
            label = f
            label += " — Overall: %d" % overall if overall else " — Overall: No score"
            # append per-game totals (only include games with non-zero total to keep list concise)
            parts = []
            for g, total in (per_game_totals if 'per_game_totals' in locals() else []):
                try:
                    if total and int(total) > 0:
                        parts.append(f"{g}: {total}")
                except Exception:
                    # non-numeric or None -> skip
                    continue
            if parts:
                label += " | " + " | ".join(parts)
            self.friends_list.insert(tk.END, label)

    def build_leaderboard_tab(self):
        frm = self.leaderboard_frame
        top = ttk.Frame(frm)
        top.pack(fill=tk.X, pady=8)
        ttk.Label(top, text="Game:").pack(side=tk.LEFT, padx=6)
        self.game_choice = tk.StringVar(value=GAMES[0][0])
        cb = ttk.Combobox(top, textvariable=self.game_choice, values=[g for g,_ in GAMES], state="readonly")
        cb.pack(side=tk.LEFT)
        cb.bind('<<ComboboxSelected>>', lambda e: self.refresh_friends())
        ttk.Button(top, text="Show", command=self.show_leaderboard).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Overall", command=self.show_overall).pack(side=tk.LEFT)

        self.lb_text = tk.Text(frm, height=20)
        self.lb_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        # no in-line highlighting — rank shown at bottom
        # make leaderboard read-only / non-editable by users
        self.lb_text.bind('<Key>', lambda e: 'break')
        self.lb_text.config(state=tk.DISABLED)

        # status label at bottom showing current user's rank and best score
        self.user_status = ttk.Label(frm, text="")
        self.user_status.pack(fill=tk.X, padx=10, pady=(0,8))
        # make leaderboard read-only / non-editable by users
        self.lb_text.bind('<Key>', lambda e: 'break')
        self.lb_text.config(state=tk.DISABLED)

    def show_leaderboard(self):
        self._leaderboard_mode = 'game'
        game = self.game_choice.get()
        rows = get_leaderboard(game, limit=20)
        self.lb_text.config(state=tk.NORMAL)
        self.lb_text.delete("1.0", tk.END)
        self.lb_text.insert(tk.END, f"Leaderboard - {game}" + "\n\n")
        # only highlight the current user in the leaderboard
        my_row = None
        for i, (user, score, ts) in enumerate(rows, start=1):
            # date-only
            date_only = ts.split('T')[0] if ts and 'T' in ts else ts.split(' ')[0] if ts else ''
            line = f"{i}. {user} — {score} ({date_only})\n"
            # compute exact start index, insert, then get end index to tag precisely
            start = self.lb_text.index(tk.END)
            self.lb_text.insert(tk.END, line)
            end = self.lb_text.index(tk.END)
            if user.strip().lower() == self.username.strip().lower():
                my_row = (i, user, score)
        # refresh friends list to reflect selected game
        self.refresh_friends()
        # show user's rank/best at bottom
        try:
            # show rank even if user isn't in the top N list
            rank = get_rank_for_game(self.username, game)
            best = get_user_best_for_game(self.username, game)
            if rank is not None:
                self.user_status.config(text=f"Your rank: {rank} — Your best for {game}: {best}")
            else:
                self.user_status.config(text=f"Your best for {game}: {best}")
        except Exception:
            self.user_status.config(text="")
        self.lb_text.config(state=tk.DISABLED)

    def on_tab_changed(self, event):
        # start/stop leaderboard auto-refresh when switching tabs
        selected = event.widget.select()
        if self.nb.nametowidget(selected) is self.leaderboard_frame:
            # show and start auto-refresh
            self.show_leaderboard()
            self._start_leaderboard_auto_refresh()
        else:
            self._stop_leaderboard_auto_refresh()

    def show_overall(self):
        self._leaderboard_mode = 'overall'
        rows = get_overall_leaderboard_by_bests(limit=20)
        self.lb_text.config(state=tk.NORMAL)
        self.lb_text.delete("1.0", tk.END)
        self.lb_text.insert(tk.END, "Overall Leaderboard\n\n")
        my_row = None
        for i, (user, score) in enumerate(rows, start=1):
            line = f"{i}. {user} — {score}\n"
            start = self.lb_text.index(tk.END)
            self.lb_text.insert(tk.END, line)
            end = self.lb_text.index(tk.END)
            if user.strip().lower() == self.username.strip().lower():
                my_row = (i, user, score)
        self.refresh_friends()
        try:
            total = None
            # show overall rank even if not in the top N
            rank = get_overall_rank_by_bests(self.username)
            # compute total score
            total = get_user_overall_by_bests(self.username)
            if rank is not None:
                self.user_status.config(text=f"Your rank: {rank} — Total: {total}")
            else:
                self.user_status.config(text=f"Your total score: {total}")
        except Exception:
            self.user_status.config(text="")
        self.lb_text.config(state=tk.DISABLED)

    def _start_leaderboard_auto_refresh(self):
        self._stop_leaderboard_auto_refresh()
        def _tick():
            try:
                if self._leaderboard_mode == 'overall':
                    self.show_overall()
                else:
                    self.show_leaderboard()
            except Exception:
                pass
            self._auto_refresh_id = self.after(5000, _tick)
        _tick()

    def _stop_leaderboard_auto_refresh(self):
        if getattr(self, '_auto_refresh_id', None):
            try:
                self.after_cancel(self._auto_refresh_id)
            except Exception:
                pass
            self._auto_refresh_id = None

    def build_profile_tab(self):
        frm = self.profile_frame
        toolbar = ttk.Frame(frm)
        toolbar.pack(fill=tk.X, pady=6)
        ttk.Button(toolbar, text="Record Score Manually", command=self.record_score_dialog).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Refresh Profile", command=self.refresh_profile).pack(side=tk.LEFT, padx=6)

        self.profile_text = tk.Text(frm, height=10)
        self.profile_text.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(frm, text="Achievements:").pack(anchor=tk.W, padx=10)
        self.achievements_list = tk.Listbox(frm, height=8)
        self.achievements_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.refresh_profile()

    def _infer_achievement_reason(self, key, reason):
        # return provided reason if present, otherwise try to infer from key
        if reason and reason.strip():
            return reason
        try:
            if key.endswith('_big_score'):
                game = key.rsplit('_', 2)[0]
                return f"Score >= 1000 in {game}"
            if key.endswith('_veteran'):
                game = key.rsplit('_', 1)[0]
                return f"Played 10 games of {game}"
        except Exception:
            pass
        return ''

    def _pretty_achievement_name(self, key):
        # map achievement keys to friendly tier names
        if key.endswith('_score_500'):
            return 'Pro'
        if key.endswith('_score_1000'):
            return 'Hacker'
        if '_plays_' in key:
            if key.endswith('_plays_5'):
                return 'Rookie'
            if key.endswith('_plays_10'):
                return 'Pro'
            if key.endswith('_plays_25'):
                return 'Expert'
        # legacy keys
        if key.endswith('_veteran'):
            return 'Veteran'
        if key.endswith('_big_score'):
            return 'Big Scorer'
        # default to raw key
        return key

    def record_score_dialog(self):
        game = simpledialog.askstring("Record Score", "Game name:")
        if not game:
            return
        try:
            score = int(simpledialog.askstring("Record Score", "Score (integer):") or "0")
        except Exception:
            messagebox.showerror("Invalid", "Score must be an integer")
            return
        record_score(game, self.username, score)
        messagebox.showinfo("Recorded", "Score recorded. Check Leaderboards.")

    def view_profile(self):
        dlg = tk.Toplevel(self)
        dlg.title("Profile")
        text = tk.Text(dlg, width=60, height=20)
        text.pack(padx=8, pady=8)
        # show basic info and achievements with reasons
        profile = get_user_profile(self.username)
        text.insert(tk.END, profile.splitlines()[0] + "\n")
        text.insert(tk.END, profile.splitlines()[1] + "\n")
        text.insert(tk.END, profile.splitlines()[2] + "\n")
        text.insert(tk.END, profile.splitlines()[3] + "\n\n")
        text.insert(tk.END, "Achievements:\n")
        try:
            for key, reason, at in get_user_achievements(self.username):
                reason = self._infer_achievement_reason(key, reason)
                display_name = self._pretty_achievement_name(key)
                date_only = at.split('T')[0] if at and 'T' in at else at
                text.insert(tk.END, f"- {display_name} ({key}): {reason} ({date_only})\n")
        except Exception:
            text.insert(tk.END, "- None yet\n")
        text.config(state=tk.DISABLED)

    def refresh_profile(self):
        profile = get_user_profile(self.username)
        self.profile_text.config(state=tk.NORMAL)
        self.profile_text.delete('1.0', tk.END)
        # show only basic profile info here; achievements are in the separate list
        self.profile_text.insert(tk.END, '\n'.join(profile.splitlines()[:4]))
        self.profile_text.config(state=tk.DISABLED)
        self.achievements_list.delete(0, tk.END)
        try:
            for key, reason, at in get_user_achievements(self.username):
                reason = self._infer_achievement_reason(key, reason)
                display_name = self._pretty_achievement_name(key)
                date_only = at.split('T')[0] if at and 'T' in at else at
                self.achievements_list.insert(tk.END, f"{display_name} ({key}): {reason} ({date_only})")
        except Exception:
            pass


if __name__ == '__main__':
    app = GameZoneApp()
    app.mainloop()
