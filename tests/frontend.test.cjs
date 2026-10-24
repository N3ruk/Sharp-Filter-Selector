// Run the actual TSX in a small Decky/hooks harness; no Steam session needed.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const ts = require('typescript');

const source = fs.readFileSync('src/index.tsx', 'utf8');
const code = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;

function harness(initial, preferences = {}) {
  let capabilities = initial;
  let failCapabilities = false;
  const states = [];
  let index = 0;
  let effect;
  let timer;
  let cleanup;
  let intervalCleared = false;
  const exports = {};
  const jsx = (type, props) => ({ type, ...props });
  const react = {
    useState(value) {
      const slot = index++;
      if (!(slot in states)) states[slot] = typeof value === 'function' ? value() : value;
      return [states[slot], value => {
        states[slot] = typeof value === 'function' ? value(states[slot]) : value;
      }];
    },
    useEffect(fn) { effect = fn; },
  };
  const modules = {
    react,
    'react/jsx-runtime': { jsx, jsxs: jsx },
    '@decky/ui': { PanelSection: 'section', PanelSectionRow: 'row', ToggleField: 'toggle',
      SliderField: 'slider', staticClasses: {} },
    'react-icons/fa6': { FaWandMagicSparkles: 'icon' },
    '@decky/api': {
      definePlugin: fn => fn,
      callable: name => async () => {
        if (name === 'get_capabilities') {
          if (failCapabilities) throw new Error('Temporary backend failure');
          return capabilities;
        }
        return { success: false, error: 'No accessible Gamescope/Xwayland target was found' };
      },
    },
  };
  const context = { exports, require: name => {
    assert.ok(modules[name], `Unexpected import: ${name}`);
    return modules[name];
  }, localStorage: { getItem: key => preferences[key] ?? null,
    setItem: (key, value) => { preferences[key] = value; } },
  setInterval: fn => { timer = fn; return 1; },
  clearInterval: () => { intervalCleared = true; },
  setTimeout: fn => { fn(); return 1; } };
  vm.runInNewContext(code, context);
  const Component = exports.default().content.type;
  const render = () => { index = 0; return Component(); };
  const flush = () => new Promise(resolve => setImmediate(resolve));
  return {
    async mount() { render(); cleanup = effect(); await flush(); return render(); },
    async refresh(next) { capabilities = next; await timer(); await flush(); return render(); },
    async failRefresh() { failCapabilities = true; await timer(); return render(); },
    cleanup() { cleanup(); assert.ok(intervalCleared); },
    hasTimer: () => typeof timer === 'function',
  };
}

function nodes(tree) {
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...[tree.children].flat(Infinity).flatMap(nodes)];
}
const hasFsr = tree => nodes(tree).some(n => n.label === 'Use FSR');
const caps = (extra = {}) => ({ success: true, supportsSGSR: true,
  hdrInput: false, showFsrOverride: true, steamos: true, ...extra });

test('SDR and unknown feedback show both FSR and NIS', async () => {
  const h = harness(caps());
  const tree = await h.mount();
  assert.ok(hasFsr(tree));
  assert.ok(nodes(tree).some(n => n.label === 'Use NIS'));
  h.cleanup();
});

test('application HDR hides FSR, SDR/unknown immediately restores it', async () => {
  const h = harness(caps());
  await h.mount();
  assert.equal(hasFsr(await h.refresh(caps({ hdrInput: true, showFsrOverride: false }))), false);
  assert.equal(hasFsr(await h.refresh(caps({ hdrOutputEnabled: true }))), true);
  h.cleanup();
});

test('old Gamescope does not show a redundant FSR override', async () => {
  const h = harness(caps({ supportsSGSR: false, showFsrOverride: false }));
  assert.equal(hasFsr(await h.mount()), false);
  h.cleanup();
});

test('desktop does not pretend installed Gamescope is an active SGSR session', async () => {
  const h = harness(caps({ success: false, supportsSGSR: false, showFsrOverride: false }));
  const tree = await h.mount();
  assert.equal(hasFsr(tree), false);
  assert.ok(nodes(tree).some(n => n.type === 'div' && String(n.children).includes('Gaming Mode')));
  assert.ok(h.hasTimer());
  h.cleanup();
});

test('failed stored-NIS restore cannot prevent later SGSR/FSR detection', async () => {
  const h = harness(caps({ success: false, supportsSGSR: false, showFsrOverride: false }),
    { 'sharp-filter-nis-enabled': 'true' });
  assert.equal(hasFsr(await h.mount()), false);
  assert.ok(h.hasTimer());
  assert.equal(hasFsr(await h.refresh(caps())), true);
  h.cleanup();
});

test('refresh failure clears stale HDR gating but keeps verified SGSR support', async () => {
  const h = harness(caps({ hdrInput: true, showFsrOverride: false }));
  assert.equal(hasFsr(await h.mount()), false);
  assert.equal(hasFsr(await h.failRefresh()), true);
  h.cleanup();
});

test('SGSR state is visible even when FSR controls are unavailable', async () => {
  const h = harness(caps({ success: false, supportsSGSR: false, showFsrOverride: false }));
  const tree = await h.mount();
  assert.ok(nodes(tree).some(n => n.type === 'div' && n.children === 'SGSR: waiting for an active Gamescope session'));
  const ready = await h.refresh(caps());
  assert.ok(nodes(ready).some(n => n.type === 'div' && n.children === 'QAM Sharp → SGSR (both overrides off)'));
  assert.ok(hasFsr(ready));
  h.cleanup();
});
