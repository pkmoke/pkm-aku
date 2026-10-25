"""Bounded real HTTP+PostgreSQL integration checks using disposable local accounts."""
import json,os,sys
from pathlib import Path
import httpx
runtime=json.loads(Path('/private/tmp/bemai-runtime.json').read_text())
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8899'
origin='https://husked-reappoint-from.ngrok-free.dev' if base.startswith('https') else base
headers={'Origin':origin,'X-Requested-With':'bemai','ngrok-skip-browser-warning':'1'}
checks=[]
def check(name,condition):
 checks.append({'name':name,'pass':bool(condition)})
 if not condition: raise AssertionError(name)
def login(account):
 c=httpx.Client(base_url=base,headers=headers,timeout=20)
 r=c.post('/api/auth/login/'+account['peran'],json={'identitas':account['identitas'],'kataSandi':account['sandi']})
 check('login '+account['identitas'],r.status_code==200)
 # Local HTTP check uses the real secure cookie over HTTPS only; for loopback
 # transport send the server-issued token explicitly without weakening server config.
 if base.startswith('http:'):
  c.headers['Cookie']='bemai_sesi='+r.cookies['bemai_sesi']
 return c
anon=httpx.Client(base_url=base,headers=headers,timeout=20)
check('health',anon.get('/api/health').json()=={'status':'ok'})
check('anonymous state denied',anon.get('/api/state').status_code==401)
check('seed answer asset unavailable',anon.get('/src/js/data-contoh.js').status_code==404)
t=login(runtime['accounts'][0]);a=login(runtime['accounts'][1]);b=login(runtime['accounts'][2])
created=[]
try:
 check('student cannot write material',a.post('/api/materi',json={}).status_code==403)
 check('student cannot read teacher analytics',a.get('/api/analisis').status_code==403)
 check('wrong origin blocked',t.post('/api/materi',json={},headers={'Origin':'https://attacker.invalid'}).status_code==403)
 r=t.post('/api/materi',json={'mapel':'IPA','kelas':'VIII','rombel':['A'],'judul':'Materi Uji Integrasi','teks':['Integrasi adalah penyambungan frontend dan backend.'],'rangkuman':['Integrasi menghubungkan aplikasi.']})
 check('teacher creates material',r.status_code==200);m=r.json();created.append(m['id'])
 check('other class cannot read material',b.get('/api/materi/'+m['id']).status_code==404)
 check('correct class sees material',a.get('/api/materi/'+m['id']).status_code==200)
 q={'materiId':m['id'],'tanya':'Apa itu integrasi?','opsi':['Penyambungan','Pemutusan'],'jawaban':0,'kelas':['VIII A'],'pembahasan':'Penyambungan frontend dan backend.'}
 r=t.post('/api/soal',json=q);check('teacher creates question',r.status_code==200);s=r.json()
 bad={**q,'kelas':['VII B']}
 check('cross-class publishing rejected',t.post('/api/soal',json=bad).status_code==400)
 student_soal=a.get('/api/soal').json()
 check('student list contains no answer/explanation',all('jawaban' not in x and 'pembahasan' not in x for x in student_soal))
 check('other class has no question',all(x['id']!=s['id'] for x in b.get('/api/soal').json()))
 r=a.post('/api/latihan',json={'materiId':m['id'],'jawaban':[{'soalId':s['id'],'pilihan':1}],'nilai':100,'benar':1})
 check('forged client score ignored',r.status_code==200 and r.json()['nilai']==0)
 h=r.json()
 check('server returns explanation after grading',h['detail'][0]['kunci']==0)
 check('other student history isolated',all(x['id']!=h['id'] for x in b.get('/api/state').json()['hasil']))
 r=a.post('/api/latihan',json={'materiId':m['id'],'ulangDari':h['id'],'jawaban':[{'soalId':s['id'],'pilihan':0}]})
 check('retry server graded',r.status_code==200 and r.json()['nilai']==100)
 check('other class cannot submit',b.post('/api/latihan',json={'materiId':m['id'],'jawaban':[{'soalId':s['id'],'pilihan':0}]}).status_code==404)
 check('duplicate question ids rejected',a.post('/api/latihan',json={'materiId':m['id'],'jawaban':[{'soalId':s['id'],'pilihan':0}]*2}).status_code==400)
 check('server chat works',a.post('/api/chat',json={'pertanyaan':'Apa itu integrasi?'}).json()['jawaban'] is not None)
 token=a.cookies.get('bemai_sesi')
 check('logout',a.post('/api/auth/logout').status_code==204)
 check('revoked token rejected',anon.get('/api/state',headers={'Cookie':'bemai_sesi='+token}).status_code==401)
 check('teacher dashboard reflects results',t.get('/api/dashboard').json()['latihan']>=2)
finally:
 for ident in created: t.delete('/api/materi/'+ident)
 for c in [t,a,b]:
  c.post('/api/auth/logout');c.close()
Path(__file__).with_name('integration-http-results.json').write_text(json.dumps({'base':base,'checks':checks},indent=2))
print(f'PASS {len(checks)} real HTTP/database checks on {base}')
