import { editMateri, editSoal } from './guru/editor.js';
import { catatanTeknis, hapusAnalisisSekarang, renderAnalisis, resetData } from './guru/analisis.js';
import { hapusMateri, tambahMateri } from './guru/materi.js';
import { generateSoal, sinkronKelasManual, tambahSoalManual, terbitkanSoal } from './guru/soal.js';
import { pilihFile, tempelMateri } from './guru/upload.js';
import { kodeKelas, tingkatDari } from './konstanta.js';
import { geserSorot, pasangSemuaTilt, pasangTilt } from './efek/inti.js';
import { tampilkanView } from './efek/halaman.js';
import { kirimChat } from './siswa/chat.js';
import { batalLatihan, mulaiLatihan } from './siswa/latihan.js';
import { bacaMateri, tanyaMateri } from './siswa/materi.js';
import { buatRangkuman, simpanRangkuman } from './siswa/rangkuman.js';
import { aturRoleUI, bukaSidebar, tampilkanHalaman, tutupModal, tutupSidebar } from './ui.js';
import { $, $$ } from './util.js';
import { status, muat, bersihkanSesi } from './status.js';
import { api } from './api.js';
import { toast, bukaModal } from './ui.js';
import { elemen } from './util.js';

export const AKSI = {
  editMateri(el) { editMateri(el.dataset.id); },
  editSoal(el) { editSoal(el.dataset.id); },
  pilihRole(el) {
    $$('.rolebtn').forEach((b) => b.classList.remove('selected'));
    el.classList.add('selected');
    status.role = el.dataset.role;
    $('#loginUser').value = ''; 
    $('#barisKelasSiswa').style.display = 'none';
  },
  async masuk() {
    const button = $('[data-act="masuk"]');
    if (button.disabled) return;
    button.disabled = true;
    try {
      const fn = status.role === 'teacher' ? api.loginGuru : api.loginSiswa;
      const { pengguna } = await fn($('#loginUser').value.trim(), $('#loginPass').value);
      $('#loginPass').value = '';
      await bukaSesi(pengguna);
    } catch (e) { toast(e.message); }
    finally { button.disabled = false; }
  },
  async keluar() {
    await api.keluar();
    bersihkanSesi();
    batalLatihan();
    window._draftSoal = [];
    for (const id of ['messages', 'daftarSoal', 'daftarMateriGuru', 'tabelRiwayat', 'modalIsi']) {
      document.getElementById(id)?.replaceChildren();
    }
    $('#areaRangkuman').replaceChildren();
    tutupModal(); tutupSidebar();
    $('#appView').style.display = 'none';
    $('#loginView').style.display = 'grid';
    $('#loginPass').value = '';
  },
  bukaSidebar() { bukaSidebar(); },
  tutupSidebar() { tutupSidebar(); },
  bukaHalaman(el) { tampilkanHalaman(el.dataset.page); },
  catatanTeknis() { catatanTeknis(); },
  tutupModal() { tutupModal(); },
  kirimChat() { return kirimChat(); },
  chip(el) { return kirimChat(el.dataset.q); },
  bacaMateri(el) { bacaMateri(el.dataset.id); },
  tanyaMateri(el) { tanyaMateri(el.dataset.id); },
  keLatihan(el) {
    tutupModal();
    tampilkanHalaman('s-latihan');
    mulaiLatihan(el.dataset.id);
  },
  mulaiLatihan() { mulaiLatihan(); },
  batalLatihan() { batalLatihan(); },
  buatRangkuman() { buatRangkuman(); },
  rangkumanCepat(el) {
    $('#pilihMateriRangkuman').value = el.dataset.id;
    buatRangkuman();
  },
  simpanRangkuman(el) { return simpanRangkuman(el.dataset.id); },
  tambahMateri() { return tambahMateri(); },
  hapusMateri(el) { return hapusMateri(el.dataset.id); },
  bersihkanMateri() { $('#mJudul').value = ''; $('#mTeks').value = ''; },
  generateSoal() { generateSoal(); },
  terbitkanSoal() { return terbitkanSoal(); },
  tambahSoalManual() { return tambahSoalManual(); },
  pilihFile(el) { pilihFile(el); },
  tempelMateri() { return tempelMateri(); },
  resetData() { resetData(); },
  filterTingkat(el) { status.filterTingkat = el.dataset.tingkat; status.filterRombel = 'semua'; renderAnalisis(); },
  filterRombel(el) { status.filterRombel = el.dataset.rombel; renderAnalisis(); },
  pilihSemuaKelas(el) {
    const target = el.dataset.target;
    const t = el.dataset.tingkat;
    $$(`${target} input`).forEach((c) => { if (tingkatDari(c.value) === t) c.checked = true; });
  },
  hapusAnalisis() { return hapusAnalisisSekarang(); }
};

document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-act]');
  if (!el) return;
  const fn = AKSI[el.dataset.act];
  if (!fn) return;
  if (el.tagName === 'INPUT' && el.type === 'file') return;
  e.preventDefault();
  Promise.resolve().then(() => fn(el)).catch(e => toast(e.message));
});

$('#fileMateri').addEventListener('change', (e) => pilihFile(e.target));
$('#qMateriManual').addEventListener('change', sinkronKelasManual);

$('#chatInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); kirimChat(); }
});

$('#modal').addEventListener('click', (e) => { if (e.target.id === 'modal') tutupModal(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { tutupModal(); tutupSidebar(); } });

$('#appView').style.display = 'none';
$('#loginView').style.display = 'grid';
pasangSemuaTilt();
pasangTilt($('.login-card'), 7);
geserSorot();
window.addEventListener('resize', geserSorot);

async function bukaSesi(pengguna) {
  status.pengguna = pengguna;
  status.role = pengguna.peran === 'guru' ? 'teacher' : 'student';
  status.kelasSiswa = pengguna.kelas || '';
  if (pengguna.wajibGantiSandi) { gantiAwal(); return; }
  await muat();
  $('#loginView').style.display = 'none';
  $('#appView').style.display = 'flex';
  aturRoleUI();
}
function gantiAwal() {
  const lama = elemen('input', { type: 'password', required: true, autocomplete: 'current-password', placeholder: 'Kata sandi awal' });
  const baru = elemen('input', { type: 'password', required: true, minlength: '8', autocomplete: 'new-password', placeholder: 'Kata sandi baru (min. 8 karakter)' });
  const pesan = elemen('p', { role: 'alert' });
  const tombol = elemen('button', { type: 'submit', class: 'btn primary' }, 'Ganti kata sandi');
  const form = elemen('form', {}, lama, baru, pesan, tombol);
  form.addEventListener('submit', async e => {
    e.preventDefault(); tombol.disabled = true;
    try {
      await api.gantiSandi(lama.value, baru.value);
      const { pengguna } = await api.saya();
      await bukaSesi(pengguna); tutupModal();
    } catch (e) { pesan.textContent = e.message; }
    finally { tombol.disabled = false; }
  });
  bukaModal('Keamanan akun', 'Ganti kata sandi awal', form);
}
$('#barisKelasSiswa').style.display = 'none';
$('#loginPass').addEventListener('keydown', e => { if (e.key === 'Enter') AKSI.masuk(); });
api.saya().then(({pengguna}) => bukaSesi(pengguna)).catch(e => { if (e.status !== 401) toast(e.message); });
