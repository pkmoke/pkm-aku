import { api } from '../api.js';
import { muat } from '../status.js';
import { ROMBEL, TINGKAT, kodeKelas, tingkatDari } from '../konstanta.js';
import { hasilFilter, materiKelas, materiTingkat, rombelLabel, soalKelas, soalTingkat } from '../seleksi.js';
import { bersihkanDataLama } from '../status.js';
import { aturRoleUI, bukaModal, toast, tutupModal } from '../ui.js';
import { $, elemen, esc, jam } from '../util.js';
import { status } from '../status.js';

export function renderAnalisis() {
  const dibuang = bersihkanDataLama();
  if (dibuang) toast(dibuang + ' baris data lebih dari 24 jam dihapus otomatis');

  $('#filterKelasAnalisis').innerHTML = ['semua', ...TINGKAT].map((k) =>
    `<button class="chipkelas" data-act="filterTingkat" data-tingkat="${k}" aria-pressed="${status.filterTingkat === k}">${k === 'semua' ? 'Semua tingkat' : 'Kelas ' + k}</button>`).join('');
  $('#filterRombelAnalisis').innerHTML = status.filterTingkat === 'semua' ? '' : ['semua', ...ROMBEL].map((r) =>
    `<button class="chipkelas" data-act="filterRombel" data-rombel="${r}" aria-pressed="${status.filterRombel === r}">${r === 'semua' ? 'Semua rombel' : status.filterTingkat + ' ' + r}</button>`).join('');
  $('#filterRombelAnalisis').style.display = status.filterTingkat === 'semua' ? 'none' : 'flex';

  const lingkup = status.filterTingkat === 'semua' ? 'seluruh kelas'
    : status.filterRombel === 'semua' ? 'kelas ' + status.filterTingkat : 'kelas ' + status.filterTingkat + ' ' + status.filterRombel;
  const labelTombol = status.filterTingkat === 'semua' ? 'Pilih kelas untuk menghapus'
    : 'Hapus data ' + lingkup;
  $('#ttlInfo').innerHTML =
    `<b>Data analisis disimpan 24 jam saja.</b> Hasil latihan &amp; riwayat yang lebih tua dihapus otomatis supaya tidak menumpuk di database — jadi semua angka di halaman ini hanya untuk <b>1 hari terakhir</b>.` +
    `<div class="small" style="margin-top:8px">Tersimpan sekarang: <b>${status.db.hasil.length}</b> hasil latihan · <b>${status.db.aktivitas.length}</b> aktivitas · <b>${status.db.chat.length}</b> riwayat chat. Terakhir dibersihkan ${jam(status.db.bersihTerakhir || Date.now())} · total sudah dihapus otomatis: <b>${status.db.dihapus || 0}</b> baris.</div>` +
    `<div class="btnrow" style="margin-top:10px"><button class="btn danger small" data-act="hapusAnalisis">${labelTombol}</button><button class="btn ghost small" data-act="eksporNilai">Unduh nilai (CSV)</button></div>` +
    `<div class="small" style="margin-top:8px">Pilih tingkat (dan rombel) di atas untuk menghapus data kelas itu saja. Tanpa pilihan, penghapusan ditolak.</div>`;

  const barisRingkasan = (judul, cocok, materiN, soalN) => {
    const h = status.db.hasil.filter(cocok);
    const r = h.length ? Math.round(h.reduce((a, b) => a + b.nilai, 0) / h.length) : 0;
    return `<div style="margin-bottom:14px">
      <div class="stat"><span>${judul} <span class="small muted"> ${h.length} latihan · ${materiN} materi · ${soalN} soal</span></span><b>${h.length ? r + '%' : '—'}</b></div>
      <div class="bar"><span style="width:${r}%"></span></div></div>`;
  };
  if (status.filterTingkat === 'semua') {
    $('#judulRingkasan').textContent = 'Ringkasan per Tingkat';
    $('#ringkasanKelas').innerHTML = TINGKAT.map((t) =>
      barisRingkasan('Kelas ' + t, (x) => tingkatDari(x.kelas) === t, materiTingkat(t).length, soalTingkat(t).length)).join('') +
      '<p class="small muted">Pilih salah satu tingkat di atas untuk melihat rincian per rombel (AF).</p>';
  } else {
    $('#judulRingkasan').textContent = 'Ringkasan Kelas ' + status.filterTingkat + ' per Rombel';
    $('#ringkasanKelas').innerHTML = ROMBEL.map((r) => {
      const kode = kodeKelas(status.filterTingkat, r);
      return barisRingkasan(kode, (x) => x.kelas === kode, materiKelas(kode).length, soalKelas(kode).length);
    }).join('') +
      '<p class="small muted">Kelas tanpa latihan ditandai "—". Angka dihitung dari latihan yang benar-benar dikerjakan siswa kelas tersebut.</p>';
  }

  const hasil = hasilFilter();
  const labelKelas = status.filterTingkat === 'semua' ? 'semua kelas'
    : (status.filterRombel === 'semua' ? 'kelas ' + status.filterTingkat : 'kelas ' + status.filterTingkat + ' ' + status.filterRombel);
  const nilai = hasil.map((h) => h.nilai);
  const bucket = [['90100', (n) => n >= 90], ['8089', (n) => n >= 80 && n < 90], ['7079', (n) => n >= 70 && n < 80], ['<70', (n) => n < 70]];
  $('#distribusiNilai').innerHTML = nilai.length
    ? bucket.map(([label, fn]) =>
        `<div class="list-item"><span>${label}</span><b>${nilai.filter(fn).length} latihan</b></div>`).join('')
      + `<p class="small muted" style="margin-top:10px">Rata-rata ${Math.round(nilai.reduce((a, b) => a + b, 0) / nilai.length)} dari ${nilai.length} latihan (${labelKelas}).</p>`
    : '<p class="muted">Belum ada latihan yang dikerjakan ' + labelKelas + '.</p>';

  const agg = {};
  hasil.forEach((h) => h.detail.forEach((d) => {
    agg[d.soalId] = agg[d.soalId] || { benar: 0, total: 0 };
    agg[d.soalId].total++;
    if (d.benar) agg[d.soalId].benar++;
  }));
  const urut = Object.entries(agg).map(([id, v]) => {
    const s = status.db.soal.find((x) => x.id === id);
    return { soal: s, persen: Math.round((v.benar / v.total) * 100), total: v.total };
  }).filter((x) => x.soal).sort((a, b) => a.persen - b.persen);

  $('#soalSulit').innerHTML = urut.length
    ? urut.slice(0, 5).map((x) => `
        <div class="feature" style="margin-bottom:12px">
          <div class="icon dot ${x.persen < 50 ? 'warn' : x.persen < 80 ? 'mid' : ''}"></div>
          <div><h3>${esc(x.soal.topik || 'Soal')} — ${x.persen}% benar</h3>
            <p class="small muted">${esc(x.soal.tanya)}</p>
            <p class="small muted">Dikerjakan ${x.total} kali</p></div>
        </div>`).join('')
    : '<p class="muted">Belum ada data jawaban.</p>';

  const daftarMateriGuru = status.filterTingkat === 'semua'
    ? status.db.materi
    : status.db.materi.filter((m) => m.kelas === status.filterTingkat && (status.filterRombel === 'semua' || (m.rombel || ROMBEL).includes(status.filterRombel)));
  $('#rincianMateri').innerHTML = daftarMateriGuru.map((m) => {
    const h = hasil.filter((x) => x.materiId === m.id);
    if (!h.length) return `<div class="list-item"><span>${esc(m.judul)} <span class="tag">kelas ${esc(m.kelas)} — ${esc(rombelLabel(m))}</span></span><span class="tag">belum dikerjakan</span></div>`;
    const r = Math.round(h.reduce((a, b) => a + b.nilai, 0) / h.length);
    return `<div class="list-item"><span>${esc(m.judul)} <span class="tag">kelas ${esc(m.kelas)} — ${esc(rombelLabel(m))}</span><div class="small muted">${h.length} latihan · rata-rata ${r}</div></span>
      <span class="tag ${r >= 80 ? 'green' : 'amber'}">${r >= 80 ? 'baik' : 'perlu penguatan'}</span></div>`;
  }).join('') || '<p class="muted">Belum ada materi untuk kelas ini.</p>';

  muatRekap().catch((e) => toast(e.message));
}

