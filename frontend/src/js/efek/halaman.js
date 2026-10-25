import { $ } from '../util.js';
import { geserSorot, pasangSemuaTilt, tenang } from './inti.js';
import { gambarCincin, isiAngka } from './angka.js';

export function jalankanEfek(id) {
  const p = $('#' + id);
  if (!p) return;
  isiAngka(p);
  gambarCincin(p);
  pasangSemuaTilt(p);
  geserSorot();
}

export function tampilkanKerangka(id, lanjut) {
  const p = $('#' + id);
  const k = p ? p.querySelector('.kerangka-halaman') : null;
  if (!k || tenang()) {
    if (k) k.classList.remove('tampil');
    lanjut();
    return;
  }
  k.classList.add('tampil');
  setTimeout(() => { k.classList.remove('tampil'); lanjut(); }, 900);
}

export function tampilkanView(el, keluar) {
  if (tenang()) { keluar(); return; }
  el.classList.add('keluar-view');
  setTimeout(() => { el.classList.remove('keluar-view'); keluar(); }, 400);
}
