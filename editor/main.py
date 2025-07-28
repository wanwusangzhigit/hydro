#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cpp_tkeditor.py – 最终完整可运行版
• # 注释绿色高亮
• 括号/引号自动补全
• 智能回车缩进
• 行号、主题、交互运行等全部保留
"""
import os
import re
import secrets
import subprocess
import tempfile
import threading
import tkinter as tk
from queue import Queue, Empty
from tkinter import ttk, filedialog, messagebox, font

# ---------- Prism 主题 ----------
PRISM_COLORS = {
    "light": {
        "bg": "#ffffff", "fg": "#000000", "sel": "#c8c8c8",
        "keyword": {"foreground": "#0000ff"},
        "string":  {"foreground": "#a31515"},
        "comment": {"foreground": "#008000"},
        "number":  {"foreground": "#098658"},
        "function": {"foreground": "#795da3"},
        "operator": {"foreground": "#d73a49"},
    },
    "dark": {
        "bg": "#1e1e1e", "fg": "#d4d4d4", "sel": "#264f78",
        "keyword": {"foreground": "#569cd6"},
        "string":  {"foreground": "#ce9178"},
        "comment": {"foreground": "#6a9955"},
        "number":  {"foreground": "#b5cea8"},
        "function": {"foreground": "#dcdcaa"},
        "operator": {"foreground": "#d4d4d4"},
    }
}

KEYWORDS = {
    "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor",
    "bool", "break", "case", "catch", "char", "class", "compl", "const",
    "consteval", "constexpr", "continue", "decltype", "default", "delete",
    "do", "double", "else", "enum", "explicit", "export", "extern", "false",
    "float", "for", "friend", "goto", "if", "inline", "int", "long", "mutable",
    "namespace", "new", "noexcept", "not", "nullptr", "operator", "or",
    "private", "protected", "public", "register", "reinterpret_cast", "return",
    "short", "signed", "sizeof", "static", "struct", "switch", "template",
    "this", "throw", "true", "try", "typedef", "typeid", "typename", "union",
    "unsigned", "using", "virtual", "void", "volatile", "while"
}

# ---------- Token 规则 ----------
TOKEN_RULES = [
    (r'#.*', 'comment'),                      # # 注释
    (r'//.*?$', 'comment'),
    (r'/\*.*?\*/', 'comment', re.S),
    (r'"([^"\\]|\\.)*"', 'string'),
    (r"'([^'\\]|\\.)*'", 'string'),
    (r'\b(?:' + '|'.join(KEYWORDS) + r')\b', 'keyword'),
    (r'\b\d+(?:\.\d+)?\b', 'number'),
    (r'\b[A-Za-z_]\w*(?=\s*\()', 'function'),
    (r'[+\-*/=<>!&|%^~]+', 'operator'),
]

MAX_OUTPUT = 1 << 20
RUN_TIMEOUT = 10

class CppEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tk C++ Editor (Prism.js)")
        self.geometry("950x750")
        self.current_file = None
        self.theme = "light"
        self.mono = font.Font(family="Consolas", size=12)
        self.running = None
        self.build_ui()
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())
        self.bind_all("<F5>", lambda e: self.build_run())
        self.apply_theme()

    # ---------- UI ----------
    def build_ui(self):
        pan = ttk.PanedWindow(self, orient="vertical")
        pan.pack(fill="both", expand=1)

        edit_frm = ttk.Frame(pan)
        pan.add(edit_frm, weight=1)
        self.line_text = tk.Text(edit_frm, width=4, padx=4, takefocus=0,
                                 state="disabled", font=self.mono, wrap="none")
        self.line_text.pack(side="left", fill="y")
        self.text = tk.Text(edit_frm, font=self.mono, wrap="none", undo=True,
                            insertwidth=2, tabs="2c")
        self.text.pack(side="left", fill="both", expand=1)
        self.text.bind("<KeyRelease>", self.on_key)
        self.text.bind("<Button-1>",  self.on_key)
        self.text.bind("<Return>",    self.smart_indent)
        # 自动补全绑定
        self.text.bind("<KeyRelease>", self.auto_complete, add="+")

        io_frm = ttk.Frame(pan)
        pan.add(io_frm, weight=0)
        self.out = tk.Text(io_frm, height=10, state="disabled", font=self.mono)
        self.out.pack(fill="both", expand=1)
        in_frm = ttk.Frame(io_frm)
        in_frm.pack(fill="x")
        ttk.Label(in_frm, text="stdin:").pack(side="left", padx=4)
        self.stdin_entry = ttk.Entry(in_frm, font=self.mono)
        self.stdin_entry.pack(side="left", fill="x", expand=1, padx=4)
        self.stdin_entry.bind("<Return>", self.write_to_stdin)
        ttk.Button(in_frm, text="Send", command=self.write_to_stdin).pack(side="left", padx=4)

        # 菜单
        m = tk.Menu(self)
        self.config(menu=m)
        file_menu = tk.Menu(m, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As", command=self.save_as_file)
        m.add_cascade(label="File", menu=file_menu)
        run_menu = tk.Menu(m, tearoff=0)
        run_menu.add_command(label="Compile & Run (F5)", command=self.build_run)
        run_menu.add_command(label="Kill", command=self.kill_run)
        m.add_cascade(label="Run", menu=run_menu)
        theme_menu = tk.Menu(m, tearoff=0)
        theme_menu.add_command(label="Prism Light", command=lambda: self.switch_theme("light"))
        theme_menu.add_command(label="Prism Dark",  command=lambda: self.switch_theme("dark"))
        m.add_cascade(label="Theme", menu=theme_menu)

    # ---------- 文件 ----------
    def new_file(self):
        self.text.delete(1.0, "end")
        self.current_file = None
        self.title("Untitled – Tk C++ Editor")
        self.on_key()

    def open_file(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("C/C++", "*.c *.cpp *.h *.hpp"), ("All", "*")])
        if path:
            self.current_file = path
            with open(path, "r", encoding="utf-8") as f:
                self.text.delete(1.0, "end")
                self.text.insert("1.0", f.read())
            self.title(f"{os.path.basename(path)} – Tk C++ Editor")
            self.on_key()

    def save_file(self):
        if self.current_file:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.text.get(1.0, "end-1c"))
        else:
            self.save_as_file()

    def save_as_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".cpp",
                                            filetypes=[("C/C++", "*.c *.cpp *.h *.hpp"), ("All", "*")])
        if path:
            self.current_file = path
            self.save_file()

    # ---------- 输出 ----------
    def out_write(self, msg):
        self.out.config(state="normal")
        self.out.delete(1.0, "end")
        self.out.insert("1.0", msg)
        self.out.config(state="disabled")

    # ---------- 运行 ----------
    def build_run(self):
        if self.running:
            messagebox.showwarning("Running", "A process is already running.")
            return
        if not self.current_file:
            self.save_as_file()
            if not self.current_file:
                return
        self.save_file()

        exe = os.path.join(tempfile.gettempdir(),
                           f"cpp_tkeditor_{secrets.token_hex(8)}.exe" if os.name == "nt"
                           else f"cpp_tkeditor_{secrets.token_hex(8)}")
        cmd = ["g++", self.current_file, "-std=c++17", "-Wall", "-Wextra", "-o", exe]
        compile_proc = subprocess.run(cmd, capture_output=True, text=True)
        if compile_proc.returncode != 0:
            self.out_write("COMPILE ERROR\n" + compile_proc.stderr)
            return

        self.out_write("Running...\n")
        self.running = subprocess.Popen(
            [exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, universal_newlines=True, bufsize=0
        )
        threading.Thread(target=self.reader_thread, daemon=True).start()
        self.stdin_entry.focus_set()

    def kill_run(self):
        if self.running:
            self.running.kill()
            self.running = None

    def reader_thread(self):
        q = Queue()
        threading.Thread(target=self._enqueue_output, args=(self.running.stdout, q), daemon=True).start()
        out = []
        try:
            while self.running.poll() is None:
                try:
                    line = q.get(timeout=0.1)
                    out.append(line)
                    if sum(len(s) for s in out) > MAX_OUTPUT:
                        out.append("\n[输出截断]\n")
                        break
                except Empty:
                    continue
            self.running.wait(timeout=RUN_TIMEOUT)
        finally:
            self.running = None
            self.out_write("".join(out))

    def _enqueue_output(self, pipe, queue):
        with pipe:
            for line in iter(pipe.readline, ""):
                queue.put(line)

    def write_to_stdin(self, *_):
        if self.running and self.running.poll() is None:
            text = self.stdin_entry.get() + "\n"
            try:
                self.running.stdin.write(text)
                self.running.stdin.flush()
            except BrokenPipeError:
                pass
            self.stdin_entry.delete(0, "end")

    # ---------- 主题 ----------
    def switch_theme(self, theme_name):
        self.theme = theme_name
        self.apply_theme()

    def apply_theme(self):
        c = PRISM_COLORS[self.theme]
        for w in (self.text, self.out):
            w.config(bg=c["bg"], fg=c["fg"], selectbackground=c["sel"],
                     insertbackground=c["fg"])
        self.line_text.config(bg=c["bg"] if self.theme == "dark" else "#f0f0f0",
                              fg=c["fg"])
        for tag, style in c.items():
            if tag not in ("bg", "fg", "sel"):
                self.text.tag_config(tag, **style)

    # ---------- 行号 ----------
    def update_line_numbers(self):
        self.line_text.config(state="normal")
        self.line_text.delete(1.0, "end")
        line_cnt = int(self.text.index("end-1c").split(".")[0])
        self.line_text.insert("1.0", "\n".join(map(str, range(1, line_cnt + 1))))
        self.line_text.config(state="disabled")

    # ---------- 事件 ----------
    def on_key(self, event=None):
        self.update_line_numbers()
        self.highlight_all()

    # ---------- 缩进 ----------
    def smart_indent(self, event):
        line = self.text.get("insert linestart", "insert")
        indent = len(line) - len(line.lstrip())

        # 如果上一行以 { 结尾且本行开头是 }，则回退 4 空格
        prev_line = self.text.get("insert linestart - 1 lines", "insert linestart").rstrip()
        if prev_line.endswith('{') and line.lstrip() == '}':
            indent = max(0, indent - 4)

        self.text.insert("insert", "\n" + " " * indent)
        return "break"
    # ---------- 自动补全 ----------
    PAIRS = {"parenleft": "()", "bracketleft": "[]", "braceleft": "{}",
             "quotedbl": '""', "apostrophe": "''"}
    def auto_complete(self, event):
        key = event.keysym
        if key in self.PAIRS:
            pair = self.PAIRS[key]
            self.text.insert("insert", pair[1])
            self.text.mark_set("insert", "insert-1c")
    # ---------- Prism 高亮 ----------
    def highlight_all(self):
        self.text.tag_remove("all", 1.0, "end")
        first = int(self.text.index("@0,0").split(".")[0])
        last = int(self.text.index(f"@0,{self.text.winfo_height()}").split(".")[0])
        start, end = f"{max(1, first-3)}.0", f"{last+3}.0"
        code = self.text.get(start, end)
        for pattern, tag, *flags in TOKEN_RULES:
            flags = flags[0] if flags else 0
            for m in re.finditer(pattern, code, flags):
                idx1 = self.text.index(f"{start}+{m.start()}c")
                idx2 = self.text.index(f"{start}+{m.end()}c")
                self.text.tag_add(tag, idx1, idx2)
                self.text.tag_config(tag, **PRISM_COLORS[self.theme][tag])

# ---------------- 启动 ----------------
if __name__ == "__main__":
    if subprocess.run(["g++", "--version"], capture_output=True).returncode:
        messagebox.showerror("依赖缺失", "请安装 g++ 并加入 PATH")
        exit(1)
    CppEditor().mainloop()