function lingkupSekarang() {
  if (status.filterTingkat === 'semua') return null;
  return { tingkat: status.filterTingkat, rombel: status.filterRombel === 'semua' ? '' : status.filterRombel };
}

async function muatRekap() {
  const el = $('#rekapHarian');
  if (!el) return;
  const q = new URLSearchParams({ hari: '30' });
  const l = lingkupSekarang();
  if (l) { q.set('tingkat', l.tingkat); if (l.rombel) q.set('rombel', l.rombel); }
  const data = await api.get('/rekap?' + q.toString());
  el.innerHTML = data.perKelas.length
    ? data.perKelas.map((r) => `<div class="list-item"><span>Kelas ${esc(r.kelas)}
        <div class="small muted">${r.latihan} latihan dalam 30 hari</div></span>
        <span class="tag ${r.rataRata != null && r.rataRata >= 80 ? 'green' : 'amber'}">${r.rataRata == null ? '—' : r.rataRata + '%'}</span></div>`).join('')
      + `<p class="small muted" style="margin-top:10px">Diambil dari rekap harian yang disimpan sebelum data 24 jam dibersihkan. Total ${data.totalLatihan} latihan.</p>`
    : '<p class="muted">Belum ada rekap harian. Rekap terisi setelah pembersihan otomatis berjalan di server.</p>';
}

