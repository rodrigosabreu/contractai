'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  Plus, HardDrive, RefreshCw, Trash2, Edit, ExternalLink,
  CheckCircle, XCircle, Loader2, Cloud, Globe, X,
} from 'lucide-react';
import { ConnectorResponse } from '@/lib/types';
import { toast } from 'react-hot-toast';

export function ConnectorsView() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingConnector, setEditingConnector] = useState<any>(null);
  const [modalType, setModalType] = useState<'create' | 'edit' | 'auth' | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['connectors'],
    queryFn: () => api.getConnectors(),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.createConnector(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] });
      toast.success('Conector criado com sucesso');
      setShowCreateModal(false);
    },
    onError: (error: any) => toast.error(error.response?.data?.message || 'Erro ao criar conector'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.updateConnector(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] });
      toast.success('Conector atualizado');
      setEditingConnector(null);
    },
    onError: (error: any) => toast.error(error.response?.data?.message || 'Erro ao atualizar conector'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteConnector(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] });
      toast.success('Conector excluído');
    },
    onError: () => toast.error('Erro ao excluir conector'),
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => api.syncConnector(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] });
      toast.success('Sincronização iniciada');
    },
    onError: () => toast.error('Erro ao sincronizar'),
  });

  const typeIcons = {
    google_drive: Cloud,
    onedrive: Globe,
  };

  const typeLabels = {
    google_drive: 'Google Drive',
    onedrive: 'OneDrive',
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Conectores de Armazenamento</h1>
          <p className="text-secondary-600 mt-1">Conecte suas fontes de documentos</p>
        </div>
        <button
          onClick={() => { setModalType('create'); setShowCreateModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Novo Conector
        </button>
      </div>

      {isLoading ? (
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-500 border-t-transparent mx-auto"></div>
          <p className="mt-2 text-secondary-600">Carregando conectores...</p>
        </div>
      ) : error ? (
        <div className="p-8 text-center text-danger-600">
          Erro ao carregar conectores: {error.message}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-secondary-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary-50 border-b border-secondary-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Conector</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Última Sincronização</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-secondary-600 uppercase tracking-wider">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-100">
                {data?.connectors?.map((connector: ConnectorResponse) => (
                  <tr key={connector.id} className="hover:bg-secondary-50">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg bg-${connector.type === 'google_drive' ? 'primary' : 'secondary'}-100`}>
                          {connector.type === 'google_drive' ? <Cloud className="h-5 w-5 text-primary-600" /> : <Globe className="h-5 w-5 text-secondary-600" />}
                        </div>
                        <div>
                          <p className="font-medium text-secondary-900">{connector.name}</p>
                          <p className="text-sm text-secondary-500 capitalize">{typeLabels[connector.type] || connector.type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className="capitalize">{typeLabels[connector.type] || connector.type}</span>
                    </td>
                    <td className="px-4 py-4">
                      <span className={cn('inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                        connector.is_active ? 'bg-success-100 text-success-700' : 'bg-secondary-100 text-secondary-700'
                      )}>
                        {connector.is_active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-secondary-600">
                      {connector.last_sync_at
                        ? new Date(connector.last_sync_at).toLocaleDateString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                        : 'Nunca'}
                    </td>
                    <td className="px-4 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => syncMutation.mutate(connector.id)}
                          disabled={syncMutation.isPending}
                          className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-600 hover:text-secondary-900 disabled:opacity-50"
                          aria-label="Sincronizar"
                        >
                          {syncMutation.isPending && syncMutation.variables === connector.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RefreshCw className="h-4 w-4" />
                          )}
                        </button>
                        <button
                          onClick={() => { setEditingConnector(connector); setModalType('edit'); }}
                          className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-600 hover:text-secondary-900"
                          aria-label="Editar"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Excluir "${connector.name}"?`)) {
                              deleteMutation.mutate(connector.id);
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
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || editingConnector) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-secondary-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-secondary-900">
                {modalType === 'create' ? 'Novo Conector' : 'Editar Conector'}
              </h2>
              <button onClick={() => { setShowCreateModal(false); setEditingConnector(null); setModalType(null); }} className="p-2 hover:bg-secondary-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form className="p-6 space-y-4" onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              const data = {
                name: formData.get('name'),
                type: formData.get('type'),
                config: {},
                credentials: {},
              };
              if (modalType === 'create') {
                createMutation.mutate(data);
              } else if (editingConnector) {
                updateMutation.mutate({ id: editingConnector.id, data });
              }
            }}>
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Nome</label>
                <input name="name" defaultValue={editingConnector?.name || ''} required className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Tipo</label>
                <select name="type" defaultValue={editingConnector?.type || 'google_drive'} disabled={!!editingConnector} className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
                  <option value="google_drive">Google Drive</option>
                  <option value="onedrive">OneDrive</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => { setShowCreateModal(false); setEditingConnector(null); setModalType(null); }} className="px-4 py-2 border border-secondary-300 rounded-lg hover:bg-secondary-50">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                  {modalType === 'create' ? 'Criar' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}