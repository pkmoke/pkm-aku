"""HTTP/ASGI tests of real FastAPI routes. DB and authenticated identities are test doubles.
Run: /private/tmp/bemai-api-audit-venv/bin/python audit/api_checks.py
Does not start lifespan, connect PostgreSQL, or modify application source.
"""
import os
import sys
import json
import runpy
from pathlib import Path
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['DATABASE_URL'] = 'postgresql://unused:unused@127.0.0.1:1/unused'
os.environ['COOKIE_SECURE'] = 'true'
os.environ['ASAL_DIIZINKAN'] = 'https://testserver'
from fastapi.testclient import TestClient
from app.main import app
from app.db import koneksi
from app.deps import sesi_pengguna, Pengguna
from app.security import hash_sandi

matrix = runpy.run_path(str(ROOT / 'backend/tests/test_auth_dan_rbac.py'))
TEACHER = matrix['ENDPOINT_GURU']
STUDENT = matrix['ENDPOINT_SISWA']
BOTH = matrix['ENDPOINT_KEDUANYA']
H = {'X-Requested-With': 'bemai', 'Origin': 'https://testserver'}
results = []

class FakeDB:
    def __init__(self):
        self.calls = []
        self.raise_error = False
        self.password_hash = hash_sandi('audit-test-old-password')
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if self.raise_error:
            raise RuntimeError('INTERNAL_AUDIT_MARKER')
        self.sql = sql
        return self
    def fetchone(self):
        if 'select kata_sandi_hash' in self.sql:
            return {'kata_sandi_hash': self.password_hash}
        return None
    def commit(self):
        pass

db = FakeDB()
app.dependency_overrides[koneksi] = lambda: db
client = TestClient(app, base_url='https://testserver', raise_server_exceptions=False)

def record(name, actual, expected):
    ok = actual == expected
    results.append({'name': name, 'actual': actual, 'expected': expected, 'pass': ok})
    if not ok:
        print('MISMATCH', name, actual, expected)

def request(method, url, headers=None, body=None):
    return client.request(method, url, headers=H if headers is None else headers,
                          **({'json': {} if body is None else body} if method in ('POST','PUT','PATCH') else {}))

# Real cookie guard, using DB double only for lookup.
for m, u in TEACHER + STUDENT + BOTH:
    record(f'anonymous {m} {u}', request(m,u).status_code, 401)
client.cookies.set('bemai_sesi', 'invalid-session')
record('invalid session rejected', request('GET','/api/materi').status_code,401)
client.cookies.clear()

# Explicitly injected identity tests only: does not prove real login/session persistence.
for role, denied, allowed in [('siswa', TEACHER, STUDENT+BOTH), ('guru', STUDENT, TEACHER+BOTH)]:
    app.dependency_overrides[sesi_pengguna] = lambda role=role: Pengguna('00000000-0000-0000-0000-000000000001','Audit',role,'AUDIT' if role=='siswa' else None,'VIII' if role=='siswa' else None,'A' if role=='siswa' else None,False)
    for m,u in denied:
        record(f'{role} blocked {m} {u}',request(m,u).status_code,403)
    for m,u in allowed:
        record(f'{role} allowed but stub {m} {u}',request(m,u).status_code,501)

app.dependency_overrides[sesi_pengguna] = lambda: Pengguna('00000000-0000-0000-0000-000000000001','Audit','siswa','AUDIT','VIII','A',True)
record('initial-password account blocked',request('GET','/api/materi').status_code,403)
record('initial-password account can read profile',request('GET','/api/auth/saya').status_code,200)
app.dependency_overrides.pop(sesi_pengguna)

for label, headers in [('missing custom header',{}),('wrong origin',{'X-Requested-With':'bemai','Origin':'https://attacker.invalid'}),('null origin',{'X-Requested-With':'bemai','Origin':'null'})]:
    record(label,request('POST','/api/auth/login/guru',headers,{'identitas':'audit','kataSandi':'wrong'}).status_code,403)
record('CORS preflight not allowed',client.options('/api/auth/login/guru',headers={'Origin':'https://attacker.invalid','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'x-requested-with,content-type'}).status_code,405)
for body in [{},{'identitas':'','kataSandi':'x'},{'identitas':'a'*121,'kataSandi':'x'},{'identitas':'x','kataSandi':'a'*201}]:
    record('invalid login body '+str(len(str(body))),request('POST','/api/auth/login/guru',body=body).status_code,400)
for identity in ['missing@audit.invalid',"' OR 1=1 --"]:
    record('unknown/injection identity rejected',request('POST','/api/auth/login/guru',body={'identitas':identity,'kataSandi':'invalid'}).status_code,401)
    login_call = next((p for s,p in reversed(db.calls) if 'from pengguna where' in s),None)
    record('identity passed as SQL parameter',login_call,('guru',identity))

# Bounded reproduction of missing throttling and failed-attempt audit on password change.
app.dependency_overrides[sesi_pengguna] = lambda: Pengguna('00000000-0000-0000-0000-000000000001','Audit','guru',None,None,None,False)
db.calls.clear()
codes = [request('POST','/api/auth/ganti-sandi',body={'kataSandiLama':'incorrect','kataSandiBaru':'audit-new-password'}).status_code for _ in range(6)]
record('six wrong old-password attempts processed without 429',codes,[400]*6)
record('no failed-password audit write',any('insert into log_audit' in s for s,p in db.calls),False)
app.dependency_overrides.pop(sesi_pengguna)
record('health responds',request('GET','/api/health').status_code,200)
record('docs disabled',request('GET','/api/docs').status_code,404)
record('openapi disabled',request('GET','/api/openapi.json').status_code,404)
record('unknown route JSON error',request('GET','/api/missing').json()['error']['kode'],'tidak_ada')
record('profile response no-store',request('GET','/api/auth/saya').headers.get('cache-control'),'no-store')
db.raise_error = True
r = request('GET','/api/health')
record('unexpected DB error status',r.status_code,500)
record('unexpected DB error is plain text',r.headers.get('content-type'),'text/plain; charset=utf-8')
record('internal marker not exposed','INTERNAL_AUDIT_MARKER' in r.text,False)
app.dependency_overrides.clear()
report = {'scope':'Real FastAPI HTTP/ASGI; fake DB and injected identities for RBAC; not PostgreSQL or public backend test','checks':len(results),'passed':sum(x['pass'] for x in results),'results':results}
(ROOT/'audit/api-results.json').write_text(json.dumps(report,indent=2))
print(f"Checks: {report['checks']}; passed: {report['passed']}")
sys.exit(0 if report['checks']==report['passed'] else 1)
