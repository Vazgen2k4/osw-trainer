// Feature: lessons — check the answer, reveal hints one by one, show the reference solution, reset the draft.
import { state } from '../../core/state.js';
import { esc } from '../../core/html.js';
import { api } from '../../core/api.js';
import { t, lang } from '../../core/i18n.js';
import { highlight } from '../editor/highlight.js';
import { progress } from '../progress/progress.js';
import { renderNav } from './nav.js';
import { editor } from './view.js';

const hintsShown = {};
const lesson = () => state.lessons[state.cur];
const $ = id => document.getElementById(id);

function table(cols, rows) {
  return `<div class="res"><table><tr>${cols.map(c => `<th>?${esc(c)}</th>`).join('')}</tr>` +
    rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('') +
    `</table></div><div class="small">${rows.length} ${esc(t('ui_rows'))}</div>`;
}

function verdict(r) {
  if (r.error) return `<div class="verdict bad">${esc(t('ui_error'))}<pre>${esc(r.error)}</pre></div>`;
  let h = `<div class="verdict ${r.passed ? 'ok' : 'bad'}">${r.passed ? '✓ ' : '✗ '}${esc(r.message).replace(/\n/g, '<br>')}`;
  if (r.checks) h += '<ul>' + r.checks.map(c => `<li>${c.ok ? '✓' : '✗'} ${esc(c.desc)}</li>`).join('') + '</ul>';
  if (r.diff && r.diff.length) h += '<ul>' + r.diff.map(d => `<li>${esc(d)}</li>`).join('') + '</ul>';
  h += '</div>';
  const q = r.result;
  if (q && q.type === 'SELECT') h += table(q.cols, q.rows);
  else if (q && q.type === 'ASK') h += `<pre>${q.value}</pre>`;
  else if (q && q.type === 'CONSTRUCT') h += table(['s', 'p', 'o'], q.triples);
  if (r.triples && r.triples.length) h += table(['s', 'p', 'o'], r.triples.map(x => [x.s, x.p, x.o]));
  return h;
}

export async function run() {
  const l = lesson(), btn = $('run'), inf = $('inf');
  btn.disabled = true; btn.textContent = '…';
  let r;
  try { r = await api.run(l.id, editor.value, inf ? inf.checked : false, lang) } catch (e) { r = { error: String(e) } }
  btn.disabled = false; btn.textContent = t('ui_run');
  $('out').innerHTML = verdict(r);
  // an exam task whose solution was revealed does not count
  const revealed = l.exam && $('sol').style.display === 'block';
  if (r.passed && !progress.isDone(l.id) && !revealed) { progress.markDone(l.id); renderNav() }
}

export function hint() {
  const l = lesson();
  if (!l.hints.length) { $('hints').innerHTML = `<div class="hint small">${esc(t('ui_noHints'))}</div>`; return }
  const n = hintsShown[l.id] = Math.min((hintsShown[l.id] || 0) + 1, l.hints.length);
  $('hints').innerHTML = l.hints.slice(0, n).map((x, k) => `<div class="hint"><b>${k + 1}.</b> ${x}</div>`).join('')
    + (n === l.hints.length ? `<div class="small">${esc(t('ui_allHints'))}</div>` : '');
  $('hints').querySelectorAll('pre').forEach(p => { p.innerHTML = highlight(p.textContent) });
}

export function resetHints() { delete hintsShown[lesson().id] }

export async function solution() {
  const l = lesson();
  if (l.exam && !confirm(t('ui_confirmSol'))) return;
  const r = await api.solution(l.id);
  $('solt').innerHTML = highlight(r.ref || '');
  $('sol').style.display = 'block';
  if (l.exam) { progress.unmark(l.id); renderNav() }
}

export function resetDraft() {
  const l = lesson();
  if (!confirm(t('ui_confirmReset'))) return;
  progress.dropDraft(l.id);
  editor.value = l.starter;
}
