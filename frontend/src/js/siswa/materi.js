import { definisiDariMateri, kelasMapel, materiSiswa, singkatanMapel } from '../seleksi.js';
import { kirimChat } from './chat.js';
import { bukaModal, tampilkanHalaman, tutupModal } from '../ui.js';
import { $, esc, elemen } from '../util.js';
import { status } from '../status.js';

const IKON_BUKU = '<svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v15H6.5A2.5 2.5 0 0 0 4 20.5Z"/><path d="M4 5.5v15"/></svg>';

export function renderChips() {
  const m = materiSiswa()[0];
  const def = m ? definisiDariMateri(m).slice(0, 3) : [];
  $('#chipCepat').replaceChildren(...(def.length
    ? def.map((d) => elemen('button', { class: 'btn ghost', 'data-act': 'chip', 'data-q': `Apa itu ${d.istilah}?` }, d.istilah))
    : [elemen('span', { class: 'small muted' }, 'Belum ada contoh pertanyaan — guru belum mengisi materi untuk kelas ini.')]));
}

export function renderMateriSiswa() {
  const wadah = $('#daftarMateriSiswa');
  const daftar = materiSiswa();
  const label = $('#labelKelasSiswa');
  if (label) label.textContent = 'Kelas ' + status.kelasSiswa;
  if (!daftar.length) {
    wadah.innerHTML = `
      <div class="card">
        <div class="kosong">
          <span class="kosong-ikon">${IKON_BUKU}</span>
          <b>Materi belum tersedia</b>
          <p class="muted small">Guru belum mengisi materi untuk kelas ${esc(status.kelasSiswa)}. Materi kelas lain memang tidak ditampilkan di sini.</p>
        </div>
      </div>`;
    return;
  }
  wadah.replaceChildren(...daftar.map((m) => elemen('div', {
    class: `card materi mapel-${kelasMapel(m.mapel)}`, 'data-tilt': '1', 'data-tilt-kuat': '9'
  },
    elemen('div', { class: 'baris', style: 'justify-content:space-between' },
      elemen('span', { class: 'mapel-ikon' }, singkatanMapel(m.mapel)),
      elemen('span', { class: 'tag' }, 'Kelas ' + status.kelasSiswa)),
    elemen('h3', {}, m.judul),
    elemen('p', { class: 'muted small', style: 'margin:0' }, `${m.teks.length} bagian materi · ${m.mapel}`),
    elemen('div', { class: 'btnrow' },
      elemen('button', { class: 'btn primary', 'data-act': 'bacaMateri', 'data-id': m.id }, 'Buka materi'),
      elemen('button', { class: 'btn ghost', 'data-act': 'tanyaMateri', 'data-id': m.id }, 'Tanya AI'))
  )));
}

export function bacaMateri(id) {
  const m = status.db.materi.find((x) => x.id === id);
  if (!m) return;
  bukaModal(m.mapel + ' · Kelas ' + m.kelas, m.judul, [
    ...m.teks.map((t) => elemen('p', { style: 'margin:0 0 10px' }, t)),
    elemen('div', { class: 'spacer' }),
    elemen('div', { class: 'btnrow' },
      elemen('button', { class: 'btn primary', 'data-act': 'tanyaMateri', 'data-id': m.id }, 'Tanya AI tentang materi ini'),
      elemen('button', { class: 'btn ghost', 'data-act': 'keLatihan', 'data-id': m.id }, 'Latihan soal materi ini'))
  ]);
}

export function tanyaMateri(id) {
  const m = status.db.materi.find((x) => x.id === id);
  if (!m) return;
  tutupModal();
  tampilkanHalaman('s-chat');
  $('#chatInput').value = 'Apa itu ' + m.judul.toLowerCase().split(' ')[0] + '?';
  kirimChat('Jelaskan ' + m.judul);
}
