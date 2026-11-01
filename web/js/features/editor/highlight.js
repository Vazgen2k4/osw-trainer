// Feature: syntax highlighting shared by Turtle, SPARQL and RML (one tokenizer is enough for all three).
import { t } from '../../core/i18n.js';
import { esc } from '../../core/html.js';

const KW = /^(SELECT|DISTINCT|WHERE|FILTER|OPTIONAL|UNION|VALUES|BIND|IF|EXISTS|NOT|ORDER|BY|GROUP|LIMIT|OFFSET|ASC|DESC|COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT|AS|ASK|CONSTRUCT|DESCRIBE|INSERT|DELETE|DATA|PREFIX|BASE|lang|langMatches|datatype|str|bound|isBlank|isLiteral|isIRI|contains|strstarts|regex|a|true|false|separator|rdf:type)$/i;
const TOKEN = /(#[^\n]*)|("(?:[^"\\\n]|\\.)*"(?:@[a-zA-Z-]+|\^\^[\w:]+)?)|(<[^<>\s"]*>)|([?$][A-Za-z_]\w*)|(@prefix|@base)|([A-Za-z_][\w-]*:[\w\-.%À-ɏ]*|:[\w\-.%À-ɏ]+)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g;
const VOCABS = new Set(['rdf', 'rdfs', 'xsd', 'owl', 'skos', 'rml', 'bv', 'kat', 'iucn', 'optyp']);
const e = x => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// tooltip naming the vocabulary a prefixed name comes from
function vocab(token) {
  const p = token.split(':')[0];
  if (p === '') return t('vocab_empty');
  return VOCABS.has(p) ? t('vocab_' + p) : null;
}

export function highlight(src) {
  let out = '', last = 0, m;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(src))) {
    out += e(src.slice(last, m.index));
    last = TOKEN.lastIndex;
    const tok = m[0];
    let c = null;
    if (m[1]) c = 'c'; else if (m[2]) c = 's'; else if (m[3]) c = 'i'; else if (m[4]) c = 'v';
    else if (m[5]) c = 'k'; else if (m[6]) c = 'p'; else if (m[7]) c = 'n'; else if (m[8]) c = KW.test(tok) ? 'k' : null;
    const title = c === 'p' ? vocab(tok) : null;
    out += c ? `<span class="tk-${c}"${title ? ` title="${esc(title)}"` : ''}>${e(tok)}</span>` : e(tok);
  }
  return out + e(src.slice(last));
}

// re-highlight every code sample inside a container (theory, hints, …)
export function highlightBlocks(root) {
  root.querySelectorAll('.card pre, .hint pre').forEach(p => { p.innerHTML = highlight(p.textContent) });
}
