import os
import sys
import json
import threading
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import tempfile
import re

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

# ---------- 模板浏览器 ----------
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "json.json")

def load_templates():
    try:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and all("名称" in d and "描述" in d and "代码" in d for d in data):
                return data
    except Exception as e:
        messagebox.showerror("错误", f"读取 json.json 失败：\n{e}")
    return []

class TemplateWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("信息竞赛模板浏览器")
        self.geometry("620x420")
        master.make_topmost(self)
        self.transient(master)

        self.templates = load_templates()
        self.create_widgets()
        if self.templates:
            self.show_all()
        else:
            self.code_text.insert("end", "json.json 加载失败或无数据")

    def create_widgets(self):
        # 搜索框
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="搜索：").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="搜索", command=self.do_search).pack(side="left")
        ttk.Button(search_frame, text="全部", command=self.show_all).pack(side="left", padx=2)

        # 主区域：Treeview + 代码预览
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(paned, columns=("描述",), show="tree headings", height=15)
        self.tree.heading("#0", text="名称")
        self.tree.column("#0", width=180)
        self.tree.heading("描述", text="描述")
        self.tree.column("描述", width=300)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        paned.add(self.tree)

        code_frame = ttk.Labelframe(paned, text="代码预览")
        paned.add(code_frame)
        self.code_text = tk.Text(code_frame, wrap="none", font=("Consolas", 11))
        self.code_text.pack(fill="both", expand=True)
        vsb = ttk.Scrollbar(code_frame, orient="vertical", command=self.code_text.yview)
        self.code_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        # 底部按钮
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=5, pady=2)
        ttk.Button(ctrl, text="复制代码", command=self.copy_code).pack(side="right")

    def show_all(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.templates:
            self.tree.insert("", "end", text=item["名称"], values=(item["描述"],))

    def do_search(self):
        keyword = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        for item in self.templates:
            if keyword in item["名称"].lower() or keyword in item["描述"].lower():
                self.tree.insert("", "end", text=item["名称"], values=(item["描述"],))

    def on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        name = self.tree.item(sel[0], "text")
        item = next((i for i in self.templates if i["名称"] == name), None)
        if not item:
            return
        self.code_text.delete("1.0", "end")
        self.code_text.insert("end", item["代码"])

    def copy_code(self):
        code = self.code_text.get("1.0", "end-1c")
        if not code:
            messagebox.showwarning("提示", "没有可复制的代码")
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update()
        messagebox.showinfo("完成", "已复制到剪贴板")

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
        # 按钮区
        btn_frame = tk.Frame(self)
        btn_frame.pack(expand=True)
        tk.Button(btn_frame, text='提交', command=self.handle_submit).pack(side='left', padx=5)
        tk.Button(btn_frame, text='模板', command=self.open_template).pack(side='left', padx=5)
        self.bind('<Button-3>', lambda e: self.destroy())

    def _click(self, event):
        self._x, self._y = event.x, event.y

    def _drag(self, event):
        x = self.winfo_pointerx() - self._x
        y = self.winfo_pointery() - self._y
        self.geometry(f'+{x}+{y}')

    def make_topmost(self, win):
        win.attributes('-topmost', True)

    def open_template(self):
        TemplateWindow(self)

    # ---------- 提交逻辑 ----------
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

        final_path = file_path
        if lang == 'cpp':
            fileio_script = os.path.join(os.path.dirname(__file__), 'fileio', 'fileio.py')
            io_name = '0'
            if os.path.isfile(fileio_script):
                try:
                    io_name = subprocess.run(
                        [sys.executable, fileio_script, base, pid, user, pwd],
                        capture_output=True, text=True, timeout=10
                    ).stdout.strip()
                except Exception:
                    pass

            with open(file_path, encoding='utf-8') as f:
                code = f.read()

            header = (
                '#include <cstdio>\n'
                f'static const char FILE_IN[]  = "{io_name}.in";\n'
                f'static const char FILE_OUT[] = "{io_name}.out";\n'
                '__attribute__((constructor))\n'
                'void before_main() {\n'
                '    freopen(FILE_IN,  "r", stdin);\n'
                '    freopen(FILE_OUT, "w", stdout);\n'
                '}\n'
            )
            code = header + '\n' + code
            fd, final_path = tempfile.mkstemp(suffix='.cpp')
            os.write(fd, code.encode('utf-8'))
            os.close(fd)
        else:
            final_path = file_path

        submit_script = os.path.join(os.path.dirname(__file__), 'submit', 'submit.py')
        if not os.path.isfile(submit_script):
            messagebox.showerror('错误', f'找不到 {submit_script}')
            return
        cmd_submit = [sys.executable, submit_script, base, pid, user, pwd, final_path, lang]

        dlg = tk.Toplevel(self)
        self.make_topmost(dlg)
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
                if final_path != file_path and os.path.exists(final_path):
                    os.remove(final_path)
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
            status, score = "UNKNOWN", "0"
            for _ in range(60):
                try:
                    result = subprocess.run(cmd_get, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        line = result.stdout.strip()
                        parts = line.split()
                        status = " ".join(parts[:-1]).upper()
                        score = parts[-1]
                        if status not in {"PENDING", "JUDGING", "RUNNING"}:
                            break
                except Exception:
                    status, score = "ERROR", "0"
                    break
                time.sleep(5)
            else:
                status, score = "TIMEOUT", "0"
            top = tk.Toplevel(self)
            self.make_topmost(top)
            top.title("评测结果")
            tk.Label(top, text=f"状态：{status}\n分数：{score}", font=("Consolas", 14)).pack(pady=20)
            tk.Button(top, text="确定", command=top.destroy).pack()

        threading.Thread(target=_poll, daemon=True).start()

if __name__ == '__main__':
    FloatingWindow().mainloop()