const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'web', 'taste-navigation.js'), 'utf8');

function setup(hash) {
  const nodes = {};
  for (const name of ['taste', 'match', 'connection']) {
    nodes[name + '-view'] = { hidden: true };
    nodes[name + '-frame'] = { srcdoc: '', focus() {} };
  }
  for (const name of ['taste', 'match']) nodes[name + '-page-source'] = { content: { textContent: name + ' page' } };
  for (const id of ['compare-friends', 'find-matches']) nodes[id] = { focus() {} };
  const location = { hash };
  const listeners = {};
  const window = { scrollY: 0, scrollTo() {}, addEventListener(name, callback) { listeners[name] = callback; } };
  vm.runInContext(source, vm.createContext({
    window, location,
    history: { replaceState(state, title, url) { location.hash = url; } },
    document: { getElementById: id => nodes[id] || null, body: { classList: { add() {}, remove() {} } } },
    requestAnimationFrame: callback => callback(),
  }));
  const go = next => { location.hash = next; listeners.hashchange(); };
  const visible = () => Object.keys(nodes).filter(id => id.endsWith('-view') && !nodes[id].hidden);
  return { nodes, location, go, visible, pages: window.ReceiptPages };
}

test('each match opens a freshly loaded chart and the list keeps its state', () => {
  const { nodes, location, go, visible, pages } = setup('#match');
  assert.deepEqual(visible(), ['match-view']);
  nodes['match-frame'].srcdoc = 'list with a chosen range';
  const pair = { score: 81 };
  pages.showConnection(pair);
  assert.equal(location.hash, '#connection');
  go('#connection');
  assert.deepEqual(visible(), ['connection-view']);
  assert.equal(nodes['connection-frame'].srcdoc, 'taste page');
  assert.equal(pages.connection(), pair);
  nodes['connection-frame'].srcdoc = 'chart of the previous match';
  pages.showMatches();
  go(location.hash);
  assert.deepEqual(visible(), ['match-view']);
  assert.equal(nodes['match-frame'].srcdoc, 'list with a chosen range');
  pages.showConnection({ score: 75 });
  go('#connection');
  assert.equal(nodes['connection-frame'].srcdoc, 'taste page');
});

test('a connection address without a chosen match falls back to the list', () => {
  const { location, visible } = setup('#connection');
  assert.equal(location.hash, '#match');
  assert.deepEqual(visible(), ['match-view']);
});

test('the friend comparison still opens on its own', () => {
  const { go, visible } = setup('');
  assert.deepEqual(visible(), []);
  go('#friends');
  assert.deepEqual(visible(), ['taste-view']);
});
