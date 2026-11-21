// Render the component with deterministic hook/API doubles; no network or real data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const state = [];
let cursor = 0;
const requests = [];
const keys = [];
const react = {
  useState(initial) {
    const index = cursor++;
    if (!(index in state)) state[index] = initial;
    return [state[index], value => { state[index] = typeof value === 'function' ? value(state[index]) : value; }];
  },
};
const jsx = { jsx: (type, props) => ({ type, props }), jsxs: (type, props) => ({ type, props }) };
const mocks = {
  react,
  'react/jsx-runtime': jsx,
  '@tanstack/react-query': {
    useQueryClient: () => ({}),
    useQuery: opts => { keys.push(opts.queryKey); return { data: opts.queryFn() }; },
    useMutation: () => ({}),
  },
  '@/lib/api': { api: { getContracts: params => {
    requests.push(params);
    if (params.status === 'uploaded') return { items: params.page === 1 ? [{ id: 'fictional', title: 'Contrato fictício', status: 'uploaded', source: 'upload', updated_at: '2026-01-01' }] : [], total: 1, total_pages: 1 };
    if (params.status === 'error') return { items: [], total: 0, total_pages: 0 };
    return { items: [], total: 40, total_pages: 2 };
  } } },
  '@/lib/utils': { cn: () => '' },
  'lucide-react': new Proxy({}, { get: (_, name) => name }),
  'react-hot-toast': { toast: {} },
  './ContractUploadModal': { ContractUploadModal: () => null },
  './ContractDetailModal': { ContractDetailModal: () => null },
};
const source = ts.transpileModule(fs.readFileSync('components/ContractsView.tsx', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;
const moduleObject = { exports: {} };
vm.runInNewContext(source, {
  module: moduleObject, exports: moduleObject.exports,
  require: name => { if (!(name in mocks)) throw Error(`Unexpected import: ${name}`); return mocks[name]; },
});
const { ContractsView } = moduleObject.exports;
function render() { cursor = 0; return ContractsView(); }
function nodes(tree) {
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...Object.values(tree.props || {}).flatMap(v => Array.isArray(v) ? v.flatMap(nodes) : nodes(v))];
}
let tree = render();
assert.equal(nodes(tree).filter(n => n.type === 'input' && (n.props.type === 'search' || /buscar|pesquisar|search/i.test(n.props.placeholder || ''))).length, 0);
assert.equal(requests.at(-1).page, 1);
assert.equal(requests.at(-1).status, '');
assert.equal('search' in requests.at(-1), false);
assert.equal(keys.at(-1).length, 3);
const select = nodes(tree).find(n => n.type === 'select');
assert.ok(select, 'status filter remains available');
select.props.onChange({ target: { value: 'parsed' } });
tree = render();
assert.equal(requests.at(-1).status, 'parsed');
const next = nodes(tree).filter(n => n.type === 'button' && n.props.onClick && n.props.disabled === false).at(-1);
next.props.onClick();
tree = render();
assert.equal(requests.at(-1).page, 2);
assert.equal(requests.at(-1).status, 'parsed');
// Changing from page 2 to a filter with just one result must request page 1.
nodes(tree).find(n => n.type === 'select').props.onChange({ target: { value: 'uploaded' } });
tree = render();
assert.equal(requests.at(-1).page, 1);
assert.equal(requests.at(-1).status, 'uploaded');
function text(value) {
  if (value == null || typeof value === 'boolean') return '';
  if (typeof value !== 'object') return String(value);
  if (Array.isArray(value)) return value.map(text).join('');
  return text(value.props?.children);
}
let rendered = text(tree);
assert.match(rendered, /Contrato fictício/);
assert.match(rendered, /Mostrando 1 a 1 de 1 contratos/);
nodes(tree).find(n => n.type === 'select').props.onChange({ target: { value: 'error' } });
tree = render();
assert.equal(requests.at(-1).page, 1);
assert.match(text(tree), /Mostrando 0 a 0 de 0 contratos/);
console.log('PASS: no search; filter resets pagination; empty range is correct');
