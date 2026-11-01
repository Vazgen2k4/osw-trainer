// Delegated click handling: <button data-action="name" data-arg="…"> calls the handler registered as "name".
const handlers = {};

export function onAction(name, fn) { handlers[name] = fn }

export function listen(root = document) {
  root.addEventListener('click', e => {
    const el = e.target.closest('[data-action]');
    if (el && handlers[el.dataset.action]) handlers[el.dataset.action](el, e);
  });
}
