import { api } from '../api.js';
import { muat } from '../status.js';
import { ROMBEL, TINGKAT, kodeKelas } from '../konstanta.js';
import { definisiDariMateri, kodeMateri, rombelLabel } from '../seleksi.js';
import { catat, simpan } from '../status.js';
import { bukaModal, toast, tutupModal } from '../ui.js';
import { $, esc, renderOpsi } from '../util.js';
import { status } from '../status.js';

export function renderKelolaSoal() {
  const label = (m) => `${m.mapel} — ${m.judul} (kelas ${m.kelas})`;
  renderOpsi($('#soalMateri'), status.db.materi, label);
  renderOpsi($('#qMateriManual'), status.db.materi, label);
  $('#jumlahSoal').textContent = status.db.soal.length;
  sinkronKelasManual();

  $('#daftarSoal').innerHTML = status.db.soal.length
    ? status.db.soal.map((s, i) => {
        const m = status.db.materi.find((x) => x.id === s.materiId);
        const kelas = s.kelas || [];
        const labelKelas = kelas.length > 3 ? kelas.length + ' kelas' : 'kelas ' + kelas.join(', ');
        return `<div class="list-item">
          <div style="min-width:0"><b>${i + 1}. ${esc(s.tanya)}</b>
            <div class="small muted">${esc(m ? m.mapel + ' · ' + m.judul : 'materi dihapus')} — kunci: ${esc(s.opsi[s.jawaban])}</div></div>
          <div class="btnrow">
            <button class="btn ghost small" data-act="editSoal" data-id="${esc(s.id)}">Edit</button>
            <span class="tag green" title="${esc(kelas.join(', '))}">${esc(labelKelas)}</span>
            <span class="tag ${s.otomatis ? 'purple' : ''}">${s.otomatis ? 'auto' : 'manual'}</span>
          </div>
        </div>`;
      }).join('')
    : `<div class="kosong">
        <span class="kosong-ikon"><svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5h14M5 10h14M5 15h9M5 20h6"/></svg></span>
        <b>Bank soal masih kosong</b>
        <p class="muted small">Pakai tab <b>Generate dari materi</b> untuk membuat soal otomatis, atau <b>Tambah soal manual</b> kalau ingin menulis sendiri. Soal baru terbit setelah kamu pilih kelas tujuannya.</p>
      </div>`;
}

export function sinkronKelasManual() {
  const m = status.db.materi.find((x) => x.id === $('#qMateriManual').value);
  if (!m) return;
  renderPilihKelas('#qKelasManual', kodeMateri(m));
}

export function kelasTercentang(sel) {
  return Array.from(document.querySelectorAll(sel + ' input:checked')).map((c) => c.value);
}

export function renderRombel(sel, tercentang) {
  const isi = $(sel);
  if (!isi) return;
  isi.innerHTML = ROMBEL.map((r) => `<label><input type="checkbox" value="${r}" ${tercentang.includes(r) ? 'checked' : ''}/> ${r}</label>`).join('');
}

export function renderPilihKelas(sel, tercentang) {
  const isi = document.querySelector(sel);
  if (!isi) return;
  isi.innerHTML = TINGKAT.map((t) => `
    <div style="margin-bottom:12px">
      <div class="small" style="font-weight:800;margin-bottom:6px;color:#46627a">Tingkat ${t}
        <button class="btn ghost small" type="button" data-act="pilihSemuaKelas" data-tingkat="${t}" data-target="${sel}">pilih semua AF</button>
      </div>
      <div class="kelas-pilih">
        ${ROMBEL.map((r) => { const k = kodeKelas(t, r); return `<label><input type="checkbox" value="${k}" ${tercentang.includes(k) ? 'checked' : ''}/> ${k}</label>`; }).join('')}
      </div>
    </div>`).join('');
}

