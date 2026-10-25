import { api } from '../api.js';
import { muat } from '../status.js';
import { kelasTercentang, renderRombel } from './soal.js';
import { ROMBEL } from '../konstanta.js';
import { kelasMapel, rombelLabel, singkatanMapel } from '../seleksi.js';
import { bacaMateri } from '../siswa/materi.js';
import { catat, simpan } from '../status.js';
import { toast } from '../ui.js';
import { $, esc } from '../util.js';
import { status } from '../status.js';

const IKON_KOSONG = '<svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v15H6.5A2.5 2.5 0 0 0 4 20.5Z"/><path d="M4 5.5v15"/></svg>';

export function renderKelolaMateri() {
  $('#jumlahMateri').textContent = status.db.materi.length;
  renderRombel('#mRombel', ROMBEL);
  const daftar = status.db.materi;
  $('#daftarMateriGuru').innerHTML = daftar.length
    ? daftar.map((m) => `
      <div class="list-item">
        <div class="baris" style="flex-wrap:nowrap;min-width:0">
          <span class="mapel-ikon mapel-${kelasMapel(m.mapel)}">${esc(singkatanMapel(m.mapel))}</span>
          <div style="min-width:0">
            <b>${esc(m.judul)}</b>
            <div class="small muted">${esc(m.mapel)} · kelas ${esc(m.kelas)} — ${esc(rombelLabel(m))} · ${m.teks.length} kalimat · ${status.db.soal.filter((s) => s.materiId === m.id).length} soal</div>
          </div>
        </div>
        <div class="btnrow">
          <button class="btn ghost small" data-act="bacaMateri" data-id="${m.id}">Lihat</button>
          <button class="btn ghost small" data-act="editMateri" data-id="${esc(m.id)}">Edit</button>
          <button class="btn danger small" data-act="hapusMateri" data-id="${m.id}">Hapus</button>
        </div>
      </div>`).join('')
    : `<div class="kosong">
        <span class="kosong-ikon">${IKON_KOSONG}</span>
        <b>Belum ada materi</b>
        <p class="muted small">Isi formulir <b>Materi baru</b> di atas. Setelah tersimpan, materinya langsung muncul di halaman Materi siswa dan jadi sumber jawaban chatbot.</p>
      </div>`;
}

export async function tambahMateri() {
  const judul = $('#mJudul').value.trim();
  const kelas = $('#mKelas').value;
  const rombel = kelasTercentang('#mRombel');
  const teks = $('#mTeks').value.split('\n').map((t) => t.trim()).filter(Boolean);
  if (!judul || !teks.length) { toast('Judul dan isi materi wajib diisi'); return; }
  if (!rombel.length) { toast('Centang minimal satu rombel'); return; }
  await api.post('/materi', {
    id: 'm' + Date.now(), mapel: $('#mMapel').value, kelas, rombel,
    judul, teks, rangkuman: teks.slice(0, 3).map((t) => t.split(' ').slice(0, 12).join(' ') + '…')
  });
  await muat();
  catat('Materi baru', judul, 'Kelas ' + kelas + ' — ' + rombelLabel({ rombel }), kelas + ' ' + rombel.join(','));
  simpan();
  $('#mJudul').value = ''; $('#mTeks').value = '';
  renderKelolaMateri();
  toast('Materi kelas ' + kelas + ' (' + rombel.length + ' rombel) tersimpan — hanya siswa kelas itu yang melihatnya');
}

export async function hapusMateri(id) {
  const m = status.db.materi.find((x) => x.id === id);
  if (!m) return;
  if (!confirm('Hapus materi "' + m.judul + '"? Soal yang terkait juga akan dihapus.')) return;
  await api.hapus('/materi/' + encodeURIComponent(id));
  await muat();
  status.db.materi = status.db.materi.filter((x) => x.id !== id);
  status.db.soal = status.db.soal.filter((s) => s.materiId !== id);
  catat('Materi dihapus', m.judul, 'Dihapus');
  simpan();
  renderKelolaMateri();
  toast('Materi dihapus');
}
