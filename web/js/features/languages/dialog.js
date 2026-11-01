// Feature: languages — export a translation template, copy the AI prompt, upload translated packs, remove them.
import { esc } from '../../core/html.js';
import { t, lang } from '../../core/i18n.js';
import { api } from '../../core/api.js';
import { store } from '../../core/store.js';

const dlg = () => document.getElementById('lang-dialog');
let ctx = null;  // {locales, tabs, onChanged(code?)}
let report = '';

function form() {
  const v = id => (document.getElementById(id) || {}).value || '';
  return { name: v('ld-name').trim(), code: v('ld-code').trim(), source: v('ld-source'), part: v('ld-part') };
}

function render() {
  const f = Object.assign({ source: lang === 'ru' ? 'ru' : 'en', part: 'all' }, store.get('osw_lang_target', {}));
  const builtin = ctx.locales.filter(x => x.builtin);
  const parts = ['all', 'ui', ...ctx.tabs];
  const partName = p => t(p === 'all' || p === 'ui' ? 'ui_langPart_' + p : 'ui_tab_' + p);
  const rows = ctx.locales.map(x => `<li><b>${esc(x.name)}</b> <code>${esc(x.code)}</code>
      <span class="small">${x.builtin ? esc(t('ui_langBuiltin')) : esc(t('ui_langCoverage', { pct: x.coverage }))}</span>
      ${x.builtin ? '' : `<button data-action="lang-remove" data-arg="${esc(x.code)}" data-name="${esc(x.name)}">${esc(t('ui_langRemove'))}</button>`}</li>`).join('');
  dlg().innerHTML = `<form method="dialog" class="dlg">
    <h2>${esc(t('ui_langTitle'))}</h2>
    <div class="small">${esc(t('ui_langIntro'))}</div>
    <h3>${esc(t('ui_langInstalled'))}</h3><ul class="langs">${rows}</ul>
    <h3>${esc(t('ui_langStep1'))}</h3>
    <div class="row">
      <label>${esc(t('ui_langTarget'))}<input id="ld-name" placeholder="Deutsch" value="${esc(f.name || '')}" autocomplete="off"></label>
      <label style="flex:0 0 110px;min-width:0">${esc(t('ui_langCode'))}<input id="ld-code" placeholder="de" value="${esc(f.code || '')}" pattern="[a-z]{2,3}(-[A-Za-z0-9]{2,8})*" autocomplete="off"></label>
    </div>
    <div class="row">
      <label>${esc(t('ui_langSource'))}<select id="ld-source">${builtin.map(x => `<option value="${esc(x.code)}"${x.code === f.source ? ' selected' : ''}>${esc(x.name)}</option>`).join('')}</select></label>
      <label>${esc(t('ui_langPart'))}<select id="ld-part">${parts.map(p => `<option value="${p}"${p === f.part ? ' selected' : ''}>${esc(partName(p))}</option>`).join('')}</select></label>
    </div>
    <div class="small">${esc(t('ui_langPartHelp'))}</div>
    <div class="row"><button type="button" class="p" data-action="lang-download">${esc(t('ui_langDownload'))}</button></div>
    <h3>${esc(t('ui_langStep2'))}</h3>
    <div class="row"><button type="button" data-action="lang-prompt">${esc(t('ui_langCopyPrompt'))}</button><span id="ld-copied" class="small"></span></div>
    <h3>${esc(t('ui_langStep3'))}</h3>
    <div class="row"><button type="button" data-action="lang-upload">${esc(t('ui_langUpload'))}</button>
      <input id="ld-file" type="file" accept=".arb,.json,application/json" multiple hidden></div>
    <div id="ld-report" class="report">${report}</div>
    <div class="row" style="justify-content:flex-end"><button value="close">${esc(t('ui_close'))}</button></div>
  </form>`;
  dlg().querySelectorAll('input,select').forEach(el => el.addEventListener('change', () => store.set('osw_lang_target', form())));
  document.getElementById('ld-file').addEventListener('change', e => upload([...e.target.files]));
}

export function openLanguageDialog(context) {
  ctx = context;
  report = '';
  render();
  if (!dlg().open) dlg().showModal();
}

export function downloadTemplate() {
  const f = form();
  store.set('osw_lang_target', f);
  const a = document.createElement('a');
  a.href = api.templateUrl({ source: f.source, part: f.part, code: f.code, name: f.name });
  a.download = '';
  document.body.appendChild(a); a.click(); a.remove();
}

export async function copyPrompt() {
  const f = form();
  const target = f.name && f.code ? `${f.name} (${f.code})` : (f.name || f.code || '…');
  try {
    await navigator.clipboard.writeText(t('ui_langPrompt', { target }));
    document.getElementById('ld-copied').textContent = '✓ ' + t('ui_langCopied');
  } catch (e) {}
}

export function chooseFiles() { document.getElementById('ld-file').click() }

async function upload(files) {
  const f = form();
  const parts = [];
  let last = null;
  for (const file of files) {
    const r = await api.importPack(await file.text(), { lang, code: f.code, name: f.name });
    if (r.error) { parts.push(`<div class="verdict bad">${esc(file.name)}: ${esc(r.error)}</div>`); continue }
    last = r.code;
    parts.push(`<div class="verdict ok">✓ ${esc(t('ui_langImported', { name: r.name, code: r.code, count: r.count, pct: r.coverage }))}`
      + (r.warnings.length ? `<div class="small">${esc(t('ui_langWarnings'))}:</div><ul>${r.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : '')
      + '</div>');
  }
  report = parts.join('');
  ctx = await ctx.onChanged(last) || ctx;
  render();
}

export async function removeLanguage(button) {
  if (!confirm(t('ui_langConfirmRemove', { name: button.dataset.name }))) return;
  const r = await api.removePack(button.dataset.arg, lang);
  report = r.error ? `<div class="verdict bad">${esc(r.error)}</div>` : '';
  ctx = await ctx.onChanged(null, button.dataset.arg) || ctx;
  render();
}