export function generateSoal() {
  const m = status.db.materi.find((x) => x.id === $('#soalMateri').value);
  if (!m) { toast('Pilih materi dulu'); return; }
  const jumlah = Math.max(2, Math.min(8, Number($('#soalJumlah').value) || 4));
  const def = definisiDariMateri(m);
  if (def.length < 3) { toast('Materi ini belum punya cukup kalimat definisi'); return; }

  const dibuat = [];
  const acak = def.slice().sort(() => Math.random() - 0.5).slice(0, Math.min(jumlah, def.length));
  acak.forEach((d, i) => {
    const salah = def.filter((x) => x.istilah !== d.istilah).sort(() => Math.random() - 0.5).slice(0, 3).map((x) => x.arti);
    const opsi = [d.arti, ...salah].sort(() => Math.random() - 0.5);
    dibuat.push({
      id: 'q' + (Date.now() + i), materiId: m.id, topik: 'Definisi', otomatis: true,
      tanya: 'Apa yang dimaksud dengan ' + d.istilah + '?',
      opsi, jawaban: opsi.indexOf(d.arti), pembahasan: d.istilah + ' adalah ' + d.arti
    });
  });

  bukaModal('Draft soal', 'Preview ' + dibuat.length + ' soal dari "' + m.judul + '"',
    dibuat.map((s, i) => `<p style="margin:0 0 6px"><b>${i + 1}. ${esc(s.tanya)}</b></p>
      <p class="small muted" style="margin:0 0 4px">${s.opsi.map((o, j) => (j === s.jawaban ? '<b>' + esc(o) + '</b> ' : esc(o))).join(' &nbsp;|&nbsp; ')}</p><hr/>`).join('') +
    `<div><label>Terbitkan untuk kelas</label>
      <div id="kelasTerbit"></div>
      <p class="small muted" style="margin:8px 0 14px">Default mengikuti kelas materi sumber (kelas ${esc(m.kelas)} — ${esc(rombelLabel(m))}). Pilih kelas yang termasuk kelas materi sumber.</p></div>` +
    '<div class="btnrow"><button class="btn primary" data-act="terbitkanSoal" data-materi="' + m.id + '">Terbitkan ke siswa</button>' +
    '<button class="btn ghost" data-act="tutupModal">Batal</button></div>');
  renderPilihKelas('#kelasTerbit', kodeMateri(m));
  window._draftSoal = dibuat;
}

export async function terbitkanSoal() {
  const draft = window._draftSoal || [];
  if (!draft.length) { tutupModal(); return; }
  const kelas = kelasTercentang('#kelasTerbit');
  if (!kelas.length) { toast('Centang minimal satu kelas tujuan'); return; }
  draft.forEach((s) => { s.kelas = kelas.slice(); });
  await api.post('/soal/terbitkan', { usulan: draft });
  await muat();
  catat('Soal baru', draft.length + ' soal dari materi', 'Terbit ke kelas ' + kelas.join(', '), kelas.join(', '));
  simpan();
  window._draftSoal = [];
  tutupModal();
  renderKelolaSoal();
  toast(draft.length + ' soal diterbitkan ke kelas ' + kelas.join(', '));
}

export async function tambahSoalManual() {
  const t = $('#qPertanyaan').value.trim();
  const opsi = ['#qA', '#qB', '#qC', '#qD'].map((s) => $(s).value.trim());
  const jawaban = Number($('#qBenar').value);
  const materiId = $('#qMateriManual').value;
  const kelas = kelasTercentang('#qKelasManual');
  if (!t || opsi.some((o) => !o) || !materiId) { toast('Lengkapi pertanyaan dan 4 opsi'); return; }
  if (!kelas.length) { toast('Centang minimal satu kelas tujuan'); return; }
  await api.post('/soal', { id: 'q' + Date.now(), materiId, topik: 'Manual', tanya: t, opsi, jawaban, kelas, pembahasan: $('#qPembahasan').value.trim() });
  await muat();
  catat('Soal manual', t.slice(0, 40), 'Terbit ke kelas ' + kelas.join(', '), kelas.join(', '));
  simpan();
  ['#qPertanyaan', '#qA', '#qB', '#qC', '#qD', '#qPembahasan'].forEach((s) => { $(s).value = ''; });
  renderKelolaSoal();
  toast('Soal ditambahkan untuk kelas ' + kelas.join(', '));
}
