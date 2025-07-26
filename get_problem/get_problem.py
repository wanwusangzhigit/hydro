#!/usr/bin/env python3
"""
by jason
2025-07-26
copyright wanwusangzhi 2024-2025
"""
import requests, re, sys
from bs4 import BeautifulSoup
import html2text

# ========== 按需修改 ==========
BASE_URL = input("")       # 你的站点根域名
LOGIN_URL = f'{BASE_URL}/login' # login page
Problem_ID = input("")
HOME_URL = f'{BASE_URL}/p/{Problem_ID}'
USERNAME  = input("")
PASSWORD  = input("")
# ===============================

def main():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36'
    })

    # 1. 拉登录页，取 csrf
    login_html = s.get(LOGIN_URL).text
    soup = BeautifulSoup(login_html, 'lxml')
    csrf = (soup.find('meta', attrs={'name': 'csrf-token'}) or
            soup.find('input', attrs={'name': re.compile(r'csrf|_csrf')}))
    if csrf:
        csrf = csrf.get('content') or csrf['value']
    else:
        csrf = ''          # 站点没开 csrf 验证

    # 2. 提交账号密码
    resp = s.post(LOGIN_URL, data={
        'uname': USERNAME,
        'password': PASSWORD,
        '_csrf': csrf
    }, allow_redirects=False)

    if resp.status_code != 302:
        raise RuntimeError('登录失败，请检查账号密码或抓包核对字段名')

    # 3. 登录成功后拿首页
    home_html = s.get(HOME_URL).text
    soup = BeautifulSoup(home_html, 'html.parser')
    for katex_span in soup.find_all('span', class_='katex'):
        annotation = katex_span.find('annotation')
        if annotation:
            katex_span.replace_with(f"${annotation.text}$")  # 可选：加 $ 变成 LaTeX 公式
        # 查找class="problem-content"的div
    problem_content = soup.find('div', class_='problem-content')
    html=problem_content
    print(html)
    # 创建 html2text 处理器
    h = html2text.HTML2Text()
    h.ignore_links = False  # 不忽略链接
    h.bypass_tables = False  # 不忽略表格
    h.ignore_images = False  # 不忽略图片
    h.body_width = 0  # 不自动换行
    		# 转换 HTML 为 Markdown
    markdown = h.handle(str(html))
    print(markdown)		
    with open("p.md","w",encoding='utf-8') as f:
        f.write(markdown)

if __name__ == '__main__':
    main()