// Feature: lessons — the left menu with section tabs, progress bar and the list of the current section.
import { state } from '../../core/state.js';
import { esc } from '../../core/html.js';
import { t } from '../../core/i18n.js';
import { progress } from '../progress/progress.js';

export const visibleTabs = () => state.tabs.filter(x => !x.hidden).map(x => x.id);
export const tabItems = tab => state.lessons.map((l, i) => [l, i]).filter(x => x[0].tab === tab);

export function renderNav() {
  const tabs = visibleTabs();
  const stat = tab => { const it = tabItems(tab); return [it.filter(x => progress.isDone(x[0].id)).length, it.length] };
  const total = state.lessons.filter(l => progress.isDone(l.id)).length;
  let h = `<h1>${esc(t('ui_title'))}</h1>
  <div class="small" style="margin:0 6px">${tabs.map(x => esc(t('ui_tab_' + x)) + ' ' + stat(x).join('/')).join(' · ')}</div>
  <div class="bar"><i style="width:${state.lessons.length ? 100 * total / state.lessons.length : 0}%"></i></div>
  <div class="ntabs">${tabs.map(x => `<button class="${x === state.curTab ? 'on' : ''}" title="${esc(t('ui_tabTip_' + x))}" data-action="go-tab" data-arg="${x}">${esc(t('ui_tab_' + x))}<span>${stat(x).join('/')}</span></button>`).join('')}</div>`;
  let part = '';
  tabItems(state.curTab).forEach(([l, i]) => {
    if (l.part !== part) { part = l.part; h += `<h2>${esc(part)}</h2>` }
    h += `<a class="${i === state.cur ? 'cur' : ''}" data-action="show" data-arg="${i}"><span class="m">${progress.isDone(l.id) ? '✓' : '·'}</span><span>${esc(l.title)}</span></a>`;
  });
  h += `<div style="margin:18px 6px 4px"><button style="width:100%;font-size:13px" data-action="reset-all">${esc(t('ui_resetAll'))}</button></div>`;
  document.getElementById('nav').innerHTML = h;
}
