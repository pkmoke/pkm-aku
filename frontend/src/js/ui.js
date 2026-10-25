import { renderAnalisis } from './guru/analisis.js';
import { renderDashboard } from './guru/dashboard.js';
import { renderKelolaMateri } from './guru/materi.js';
import { renderKelolaSoal } from './guru/soal.js';
import { renderUpload } from './guru/upload.js';
import { renderKelolaSiswa } from './guru/siswa.js';
import { SISWA } from './konstanta.js';
import { renderPilihLatihan } from './siswa/latihan.js';
import { renderChips, renderMateriSiswa } from './siswa/materi.js';
import { renderPilihRangkuman } from './siswa/rangkuman.js';
import { renderRiwayat } from './siswa/riwayat.js';
import { jalankanEfek, tampilkanKerangka } from './efek/halaman.js';
import { $, $$ } from './util.js';
import { status, muat } from './status.js';

export const JUDUL = {
  's-chat': 'Bemai — Chat Siswa', 's-materi': 'Materi Pembelajaran', 's-latihan': 'Latihan Soal',
  's-rangkuman': 'Rangkuman Materi', 's-riwayat': 'Riwayat Belajar',
  't-dashboard': 'Dashboard Guru', 't-materi': 'Kelola Materi', 't-soal': 'Kelola Soal',
  't-upload': 'Upload Dokumen', 't-analisis': 'Analisis Hasil Belajar',
  't-siswa': 'Kelola Siswa'
};

export function toast(pesan) {
  const t = $('#toast');
  t.textContent = pesan;
  t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove('show'), 2600);
}
function judulAtas(id) {
  const j = JUDUL[id] || 'Bemai';
  return window.innerWidth < 900 ? j.replace('Bemai — ', '') : j;
}

export function tampilkanHalaman(id) {
  if (status.role === 'student' && id.startsWith('t-')) return;
  $$('.page').forEach((p) => p.classList.toggle('active', p.id === id));
  if (status.role === 'student' && id.startsWith('t-')) return;
  const nav = $(status.role === 'student' ? '#navStudent' : '#navTeacher');
  $$('button', nav).forEach((b) => b.classList.toggle('active', b.dataset.page === id));
  $('#topTitle').textContent = judulAtas(id);
  tutupSidebar();
  tampilkanKerangka(id, async () => {
    try { await muat(); segarkanHalaman(); jalankanEfek(id); }
    catch (e) { toast(e.message); }
  });
}

export function segarkanHalaman() {
  const aktif = $('.page.active')?.id;
  if (aktif === 's-materi') renderMateriSiswa();
  if (aktif === 's-latihan') renderPilihLatihan();
  if (aktif === 's-rangkuman') renderPilihRangkuman();
  if (aktif === 's-riwayat') renderRiwayat();
  if (aktif === 't-dashboard') renderDashboard();
  if (aktif === 't-materi') renderKelolaMateri();
  if (aktif === 't-soal') renderKelolaSoal();
  if (aktif === 't-upload') renderUpload();
  if (aktif === 't-siswa') renderKelolaSiswa();
  if (aktif === 't-analisis') renderAnalisis();
}

export function aturRoleUI() {
  const guru = status.role === 'teacher';
  document.body.classList.toggle('mode-guru', guru);
  document.body.classList.toggle('mode-siswa', !guru);
  $('#navStudent').style.display = guru ? 'none' : 'grid';
  $('#navTeacher').style.display = guru ? 'grid' : 'none';
  $('#roleLabel').textContent = guru ? 'Mode Guru' : 'Mode Siswa';
  $('#userName').textContent = status.pengguna?.nama || '';
  $('#userAvatar').textContent = (status.pengguna?.nama || '?').slice(0, 1);
  $('#chipKelas').textContent = guru ? 'Semua kelas' : 'Kelas ' + status.kelasSiswa;
  $('#labelKelasChat').textContent = 'kelas ' + status.kelasSiswa;
  $('#labelKelasLatihan').textContent = status.kelasSiswa;
  $('#sapaanNama').textContent = status.pengguna?.nama || ''; 
  $('#areaLatihan').replaceChildren();
  renderChips();
  tampilkanHalaman(guru ? 't-dashboard' : 's-chat');
}

function tandaiMenu(terbuka) {
  const h = $('.hamburger');
  if (h) h.setAttribute('aria-expanded', terbuka ? 'true' : 'false');
  document.body.classList.toggle('nav-terbuka', terbuka);
}
export function bukaSidebar() {
  $('#sidebar').classList.add('open');
  $('#overlay').classList.add('open');
  tandaiMenu(true);
}
export function tutupSidebar() {
  $('#sidebar').classList.remove('open');
  $('#overlay').classList.remove('open');
  tandaiMenu(false);
}

export function bukaModal(tag, judul, isi) {
  $('#modalTag').textContent = tag;
  $('#modalJudul').textContent = judul;
  // Legacy callers still pass escaped HTML; new renderers pass DOM nodes.
  if (typeof isi === 'string') $('#modalIsi').innerHTML = isi;
  else $('#modalIsi').replaceChildren(...(Array.isArray(isi) ? isi : [isi]));
  $('#modal').classList.add('open');
}
export function tutupModal() { $('#modal').classList.remove('open'); }
