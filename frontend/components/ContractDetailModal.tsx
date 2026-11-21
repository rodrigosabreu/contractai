'use client';

import { useState } from 'react';
import { X, Eye, Download, FileText, Shield, AlertTriangle, CheckCircle, MoreVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ContractDetailModalProps {
  contract: any;
  onClose: () => void;
}

export function ContractDetailModal({ contract, onClose }: ContractDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'analysis' | 'versions'>('details');

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

  const sourceLabels: Record<string, string> = {
    upload: 'Upload Direto',
    google_drive: 'Google Drive',
    onedrive: 'OneDrive',
    api: 'API',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-secondary-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-secondary-900 truncate max-w-md">{contract.title}</h2>
            <p className="text-sm text-secondary-500">ID: {contract.id}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-secondary-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          <div className="flex gap-4 mb-6 border-b border-secondary-200 pb-4">
            <div className="flex-1">
              <p className="text-sm text-secondary-500">Status</p>
              <span className={cn('inline-flex items-center px-2 py-1 rounded-full text-xs font-medium', statusColors[contract.status])}>
                {statusLabels[contract.status]}
              </span>
            </div>
            <div className="flex-1">
              <p className="text-sm text-secondary-500">Origem</p>
              <p className="font-medium text-secondary-900">{sourceLabels[contract.source] || contract.source}</p>
            </div>
            <div className="flex-1">
              <p className="text-sm text-secondary-500">Páginas</p>
              <p className="font-medium text-secondary-900">{contract.page_count || '—'}</p>
            </div>
            <div className="flex-1">
              <p className="text-sm text-secondary-500">Idioma</p>
              <p className="font-medium text-secondary-900">{contract.language || 'pt-BR'}</p>
            </div>
          </div>

          <div className="border-b border-secondary-200 mb-6">
            <nav className="flex gap-4" aria-label="Abas do contrato">
              {[
                { id: 'details', label: 'Detalhes', icon: FileText },
                { id: 'analysis', label: 'Análise', icon: Shield },
                { id: 'versions', label: 'Versões', icon: FileText },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === tab.id
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:bg-secondary-50'
                  )}
                >
                  <tab.icon className="h-5 w-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {activeTab === 'details' && (
            <div className="space-y-6 mt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-medium text-secondary-500 mb-2">Descrição</h3>
                  <p className="text-secondary-900 whitespace-pre-wrap">{contract.description || 'Sem descrição'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-secondary-500 mb-2">Metadados</h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-secondary-500">Tamanho do Arquivo</dt>
                      <dd className="font-medium text-secondary-900">{contract.file_size ? `${(contract.file_size / 1024 / 1024).toFixed(2)} MB` : '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-secondary-500">Tipo MIME</dt>
                      <dd className="font-medium text-secondary-900">{contract.mime_type || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-secondary-500">Hash do Conteúdo</dt>
                      <dd className="font-medium text-secondary-900 font-mono text-xs">{contract.content_hash || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-secondary-500">Criado em</dt>
                      <dd className="font-medium text-secondary-900">{new Date(contract.created_at).toLocaleString('pt-BR')}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-secondary-500">Atualizado em</dt>
                      <dd className="font-medium text-secondary-900">{new Date(contract.updated_at).toLocaleString('pt-BR')}</dd>
                    </div>
                  </dl>
                </div>
              </div>

              {contract.error_message && (
                <div className="p-4 bg-danger-50 border border-danger-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-danger-600" />
                    <h4 className="font-medium text-danger-800">Erro no Processamento</h4>
                  </div>
                  <p className="text-danger-700 mt-2">{contract.error_message}</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-secondary-900 mb-4">Análises Realizadas</h3>
              <p className="text-secondary-600">Nenhuma análise realizada para este contrato ainda.</p>
              <button className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                Iniciar Nova Análise
              </button>
            </div>
          )}

          {activeTab === 'versions' && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-secondary-900 mb-4">Histórico de Versões</h3>
              <p className="text-secondary-600">Nenhuma versão anterior registrada.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}