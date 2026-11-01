// Feature: colour theme. Dark unless the user chose light; the system preference is deliberately ignored.
import { store } from '../../core/store.js';
import { t } from '../../core/i18n.js';

const KEY = 'osw_theme';
const current = () => (document.documentElement.dataset.theme === 'light' ? 'light' : 'dark');

export function renderThemeButton() {
  const b = document.getElementById('theme');
  b.textContent = current() === 'dark' ? '☾' : '☀';
  b.title = t('ui_themeT');
  b.setAttribute('aria-label', t('ui_themeT'));
}

export function toggleTheme() {
  const next = current() === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  store.set(KEY, next);
  renderThemeButton();
}
