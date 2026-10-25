// Run with Node and Playwright available; start the frontend on port 8899 first.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage(); // Isolated storage; never changes the user's demo data.
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8899/');
    await page.locator('[data-act="masuk"]').click();
    await page.locator('#appView').waitFor({ state: 'visible' });
    const results = await page.evaluate(async () => {
      const { status } = await import('/src/js/status.js');
      const chat = await import('/src/js/siswa/chat.js');
      const materi = await import('/src/js/siswa/materi.js');
      const ringkas = await import('/src/js/siswa/rangkuman.js');
      const latihan = await import('/src/js/siswa/latihan.js');
      const soal = await import('/src/js/guru/soal.js');
      const ui = await import('/src/js/ui.js');
      const payload = '<img src=x onerror="window.injected=1"> & "quotes"';
      const bubble = chat.tambahBubble(payload + '\nsecond line', 'me', payload);
      const chatSafe = bubble.textContent.includes(payload) && !bubble.querySelector('img') && bubble.querySelectorAll('br').length === 1;
      chat.isiBubble(bubble, payload + '\nsecond line', payload);
      const animatedSafe = bubble.querySelectorAll('.baris-jawab').length === 2 && !bubble.querySelector('img');
      const m = status.db.materi[0];
      status.kelasSiswa = m.kelas + ' ' + m.rombel[0];
      m.judul = payload; m.teks = [payload]; m.rangkuman = [payload];
      materi.renderMateriSiswa();
      const cardsSafe = document.querySelector('#daftarMateriSiswa').textContent.includes(payload) && !document.querySelector('#daftarMateriSiswa img');
      materi.bacaMateri(m.id);
      const modalSafe = document.querySelector('#modalIsi').textContent.includes(payload) && !document.querySelector('#modalIsi img');
      ui.tutupModal();
      ringkas.renderPilihRangkuman();
      document.querySelector('#pilihMateriRangkuman').value = m.id;
      ringkas.buatRangkuman();
      const summarySafe = document.querySelector('#areaRangkuman li').textContent === payload && !document.querySelector('#areaRangkuman img');
      soal.renderKelolaSoal();
      const optionsSafe = document.querySelector('#soalMateri option').textContent.includes(payload) && document.querySelector('#qMateriManual option').value === m.id;
      latihan.renderPilihLatihan();
      const selected = document.querySelector('#pilihMateriLatihan').value;
      latihan.mulaiLatihan(selected);
      const form = document.querySelector('#formLatihan');
      if (form) {
        for (const group of form.querySelectorAll('[data-soal]')) group.querySelector('input').checked = true;
        form.requestSubmit();
      }
      const quizWorks = !!form && status.db.hasil.length > 0 && !!document.querySelector('.skor-ring');
      latihan.batalLatihan();
      const cleared = !document.querySelector('#areaLatihan').childNodes.length;
      status.db.materi = []; status.db.soal = [];
      ringkas.renderPilihRangkuman(); latihan.renderPilihLatihan(); soal.renderKelolaSoal();
      const emptyWorks = document.querySelector('#pilihMateriRangkuman').value === '' && document.querySelector('#soalMateri').options.length === 0;
      return { chatSafe, animatedSafe, cardsSafe, modalSafe, summarySafe, optionsSafe, quizWorks, cleared, emptyWorks, noInjection: !window.injected };
    });
    for (const [name, passed] of Object.entries(results)) assert.equal(passed, true, name);
    assert.deepEqual(errors, [], 'Browser runtime errors');
    console.log('PASS', Object.keys(results).join(', '));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
