#!/usr/bin/env python3
# pip install requests beautifulsoup4

import os
import re
import sys
import json
import requests
from bs4 import BeautifulSoup

# ========== 用户配置 ==========
BASE_URL = 'https://hydro.ac'        # Hydro 站点根地址
USERNAME = 'your_username'
PASSWORD = 'your_password'
# ===============================

LOGIN_URL   = f'{BASE_URL}/login'
PROBLEM_API = f'{BASE_URL}/api/problem'     # REST 风格接口
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36'
}

session = requests.Session()
session.headers.update(HEADERS)

# ---------- 1. 登录 ----------
def login() -> None:
    login_page = session.get(LOGIN_URL)
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text).group(1)

    resp = session.post(LOGIN_URL, data={
        'uname': USERNAME,
        'password': PASSWORD,
        'csrf_token': csrf
    }, allow_redirects=False)
    if resp.status_code != 302:
        raise RuntimeError('登录失败，请检查账号密码')

# ---------- 2. 拉取题目 ----------
def fetch_problem(pid: str, save_dir: str = '.') -> None:
    """pid 形如 P1000 / B / A+B 均可"""
    # 2.1 获取题面（Markdown）
    info_resp = session.get(f'{PROBLEM_API}/{pid}')
    info_resp.raise_for_status()
    info = info_resp.json()

    title = info['title']
    md = info['content']                    # 已经是 Markdown
    tags = ', '.join(info.get('tag', []))
    limits = f"时间限制：{info['time_limit']} ms  \n内存限制：{info['memory_limit']} MiB"

    # 2.2 保存题面
    os.makedirs(save_dir, exist_ok=True)
    md_path = os.path.join(save_dir, f'{pid}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {pid} - {title}\n\n")
        f.write(f"{tags}\n\n{limits}\n\n---\n\n")
        f.write(md)
    print(f'已保存 {md_path}')

    # 2.3 下载测试数据
    data_resp = session.get(f'{PROBLEM_API}/{pid}/testdata')
    data_resp.raise_for_status()
    data = data_resp.json()
    for filename, content in data.items():
        with open(os.path.join(save_dir, filename), 'wb') as f:
            f.write(content.encode() if isinstance(content, str) else content)
    print(f'测试数据已保存到 {save_dir}/')

# ---------- 3. 主函数 ----------
def main():
    if len(sys.argv) < 2:
        print('用法：python hydro_crawler.py <题号>')
        sys.exit(1)

    pid = sys.argv[1]
    login()
    fetch_problem(pid, pid)

if __name__ == '__main__':
    main()