"""Verify initial-password UI with a disposable account, then delete it."""
import json,secrets,sys,os
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
from app.akun import buat_siswa
r=json.loads(Path('/private/tmp/bemai-runtime.json').read_text())
url=r['env']['DATABASE_URL']
with psycopg.connect(url,row_factory=dict_row) as c:
 ident,old=buat_siswa(c,'BROWSERINIT','Siswa Sandi Awal','VIII','A')
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  ctx=browser.new_context(extra_http_headers={'ngrok-skip-browser-warning':'1'},reduced_motion='reduce')
  page=ctx.new_page();page.goto('https://husked-reappoint-from.ngrok-free.dev')
  page.locator('#loginUser').fill('BROWSERINIT');page.locator('#loginPass').fill(old)
  page.locator('[data-act="masuk"]').click()
  page.locator('#modal.open').wait_for()
  assert not page.locator('#appView').is_visible()
  page.locator('#modalIsi input').nth(0).fill(old)
  page.locator('#modalIsi input').nth(1).fill(secrets.token_urlsafe(16))
  page.locator('#modalIsi button[type="submit"]').click()
  page.locator('#appView').wait_for(state='visible',timeout=20000)
  assert page.locator('#userName').inner_text()=='Siswa Sandi Awal'
  assert not page.locator('#modal').is_visible()
  assert ctx.request.get('https://husked-reappoint-from.ngrok-free.dev/api/auth/saya').json()['pengguna']['wajibGantiSandi'] is False
  browser.close()
 print('PASS initial-password UI, server update and gated access over public HTTPS')
finally:
 with psycopg.connect(url) as c: c.execute('delete from pengguna where id=%s',(ident,))
