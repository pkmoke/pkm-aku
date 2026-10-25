import { api } from './api.js';
const kosong = () => ({ materi: [], soal: [], hasil: [], aktivitas: [], chat: [], dihapus: 0 });
export const status = { db: kosong(), pengguna: null, kelasSiswa: '', filterTingkat: 'semua', filterRombel: 'semua', role: 'student' };
let generasi = 0;
export async function muat() {
  const saatMulai = generasi;
  const data = await api.get('/state');
  if (saatMulai === generasi) status.db = data;
  return status.db;
}
export function bersihkanSesi() { generasi++; status.db = kosong(); status.pengguna = null; status.kelasSiswa = ''; status.role = 'student'; }
// Legacy renderers may still call these. Persistence is performed explicitly through API operations.
export function simpan() {}
export function simpanKe() { throw new Error('Gunakan API untuk menyimpan data'); }
export function bersihkanDataLama() {
  const batas = Date.now() - 86400000;
  for (const key of ['hasil', 'aktivitas', 'chat']) status.db[key] = status.db[key].filter(x => x.waktu >= batas);
  return 0;
}
export function catat() {}
