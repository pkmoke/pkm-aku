import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
runtime=json.loads(Path('/private/tmp/bemai-runtime.json').read_text())
base='https://husked-reappoint-from.ngrok-free.dev'
checks=[]
def check(name, condition=True):
 assert condition,name
 checks.append(name)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 context=browser.new_context(extra_http_headers={'ngrok-skip-browser-warning':'1'},reduced_motion='reduce')
 page=context.new_page()
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('dialog',lambda d:d.accept())
 page.goto(base)
 page.wait_for_response(lambda r:'/api/auth/saya' in r.url) if False else None
 def login(acc):
  page.locator('[data-act="pilihRole"][data-role="'+('teacher' if acc['peran']=='guru' else 'student')+'"]').click()
  page.locator('#loginUser').fill(acc['identitas']);page.locator('#loginPass').fill(acc['sandi'])
  page.locator('[data-act="masuk"]').click()
  page.locator('#appView').wait_for(state='visible',timeout=20000)
 def logout():
  page.locator('[data-act="keluar"]').click()
  page.locator('#loginView').wait_for(state='visible')
 teacher=runtime['accounts'][0];student=runtime['accounts'][1]
 page.locator('[data-act="pilihRole"][data-role="teacher"]').click()
 page.locator('#loginUser').fill(teacher['identitas']);page.locator('#loginPass').fill('intentionally-wrong')
 with page.expect_response(lambda r:'/api/auth/login/guru' in r.url) as resp: page.locator('[data-act="masuk"]').click()
 check('wrong password rejected',resp.value.status==401)
 check('wrong login does not reveal app',not page.locator('#appView').is_visible())
 login(teacher)
 check('teacher identity shown','Guru Uji' in page.locator('#userName').inner_text())
 page.locator('[data-page="t-materi"]').click()
 page.locator('#daftarMateriGuru [data-act="editMateri"]').first.wait_for()
 page.locator('#mJudul').fill('Materi Browser Terhubung')
 page.locator('#mTeks').fill('Browser adalah aplikasi untuk membuka halaman web.\nServer adalah aplikasi untuk memproses permintaan.')
 with page.expect_response(lambda r:r.url.endswith('/api/materi') and r.request.method=='POST') as resp:
  page.locator('[data-act="tambahMateri"]').click()
 check('material form saves through API',resp.value.status==200)
 ident=resp.value.json()['id']
 try:
  page.get_by_text('Materi Browser Terhubung',exact=True).wait_for()
  page.reload();page.locator('#appView').wait_for(state='visible')
  check('session restored after reload',page.locator('#userName').inner_text()=='Guru Uji')
  page.locator('[data-page="t-materi"]').click()
  page.locator('[data-act="editMateri"][data-id="'+ident+'"]').wait_for()
  check('material persisted across reload')
  page.locator('[data-page="t-analisis"]').click()
  page.locator('[data-act="filterTingkat"][data-tingkat="VIII"]').wait_for()
  page.locator('[data-act="filterTingkat"][data-tingkat="VIII"]').click()
  page.locator('[data-act="filterRombel"][data-rombel="A"]').wait_for()
  check('analysis filter click works')
  logout();login(student)
  check('class from server','VIII A' in page.locator('#chipKelas').inner_text())
  page.locator('[data-page="s-materi"]').click()
  page.get_by_text('Materi Browser Terhubung',exact=True).wait_for()
  check('teacher material visible to student')
  state=page.evaluate("async () => (await fetch('/api/state')).json()")
  check('no answer keys in student question list',all('jawaban' not in s for s in state['soal']))
  page.locator('[data-page="s-latihan"]').click()
  page.locator('#pilihLatihanCepat [data-act="keLatihan"]').first.wait_for()
  page.locator('#pilihLatihanCepat [data-act="keLatihan"]').first.click()
  page.locator('#formLatihan').wait_for()
  for item in page.locator('#formLatihan [data-soal]').all(): item.locator('input').first.check()
  with page.expect_response(lambda r:r.url.endswith('/api/latihan') and r.request.method=='POST') as resp:
   page.locator('#formLatihan button[type="submit"]').click()
  check('quiz sent to backend',resp.value.status==200)
  page.locator('#pembahasanLatihan').wait_for()
  check('server score displayed',page.get_by_text('Nilai kamu: '+str(resp.value.json()['nilai'])+'/100',exact=True).count()==1)
  page.locator('[data-page="s-chat"]').click()
  page.locator('#chatInput').fill('Apa itu alveolus?')
  with page.expect_response(lambda r:r.url.endswith('/api/chat') and r.request.method=='POST') as resp:
   page.locator('[data-act="kirimChat"]').click()
  check('chat uses backend',resp.value.status==200)
  page.locator('.bubble.bot:not(.mengetik)').last.wait_for()
  logout()
  check('chat cleared on logout',page.locator('#messages').inner_text()=='')
  check('no local persistence',page.evaluate("localStorage.getItem('bemai.v1')") is None)
  check('no browser runtime errors',not errors)
  page.screenshot(path='/private/tmp/bemai-connected.png',full_page=True)
 finally:
  # Dispose only the material created by this test, through authenticated API.
  acc=runtime['accounts'][0]
  context.request.post(base+'/api/auth/login/guru',headers={'Origin':base,'X-Requested-With':'bemai'},data={'identitas':acc['identitas'],'kataSandi':acc['sandi']})
  context.request.delete(base+'/api/materi/'+ident,headers={'Origin':base,'X-Requested-With':'bemai'})
  context.request.post(base+'/api/auth/logout',headers={'Origin':base,'X-Requested-With':'bemai'},data={})
 browser.close()
Path(__file__).with_name('integration-browser-results.json').write_text(json.dumps({'base':base,'checks':checks,'browserErrors':errors},indent=2))
print('PASS',len(checks),'browser checks over public HTTPS')
