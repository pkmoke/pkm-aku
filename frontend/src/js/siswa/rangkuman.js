import { api } from '../api.js';
import { muat } from '../status.js';
import { kelasMapel, materiSiswa, singkatanMapel } from '../seleksi.js';
import { catat } from '../status.js';
import { toast } from '../ui.js';
import { $, esc, elemen, renderOpsi } from '../util.js';
import { status } from '../status.js';

const IKON_KOSONG = '<svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 6h14M5 12h14M5 18h8"/></svg>';
const PANAH = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M13 7l5 5-5 5"/></svg>';

export function renderPilihRangkuman() {
  const daftar = materiSiswa();
  renderOpsi($('#pilihMateriRangkuman'), daftar,
    (m) => `${m.mapel} — ${m.judul}`, 'Belum ada materi untuk kelas ini');

  const cepat = $('#pilihRangkumanCepat');
  if (!cepat) return;
  cepat.innerHTML = daftar.length
    ? daftar.map((m) => `
        <button class="mapel-${kelasMapel(m.mapel)}" data-act="rangkumanCepat" data-id="${m.id}">
          <span class="pk-atas">
            <span class="mapel-ikon">${esc(singkatanMapel(m.mapel))}</span>
            <span class="tag mapel">${m.teks.length} poin</span>
          </span>
          <b>${esc(m.judul)}</b>
          <span class="pk-bawah">
            <span class="small muted">${esc(m.mapel)}</span>
            <span class="pk-aksi">Rangkum ${PANAH}</span>
          </span>
        </button>`).join('')
    : `
      <div class="kosong">
        <span class="kosong-ikon">${IKON_KOSONG}</span>
        <b>Belum ada materi untuk dirangkum</b>
        <p class="muted small">Materi untuk <b>kelas ${esc(status.kelasSiswa)}</b> belum diisi guru, jadi belum ada yang bisa diringkas.</p>
      </div>`;
}

export function buatRangkuman() {
  const id = $('#pilihMateriRangkuman').value;
  const m = status.db.materi.find((x) => x.id === id);
  if (!m) return;

  const poin = (m.rangkuman && m.rangkuman.length)
    ? m.rangkuman
    : m.teks.slice(0, 3).map((t) => t.split(' ').slice(0, 12).join(' ') + '…');

  $('#areaRangkuman').replaceChildren(
    elemen('div', { class: 'spacer' }),
    elemen('div', { class: 'card' },
      elemen('div', { class: 'btnrow', style: 'justify-content:space-between;align-items:center' },
        elemen('span', { class: 'tag purple' }, `${m.mapel} · ${m.judul}`),
        elemen('button', { class: 'btn ghost small', 'data-act': 'simpanRangkuman', 'data-id': m.id }, 'Simpan ke riwayat')),
      elemen('div', { class: 'spacer' }), elemen('h3', {}, 'Inti materi'),
      elemen('ul', {}, poin.map((p) => elemen('li', {}, p))),
      elemen('p', { class: 'small muted' }, 'Ringkasan disusun dari poin materi yang diisi guru — belum memakai LLM, jadi tidak ada kalimat yang dikarang.'))
  );
}

export async function simpanRangkuman(id) {
  const m = status.db.materi.find((x) => x.id === id);
  if (!m) return;
  await api.post('/rangkuman', { materiId: id });
  await muat();
  toast('Rangkuman disimpan ke riwayat');
}
