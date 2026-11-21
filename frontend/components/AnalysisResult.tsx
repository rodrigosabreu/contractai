import React from 'react';

type RecordValue = Record<string, unknown>;
const record = (value: unknown): RecordValue | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as RecordValue : null;
const present = (value: unknown): boolean => value !== null && value !== undefined && !(typeof value === 'string' && !value.trim()) && !(Array.isArray(value) && !value.length) && !(record(value) && !Object.keys(record(value)!).length);
const pick = (obj: RecordValue | null, keys: string[]): unknown => keys.map(key => obj?.[key]).find(present);
const text = (value: unknown): string | null => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : null;

// Render all model-provided content as React text nodes, never as HTML or URLs.
function Value({ value }: { value: unknown }): React.ReactNode {
  if (!present(value)) return <span>Não informado</span>;
  if (Array.isArray(value)) return <ul className="list-disc pl-5 space-y-1">{value.map((item, i) => <li key={i}><Value value={item} /></li>)}</ul>;
  const obj = record(value);
  if (obj) return <dl className="space-y-1">{Object.entries(obj).map(([key, item]) => <div key={key}><dt className="font-medium inline">{key}: </dt><dd className="inline"><Value value={item} /></dd></div>)}</dl>;
  return <span className="whitespace-pre-wrap break-words">{text(value) ?? (typeof value === 'boolean' ? String(value) : 'Não informado')}</span>;
}

const levels = [
  { label: 'Crítico', keys: ['critical_risk', 'critical', 'critico', 'crítico'] },
  { label: 'Alto', keys: ['high_risk', 'high', 'alto'] },
  { label: 'Médio', keys: ['medium_risk', 'medium', 'medio', 'médio'] },
  { label: 'Baixo', keys: ['low_risk', 'low', 'baixo'] },
];
const riskLabels: Record<string, string> = { critical: 'Crítico', critico: 'Crítico', 'crítico': 'Crítico', high: 'Alto', alto: 'Alto', medium: 'Médio', medio: 'Médio', 'médio': 'Médio', low: 'Baixo', baixo: 'Baixo' };
const clauseKeys = ['clauses', 'clausulas', 'cláusulas', 'high_risk_clauses'];
const summaryKeys = ['risk_summary', 'resumo_riscos', 'resumo_risco'];
const entityKeys = ['entities', 'entidades'];
const recommendationKeys = ['recommendations', 'recomendacoes', 'recomendações'];

export function AnalysisResult({ result }: { result: unknown }) {
  const data = record(result);
  if (!present(result) || (data && !Object.keys(data).length)) return <p className="mt-3 text-secondary-600">Resultado não disponível ou vazio.</p>;
  if (!data) return <div className="mt-3"><p>Formato de resultado não reconhecido:</p><Value value={result} /></div>;
  const summary = record(pick(data, summaryKeys));
  const clauses = pick(data, clauseKeys);
  const entities = pick(data, entityKeys);
  const recommendations = pick(data, recommendationKeys);
  const known = new Set([...summaryKeys, ...clauseKeys, ...entityKeys, ...recommendationKeys]);
  const extras = Object.fromEntries(Object.entries(data).filter(([key, value]) => !known.has(key) && present(value)));

  return <div className="mt-4 space-y-6 text-secondary-800">
    <p className="text-sm text-secondary-600">Resultado automatizado para apoio à análise; não constitui aconselhamento jurídico.</p>
    <section><h3 className="font-semibold text-lg">Resumo de risco por nível</h3>
      {summary ? <><p className="text-sm text-secondary-600">Contagens informadas no resultado da análise.</p><dl className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">{levels.map(level => <div key={level.label} className="bg-secondary-50 rounded p-3"><dt>{level.label}</dt><dd className="font-semibold"><Value value={pick(summary, level.keys)} /></dd></div>)}</dl>
        {Object.entries(summary).filter(([key, value]) => !levels.some(level => level.keys.includes(key)) && present(value)).map(([key, value]) => <div key={key} className="mt-2"><span className="font-medium">{key} (informado no resultado): </span><Value value={value} /></div>)}
      </> : present(pick(data, summaryKeys)) ? <><p>Formato de resumo não reconhecido:</p><Value value={pick(data, summaryKeys)} /></> : <p>Resumo de risco não informado.</p>}
    </section>
    <section><h3 className="font-semibold text-lg">Cláusulas</h3>
      {Array.isArray(clauses) && clauses.length ? <div className="space-y-3 mt-2">{clauses.map((clause, i) => {
        const item = record(clause);
        const risk = text(pick(item, ['risk_level', 'risk', 'classificacao', 'classificação', 'nivel_risco']));
        return <article key={i} className="border border-secondary-200 rounded-lg p-4 space-y-2"><h4 className="font-semibold"><Value value={pick(item, ['title', 'titulo', 'título', 'name']) ?? 'Título não informado'} /></h4>
          <div><span className="font-medium">Trecho: </span><Value value={item ? pick(item, ['content', 'excerpt', 'trecho', 'texto']) : clause} /></div>
          <div><span className="font-medium">Classificação: </span>{risk ? riskLabels[risk.trim().toLowerCase()] ?? risk : 'Não informada'}</div>
          <div><span className="font-medium">Explicação: </span><Value value={pick(item, ['risk_explanation', 'explanation', 'analysis', 'analise', 'análise', 'explicacao', 'explicação'])} /></div>
        </article>;
      })}</div> : present(clauses) ? <><p>Formato de cláusulas não reconhecido:</p><Value value={clauses} /></> : <p>Cláusulas não informadas.</p>}
    </section>
    <section><h3 className="font-semibold text-lg">Entidades</h3>{present(entities) ? <Value value={entities} /> : <p>Entidades não informadas.</p>}</section>
    <section><h3 className="font-semibold text-lg">Recomendações</h3>{present(recommendations) ? <Value value={recommendations} /> : <p>Recomendações não informadas.</p>}</section>
    {Object.keys(extras).length > 0 && <section><h3 className="font-semibold text-lg">Outras informações do resultado</h3><Value value={extras} /></section>}
  </div>;
}
