#!/usr/bin/env python3
"""
by jason
2025-07-26
copyright wanwusangzhi 2024-2025
"""
import sys
import requests
import re
from bs4 import BeautifulSoup
import html2text

def main():
    # ---------- 1. 读取命令行参数 ----------
    if len(sys.argv) != 5:
        print("用法：python get_problem_cmd.py <oj题目的域的根域名> <题目ID> <用户名> <密码>")
        sys.exit(1)

    BASE_URL   = sys.argv[1].rstrip('/')   # 去掉尾部多余斜杠
    PROBLEM_ID = sys.argv[2]
    USERNAME   = sys.argv[3]
    PASSWORD   = sys.argv[4]

    LOGIN_URL = f'{BASE_URL}/login'
    PROBLEM_URL = f'{BASE_URL}/p/{PROBLEM_ID}'

    # ---------- 2. 创建会话 ----------
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36'
    })

    # ---------- 3. 获取登录页并提取 csrf ----------
    login_html = s.get(LOGIN_URL).text
    soup = BeautifulSoup(login_html, 'lxml')
    csrf = (soup.find('meta', attrs={'name': 'csrf-token'}) or
            soup.find('input', attrs={'name': re.compile(r'csrf|_csrf')}))
    csrf = csrf.get('content', '') if csrf else ''

    # ---------- 4. 登录 ----------
    resp = s.post(LOGIN_URL, data={
        'uname': USERNAME,
        'password': PASSWORD,
        '_csrf': csrf
    }, allow_redirects=False)

    if resp.status_code != 302:
        raise RuntimeError('登录失败，请检查账号/密码/字段名')

    # ---------- 5. 获取题目页面 ----------
    html = s.get(PROBLEM_URL).text
    soup = BeautifulSoup(html, 'html.parser')

    # 可选：把 KaTeX 公式转成纯 LaTeX
    for katex_span in soup.find_all('span', class_='katex'):
        annotation = katex_span.find('annotation')
        if annotation:
            katex_span.replace_with(f"${annotation.text}$")

    # 提取题面
    problem_content = soup.find('div', class_='problem-content')
    if not problem_content:
        raise RuntimeError('未找到 class="problem-content" 的节点')

    # ---------- 6. 转 Markdown ----------
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.bypass_tables = False
    h.ignore_images = False
    h.body_width = 0

    markdown = h.handle(str(problem_content))

    # ---------- 7. 保存 ----------
    with open(f"{PROBLEM_ID}.md", "w", encoding='utf-8') as f:
        f.write(markdown)
    print(f"已保存 {PROBLEM_ID}.md")

if __name__ == '__main__':
    main()