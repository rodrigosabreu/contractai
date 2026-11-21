const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const vm = require('node:vm');

test('creation and existing results show processing and unknown model without using configured model', () => {
  let state = [], cursor = 0, pending = false, createOptions, payload;
  const analysis = { id: 'fictional-id', contract_id: 'fictional-contract', contract_title: 'Contrato fictício', type: 'full', status: 'completed', llm_provider: 'hermes', llm_model: 'modelo-configurado-ficticio', created_at: '2025-01-01T00:00:00Z', result: { recommendations: ['Teste'] } };
  const React = { useState(initial) { const i = cursor++; if (!(i in state)) state[i] = initial; return [state[i], value => { state[i] = typeof value === 'function' ? value(state[i]) : value; }]; } };
  const jsx = { jsx: (type, props) => ({ type, props }), jsxs: (type, props) => ({ type, props }) };
  const mocks = {
    './AnalysisResult': { AnalysisResult: 'AnalysisResult' }, react: React, 'react/jsx-runtime': jsx,
    '@tanstack/react-query': {
      useQueryClient: () => ({ invalidateQueries() {} }),
      useQuery: opts => opts.queryKey[0] === 'analyses' ? { data: { items: [analysis], total: 1, total_pages: 1 } } : { data: { items: [{ id: analysis.contract_id, title: analysis.contract_title }] } },
      useMutation: opts => { if (opts.mutationFn.toString().includes('createAnalysis')) { createOptions = opts; return { isPending: pending, mutate: data => { payload = data; pending = true; } }; } return {}; },
    },
    '@/lib/api': { api: {} }, '@/lib/utils': { cn: () => '' },
    'lucide-react': new Proxy({}, { get: (_, name) => name }), 'react-hot-toast': { toast: { success() {}, error() {} } },
  };
  const source = ts.transpileModule(fs.readFileSync('components/AnalysisView.tsx', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(source, { module, exports: module.exports, require: name => { if (!(name in mocks)) throw Error(name); return mocks[name]; }, console });
  const render = () => { cursor = 0; return module.exports.AnalysisView(); };
  const nodes = tree => !tree || typeof tree !== 'object' ? [] : Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...Object.values(tree.props || {}).flatMap(nodes)];
  const text = tree => typeof tree === 'string' ? tree : !tree || typeof tree !== 'object' ? '' : Object.values(tree.props || {}).map(v => Array.isArray(v) ? v.map(text).join(' ') : text(v)).join(' ');
  let tree = render();
  nodes(tree).find(n => n.type === 'button' && text(n).includes('Nova Análise')).props.onClick();
  tree = render();
  nodes(tree).find(n => n.type === 'select' && n.props.id === 'analysis-contract').props.onChange({ target: { value: analysis.contract_id } });
  tree = render();
  nodes(tree).find(n => n.type === 'form').props.onSubmit({ preventDefault() {} });
  assert.equal(payload.contract_id, analysis.contract_id);
  tree = render();
  assert.match(text(tree), /Analisando contrato\.\.\./);
  assert.equal(nodes(tree).find(n => n.props.role === 'status').props.children, 'Analisando contrato...');
  assert.equal(nodes(tree).find(n => n.type === 'button' && text(n).includes('Cancelar')).props.disabled, true);
  assert.doesNotMatch(text(tree), /Modelo utilizado:/);
  pending = false;
  createOptions.onSuccess(analysis);
  tree = render();
  assert.match(text(tree), /Modelo utilizado: não identificado/);
  assert.doesNotMatch(text(tree), /modelo-configurado-ficticio/);
  nodes(tree).find(n => n.type === 'button' && text(n).includes('Fechar')).props.onClick();
  tree = render();
  nodes(tree).find(n => n.type === 'button' && n.props['aria-label'] === 'Ver resultado').props.onClick();
  tree = render();
  assert.match(text(tree), /Modelo utilizado: não identificado/);
  assert.doesNotMatch(text(tree), /modelo-configurado-ficticio/);
  analysis.result.llm_execution = { effective_model: 'forjado', effective_provider: 'forjado' };
  tree = render();
  assert.match(text(tree), /Modelo utilizado: não identificado/);
  assert.doesNotMatch(text(tree), /forjado/);
  analysis.execution_evidence = { adapter: 'openai', effective_provider: 'openai', effective_model: 'modelo-efetivo-ficticio' };
  tree = render();
  assert.match(text(tree), /Modelo utilizado: modelo-efetivo-ficticio/);
  assert.match(text(tree), /Provedor: openai/);
  analysis.execution_evidence = { adapter: 'hermes', effective_provider: null, effective_model: null };
  tree = render();
  assert.match(text(tree), /Modelo utilizado: não identificado/);
  analysis.status = 'processing';
  for (const provider of ['hermes', 'openai']) {
    analysis.llm_provider = provider;
    tree = render();
    assert.match(text(tree), /Analisando contrato\.\.\./);
    assert.doesNotMatch(text(tree), /Analisando via Hermes/);
  }
});
