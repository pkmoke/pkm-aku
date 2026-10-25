import { api } from '../api.js';
import { muat } from '../status.js';
import { SISWA } from '../konstanta.js';
import { kelasMapel, materiSiswa, singkatanMapel, soalSiswa } from '../seleksi.js';
import { catat, simpan } from '../status.js';
import { jalankanEfek } from '../efek/halaman.js';
import { toast } from '../ui.js';
import { $, $$, esc, renderOpsi, elemen } from '../util.js';
import { status } from '../status.js';

const IKON_KOSONG = '<svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h11l3 3v13H5z"/><path d="M15 8h4M15 4v4"/><path d="M8.5 13.5l1.8 1.8 3.4-3.6"/></svg>';
const PANAH = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M13 7l5 5-5 5"/></svg>';

export function renderPilihLatihan() {
  const sel = $('#pilihMateriLatihan');
  const daftarSoal = soalSiswa();
  const pakai = materiSiswa().filter((m) => daftarSoal.some((s) => s.materiId === m.id));
  renderOpsi(sel, pakai,
    (m) => `${m.mapel} — ${m.judul} (${daftarSoal.filter((s) => s.materiId === m.id).length} soal)`,
    'Belum ada soal untuk kelas ini');

  const cepat = $('#pilihLatihanCepat');
  if (!cepat) return;
  cepat.innerHTML = pakai.length
    ? pakai.map((m) => {
        const n = daftarSoal.filter((s) => s.materiId === m.id).length;
        return `
          <button class="mapel-${kelasMapel(m.mapel)}" data-act="keLatihan" data-id="${m.id}">
            <span class="pk-atas">
              <span class="mapel-ikon">${esc(singkatanMapel(m.mapel))}</span>
              <span class="tag mapel">${n} soal</span>
            </span>
            <b>${esc(m.judul)}</b>
            <span class="pk-bawah">
              <span class="small muted">${esc(m.mapel)}</span>
              <span class="pk-aksi">Mulai latihan ${PANAH}</span>
            </span>
          </button>`;
      }).join('')
    : `
      <div class="kosong">
        <span class="kosong-ikon">${IKON_KOSONG}</span>
        <b>Belum ada soal untuk kelas ini</b>
        <p class="muted small">Guru belum menerbitkan soal untuk <b>kelas ${esc(status.kelasSiswa)}</b>. Coba cek lagi nanti, atau tanya Bemai dulu di halaman Chat AI.</p>
      </div>`;
}

let sesi = null;

