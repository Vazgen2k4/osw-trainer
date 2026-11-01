// Feature: lessons — one lesson on screen: theory, notes, task, editor and navigation.
import { state } from '../../core/state.js';
import { esc } from '../../core/html.js';
import { t } from '../../core/i18n.js';
import { progress } from '../progress/progress.js';
import { mountEditor } from '../editor/editor.js';
import { highlightBlocks } from '../editor/highlight.js';
import { renderNav, tabItems } from './nav.js';
import { run, resetHints } from './runner.js';

export let editor = null;

export function goTab(tab) {
  const items = tabItems(tab);
  if (!items.length) return;
  show((items.find(x => !progress.isDone(x[0].id)) || items[0])[1]);
}

function card(title, body) { return `<div class="card"><h3>${esc(title)}</h3>${body}</div>` }

export function show(i) {
  state.cur = i;
  progress.setLastIndex(i);
  const l = state.lessons[i];
  state.curTab = l.tab;
  resetHints();
  const same = tabItems(l.tab).map(x => x[1]);
  const pos = same.indexOf(i), prevI = pos > 0 ? same[pos - 1] : -1, nextI = pos < same.length - 1 ? same[pos + 1] : -1;

  let h = `<div class="part">${esc(l.part)}</div><h2 class="t">${esc(l.title)}</h2>`;
  if (l.tab === 'exam' && pos === 0) h += `<div class="banner">${t('ui_examBanner')}</div>`;
  if (l.theory) h += card(t('ui_theory'), l.theory);
  if (l.key) h += `<div class="key"><b>${esc(t('ui_key'))}</b> ${l.key}</div>`;
  l.notes.forEach(n => { h += `<div class="key"><b>${esc(n[0])}.</b> ${n[1]}</div>` });
  if (l.origins.length) h += card(t('ui_origins'), `<div class="terms">${l.origins.map(o => `<div title="${esc(o[1])}"><code>${esc(o[0])}</code><span class="en">${esc(o[1])}</span><span class="r">${esc(o[2])}</span></div>`).join('')}</div>`);
  if (l.terms.length) h += card(t('ui_terms'), `<div class="terms">${l.terms.map(x => `<div><span class="en">${esc(x[0])}</span><span class="r">${esc(x[1])}</span></div>`).join('')}</div>`);
  if (l.needs.length) h += card(t('ui_needs'), `<div class="terms">${l.needs.map(n => `<div><code>${esc(n[0])}</code><span class="r">${esc(n[1])}${n[2] ? ' · «' + esc(n[2]) + '»' : ''}</span></div>`).join('')}</div>`);
  h += card(t('ui_task'), l.task + (l.taskOriginal ? `<div class="task-en"><div class="lab">${esc(t('ui_taskOriginal'))}</div>${l.taskOriginal}</div>` : ''));
  const draft = progress.draft(l.id) ?? l.starter;
  h += `<div class="ed"><pre id="hl" aria-hidden="true"></pre><textarea id="ed" spellcheck="false">${esc(draft)}</textarea></div>
  <div class="row"><button class="p" id="run" data-action="run">${esc(t('ui_run'))}</button>
  ${l.exam ? '' : `<button data-action="hint">${esc(t('ui_hint'))}</button>`}
  <button data-action="solution">${esc(t('ui_showSol'))}</button><button data-action="reset">${esc(t('ui_reset'))}</button>
  ${l.kind === 'sparql' ? `<label class="inf"><input type="checkbox" id="inf"> ${esc(t('ui_includeInferred'))}</label>` : ''}</div>
  <div class="small" style="margin:-2px 0 6px">⌨ ${esc(t('ui_keys'))}</div>
  <div id="hints"></div><div id="out"></div><div id="sol" class="sol card"><h3>${esc(t('ui_solution'))}</h3><pre id="solt"></pre></div>`;
  if (l.tab === 'learn' && nextI < 0) h += `<div class="banner">${t('ui_lessonsDone')}<button data-action="go-tab" data-arg="sparql">${esc(t('ui_startPractice'))}</button> <button data-action="go-tab" data-arg="exam">${esc(t('ui_startExam'))}</button></div>`;
  h += `<div class="row">${prevI >= 0 ? `<button data-action="show" data-arg="${prevI}">${esc(t('ui_back'))}</button>` : ''}${nextI >= 0 ? `<button data-action="show" data-arg="${nextI}">${esc(t('ui_next'))}</button>` : ''}</div>`;
  if (l.tab === 'exam' && nextI < 0 && tabItems('exam').every(x => progress.isDone(x[0].id))) h += `<div class="banner">${t('ui_allDone')}</div>`;

  const main = document.getElementById('main');
  main.innerHTML = h;
  highlightBlocks(main);
  editor = mountEditor({
    textarea: document.getElementById('ed'), mirror: document.getElementById('hl'),
    onInput: text => progress.saveDraft(l.id, text), onRun: run,
  });
  renderNav();
  window.scrollTo(0, 0);
}
