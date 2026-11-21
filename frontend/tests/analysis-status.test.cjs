const assert = require('assert');
const fs = require('fs');
const ts = require('typescript');
const vm = require('vm');
let calls = [], state = [], cursor = 0;
const React = { useState(initial) { const i = cursor++; if (!(i in state)) state[i] = initial; return [state[i], value => { state[i] = typeof value === 'function' ? value(state[i]) : value; }]; } };
const jsx = { jsx: (type, props) => ({type, props}), jsxs: (type, props) => ({type, props}) };
const api = { getAnalyses: params => { calls.push(params); return {items: [], total: 40, total_pages: 2}; } };
const mocks = {'./AnalysisResult': {AnalysisResult: () => null}, 'react': React, 'react/jsx-runtime': jsx, '@tanstack/react-query': {useQueryClient: () => ({}), useQuery: opts => opts.queryKey[0] === 'analyses' ? {data: opts.queryFn()} : {}, useMutation: () => ({})}, '@/lib/api': {api}, '@/lib/utils': {cn: () => ''}, 'lucide-react': new Proxy({}, {get: (_, name) => name}), 'react-hot-toast': {toast: {}}};
function load(path, mocks) { const source = ts.transpileModule(fs.readFileSync(path,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText; const module = {exports:{}}; vm.runInNewContext(source, {exports:module.exports,module,require:n => {if (!(n in mocks)) throw Error(n); return mocks[n]}, process, console}); return module.exports; }
const {AnalysisView} = load('components/AnalysisView.tsx', mocks);
function render() {cursor=0; return AnalysisView();}
function nodes(tree) { if (!tree || typeof tree !== 'object') return []; return [tree, ...Object.values(tree.props || {}).flatMap(v => Array.isArray(v) ? v.flatMap(nodes) : nodes(v))]; }
let tree = render(); assert.equal(calls.at(-1).status_filter, undefined); assert.equal(calls.at(-1).page, 1);
assert.equal(nodes(tree).filter(n => n.type === 'input' && n.props.placeholder === 'Buscar análises...').length, 0);
let buttons = nodes(tree).filter(n => n.type === 'button' && n.props.onClick && n.props.disabled === false); buttons.at(-1).props.onClick(); tree=render(); assert.equal(calls.at(-1).page, 2);
let select = nodes(tree).find(n => n.type === 'select'); select.props.onChange({target:{value:'completed'}}); tree=render(); assert.equal(calls.at(-1).page, 1); assert.equal(calls.at(-1).status_filter, 'completed');
for (const status of ['pending','processing','failed','']) { nodes(tree).find(n=>n.type==='select').props.onChange({target:{value:status}}); tree=render(); assert.equal(calls.at(-1).status_filter,status || undefined); }
let received; const client={interceptors:{request:{use(){}},response:{use(){}}},get:async (url,config)=>{received={url,config}; return {data:{analyses:[],total:0}}}};
const axios = {create:()=>client}; const apiModule=load('lib/api.ts',{'axios':{default:axios},'cookies-next':{getCookie(){},setCookie(){},deleteCookie(){}}});
(async()=>{await apiModule.api.getAnalyses({page:1,page_size:20,status_filter:'completed'}); assert.equal(received.url,'/analysis'); assert.equal(received.config.params.status_filter,'completed'); console.log('PASS: status options, clear, pagination reset and API parameter');})().catch(e=>{console.error(e);process.exit(1)});
