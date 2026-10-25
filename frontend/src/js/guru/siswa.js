import { api } from '../api.js';
import { ROMBEL, TINGKAT } from '../konstanta.js';
import { bukaModal, toast } from '../ui.js';
import { $, elemen, esc } from '../util.js';

const keadaan = { tingkat: '', rombel: '', cari: '', daftar: [] };

document.addEventListener('keydown', (e) => {
  if (e.target.id === 'cariSiswa' && e.key === 'Enter') {
    e.preventDefault();
    cariSiswa();
  }
});

export function renderKelolaSiswa() {
  muatSiswa().catch((e) => toast(e.message));
}

async function muatSiswa() {
  const q = new URLSearchParams();
  if (keadaan.tingkat) q.set('tingkat', keadaan.tingkat);
  if (keadaan.rombel) q.set('rombel', keadaan.rombel);
  if (keadaan.cari) q.set('cari', keadaan.cari);
  const [daftar, kelas] = await Promise.all([
    api.get('/siswa?' + q.toString()),
    api.get('/kelas'),
  ]);
  keadaan.daftar = daftar;
  $('#jumlahSiswa').textContent = kelas.total;
  renderSaringan(kelas);
  renderTabel();
}

function renderSaringan(kelas) {
  $('#filterSiswaTingkat').innerHTML = [['', 'Semua tingkat'], ...TINGKAT.map((t) => [t, 'Kelas ' + t])]
    .map(([t, label]) => `<button class="chipkelas" data-act="filterSiswa" data-tingkat="${t}"
      aria-pressed="${keadaan.tingkat === t}">${label}</button>`).join('');

  const isi = $('#filterSiswaRombel');
  isi.style.display = keadaan.tingkat ? 'flex' : 'none';
  isi.innerHTML = [['', 'Semua rombel'], ...ROMBEL.map((r) => [r, r])]
    .map(([r, label]) => `<button class="chipkelas" data-act="filterSiswaRombel" data-rombel="${r}"
      aria-pressed="${keadaan.rombel === r}">${label}</button>`).join('');

  const total = kelas.kelas.find((k) => k.tingkat === keadaan.tingkat && k.rombel === keadaan.rombel);
  $('#infoSiswa').textContent = !keadaan.tingkat ? `${kelas.total} siswa di semua kelas`
    : keadaan.rombel ? `${total ? total.siswa : 0} siswa di kelas ${keadaan.tingkat} ${keadaan.rombel}`
      : `${kelas.kelas.filter((k) => k.tingkat === keadaan.tingkat).reduce((a, b) => a + b.siswa, 0)} siswa di tingkat ${keadaan.tingkat}`;
}

function renderTabel() {
  $('#tabelSiswa').innerHTML = keadaan.daftar.length
    ? `<table class="table"><thead><tr><th>NIS</th><th>Nama</th><th>Kelas</th><th>Status akun</th><th></th></tr></thead><tbody>
        ${keadaan.daftar.map((s) => `<tr>
          <td>${esc(s.nis)}</td>
          <td>${esc(s.nama)}</td>
          <td><span class="tag">${esc(s.kelas)}</span></td>
          <td><span class="tag ${!s.aktif ? 'purple' : s.wajibGantiSandi ? 'amber' : 'green'}" title="${s.wajibGantiSandi ? 'Siswa belum mengganti sandi awal' : ''}">${!s.aktif ? 'Nonaktif' : s.wajibGantiSandi ? 'Sandi awal' : 'Aktif'}</span></td>
          <td><div class="btnrow" style="justify-content:flex-end">
            <button class="btn ghost small" data-act="statusSiswa" data-id="${esc(s.id)}" data-nama="${esc(s.nama)}"
              data-aktif="${s.aktif}">${s.aktif ? 'Nonaktifkan' : 'Aktifkan'}</button>
            <button class="btn ghost small" data-act="resetSandiSiswa" data-id="${esc(s.id)}"
              data-nis="${esc(s.nis)}" data-nama="${esc(s.nama)}">Reset sandi</button>
          </div></td></tr>`).join('')}
      </tbody></table>`
    : `<div class="kosong">
        <span class="kosong-ikon"><svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8.5" r="3.6"/><path d="M4.5 20c1.2-3.6 4-5.4 7.5-5.4S18.3 16.4 19.5 20"/></svg></span>
        <b>Belum ada akun siswa di kelas ini</b>
        <p class="muted small">Tambahkan satu per satu lewat formulir di atas, atau tempel daftar kelas sekaligus di kartu impor.</p>
      </div>`;
}

