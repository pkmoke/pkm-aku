import { api } from '../api.js';
import { muat } from '../status.js';
import { kelasTercentang, renderRombel } from './soal.js';
import { ROMBEL } from '../konstanta.js';
import { kelasMapel, rombelLabel, singkatanMapel } from '../seleksi.js';
import { catat, simpan } from '../status.js';
import { bukaModal, toast, tutupModal } from '../ui.js';
import { $, esc } from '../util.js';
import { status } from '../status.js';

export function renderUpload() {
  renderRombel('#uRombel', ROMBEL);
  const terakhir = status.db.materi.slice(-3).reverse();
  $('#daftarUpload').innerHTML = terakhir.length
    ? terakhir.map((m) => `
      <div class="list-item">
        <div class="baris" style="flex-wrap:nowrap;min-width:0">
          <span class="mapel-ikon mapel-${kelasMapel(m.mapel)}">${esc(singkatanMapel(m.mapel))}</span>
          <div style="min-width:0">
            <b>${esc(m.judul)}</b>
            <div class="small muted">kelas ${esc(m.kelas)} — ${esc(rombelLabel(m))}</div>
          </div>
        </div>
        <span class="tag green">Siap dipakai</span>
      </div>`).join('')
    : '<p class="muted small">Belum ada materi yang diunggah. Materi yang kamu simpan akan muncul di sini.</p>';
}

export function pilihFile(input) {
  const f = input.files && input.files[0];
  if (!f) return;
  if (f.size > 2 * 1024 * 1024) { toast('Ukuran file maksimal 2 MB'); input.value = ''; return; }
  const nama = f.name.toLowerCase();
  if (nama.endsWith('.txt') || nama.endsWith('.md')) {
    const reader = new FileReader();
    reader.onload = () => {
      const teks = String(reader.result).split('\n').map((t) => t.trim()).filter((t) => t.length > 20);
      $('#uJudul').value = f.name.replace(/\.[^.]+$/, '');
      $('#uTeks').value = teks.join('\n');
      toast('Isi file terbaca — cek lalu simpan sebagai materi');
    };
    reader.readAsText(f);
  } else {
    bukaModal('Upload', 'File ' + f.name,
      '<p>File <b>' + esc(f.name) + '</b> perlu diekstraksi di server dulu (pdf-parse / mammoth untuk DOCX). Browser tidak bisa membacanya sendiri.</p>' +
      '<p class="small muted">Untuk demo: buka file itu, salin isinya, lalu tempel di kotak <b>"Atau tempel teks materi"</b> di halaman Upload.</p>' +
      '<div class="btnrow"><button class="btn primary" data-act="tutupModal">Mengerti</button></div>');
  }
  input.value = '';
}

export async function tempelMateri() {
  const judul = $('#uJudul').value.trim();
  const kelas = $('#uKelas').value;
  const rombel = kelasTercentang('#uRombel');
  const teks = $('#uTeks').value.split('\n').map((t) => t.trim()).filter(Boolean);
  if (!judul || teks.length < 2) { toast('Judul dan isi materi minimal 2 baris'); return; }
  if (!rombel.length) { toast('Centang minimal satu rombel'); return; }
  await api.post('/materi', {
    id: 'm' + Date.now(), mapel: $('#uMapel').value, kelas, rombel, judul, teks,
    rangkuman: teks.slice(0, 3).map((t) => t.split(' ').slice(0, 12).join(' ') + '…')
  });
  await muat();
  catat('Upload materi', judul, 'Kelas ' + kelas + ' — ' + rombelLabel({ rombel }), kelas + ' ' + rombel.join(','));
  simpan();
  $('#uJudul').value = ''; $('#uTeks').value = '';
  renderUpload();
  toast('Materi dari dokumen tersimpan untuk kelas ' + kelas + ' (' + rombel.length + ' rombel)');
}
