'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  Plus, Search, Filter, ChevronDown, Upload, Eye, Edit, Trash2, HardDrive,
  FileText, Clock, AlertCircle, CheckCircle, XCircle,
  Download, MoreVertical, Shield, AlertTriangle,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ContractUploadModal } from './ContractUploadModal';
import { ContractDetailModal } from './ContractDetailModal';

export function ContractsView() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedContract, setSelectedContract] = useState<any>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['contracts', page, statusFilter],
    queryFn: () => api.getContracts({ page, page_size: 20, status: statusFilter }),
  });

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => api.uploadContract(formData.get('file') as File, {
      title: formData.get('title') as string,
      description: formData.get('description') as string,
      source: formData.get('source') as any,
      language: formData.get('language') as string,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      toast.success('Contrato enviado com sucesso');
      setShowUploadModal(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao enviar contrato');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteContract(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      toast.success('Contrato excluído');
    },
    onError: () => toast.error('Erro ao excluir contrato'),
  });

  const statusColors: Record<string, string> = {
    uploaded: 'bg-secondary-100 text-secondary-700',
    parsing: 'bg-warning-100 text-warning-700',
    parsed: 'bg-primary-100 text-primary-700',
    analyzing: 'bg-primary-100 text-primary-700',
    analyzed: 'bg-success-100 text-success-700',
    error: 'bg-danger-100 text-danger-700',
  };

  const statusLabels: Record<string, string> = {
    uploaded: 'Enviado',
    parsing: 'Processando',
    parsed: 'Processado',
    analyzing: 'Analisando',
    analyzed: 'Analisado',
    error: 'Erro',
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Contratos</h1>
          <p className="text-secondary-600 mt-1">Gerencie e analise seus contratos</p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Novo Contrato
        </button>
      </div>

      <div className="bg-white rounded-lg border border-secondary-200">
        <div className="p-4 border-b border-secondary-200 flex flex-col sm:flex-row gap-4">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">Todos os status</option>
            <option value="uploaded">Enviado</option>
            <option value="parsing">Processando</option>
            <option value="parsed">Processado</option>
            <option value="analyzing">Analisando</option>
            <option value="analyzed">Analisado</option>
            <option value="error">Erro</option>
          </select>
        </div>

        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-500 border-t-transparent mx-auto"></div>
            <p className="mt-2 text-secondary-600">Carregando contratos...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-danger-600">
            Erro ao carregar contratos: {error.message}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-secondary-50 border-b border-secondary-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Contrato</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Origem</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Páginas</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Atualizado</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-secondary-600 uppercase tracking-wider">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-100">
                  {data?.items.map((contract: any) => (
                    <tr key={contract.id} className="hover:bg-secondary-50">
                      <td className="px-4 py-4">
                        <div>
                          <p className="font-medium text-secondary-900 truncate max-w-xs">{contract.title}</p>
                          <p className="text-sm text-secondary-500 truncate max-w-xs">{contract.description || 'Sem descrição'}</p>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-secondary-100 text-secondary-700">
                          {contract.source === 'upload' ? (
                            <>
                              <FileText className="h-3 w-3" />
                              Upload
                            </>
                          ) : contract.source === 'google_drive' ? (
                            <>
                              <HardDrive className="h-3 w-3" />
                              Google Drive
                            </>
                          ) : contract.source === 'onedrive' ? (
                            <>
                              <HardDrive className="h-3 w-3" />
                              OneDrive
                            </>
                          ) : (
                            <>
                              <Search className="h-3 w-3" />
                              API
                            </>
                          )}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className={cn('inline-flex items-center px-2 py-1 rounded-full text-xs font-medium', statusColors[contract.status])}>
                          {statusLabels[contract.status]}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-secondary-600">
                        {contract.page_count || '—'}
                      </td>
                      <td className="px-4 py-4 text-secondary-600 whitespace-nowrap">
                        {new Date(contract.updated_at).toLocaleDateString('pt-BR')}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedContract(contract)}
                            className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-600 hover:text-secondary-900"
                            aria-label="Ver detalhes"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => {}}
                            className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-600 hover:text-secondary-900"
                            aria-label="Editar"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`Excluir "${contract.title}"?`)) {
                                deleteMutation.mutate(contract.id);
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
                Mostrando {data?.items.length ? ((page - 1) * 20) + 1 : 0} a {data?.items.length ? ((page - 1) * 20) + data.items.length : 0} de {data?.total || 0} contratos
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

        {showUploadModal && (
          <ContractUploadModal
            onClose={() => setShowUploadModal(false)}
            onSuccess={() => {
              setShowUploadModal(false);
              queryClient.invalidateQueries({ queryKey: ['contracts'] });
            }}
          />
        )}

        {selectedContract && (
          <ContractDetailModal
            contract={selectedContract}
            onClose={() => setSelectedContract(null)}
          />
        )}
      </div>
    </div>
  );
}