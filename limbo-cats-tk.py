import tkinter as tk
import random
import math
import os
import sys
import tempfile
import winsound

# ============================================================
# НАСТРОЙКИ
# ============================================================
NUM_CATS = 8
CAT_SIZE = 110
RADIUS = 230
CENTER_X, CENTER_Y = 500, 380
SHOW_CORRECT_MS = 1500
SHUFFLE_ROUNDS = 5
SHUFFLE_FPS = 60
MOVE_SPEED = 0.18
SHUFFLE_ROUND_MS = 1200

CAT_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f1c40f",
    "#9b59b6", "#e67e22", "#1abc9c", "#e84393",
]

CAT_BG = "#ffffff"
HIGHLIGHT_GREEN = "#2ecc71"
OK_COLOR = "#2ecc71"
FAIL_COLOR = "#e74c3c"

EMOJI_FONT = ("Segoe UI Emoji", 30)


# ============================================================
# РЕСУРСЫ И МУЗЫКА
# ============================================================
def resource_path(relative_path):
    """Путь к ресурсу — работает и в обычном режиме, и в EXE (PyInstaller)."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def play_music():
    """Извлекает встроенный music.wav во временный файл и запускает зацикленно."""
    wav_path = resource_path("music.wav")
    if not os.path.exists(wav_path):
        print("music.wav не найден рядом со скриптом/в EXE — музыка не играет.")
        return None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with open(wav_path, "rb") as src:
            tmp.write(src.read())
        tmp.close()
        winsound.PlaySound(
            tmp.name,
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
        )
        return tmp.name
    except Exception as e:
        print(f"Ошибка музыки: {e}")
        return None


# ============================================================
# ОКНО-КОТИК
# ============================================================
class CatWindow:
    def __init__(self, master, x, y, index, game):
        self.game = game
        self.index = index
        self.correct = False
        self.clicked = False
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(x)
        self.target_y = float(y)

        # Оригинальное окно Windows (с системным заголовком и крестиком)
        self.win = tk.Toplevel(master)
        self.win.title("cat")
        self.win.geometry(f"{CAT_SIZE}x{CAT_SIZE}+{int(x)}+{int(y)}")
        self.win.configure(bg=CAT_BG)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)

        # Установка иконки для каждого окна
        try:
            self.win.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        # Крестик → полное закрытие программы
        self.win.protocol("WM_DELETE_WINDOW", self.game.quit_game)

        # Внутри — котик
        self.label = tk.Label(self.win, text="🐱", bg=CAT_BG,
                              font=EMOJI_FONT)
        self.label.pack(expand=True, fill="both")

        self.label.bind("<Button-1>", self.on_click)
        self.win.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        if self.game.state != "guess" or self.clicked:
            return
        self.clicked = True
        if self.correct:
            self.set_green_inside()
            self.game.show_message("Молодец! Это он 🐾", OK_COLOR)
        else:
            self.set_red_inside()
            self.game.show_message("Не угадал...", FAIL_COLOR)
            for c in self.game.cats:
                if c.correct:
                    c.set_green_inside()
                    break
        self.game.state = "result"

    def set_green_inside(self):
        self.win.configure(bg=HIGHLIGHT_GREEN)
        self.label.configure(bg=HIGHLIGHT_GREEN)

    def set_red_inside(self):
        self.win.configure(bg=FAIL_COLOR)
        self.label.configure(bg=FAIL_COLOR)

    def set_color(self, color):
        self.win.configure(bg=color)
        self.label.configure(bg=color)

    def set_target(self, x, y):
        self.target_x = float(x)
        self.target_y = float(y)

    def step_towards_target(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) < 1 and abs(dy) < 1:
            self.x = self.target_x
            self.y = self.target_y
            self.win.geometry(f"+{int(self.x)}+{int(self.y)}")
            return False
        self.x += dx * MOVE_SPEED
        self.y += dy * MOVE_SPEED
        self.win.geometry(f"+{int(self.x)}+{int(self.y)}")
        return True

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ============================================================
# ИГРА
# ============================================================
class LimboCatsGame:
    def __init__(self):
        self.root = tk.Tk()
        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass
        self.root.withdraw()

        # Запуск музыки
        self.music_file = play_music()

        self.state = "idle"
        self.cats = []
        self.positions = self.circle_positions()
        self.shuffle_round = 0
        self.shuffle_steps_left = 0
        self.root.after(200, self.start_game)

    def circle_positions(self):
        positions = []
        offset = random.uniform(0, 2 * math.pi)
        radius = RADIUS + random.randint(-30, 30)
        for i in range(NUM_CATS):
            angle = (2 * math.pi * i / NUM_CATS) - math.pi / 2 + offset
            x = CENTER_X + radius * math.cos(angle) - CAT_SIZE / 2
            y = CENTER_Y + radius * math.sin(angle) - CAT_SIZE / 2
            positions.append((x, y))
        return positions

    def start_game(self):
        self.new_round()

    def new_round(self):
        for c in self.cats:
            c.destroy()
        self.cats.clear()
        self.positions = self.circle_positions()

        # 1) Все окна ОДИНАКОВЫЕ (белые с 🐱)
        for i in range(NUM_CATS):
            x, y = self.positions[i]
            cat = CatWindow(self.root, x, y, i, self)
            cat.correct = False
            cat.clicked = False
            self.cats.append(cat)

        # Случайное правильное окно
        correct_idx = random.randrange(NUM_CATS)
        self.cats[correct_idx].correct = True

        self.state = "same"
        # Через 1 сек выделяем правильное зелёным
        self.root.after(1000, self.show_green)

    def show_green(self):
        if not self.cats:
            return
        for cat in self.cats:
            if cat.correct:
                cat.set_green_inside()
                break
        self.state = "memorize"
        self.root.after(SHOW_CORRECT_MS, self.start_shuffle)

    def start_shuffle(self):
        if not self.cats:
            return
        # Убираем зелёный, все снова белые
        for cat in self.cats:
            cat.set_color(CAT_BG)

        self.state = "shuffle"
        self.shuffle_round = 0
        self.do_shuffle_round()

    def do_shuffle_round(self):
        if not self.cats:
            return
        if self.shuffle_round >= SHUFFLE_ROUNDS:
            self.finish_shuffle()
            return

        targets = self.positions[:]
        random.shuffle(targets)
        for cat, (tx, ty) in zip(self.cats, targets):
            cat.set_target(tx, ty)

        self.shuffle_steps_left = int(SHUFFLE_ROUND_MS / (1000 / SHUFFLE_FPS))
        self.animate_shuffle()

    def animate_shuffle(self):
        if not self.cats:
            return
        any_moving = False
        for cat in self.cats:
            if cat.step_towards_target():
                any_moving = True
        self.shuffle_steps_left -= 1
        if any_moving and self.shuffle_steps_left > 0:
            self.root.after(int(1000 / SHUFFLE_FPS), self.animate_shuffle)
        else:
            for cat in self.cats:
                cat.x = cat.target_x
                cat.y = cat.target_y
                cat.win.geometry(f"+{int(cat.x)}+{int(cat.y)}")
            self.shuffle_round += 1
            self.root.after(100, self.do_shuffle_round)

    def finish_shuffle(self):
        if not self.cats:
            return
        # 3) После перемешивания у всех РАЗНЫЕ цвета
        colors = CAT_COLORS[:NUM_CATS]
        random.shuffle(colors)
        for cat, color in zip(self.cats, colors):
            cat.set_color(color)

        self.state = "guess"

    def show_message(self, text, color):
        msg = tk.Toplevel(self.root)
        msg.title("result")
        try:
            msg.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass
        msg.attributes("-topmost", True)
        msg.configure(bg=color)
        lbl = tk.Label(msg, text=text, bg=color, fg="white",
                       font=("Arial", 14, "bold"), padx=20, pady=10)
        lbl.pack()
        msg.update_idletasks()
        w = msg.winfo_width()
        h = msg.winfo_height()
        msg.geometry(f"+{CENTER_X - w//2}+{CENTER_Y - h//2}")
        msg.after(2000, msg.destroy)

    def quit_game(self):
        # Останавливаем музыку
        winsound.PlaySound(None, 0)
        # Удаляем временный файл
        if getattr(self, "music_file", None):
            try:
                os.unlink(self.music_file)
            except OSError:
                pass
        try:
            for c in self.cats:
                c.destroy()
        finally:
            self.root.destroy()
            raise SystemExit(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    game = LimboCatsGame()
    game.run()