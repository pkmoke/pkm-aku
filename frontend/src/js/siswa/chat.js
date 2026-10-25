import { api } from '../api.js';
import { muat } from '../status.js';
import { materiSiswa } from '../seleksi.js';
import { catat } from '../status.js';
import { barisBertahap } from '../efek/teks.js';
import { $, elemen } from '../util.js';
import { status } from '../status.js';

export const STOP = new Set(['apa', 'itu', 'yang', 'dan', 'atau', 'dengan', 'untuk', 'dari', 'pada', 'adalah',
  'jelaskan', 'tolong', 'bagaimana', 'kenapa', 'mengapa', 'kalau', 'saya', 'kak', 'dong', 'bisa',
  'tentang', 'sebutkan', 'berikan', 'contoh', 'dalam', 'tidak', 'juga', 'ada', 'nya']);

export function cariJawaban(pertanyaan) {
  const kata = pertanyaan.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/)
    .filter((w) => w.length > 2 && !STOP.has(w));
  if (!kata.length) return { ok: false };

  let terbaik = null, skorTerbaik = 0, kalimat = [];
  materiSiswa().forEach((m) => {
    let skor = 0;
    const kandidat = [];
    m.teks.forEach((t) => {
      const tl = t.toLowerCase();
      let s = 0;
      kata.forEach((k) => { if (tl.includes(k)) s += 1; });
      if (s > 0) { kandidat.push({ t, s }); skor += s; }
    });
    const judulBawah = m.judul.toLowerCase();
    kata.forEach((k) => { if (judulBawah.includes(k)) skor += 2; });
    if (skor > skorTerbaik) { skorTerbaik = skor; terbaik = m; kalimat = kandidat; }
  });

  if (!terbaik || skorTerbaik < 1) return { ok: false };
  kalimat.sort((a, b) => b.s - a.s);
  return { ok: true, materi: terbaik, jawab: kalimat.slice(0, 3).map((k) => k.t) };
}

export function tambahBubble(teks, kelas, sumber) {
  const box = $('#messages');
  const div = document.createElement('div');
  div.className = 'bubble ' + kelas;
  String(teks).split('\n').forEach((baris, i) => {
    if (i) div.append(elemen('br'));
    div.append(baris);
  });
  if (sumber) div.append(elemen('span', { class: 'sumber' }, sumber));
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

export function tambahMengetik() {
  const box = $('#messages');
  const div = document.createElement('div');
  div.className = 'bubble bot mengetik';
  div.setAttribute('aria-label', 'Bemai sedang menyusun jawaban');
  div.append(elemen('i'), elemen('i'), elemen('i'));
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

export function isiBubble(el, teks, sumber) {
  if (!el) return;
  el.classList.remove('mengetik');
  el.replaceChildren(...barisBertahap(teks));
  if (sumber) el.append(elemen('span', { class: 'sumber' }, sumber));
  const box = $('#messages');
  box.scrollTop = box.scrollHeight;
}

export async function kirimChat(teksPaksa) {
  const input = $('#chatInput');
  const q = (teksPaksa != null ? teksPaksa : input.value).trim();
  if (!q) return;
  tambahBubble(q, 'me');
  input.value = '';

  const nunggu = tambahMengetik();
  const penggunaId = status.pengguna?.id;
  try {
    const hasil = await api.post('/chat', { pertanyaan: q });
    if (status.pengguna?.id !== penggunaId) return;
    isiBubble(nunggu, hasil.jawaban || 'Belum ada materi sekolah yang cocok dengan pertanyaan itu.',
      hasil.sumber ? 'Sumber: ' + hasil.sumber.judul : null);
    await muat();
  } catch (e) { isiBubble(nunggu, e.message); }
}
