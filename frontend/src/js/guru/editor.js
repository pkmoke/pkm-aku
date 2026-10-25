import { api } from '../api.js';
import { muat } from '../status.js';
import { $, elemen, renderOpsi } from '../util.js';
import { status, catat, simpan } from '../status.js';
import { bukaModal, tutupModal, toast } from '../ui.js';
import { ROMBEL, TINGKAT } from '../konstanta.js';
import { renderKelolaMateri } from './materi.js';
import { renderKelolaSoal, renderRombel, renderPilihKelas, kelasTercentang } from './soal.js';

function field(id, label, value, multiline = false) {
  const input = elemen(multiline ? 'textarea' : 'input', { id, required: true });
  input.value = value;
  if (multiline) input.rows = 5;
  return elemen('div', {}, elemen('label', { for: id }, label), input);
}
function select(id, label, values, current) {
  const input = elemen('select', { id });
  renderOpsi(input, values.map((value) => ({ id: value })), (item) => item.id);
  input.value = current;
  return elemen('div', {}, elemen('label', { for: id }, label), input);
}
function editor(title, children, save) {
  const error = elemen('p', { class: 'small', role: 'alert', id: 'editError' });
  const form = elemen('form', { id: 'editForm' }, children, error,
    elemen('div', { class: 'btnrow' },
      elemen('button', { class: 'btn primary', type: 'submit' }, 'Simpan perubahan'),
      elemen('button', { class: 'btn ghost', type: 'button', 'data-act': 'tutupModal' }, 'Batal')));
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (status.role !== 'teacher') return;
    const submit = form.querySelector('button[type=submit]');
    if (submit.disabled) return;
    submit.disabled = true;
    try {
    const message = await save();
    if (message) { error.textContent = message; return; }
    tutupModal(); toast('Perubahan tersimpan');
    } catch (e) { error.textContent = e.message; }
    finally { submit.disabled = false; }
  });
  bukaModal('Edit', title, form);
  form.querySelector('input, textarea, select')?.focus();
}

export function editMateri(id) {
  if (status.role !== 'teacher') return;
  const m = status.db.materi.find((item) => item.id === id);
  if (!m) return;
  editor('Edit materi', [
    field('editJudul', 'Judul materi', m.judul),
    select('editMapel', 'Mata pelajaran', [...new Set(['IPA', 'Matematika', 'Bahasa Indonesia', 'IPS', m.mapel])], m.mapel),
    select('editTingkat', 'Tingkat', TINGKAT, m.kelas),
    elemen('p', {}, 'Rombel tujuan'), elemen('div', { id: 'editRombel', class: 'kelas-pilih' }),
    field('editTeks', 'Isi materi (satu bagian per baris)', m.teks.join('\n'), true),
    field('editRingkasan', 'Rangkuman (satu poin per baris)', (m.rangkuman || []).join('\n'), true),
    elemen('p', { class: 'small muted' }, 'Periksa rangkuman jika isi materi berubah. Soal terkait tetap tersimpan; kelas tujuan dan kunci soal diubah melalui Edit soal.')
  ], async () => {
    const judul = $('#editJudul').value.trim();
    const teks = $('#editTeks').value.split('\n').map((s) => s.trim()).filter(Boolean);
    const rombel = kelasTercentang('#editRombel');
    if (!judul || !teks.length || !rombel.length) return 'Isi judul, materi, dan minimal satu rombel.';
    await api.put('/materi/' + encodeURIComponent(m.id), { judul, teks, rombel, mapel: $('#editMapel').value, kelas: $('#editTingkat').value,
      rangkuman: $('#editRingkasan').value.split('\n').map((s) => s.trim()).filter(Boolean) });
    await muat();
    catat('Materi diperbarui', m.judul, 'Tersimpan'); renderKelolaMateri();
  });
  $('#editRingkasan').required = false;
  renderRombel('#editRombel', m.rombel || ROMBEL);
}

export function editSoal(id) {
  if (status.role !== 'teacher') return;
  const s = status.db.soal.find((item) => item.id === id);
  if (!s) return;
  const material = elemen('select', { id: 'editMateriId', required: true });
  renderOpsi(material, status.db.materi, (m) => `${m.mapel} — ${m.judul}`);
  material.value = s.materiId;
  editor('Edit soal', [
    elemen('div', {}, elemen('label', { for: 'editMateriId' }, 'Materi sumber'), material),
    field('editTanya', 'Pertanyaan', s.tanya, true),
    ...s.opsi.map((value, i) => field('editOpsi' + i, 'Pilihan ' + String.fromCharCode(65 + i), value)),
    select('editJawaban', 'Jawaban benar', s.opsi.map((_, i) => String.fromCharCode(65 + i)), String.fromCharCode(65 + s.jawaban)),
    field('editPembahasan', 'Pembahasan (opsional)', s.pembahasan || '', true),
    elemen('p', {}, 'Kelas tujuan'), elemen('div', { id: 'editKelas' }),
    elemen('p', { class: 'small muted' }, 'Perubahan berlaku untuk latihan berikutnya. Nilai latihan yang sudah dikumpulkan tetap tersimpan.')
  ], async () => {
    const tanya = $('#editTanya').value.trim();
    const opsi = s.opsi.map((_, i) => $('#editOpsi' + i).value.trim());
    const kelas = kelasTercentang('#editKelas');
    const materiId = material.value;
    if (!tanya || opsi.some((o) => !o) || !materiId || !kelas.length) return 'Lengkapi pertanyaan, pilihan, materi sumber, dan minimal satu kelas.';
    await api.put('/soal/' + encodeURIComponent(s.id), { tanya, opsi, kelas, materiId, jawaban: $('#editJawaban').value.charCodeAt(0) - 65,
      pembahasan: $('#editPembahasan').value.trim() });
    await muat();
    catat('Soal diperbarui', tanya.slice(0, 40), 'Tersimpan'); renderKelolaSoal();
  });
  $('#editPembahasan').required = false;
  renderPilihKelas('#editKelas', s.kelas || []);
}
