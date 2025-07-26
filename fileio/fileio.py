#!/usr/bin/env python3
import sys, requests, re
from bs4 import BeautifulSoup

if len(sys.argv) != 5:
    print("用法：python check_fileio.py <BASE> <PID> <USER> <PASS>")
    sys.exit(1)

BASE, PID, USER, PASS = sys.argv[1:]
LOGIN_URL = f"{BASE.rstrip('/')}/login"
PROB_URL  = f"{BASE.rstrip('/')}/p/{PID}"

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})

# 1. 登录
s.get(LOGIN_URL)
csrf = s.cookies.get('sid.sig', '')
resp = s.post(LOGIN_URL,
              data={'uname': USER, 'password': PASS, '_csrf': csrf},
              allow_redirects=False)
if resp.status_code != 302:
    raise RuntimeError('登录失败')

# 2. 取题面
html = s.get(PROB_URL).text

# 3. 提取文件IO
match = re.search(r'文件IO：\s*([^\s<>\n]+)', html)
if match:
    print(match.group(1).strip())   # 输出文件名
else:
    print('0')