export function mulaiLatihan(paksaId, ulangIds = null, asalId = null) {
  const id = paksaId || $('#pilihMateriLatihan').value;
  const m = status.db.materi.find((x) => x.id === id);
  const tersedia = soalSiswa().filter((s) => s.materiId === id && (!ulangIds || ulangIds.includes(s.id)));
  if (!m || !tersedia.length) { toast('Belum ada soal untuk materi ini'); return; }
  // Snapshot questions so a later edit cannot change an attempt already in progress.
  const daftar = structuredClone(tersedia);
  const materi = structuredClone(m);
  sesi = { materi, daftar, selesai: false, asalId, kelas: status.kelasSiswa };
  const form = elemen('form', { id: 'formLatihan' },
    daftar.map((s, i) => elemen('div', { style: 'margin-bottom:20px', 'data-soal': s.id },
      elemen('p', { style: 'font-weight:700;margin:0 0 10px' }, `${i + 1}. ${s.tanya}`),
      s.opsi.map((o, j) => elemen('label', { class: 'opsi' },
        elemen('input', { type: 'radio', name: 's_' + s.id, value: j, style: 'width:auto;margin-right:9px' }), o)))),
    elemen('div', { class: 'btnrow' },
      elemen('button', { class: 'btn primary', type: 'submit' }, 'Kumpulkan jawaban'),
      elemen('button', { class: 'btn ghost', type: 'button', 'data-act': 'batalLatihan' }, 'Batal')));
  $('#areaLatihan').replaceChildren(elemen('div', { class: 'spacer' }),
    elemen('div', { class: 'card' },
      elemen('span', { class: 'tag' }, `${m.mapel} · ${status.kelasSiswa}`),
      elemen('h2', { style: 'margin-top:12px' }, m.judul),
      elemen('p', { class: 'muted small' }, `${ulangIds ? 'Latihan ulang · ' : ''}${daftar.length} soal · pilih satu jawaban per soal`),
      elemen('div', { class: 'bilah-jawab' }, elemen('span', { id: 'bilahJawab' })), form));
  form.addEventListener('submit', (e) => { e.preventDefault(); kumpulkanLatihan().catch(e => toast(e.message)); });
  form.addEventListener('change', () => {
    const dijawab = new Set($$('input:checked', form).map((i) => i.name)).size;
    $('#bilahJawab').style.width = Math.round(dijawab / daftar.length * 100) + '%';
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function penjelasan(s, m) {
  if (s.pembahasan?.trim()) return { label: 'Penjelasan guru', teks: s.pembahasan };
  // Quote source text rather than inventing an explanation for older questions.
  const jawaban = s.opsi[s.jawaban].toLocaleLowerCase('id-ID');
  const kutipan = m.teks.find((t) => t.toLocaleLowerCase('id-ID').includes(jawaban));
  return kutipan
    ? { label: 'Dari materi: ' + m.judul, teks: kutipan }
    : { label: 'Pembahasan', teks: 'Guru belum menambahkan penjelasan untuk soal ini. Baca kembali materi atau tanyakan kepada guru.' };
}

export async function kumpulkanLatihan() {
  if (!sesi || sesi.selesai) return;
  const { materi: m, daftar, asalId, kelas } = sesi;
  const form = $('#formLatihan');
  if (!form) return;
  const detail = daftar.map((s) => {
    const pilih = $$('input:checked', form).find((input) => input.name === 's_' + s.id);
    const jawab = pilih ? Number(pilih.value) : -1;
    return { soalId: s.id, benar: jawab === s.jawaban, jawab };
  });
  if (detail.some((d) => d.jawab < 0) && !confirm('Masih ada soal yang belum dijawab. Tetap kumpulkan?')) return;
  const submitAwal = $('button[type="submit"]', form);
  if (submitAwal.disabled) return;
  submitAwal.disabled = true;
  let hasil;
  try {
    hasil = await api.post('/latihan', { materiId: m.id, ulangDari: asalId,
      jawaban: detail.map(d => ({ soalId: d.soalId, pilihan: d.jawab })) });
    await muat();
  } catch (e) { submitAwal.disabled = false; toast(e.message); return; }
  sesi.selesai = true;
  const { benar, nilai } = hasil;
  detail.splice(0, detail.length, ...hasil.detail);
  daftar.forEach(s => {
    const d = detail.find(d => d.soalId === s.id);
    s.jawaban = d.kunci; s.pembahasan = d.pembahasan;
  });
  $$('[data-soal]', form).forEach((kotak, i) => {
    $$('input', kotak).forEach((input) => {
      if (Number(input.value) === daftar[i].jawaban) input.closest('.opsi').classList.add('benar');
      else if (input.checked) input.closest('.opsi').classList.add('salah');
      input.disabled = true;
    });
  });
  const submit = $('button[type="submit"]', form);
  submit.disabled = true; submit.textContent = 'Jawaban sudah dikumpulkan';
  const salah = detail.filter((d) => !d.benar).map((d) => d.soalId);
  const aksi = elemen('div', { class: 'btnrow', style: 'margin-top:16px' });
  if (salah.length) {
    const retry = elemen('button', { type: 'button', class: 'btn primary', id: 'ulangSalah' }, `Coba lagi ${salah.length} soal yang belum benar`);
    retry.addEventListener('click', () => mulaiLatihan(m.id, salah, hasil.id));
    aksi.append(retry);
  } else {
    aksi.append(elemen('p', { class: 'tag green' }, 'Semua jawaban benar. Bagus!'));
  }
  const baca = elemen('button', { type: 'button', class: 'btn ghost', 'data-act': 'bacaMateri', 'data-id': m.id }, 'Baca kembali materi');
  aksi.append(baca);
  $('#areaLatihan').prepend(elemen('div', { class: 'spacer' }),
    elemen('div', { class: 'card', style: 'border-color:#bfe6cf;background:linear-gradient(135deg,#eaf9f1,#fff)' },
      elemen('div', { class: 'stat' },
        elemen('div', {}, elemen('h2', { style: 'margin:0' }, `Nilai kamu: ${nilai}/100`),
          elemen('p', { class: 'muted small' }, `${benar} benar dari ${daftar.length} soal · ${asalId ? 'latihan ulang' : 'latihan'} tersimpan di riwayat`)),
        elemen('div', { class: 'skor-ring', 'data-p': nilai }, elemen('b', { 'data-angka': nilai }, '0'), elemen('span', {}, 'nilai'))),
      aksi,
      salah.length ? elemen('p', { class: 'small muted' }, 'Latihan ulang hanya memuat soal yang salah atau belum dijawab. Nilainya disimpan sebagai percobaan baru; nilai sebelumnya tetap ada.') : null));
  $('#areaLatihan').append(elemen('div', { class: 'spacer' }),
    elemen('div', { class: 'card', id: 'pembahasanLatihan' }, elemen('h2', {}, 'Pembahasan'),
      daftar.map((s, i) => {
        const d = detail[i]; const p = penjelasan(s, m);
        return elemen('section', { style: 'padding:16px 0;border-bottom:1px solid var(--line)' },
          elemen('h3', {}, `${i + 1}. ${s.tanya}`),
          elemen('span', { class: 'tag ' + (d.benar ? 'green' : 'amber') }, d.benar ? 'Benar' : d.jawab < 0 ? 'Belum dijawab' : 'Belum benar'),
          elemen('p', {}, 'Jawabanmu: ' + (d.jawab < 0 ? 'Belum dijawab' : s.opsi[d.jawab])),
          elemen('p', {}, elemen('b', {}, 'Jawaban benar: '), s.opsi[s.jawaban]),
          elemen('p', { class: 'small muted' }, p.label), elemen('p', { style: 'white-space:pre-wrap' }, p.teks));
      })));
  jalankanEfek('s-latihan');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  toast('Jawaban terkirim — nilai ' + nilai);
}

export function batalLatihan() { sesi = null; $('#areaLatihan').replaceChildren(); }
