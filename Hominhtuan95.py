import ctypes
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pynput import keyboard, mouse

user32 = ctypes.windll.user32
MAX_SECONDS = 10800

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

def foreground():
    return int(user32.GetForegroundWindow())

def title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

def client_xy(hwnd, x, y):
    p = POINT(int(x), int(y))
    user32.ScreenToClient(hwnd, ctypes.byref(p))
    return p.x, p.y

def screen_xy(hwnd, x, y):
    p = POINT(int(x), int(y))
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    return p.x, p.y

def key_encode(k):
    if isinstance(k, keyboard.KeyCode):
        return {'kind': 'char', 'value': k.char} if k.char else None
    if isinstance(k, keyboard.Key):
        return {'kind': 'special', 'value': k.name}
    return None

def key_decode(data):
    if data['kind'] == 'char':
        return data['value']
    return getattr(keyboard.Key, data['value'], None)

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Hominhtuan95 | Macro chuột + bàn phím')
        self.root.geometry('470x450')
        self.root.minsize(440, 420)
        self.root.configure(bg='white')
        self.target = None
        self.events = []
        self.listeners = []
        self.recording = False
        self.playing = False
        self.stop_event = threading.Event()
        self.record_start = 0
        self.last_move = 0
        self.status = tk.StringVar(value='Chưa chọn cửa sổ game')
        self.info = tk.StringVar(value='Chưa ghi Macro')
        self.loop = tk.BooleanVar(value=True)
        self.speed = tk.StringVar(value='1.0')
        tk.Label(self.root, text='HOMINHTUAN95', font=('Segoe UI', 17, 'bold'), bg='white', fg='#17456c').pack(pady=(12, 2))
        tk.Label(self.root, text='MACRO 1 CỬA SỔ | CHUỘT + BÀN PHÍM', bg='white', fg='#555').pack()
        pane = ttk.Frame(self.root, padding=14)
        pane.pack(fill='both', expand=True)
        ttk.Button(pane, text='1. Chọn cửa sổ game đang mở', command=self.choose).pack(fill='x', pady=4)
        ttk.Label(pane, textvariable=self.status, wraplength=420).pack(fill='x', pady=4)
        buttons = ttk.Frame(pane)
        buttons.pack(fill='x', pady=10)
        self.rec_btn = ttk.Button(buttons, text='● BẮT ĐẦU GHI', command=self.start_record)
        self.rec_btn.pack(side='left', expand=True, fill='x', padx=2)
        self.stop_rec_btn = ttk.Button(buttons, text='■ DỪNG GHI', command=self.stop_record, state='disabled')
        self.stop_rec_btn.pack(side='left', expand=True, fill='x', padx=2)
        self.play_btn = ttk.Button(pane, text='▶ PHÁT MACRO', command=self.start_play)
        self.play_btn.pack(fill='x', pady=4)
        self.stop_btn = ttk.Button(pane, text='■ DỪNG PHÁT (F10)', command=self.stop_play)
        self.stop_btn.pack(fill='x', pady=4)
        ttk.Label(pane, textvariable=self.info).pack(anchor='w', pady=6)
        options = ttk.Frame(pane)
        options.pack(fill='x', pady=3)
        ttk.Checkbutton(options, text='Lặp lại (tối đa 3 giờ)', variable=self.loop).pack(side='left')
        ttk.Label(options, text='Tốc độ:').pack(side='left', padx=(14, 3))
        ttk.Entry(options, textvariable=self.speed, width=6).pack(side='left')
        ttk.Label(options, text='×').pack(side='left')
        files = ttk.Frame(pane)
        files.pack(fill='x', pady=8)
        ttk.Button(files, text='LƯU MACRO', command=self.save).pack(side='left', expand=True, fill='x', padx=2)
        ttk.Button(files, text='MỞ MACRO', command=self.load).pack(side='left', expand=True, fill='x', padx=2)
        tk.Label(self.root, text='Zalo: TuanHo | 0398438721', bg='white', fg='#17456c', font=('Segoe UI', 10, 'bold')).pack(pady=7)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def choose(self):
        if self.recording or self.playing:
            messagebox.showinfo('Đang hoạt động', 'Hãy dừng Macro trước khi chọn cửa sổ.')
            return
        messagebox.showinfo('Chọn game', 'Sau khi nhấn OK, bạn có 3 giây để nhấp vào cửa sổ game cần ghi/phát Macro.')
        self.status.set('Đang chờ chọn cửa sổ game...')
        threading.Thread(target=self._choose_worker, daemon=True).start()

    def _choose_worker(self):
        time.sleep(3)
        hwnd = foreground()
        name = title(hwnd)
        self.root.after(0, lambda: self._set_target(hwnd, name))

    def _set_target(self, hwnd, name):
        if not hwnd or 'Hominhtuan95' in name:
            self.status.set('Chưa chọn đúng cửa sổ game. Hãy thử lại.')
            return
        self.target = hwnd
        self.status.set('Đã chọn: ' + (name or str(hwnd)))

    def add(self, kind, **data):
        if not self.recording or foreground() != self.target:
            return
        self.events.append({'t': round(time.monotonic() - self.record_start, 4), 'type': kind, **data})

    def start_record(self):
        if self.recording or self.playing:
            return
        if not self.target or not user32.IsWindow(self.target):
            messagebox.showwarning('Chưa chọn game', 'Hãy chọn cửa sổ game trước.')
            return
        self.events = []
        self.recording = True
        self.record_start = time.monotonic()
        self.last_move = 0
        self.rec_btn.config(state='disabled')
        self.stop_rec_btn.config(state='normal')
        self.info.set('Đang ghi... Chuyển sang game để thao tác, quay lại bấm DỪNG GHI.')
        def on_press(key):
            k = key_encode(key)
            if k:
                self.add('key_down', key=k)
        def on_release(key):
            k = key_encode(key)
            if k:
                self.add('key_up', key=k)
        def on_move(x, y):
            now = time.monotonic()
            if now - self.last_move >= 0.04 and self.recording and foreground() == self.target:
                self.last_move = now
                cx, cy = client_xy(self.target, x, y)
                self.add('move', x=cx, y=cy)
        def on_click(x, y, button, pressed):
            cx, cy = client_xy(self.target, x, y)
            self.add('click', x=cx, y=cy, button=button.name, pressed=pressed)
        def on_scroll(x, y, dx, dy):
            cx, cy = client_xy(self.target, x, y)
            self.add('scroll', x=cx, y=cy, dx=dx, dy=dy)
        self.listeners = [keyboard.Listener(on_press=on_press, on_release=on_release), mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)]
        for listener in self.listeners:
            listener.start()

    def stop_record(self):
        if not self.recording:
            return
        self.recording = False
        for listener in self.listeners:
            listener.stop()
        self.listeners = []
        self.rec_btn.config(state='normal')
        self.stop_rec_btn.config(state='disabled')
        self.info.set(f'Đã ghi {len(self.events)} sự kiện.')

    def start_play(self):
        if self.recording or self.playing:
            return
        if not self.target or not user32.IsWindow(self.target):
            messagebox.showwarning('Chưa chọn game', 'Hãy chọn cửa sổ game trước.')
            return
        if not self.events:
            messagebox.showwarning('Chưa có Macro', 'Hãy ghi hoặc mở Macro trước.')
            return
        try:
            speed = float(self.speed.get().replace(',', '.'))
            if not 0.1 <= speed <= 10:
                raise ValueError
        except ValueError:
            messagebox.showerror('Tốc độ', 'Tốc độ phải trong khoảng 0.1 đến 10.')
            return
        self.playing = True
        self.stop_event = threading.Event()
        repeat = self.loop.get()  # Tkinter variables are only read on the UI thread.
        self.play_btn.config(state='disabled')
        self.info.set('Chuẩn bị phát Macro...')
        threading.Thread(target=self._play, args=(speed, repeat, self.stop_event), daemon=True).start()

    def _ui_info(self, value):
        try:
            self.root.after(0, lambda: self.info.set(value))
        except RuntimeError:
            pass

    def _play(self, speed, repeat, stop):
        kctl, mctl = keyboard.Controller(), mouse.Controller()
        deadline = time.monotonic() + MAX_SECONDS
        events = list(self.events)
        held_keys = []
        held_buttons = []
        error = None
        try:
            with keyboard.Listener(on_press=lambda k: stop.set() if k == keyboard.Key.f10 else None):
                # Give Windows time to close the button interaction and activate the game.
                for remaining in (3, 2, 1):
                    self._ui_info(f'Bắt đầu sau {remaining} giây... (F10 để dừng)')
                    if stop.wait(1):
                        return

                # Restore the game if minimized, then request focus.
                if user32.IsIconic(self.target):
                    user32.ShowWindow(self.target, 9)  # SW_RESTORE
                user32.SetForegroundWindow(self.target)
                if stop.wait(0.35):
                    return
                if foreground() != self.target:
                    self._ui_info('Không kích hoạt được game. Hãy đưa game lên trước rồi nhấn PHÁT lại.')
                    return
                self._ui_info('Đang phát Macro. Nhấn F10 để dừng.')

                while not stop.is_set() and time.monotonic() < deadline:
                    start = time.monotonic()
                    for ev in events:
                        wait = start + ev['t'] / speed - time.monotonic()
                        if wait > 0 and stop.wait(wait):
                            break
                        if stop.is_set() or time.monotonic() >= deadline:
                            break
                        if foreground() != self.target:
                            self._ui_info('Đã dừng: cửa sổ game không còn được chọn.')
                            stop.set()
                            break
                        kind = ev['type']
                        if kind in ('key_down', 'key_up'):
                            key = key_decode(ev['key'])
                            if key is not None:
                                if kind == 'key_down':
                                    kctl.press(key)
                                    held_keys.append(key)
                                else:
                                    kctl.release(key)
                                    if key in held_keys:
                                        held_keys.remove(key)
                        elif kind in ('move', 'click', 'scroll'):
                            x, y = screen_xy(self.target, ev['x'], ev['y'])
                            mctl.position = (x, y)
                            if kind == 'click':
                                btn = getattr(mouse.Button, ev['button'], None)
                                if btn:
                                    if ev['pressed']:
                                        mctl.press(btn)
                                        held_buttons.append(btn)
                                    else:
                                        mctl.release(btn)
                                        if btn in held_buttons:
                                            held_buttons.remove(btn)
                            elif kind == 'scroll':
                                mctl.scroll(ev['dx'], ev['dy'])
                    if not repeat:
                        break
                    if not events or events[-1]['t'] == 0:
                        if stop.wait(0.1):
                            break
        except Exception as exc:
            error = str(exc)
        finally:
            # Do not leave pressed keys or mouse buttons held after stopping.
            for key in reversed(held_keys):
                try:
                    kctl.release(key)
                except Exception:
                    pass
            for btn in reversed(held_buttons):
                try:
                    mctl.release(btn)
                except Exception:
                    pass
            if error:
                try:
                    self.root.after(0, lambda msg=error: messagebox.showerror('Lỗi phát Macro', msg))
                except RuntimeError:
                    pass
            try:
                self.root.after(0, lambda: self._finished(stop))
            except RuntimeError:
                pass

    def _finished(self, stop):
        if self.stop_event is stop:
            self.playing = False
            self.play_btn.config(state='normal')
            if self.info.get().startswith(('Đang phát', 'Bắt đầu', 'Chuẩn bị')):
                self.info.set('Đã dừng Macro.')

    def stop_play(self):
        self.stop_event.set()

    def save(self):
        if not self.events:
            messagebox.showwarning('Chưa có dữ liệu', 'Hãy ghi Macro trước.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('Macro JSON', '*.json')])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'version': 1, 'events': self.events}, f, ensure_ascii=False, indent=2)

    def load(self):
        if self.recording or self.playing:
            return
        path = filedialog.askopenfilename(filetypes=[('Macro JSON', '*.json')])
        if not path:
            return
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            events = data['events']
            if not isinstance(events, list) or len(events) > 200000 or any(not isinstance(e, dict) or e.get('type') not in ('key_down', 'key_up', 'move', 'click', 'scroll') or not isinstance(e.get('t'), (int, float)) or e['t'] < 0 for e in events):
                raise ValueError('File Macro không hợp lệ')
            self.events = events
            self.info.set(f'Đã mở {len(events)} sự kiện.')
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror('Không mở được Macro', str(exc))

    def close(self):
        self.stop_event.set()
        self.stop_record()
        self.root.destroy()

if __name__ == '__main__':
    App().root.mainloop()
