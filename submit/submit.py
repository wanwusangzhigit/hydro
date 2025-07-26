#!/usr/bin/env python3
import sys, requests, re
from bs4 import BeautifulSoup
def main():
    if len(sys.argv) != 7:
        print("用法：python submit.py <BASE> <PID> <USER> <PASS> <FILE> <LANG>")
        sys.exit(1)

    BASE, PID, USER, PASS, FILE, LANG = sys.argv[1:]
    LOGIN_URL  = f"{BASE.rstrip('/')}/login"
    SUBMIT_URL = f"{BASE.rstrip('/')}/p/{PID}/submit"

    # 1. 建立会话
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Referer': SUBMIT_URL
    })

    # 2. 首次 GET 登录页 → 取 Cookie 中的 CSRF
    s.get(LOGIN_URL)
    csrf_login = s.cookies.get('sid.sig', '')

    # 3. 登录
    resp = s.post(LOGIN_URL, data={
        'uname': USER,
        'password': PASS,
        '_csrf': csrf_login
    }, allow_redirects=False)
    if resp.status_code != 302:
        raise RuntimeError('登录失败')

    # 4. GET 提交页 → 取新的 CSRF
    submit_html = s.get(SUBMIT_URL).text
    soup = BeautifulSoup(submit_html, 'lxml')
    csrf_submit = None

# 1) meta 标签
    meta = soup.find('meta', attrs={'name': 'csrf-token'})
    if meta:
        csrf_submit = meta['content']
# 2) 隐藏域
    else:
        inp = soup.find('input', attrs={'name': re.compile(r'csrf|_csrf')})
        csrf_submit = inp['value'] if inp else None

# 3) 兜底：如果都没有，就直接用 Cookie 里的 sid.sig
    if not csrf_submit:
        csrf_submit = s.cookies.get('sid.sig', '')

    if not csrf_submit:
        print('⚠️ 无法提取 CSRF，页面预览：')
        print(submit_html)
        sys.exit(1)
    # 5. 读源码
    with open(FILE, encoding='utf-8') as f:
        code = f.read()

    # 6. POST 提交
    # 6.1 转换 LANG
    if LANG =='cpp':
        LANG = 'cc.cc14o2'
    elif LANG == 'python' or LANG == 'py':
        LANG = 'py.py3'
    payload = {'_csrf': csrf_submit, 'lang': LANG, 'code': code}
    resp = s.post(SUBMIT_URL, data=payload, allow_redirects=False)
    if resp.status_code == 302:
        rid = resp.headers['Location'].split('/')[-1]
        print(f'提交成功！记录号：{rid}')
        print(f'查看结果：{BASE}/record/{rid}')
    else:
        print('提交失败，状态码', resp.status_code)

if __name__ == '__main__':
    main()