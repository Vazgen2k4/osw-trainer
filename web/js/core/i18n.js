// UI strings of the current language (fetched from the server's ARB catalogs).
import { api } from './api.js';

let strings = {};
export let lang = 'ru';

export async function loadStrings(code) {
  const r = await api.strings(code);
  strings = r.strings || {};
  lang = r.locale || code;
  document.documentElement.lang = lang;
  return lang;
}

// t('ui_langCoverage', {pct: 80}) — fills {name} placeholders; a missing key shows the key itself.
export function t(key, params) {
  const s = strings[key] ?? key;
  return params ? s.replace(/\{(\w+)\}/g, (m, n) => (n in params ? params[n] : m)) : s;
}
