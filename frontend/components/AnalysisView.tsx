'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  Plus, Filter, ChevronDown, Eye, Trash2,
  FileText, AlertCircle, CheckCircle, XCircle,
  Download, MoreVertical, Shield, AlertTriangle,
  BarChart3, Zap,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { AnalysisResult } from './AnalysisResult';

export function AnalysisView() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedAnalysis, setSelectedAnalysis] = useState<any>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [contractId, setContractId] = useState('');
  const { data: contracts } = useQuery({ queryKey: ['contracts', 'analysis-options'], queryFn: () => api.getContracts({ page_size: 100 }), enabled: showCreate });

  const { data, isLoading, error } = useQuery({
    queryKey: ['analyses', page, statusFilter],
    queryFn: () => api.getAnalyses({ page, page_size: 20, status_filter: statusFilter || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.createAnalysis(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] });
      setShowCreate(false);
      setSelectedAnalysis(result);
      toast.success('Análise concluída');
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao criar análise'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteAnalysis(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] });
      toast.success('Análise excluída');
    },
    onError: () => toast.error('Erro ao excluir análise'),
  });

  const statusColors: Record<string, string> = {
    pending: 'bg-secondary-100 text-secondary-700',
    processing: 'bg-warning-100 text-warning-700',
    completed: 'bg-success-100 text-success-700',
    failed: 'bg-danger-100 text-danger-700',
  };

  const statusLabels: Record<string, string> = {
    pending: 'Pendente',
    processing: 'Analisando contrato...',
    completed: 'Concluída',
    failed: 'Falhou',
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Análises de Contratos</h1>
          <p className="text-secondary-600 mt-1">Gerencie e visualize análises de risco</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Zap className="h-4 w-4" />
            Nova Análise
          </button>
        </div>
      </div>

      {showCreate && <form onSubmit={(e) => { e.preventDefault(); if (contractId && !createMutation.isPending) { setSelectedAnalysis(null); createMutation.mutate({ contract_id: contractId }); } }} className="bg-white p-4 rounded-lg border space-y-3">
        <label htmlFor="analysis-contract" className="block">Selecione o contrato</label>
        <select id="analysis-contract" value={contractId} onChange={e => setContractId(e.target.value)} required className="border p-2 rounded w-full">
          <option value="">Selecione...</option>
          {contracts?.items?.map((contract: any) => <option key={contract.id} value={contract.id}>{contract.title}</option>)}
        </select>
        <button disabled={!contractId || createMutation.isPending} className="px-4 py-2 bg-primary-600 text-white rounded disabled:opacity-50">{createMutation.isPending ? 'Analisando contrato...' : 'Iniciar análise'}</button>{' '}
        {createMutation.isPending && <span role="status" className="sr-only">Analisando contrato...</span>}
        <button type="button" disabled={createMutation.isPending} onClick={() => setShowCreate(false)}>Cancelar</button>
      </form>}
      {selectedAnalysis && (
      <section className="bg-white p-4 rounded-lg border">
        <div className="flex justify-between">
          <h2 className="font-semibold">Resultado da análise</h2>
          <button onClick={() => setSelectedAnalysis(null)}>Fechar</button>
        </div>
        <p className="mt-3 text-sm text-secondary-600">
          {(() => {
            const exec = selectedAnalysis.execution_evidence;
            const model = typeof exec?.effective_model === 'string' && exec.effective_model.trim() ? exec.effective_model : null;
            const provider = typeof exec?.effective_provider === 'string' && exec.effective_provider.trim() ? exec.effective_provider : null;
            return `Modelo utilizado: ${model || 'não identificado'}${provider ? ` · Provedor: ${provider}` : ''}`;
          })()}
        </p>
        <AnalysisResult result={selectedAnalysis.result} />
      </section>
    )}
      <div className="bg-white rounded-lg border border-secondary-200">
        <div className="p-4 border-b border-secondary-200 flex flex-col sm:flex-row gap-4">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">Todos os status</option>
            <option value="pending">Pendente</option>
            <option value="processing">Processando</option>
            <option value="completed">Concluída</option>
            <option value="failed">Falhou</option>
          </select>
        </div>

        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-500 border-t-transparent mx-auto"></div>
            <p className="mt-2 text-secondary-600">Carregando análises...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-danger-600">
            Erro ao carregar análises: {error.message}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-secondary-50 border-b border-secondary-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Contrato</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Tipo</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Provedor solicitado</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Custo (USD)</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Tempo</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Iniciado</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-secondary-600 uppercase tracking-wider">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-100">
                  {data?.items.map((analysis: any) => (
                    <tr key={analysis.id} className="hover:bg-secondary-50">
                      <td className="px-4 py-4">
                        <p className="font-medium text-secondary-900 truncate max-w-xs">{analysis.contract_title || 'Contrato #' + analysis.contract_id.slice(0, 8)}</p>
                      </td>
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-secondary-100 text-secondary-700 capitalize">
                          {analysis.type}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className={cn('inline-flex items-center px-2 py-1 rounded-full text-xs font-medium', statusColors[analysis.status])}>
                          {statusLabels[analysis.status]}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-secondary-600 capitalize">{analysis.llm_provider}</td>
                      <td className="px-4 py-4 text-secondary-600">
                        {analysis.total_cost_usd ? `$${analysis.total_cost_usd.toFixed(4)}` : '—'}
                      </td>
                      <td className="px-4 py-4 text-secondary-600">
                        {analysis.processing_time_ms ? `${(analysis.processing_time_ms / 1000).toFixed(1)}s` : '—'}
                      </td>
                      <td className="px-4 py-4 text-secondary-600 whitespace-nowrap">
                        {new Date(analysis.created_at).toLocaleDateString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {analysis.status === 'completed' && (
                            <button
                              onClick={() => setSelectedAnalysis(analysis)}
                              className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-600 hover:text-secondary-900"
                              aria-label="Ver resultado"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => {
                              if (confirm('Excluir esta análise?')) {
                                deleteMutation.mutate(analysis.id);
                              }
                            }}
                            className="p-2 rounded-lg hover:bg-danger-100 text-danger-600 hover:text-danger-900"
                            aria-label="Excluir"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="px-4 py-3 border-t border-secondary-200 flex items-center justify-between">
              <p className="text-sm text-secondary-600">
                Mostrando {((page - 1) * 20) + 1} a {Math.min(page * 20, data?.total || 0)} de {data?.total || 0} análises
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-secondary-300 hover:bg-secondary-50 disabled:opacity-50"
                >
                  <ChevronDown className="h-4 w-4 rotate-180" />
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= (data?.total_pages || 1)}
                  className="p-2 rounded-lg border border-secondary-300 hover:bg-secondary-50 disabled:opacity-50"
                >
                  <ChevronDown className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}