function tampilKredensial(judul, keterangan, baris) {
  const isi = elemen('div', {},
    elemen('p', { class: 'small muted' }, keterangan),
    elemen('div', { class: 'kredensial' }, baris.map((b) => elemen('div', { class: 'kredensial-baris' },
      elemen('span', { class: 'small muted' }, b.label),
      elemen('b', {}, b.nilai)))),
    elemen('p', { class: 'small muted', style: 'margin-top:14px' },
      'Kata sandi ini hanya muncul sekali. Catat dulu sebelum menutup jendela ini.'));
  bukaModal('Akun siswa', judul, isi);
}

export function filterSiswa(el) {
  keadaan.tingkat = el.dataset.tingkat;
  keadaan.rombel = '';
  return muatSiswa();
}

export function filterSiswaRombel(el) {
  keadaan.rombel = el.dataset.rombel;
  return muatSiswa();
}

export function cariSiswa() {
  keadaan.cari = $('#cariSiswa').value.trim();
  return muatSiswa();
}

export async function tambahSiswa() {
  const nis = $('#siswaNis').value.trim();
  const nama = $('#siswaNama').value.trim();
  const tingkat = $('#siswaTingkat').value;
  const rombel = $('#siswaRombel').value;
  if (!nis || !nama) { toast('NIS dan nama wajib diisi'); return; }
  const data = await api.post('/siswa', { nis, nama, tingkat, rombel });
  $('#siswaNis').value = ''; $('#siswaNama').value = '';
  keadaan.tingkat = tingkat; keadaan.rombel = rombel; keadaan.cari = '';
  await muatSiswa();
  tampilKredensial(`${data.siswa.nama} — ${data.siswa.kelas}`, 'Akun siswa sudah dibuat dan langsung bisa dipakai masuk.',
    [{ label: 'NIS', nilai: data.siswa.nis }, { label: 'Kata sandi awal', nilai: data.kataSandiAwal }]);
}

function barisImpor(teks) {
  return teks.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
    const pisah = l.search(/[,;\t]/);
    if (pisah < 0) return { nis: l, nama: '' };
    return { nis: l.slice(0, pisah).trim(), nama: l.slice(pisah + 1).trim() };
  });
}

export async function imporSiswa() {
  const baris = barisImpor($('#imporTeks').value);
  if (!baris.length) { toast('Tempel dulu daftar siswa'); return; }
  const tingkat = $('#imporTingkat').value;
  const rombel = $('#imporRombel').value;
  const data = await api.post('/siswa/impor', { baris: baris.map((b) => ({ ...b, tingkat, rombel })) });
  $('#imporTeks').value = '';
  keadaan.tingkat = tingkat; keadaan.rombel = rombel;
  await muatSiswa();
  const isi = elemen('div', {},
    elemen('p', {}, `${data.jumlah} akun dibuat untuk kelas `, elemen('b', {}, `${tingkat} ${rombel}`), '.'),
    elemen('div', { class: 'kredensial' }, data.dibuat.map((s) => elemen('div', { class: 'kredensial-baris' },
      elemen('span', { class: 'small muted' }, s.nama),
      elemen('b', {}, `${s.nis} · ${s.kataSandiAwal}`)))),
    data.gagal.length ? elemen('div', { class: 'notice', style: 'margin-top:14px' },
      elemen('b', {}, `${data.gagal.length} baris dilewati`),
      elemen('ul', { class: 'small', style: 'margin:8px 0 0 18px' },
        data.gagal.map((g) => elemen('li', {}, `${g.nis || '(tanpa NIS)'} — ${g.alasan}`)))) : null,
    elemen('p', { class: 'small muted', style: 'margin-top:14px' }, 'Kata sandi hanya muncul sekali. Unduh atau catat sekarang.'));
  bukaModal('Impor siswa', 'Hasil impor', isi);
}

export async function resetSandiSiswa(el) {
  const { id, nis, nama } = el.dataset;
  if (!confirm(`Buat sandi awal baru untuk ${nama} (${nis})? Sesi login siswa itu akan diputus.`)) return;
  const data = await api.post(`/siswa/${encodeURIComponent(id)}/reset-sandi`);
  await muatSiswa();
  tampilKredensial(`${nama} — ${nis}`, 'Sandi lama tidak berlaku lagi. Berikan sandi baru ini kepada siswa.',
    [{ label: 'Kata sandi baru', nilai: data.kataSandiAwal }]);
}


export async function statusSiswa(el) {
  const { id, nama, aktif } = el.dataset;
  const target = aktif !== 'true';
  const tanya = target ? `Aktifkan kembali akun ${nama}?` : `Nonaktifkan akun ${nama}? Siswa tidak bisa masuk sampai diaktifkan lagi.`;
  if (!confirm(tanya)) return;
  await api.patch(`/siswa/${encodeURIComponent(id)}/status`, { aktif: target });
  await muatSiswa();
  toast(`Akun ${nama} ${target ? 'diaktifkan' : 'dinonaktifkan'}`);
}
