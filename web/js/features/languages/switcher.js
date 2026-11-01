// Feature: languages — the language <select> in the toolbar. Its last item opens the language dialog.
import { esc } from '../../core/html.js';
import { t, lang } from '../../core/i18n.js';

const ADD = '__add';

export function renderSwitcher(locales, { onSelect, onAdd }) {
  const sel = document.getElementById('lang');
  sel.innerHTML = locales.map(x => `<option value="${esc(x.code)}"${x.code === lang ? ' selected' : ''}>${esc(x.name)}</option>`).join('')
    + `<option value="${ADD}">${esc(t('ui_langAdd'))}</option>`;
  sel.title = t('ui_langT');
  sel.onchange = () => {
    if (sel.value === ADD) { sel.value = lang; onAdd() } else onSelect(sel.value);
  };
}