export async function eksporNilai() {
  const q = new URLSearchParams();
  const l = lingkupSekarang();
  if (l) { q.set('tingkat', l.tingkat); if (l.rombel) q.set('rombel', l.rombel); }
  const res = await fetch('/api/ekspor?' + q.toString(), { credentials: 'same-origin' });
  if (!res.ok) { toast('Gagal mengunduh nilai'); return; }
  const blob = await res.blob();
  const tautan = elemen('a', { href: URL.createObjectURL(blob), download: 'nilai-bemai.csv' });
  document.body.append(tautan);
  tautan.click();
  tautan.remove();
  URL.revokeObjectURL(tautan.href);
  toast('Nilai diunduh sebagai CSV');
}

export async function hapusAnalisisSekarang() {
  const l = lingkupSekarang();
  if (!l) {
    toast('Pilih tingkat dan rombel dulu — penghapusan dilakukan per kelas, bukan seluruh sekolah');
    return;
  }
  const label = l.rombel ? l.tingkat + ' ' + l.rombel : 'semua rombel kelas ' + l.tingkat;
  if (!confirm('Hapus hasil latihan, riwayat chat, dan aktivitas kelas ' + label + '? Tindakan ini tidak bisa dibatalkan.')) return;
  const q = new URLSearchParams({ tingkat: l.tingkat });
  if (l.rombel) q.set('rombel', l.rombel);
  const data = await api.hapus('/analisis?' + q.toString());
  await muat();
  renderAnalisis();
  const jumlah = data && data.dihapus ? Object.values(data.dihapus).reduce((a, b) => a + b, 0) : 0;
  toast(jumlah + ' baris data kelas ' + label + ' dihapus');
}

export function catatanTeknis() {
  bukaModal('Status aplikasi', 'Frontend dan API terhubung', '<p>Login, materi, soal, penilaian, chat dan riwayat memakai API serta PostgreSQL. Chat menggunakan pencarian materi, belum LLM. Ekstraksi PDF/DOCX dan impor siswa belum tersedia.</p>');
}
export function resetData() { toast('Reset data hanya melalui administrasi database lokal'); }
