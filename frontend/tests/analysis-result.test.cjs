const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

// Compile the actual TSX component in memory; no browser or test dependencies required.
require.extensions['.tsx'] = (module, filename) => {
  const source = fs.readFileSync(filename, 'utf8');
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true, target: ts.ScriptTarget.ES2020 } });
  module._compile(output.outputText, filename);
};
const { AnalysisResult } = require('../components/AnalysisResult.tsx');
const render = result => renderToStaticMarkup(React.createElement(AnalysisResult, { result }));

test('renders complete result, including zero counts and attributed extra risk', () => {
  const html = render({ risk_summary: { critical_risk: 0, high_risk: 1, medium_risk: 0, low_risk: 0, overall_risk: 'high' }, clauses: [{ title: 'Multa', content: 'Trecho fictício', risk_level: 'high', risk_explanation: 'Explicação fictícia' }], entities: { partes: ['Empresa fictícia'] }, recommendations: ['Revisar multa'] });
  for (const value of ['Crítico', '>0<', 'Alto', '>1<', 'Multa', 'Trecho fictício', 'Explicação fictícia', 'Empresa fictícia', 'Revisar multa', 'overall_risk (informado no resultado)', 'não constitui aconselhamento jurídico']) assert.ok(html.includes(value), value);
});

test('empty and missing values are explicit, never invented', () => {
  assert.match(render(null), /Resultado não disponível ou vazio/);
  assert.match(render({}), /Resultado não disponível ou vazio/);
  const html = render({ clauses: [{}] });
  for (const value of ['Resumo de risco não informado', 'Título não informado', 'Não informado', 'Não informada', 'Entidades não informadas', 'Recomendações não informadas']) assert.ok(html.includes(value), value);
});

test('untrusted strings are escaped in every area', () => {
  const attack = '<img src=x onerror=alert(1)><script>alert(2)</script>';
  const html = render({ risk_summary: { high_risk: attack }, clauses: [{ title: attack, content: attack, risk_level: attack, risk_explanation: attack }], entities: { [attack]: attack }, recommendations: [attack] });
  assert.ok(!html.includes('<img'));
  assert.ok(!html.includes('<script'));
  assert.ok(html.includes('&lt;img'));
  assert.ok(html.includes('&lt;script&gt;'));
});

test('accepts aliases, unknown risk, malformed fields and other analysis types', () => {
  const html = render({ resumo_risco: { alto: 2 }, clausulas: [{ titulo: 'Prazo', trecho: 'Um ano', classificacao: 'inesperado', analise: 'Avaliar' }], entidades: ['Parte A'], recomendacoes: 'Consultar', changes: ['Alteração fictícia'] });
  for (const value of ['>2<', 'Prazo', 'Um ano', 'inesperado', 'Avaliar', 'Parte A', 'Consultar', 'Alteração fictícia']) assert.ok(html.includes(value), value);
  assert.doesNotThrow(() => render({ clauses: { unexpected: true }, risk_summary: 'texto', entities: 0, recommendations: [null, {}] }));
  assert.match(render({ clauses: [] }), /Cláusulas não informadas/);
});
