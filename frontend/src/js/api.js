// Semua komunikasi server memakai cookie sesi pada origin yang sama.
const BASE = '/api';

export class GalatApi extends Error {
  constructor(status, kode, pesan) { super(pesan); this.status = status; this.kode = kode; }
}

async function minta(metode, path, body) {
  const opsi = {
    method: metode,
    credentials: 'same-origin',
    headers: { 'X-Requested-With': 'bemai' },   // wajib untuk request yang mengubah data (anti-CSRF)
  };
  if (body !== undefined) {
    opsi.headers['Content-Type'] = 'application/json';
    opsi.body = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, opsi);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const g = data.error || {};
    throw new GalatApi(res.status, g.kode || 'galat', g.pesan || 'Terjadi kesalahan');
  }
  return data;
}

export const api = {
  get: (p) => minta('GET', p),
  post: (p, b = {}) => minta('POST', p, b),
  put: (p, b = {}) => minta('PUT', p, b),
  hapus: (p) => minta('DELETE', p),
  // Peran ditentukan server dari akun; tidak ada parameter peran dari browser.
  loginGuru: (identitas, kataSandi) => minta('POST', '/auth/login/guru', { identitas, kataSandi }),
  loginSiswa: (identitas, kataSandi) => minta('POST', '/auth/login/siswa', { identitas, kataSandi }),
  saya: () => minta('GET', '/auth/saya'),
  keluar: () => minta('POST', '/auth/logout', {}),
  gantiSandi: (kataSandiLama, kataSandiBaru) => minta('POST', '/auth/ganti-sandi', { kataSandiLama, kataSandiBaru }),
};
