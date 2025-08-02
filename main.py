import os
import sys
import json
import threading
import subprocess
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog

CONFIG_FILE = 'config.json'

# ---------- 工具 ----------
def load_config():
    return json.load(open(CONFIG_FILE, encoding='utf-8')) if os.path.isfile(CONFIG_FILE) else {}

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

class SubmitThread(threading.Thread):
    def __init__(self, cmd, timeout=20):
        super().__init__(daemon=True)
        self.cmd = cmd
        self.timeout = timeout
        self.result = None
        self.exception = None

    def run(self):
        try:
            self.result = subprocess.run(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout
            )
        except subprocess.TimeoutExpired as e:
            self.exception = f"提交超时：{e}"
        except Exception as e:
            self.exception = str(e)

# ---------- 悬浮窗 ----------
class FloatingWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("悬浮窗")
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.geometry('220x80+50+50')
        self._x = self._y = 0
        self.bind('<Button-1>', self._click)
        self.bind('<B1-Motion>', self._drag)
        tk.Button(self, text='提交', command=self.handle_submit).pack(expand=True)
        self.bind('<Button-3>', lambda e: self.destroy())

    def _click(self, event):
        self._x, self._y = event.x, event.y

    def _drag(self, event):
        x = self.winfo_pointerx() - self._x
        y = self.winfo_pointery() - self._y
        self.geometry(f'+{x}+{y}')

    def handle_submit(self):
        cfg = load_config()
        if cfg:
            pid = simpledialog.askstring('题号', '请输入 PID：')
            if not pid:
                return
            file_path = filedialog.askopenfilename(title='选择代码文件')
            if not file_path:
                return
            base, user, pwd = cfg['base'], cfg['user'], cfg['pass']
        else:
            base = simpledialog.askstring('BASE URL', '请输入 OJ 根地址：')
            user = simpledialog.askstring('用户名', '请输入用户名：')
            pwd = simpledialog.askstring('密码', '请输入密码：')
            if not all([base, user, pwd]):
                return
            save_config({'base': base, 'user': user, 'pass': pwd})
            pid = simpledialog.askstring('题号', '请输入 PID：')
            file_path = filedialog.askopenfilename(title='选择代码文件')
            if not pid or not file_path:
                return

        _, ext = os.path.splitext(file_path.lower())
        lang = 'cpp' if ext == '.cpp' else 'python'

        submit_script = os.path.join(os.path.dirname(__file__), 'submit', 'submit.py')
        if not os.path.isfile(submit_script):
            messagebox.showerror('错误', f'找不到 {submit_script}')
            return
        cmd_submit = [sys.executable, submit_script, base, pid, user, pwd, file_path, lang]

        dlg = tk.Toplevel(self)
        dlg.title("提交中")
        dlg.geometry("300x100+200+200")
        dlg.transient(self)
        dlg.grab_set()
        tk.Label(dlg, text="正在提交，请稍候…", font=("Consolas", 12)).pack(pady=20)
        tk.Button(dlg, text="取消", command=dlg.destroy).pack()

        worker = SubmitThread(cmd_submit, timeout=20)
        worker.start()

        def check_submit():
            if not worker.is_alive():
                dlg.destroy()
                if worker.exception:
                    messagebox.showerror("提交失败", worker.exception)
                    return
                if worker.result.returncode != 0:
                    messagebox.showerror("提交错误", worker.result.stdout)
                    return
                out = worker.result.stdout
                rid_line = [ln for ln in out.splitlines() if '记录号：' in ln]
                if not rid_line:
                    messagebox.showerror("错误", "未能解析提交记录号")
                    return
                rid = rid_line[0].split('：')[-1].strip()
                self.poll_result(base, user, pwd, rid)
            else:
                self.after(200, check_submit)

        check_submit()

    def poll_result(self, base, user, pwd, rid):
        get_script = os.path.join(os.path.dirname(__file__), 'get_record', 'get_record.py')
        if not os.path.isfile(get_script):
            messagebox.showerror('错误', f'找不到 {get_script}')
            return
        cmd_get = [sys.executable, get_script, base, user, pwd, rid]

        def _poll():
            for _ in range(60):
                try:
                    result = subprocess.run(cmd_get, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        line = result.stdout.strip()
                        parts = line.split()
                        status = " ".join(parts[:-1]).upper()
                        score = parts[-1]
                        if status not in {"PENDING", "JUDGING", "RUNNING","COMPILING"}:
                            break
                except Exception:
                    status, score = "ERROR", "0"
                    break
                time.sleep(5)
            else:
                status, score = "TIMEOUT", "0"
            messagebox.showinfo("评测结果", f"状态：{status}\n分数：{score}")

        threading.Thread(target=_poll, daemon=True).start()

# ---------- 入口 ----------
if __name__ == '__main__':
    FloatingWindow().mainloop()