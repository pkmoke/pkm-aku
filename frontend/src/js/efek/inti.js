import { $, $$ } from '../util.js';

export function tenang() {
  return document.documentElement.classList.contains('tenang')
    || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function pasangTilt(el, kuat) {
  if (!el || el.dataset.tiltPasang === '1') return;
  el.dataset.tiltPasang = '1';
  el.setAttribute('data-tilt', '1');
  const batas = kuat || Number(el.dataset.tiltKuat) || 6;
  const lepas = () => { el.style.animation = 'none'; };
  el.addEventListener('animationend', lepas, { once: true });
  setTimeout(lepas, 1100);
  el.addEventListener('mousemove', (e) => {
    if (tenang()) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--ry', (((e.clientX - r.left) / r.width - 0.5) * batas).toFixed(2) + 'deg');
    el.style.setProperty('--rx', (((e.clientY - r.top) / r.height - 0.5) * -batas).toFixed(2) + 'deg');
  });
  el.addEventListener('mouseleave', () => {
    el.style.setProperty('--rx', '0deg');
    el.style.setProperty('--ry', '0deg');
  });
}

export function pasangSemuaTilt(akar) {
  $$('[data-tilt]', akar || document).forEach((el) => pasangTilt(el));
}

export function geserSorot() {
  const nav = $$('.nav').find((n) => n.offsetParent !== null);
  if (!nav) return;
  const glow = $('.nav-glow', nav);
  const aktif = $('button.active', nav);
  if (!glow || !aktif) return;
  glow.style.height = aktif.offsetHeight + 'px';
  glow.style.transform = 'translateY(' + aktif.offsetTop + 'px)';
}
