// Feature: the right side panel — copyable prefix declarations and an index of the course data.
import { esc } from '../../core/html.js';
import { t } from '../../core/i18n.js';
import { api } from '../../core/api.js';
import { store } from '../../core/store.js';
import { highlight } from '../editor/highlight.js';

const STANDARD = [
  ['rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'core RDF vocabulary'],
  ['rdfs', 'http://www.w3.org/2000/01/rdf-schema#', 'RDF Schema'],
  ['xsd', 'http://www.w3.org/2001/XMLSchema#', 'XML Schema datatypes'],
  ['owl', 'http://www.w3.org/2002/07/owl#', 'Web Ontology Language'],
  ['skos', 'http://www.w3.org/2004/02/skos/core#', 'SKOS vocabularies'],
  ['rml', 'http://w3id.org/rml/', 'RML mapping language'],
];
// [prefix, IRI, catalog key of the description]
const COURSE = [
  ['', 'https://example.org/bivak#', 'bivak'],
  ['bv', 'https://example.org/bivak#', 'bv'],
  ['bv', 'https://kbss.fel.cvut.cz/bivak#', 'bvKbss'],
  ['kat', 'https://example.org/bivak/kategorie/', 'kat'],
  ['iucn', 'https://example.org/bivak/iucn/', 'iucn'],
  ['optyp', 'https://example.org/bivak/typ-op/', 'optyp'],
];
const EXPLORE = [
  'SELECT DISTINCT ?p WHERE { ?s ?p ?o }',
  'SELECT DISTINCT ?type WHERE { ?s a ?type }',
  'SELECT ?p ?o WHERE { :OvernightBan_CS ?p ?o }',
  'SELECT ?s ?p WHERE { ?s ?p :NP_Sumava }',
];

let tab = 'pfx', schema = null;

const copyLine = (label, code) =>
  `<div class="ln">${label ? `<span class="t">${label}</span>` : ''}<pre>${highlight(code)}</pre><button class="cp" data-action="copy" data-code="${esc(code)}">${esc(t('ui_copy'))}</button></div>`;

function prefixCard(name, iri, desc, en) {
  return `<div class="pf"><div class="nm"><b>${esc(name || ':')}</b>${en ? `<span class="en">${esc(en)}</span>` : ''}</div><div class="ds">${esc(desc)}</div>`
    + copyLine('TTL', `@prefix ${name}: <${iri}> .`) + copyLine('SPARQL', `PREFIX ${name}: <${iri}>`) + '</div>';
}

function dataHtml(S) {
  const tree = S.tree.map(c => `<div class="tr" style="padding-left:${c.depth * 14}px"><code>${esc(c.name)}</code> <span class="r">${esc(c.label)}</span></div>`).join('');
  const props = S.props.map(p => {
    const dr = (p.domain.length || p.range.length) ? `<span class="r"> ${p.domain.length ? esc(p.domain.join(', ')) + ' → ' : '→ '}${esc(p.range.join(', ') || '?')}${p.transitive ? ' · ' + esc(t('ui_transitive')) : ''}</span>` : '';
    const ex = p.example ? `<div class="ex">${esc(t('ui_example'))}: <code>${esc(p.example[0])} ${esc(p.name)} ${esc(p.example[1])}</code></div>` : '';
    return `<div class="pf"><code>${esc(p.name)}</code> <span class="r">${esc(p.label)}</span>${dr}${ex}</div>`;
  }).join('');
  const inst = S.inst.map(g => `<div class="tr"><code>${esc(g.cls)}</code> <span class="r">×${g.n}</span><div class="ex">${g.items.map(esc).join(', ')}</div></div>`).join('');
  const schemes = S.schemes.map(x => `<div class="tr"><code>${esc(x.name)}</code> <span class="r">${esc(x.label)}</span><div class="ex">${x.concepts.map(esc).join(', ')}</div></div>`).join('');
  const explore = EXPLORE.map((q, i) => `<div class="pf"><span class="r">${esc(t('ui_explore_' + i))}</span>${copyLine('', q)}</div>`).join('');
  return `<h3>${esc(t('ui_dClasses'))}</h3>${tree}<h3>${esc(t('ui_dProps'))}</h3>${props}<h3>${esc(t('ui_dInst'))}</h3>${inst}`
    + `<h3>${esc(t('ui_dSchemes'))}</h3>${schemes}<h3>${esc(t('ui_dExplore'))}</h3>${explore}`;
}

export async function renderSide() {
  const el = document.getElementById('side');
  const tabs = `<div class="tabs"><button class="${tab === 'pfx' ? 'on' : ''}" data-action="side-tab" data-arg="pfx">${esc(t('ui_tabPfx'))}</button><button class="${tab === 'data' ? 'on' : ''}" data-action="side-tab" data-arg="data">${esc(t('ui_tabData'))}</button></div>`;
  if (tab === 'pfx') {
    el.innerHTML = tabs + `<h2>${esc(t('ui_sideTitle'))}</h2><div class="sub">${esc(t('ui_sideSub'))}</div><h3>${esc(t('ui_sideStd'))}</h3>`
      + STANDARD.map(([n, iri, en]) => prefixCard(n, iri, t('prefix_std_' + n), en)).join('')
      + `<h3>${esc(t('ui_sideOwn'))}</h3>` + COURSE.map(([n, iri, k]) => prefixCard(n, iri, t('prefix_own_' + k), '')).join('');
    return;
  }
  el.innerHTML = tabs + `<h2>${esc(t('ui_dataTitle'))}</h2><div class="sub">${esc(t('ui_dataSub'))}</div><div id="schema">…</div>`;
  schema = schema || await api.schema();
  const box = document.getElementById('schema');
  if (box) box.innerHTML = dataHtml(schema);
}

export function setSideTab(name) { tab = name; renderSide() }

export async function copyCode(button) {
  try {
    await navigator.clipboard.writeText(button.dataset.code);
    button.textContent = '✓';
    setTimeout(() => { button.textContent = t('ui_copy') }, 900);
  } catch (e) {}
}

export function toggleSide() { store.set('osw_noside', document.body.classList.toggle('noside')) }
export function toggleNav() { store.set('osw_nohide', document.body.classList.toggle('nohide')) }

export function restorePanels() {
  if (store.get('osw_nohide', false)) document.body.classList.add('nohide');
  if (store.get('osw_noside', window.innerWidth < 1250)) document.body.classList.add('noside');
}
