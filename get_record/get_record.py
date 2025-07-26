#!/usr/bin/env python3
import sys, requests
from bs4 import BeautifulSoup

if len(sys.argv) != 5:
    print("用法：python get_record.py <BASE> <USER> <PASS> <RID>")
    sys.exit(1)

BASE, USER, PASS, RID = sys.argv[1:]
LOGIN_URL = f"{BASE.rstrip('/')}/login"
REC_URL   = f"{BASE.rstrip('/')}/record/{RID}"

# 1. 登录
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})
s.get(LOGIN_URL)
csrf = s.cookies.get('sid.sig', '')
s.post(LOGIN_URL, data={'uname': USER, 'password': PASS, '_csrf': csrf})

# 2. 取记录页
html = s.get(REC_URL).text
soup = BeautifulSoup(html, 'lxml')

# 3. 定位和提取
h1 = soup.select_one('h1.section__title')
if not h1:
    print("UNKNOWN 0")
    sys.exit(0)

# 分数：h1 里第一个非图标的 <span>
score_span = next(
    (sp for sp in h1.find_all('span') if 'icon' not in sp.get('class', [])),
    None
)
score = score_span.get_text(strip=True) if score_span else '0'

# 状态：class 含 record-status--text 的 <span>
status_span = h1.select_one('span.record-status--text')
status = status_span.get_text(strip=True) if status_span else 'UNKNOWN'

print(status, score)