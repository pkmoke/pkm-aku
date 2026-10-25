const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    await page.goto('http://127.0.0.1:8899/');
    await page.locator('[data-act="masuk"]').click();
    await page.locator('#appView').waitFor({ state: 'visible' });
    await page.waitForTimeout(700);
    // Use actual editor buttons and submit events, with isolated browser storage.
    await page.evaluate(async () => {
      const { status } = await import('/src/js/status.js');
      status.role = 'teacher';
      const ui = await import('/src/js/ui.js');
      ui.aturRoleUI(); ui.tampilkanHalaman('t-materi');
    });
    await page.locator('[data-act="editMateri"][data-id="m1"]').click();
    await page.locator('#editJudul').fill('Respirasi <img src=x onerror="window.injected=1">');
    await page.locator('#editTeks').fill('Alveolus adalah tempat pertukaran gas.\nTrakea menghubungkan laring dengan bronkus.');
    await page.locator('#editForm button[type="submit"]').click();
    assert.equal(await page.locator('#daftarMateriGuru img').count(), 0);
    await page.locator('[data-act="editMateri"][data-id="m1"]').click();
    await page.locator('#editJudul').fill('Cancelled change');
    await page.locator('#editForm [data-act="tutupModal"]').click();
    await page.evaluate(async () => (await import('/src/js/ui.js')).tampilkanHalaman('t-soal'));
    await page.locator('[data-act="editSoal"][data-id="q1"]').click();
    await page.locator('#editTanya').fill('Di mana pertukaran gas terjadi?');
    await page.locator('#editOpsi2').fill('Alveolus (kantung udara)');
    await page.locator('#editPembahasan').fill('Dinding alveolus tipis sehingga gas dapat berdifusi. <b>teks biasa</b>');
    for (const checkbox of await page.locator('#editKelas input').all()) await checkbox.uncheck();
    await page.locator('#editForm button[type="submit"]').click();
    assert.match(await page.locator('#editError').textContent(), /minimal satu kelas/);
    await page.locator('#editKelas input[value="VIII A"]').check();
    await page.locator('#editForm button[type="submit"]').click();
    await page.reload();
    const saved = await page.evaluate(async () => {
      const { status } = await import('/src/js/status.js');
      return { m: status.db.materi.find(m => m.id === 'm1'), q: status.db.soal.find(s => s.id === 'q1'), count: status.db.soal.length };
    });
    assert.match(saved.m.judul, /^Respirasi/);
    assert.equal(saved.q.tanya, 'Di mana pertukaran gas terjadi?');
    assert.equal(saved.q.jawaban, 2);
    assert.equal(saved.q.opsi[2], 'Alveolus (kantung udara)');
    assert.deepEqual(saved.q.kelas, ['VIII A']);
    assert.equal(saved.count, 9);
    await page.locator('[data-act="masuk"]').click();
    await page.locator('#appView').waitFor({ state: 'visible' });
    await page.waitForTimeout(700);
    await page.evaluate(async () => {
      (await import('/src/js/ui.js')).tampilkanHalaman('s-latihan');
    });
    await page.locator('#pilihLatihanCepat [data-act="keLatihan"][data-id="m1"]').click();
    await page.locator('input[name="s_q1"][value="0"]').check(); // Wrong
    await page.locator('input[name="s_q2"][value="1"]').check();
    await page.locator('input[name="s_q3"][value="1"]').check(); // q4 unanswered
    await page.locator('#formLatihan button[type="submit"]').click();
    assert.match(await page.locator('#pembahasanLatihan').textContent(), /Dinding alveolus tipis/);
    assert.equal(await page.locator('#pembahasanLatihan b').filter({ hasText: 'teks biasa' }).count(), 0);
    assert.equal(await page.locator('#formLatihan button[type="submit"]').isDisabled(), true);
    await page.evaluate(async () => (await import('/src/js/siswa/latihan.js')).kumpulkanLatihan());
    assert.equal(await page.evaluate(async () => (await import('/src/js/status.js')).status.db.hasil.length), 1);
    await page.locator('#ulangSalah').click();
    assert.equal(await page.locator('#formLatihan [data-soal]').count(), 2);
    assert.equal(await page.locator('input[name="s_q2"]').count(), 0);
    await page.locator('input[name="s_q1"][value="2"]').check();
    await page.locator('input[name="s_q4"][value="0"]').check();
    await page.locator('#formLatihan button[type="submit"]').click();
    assert.equal(await page.locator('#ulangSalah').count(), 0);
    const results = await page.evaluate(async () => (await import('/src/js/status.js')).status.db.hasil);
    assert.equal(results.length, 2);
    assert.equal(results[0].nilai, 100);
    assert.equal(results[0].total, 2);
    assert.equal(results[0].ulangDari, results[1].id);
    assert.equal(results[1].nilai, 50);
    assert.equal(await page.evaluate(() => Boolean(window.injected)), false);
    assert.deepEqual(errors, []);
    await page.waitForTimeout(1200);
    await page.screenshot({ path: '/tmp/pekaem-learning-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(600);
    await page.screenshot({ path: '/tmp/pekaem-learning-mobile.png', fullPage: true });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Mobile horizontal overflow');
    const creation = await page.evaluate(async () => {
      const { status } = await import('/src/js/status.js');
      const teacher = await import('/src/js/guru/soal.js');
      status.role = 'teacher'; teacher.renderKelolaSoal();
      document.querySelector('#qPertanyaan').value = 'Contoh soal manual';
      ['qA', 'qB', 'qC', 'qD'].forEach((id, i) => document.getElementById(id).value = 'Pilihan ' + i);
      document.querySelector('#qPembahasan').value = 'Penjelasan manual';
      document.querySelector('#qBenar').value = '3';
      teacher.tambahSoalManual();
      const manual = status.db.soal.at(-1);
      document.querySelector('#soalMateri').value = 'm2';
      teacher.generateSoal();
      const generated = window._draftSoal;
      return { manual: manual.pembahasan === 'Penjelasan manual' && manual.jawaban === 3,
        generated: generated.length > 0 && generated.every(s => s.pembahasan.includes(s.opsi[s.jawaban])) };
    });
    assert.deepEqual(creation, { manual: true, generated: true });
    assert.deepEqual(errors, []);
    console.log('PASS editing, cancellation, validation, persistence, explanations, unanswered questions, retry subset, duplicate-submit prevention, perfect score, injection safety, mobile width');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
