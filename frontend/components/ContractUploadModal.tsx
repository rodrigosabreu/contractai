'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'react-hot-toast';
import { X, Upload, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface ContractUploadModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function ContractUploadModal({ onClose, onSuccess }: ContractUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [source, setSource] = useState<'upload' | 'google_drive' | 'onedrive'>('upload');
  const [language, setLanguage] = useState('pt-BR');
  const [dragActive, setDragActive] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => api.uploadContract(formData.get('file') as File, {
      title: formData.get('title') as string,
      description: formData.get('description') as string,
      source: formData.get('source') as any,
      language: formData.get('language') as string,
    }),
    onSuccess: () => {
      toast.success('Contrato enviado com sucesso');
      onClose();
      onSuccess();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao enviar contrato');
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (['pdf', 'docx', 'txt'].includes(droppedFile.name.split('.').pop()?.toLowerCase() || '')) {
        setFile(droppedFile);
        if (!title) setTitle(droppedFile.name.replace(/\.[^/.]+$/, ''));
      } else {
        toast.error('Formato de arquivo não suportado. Use PDF, DOCX ou TXT.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (['pdf', 'docx', 'txt'].includes(selectedFile.name.split('.').pop()?.toLowerCase() || '')) {
        setFile(selectedFile);
        if (!title) setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''));
      } else {
        toast.error('Formato de arquivo não suportado. Use PDF, DOCX ou TXT.');
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      toast.error('Selecione um arquivo');
      return;
    }
    if (!title.trim()) {
      toast.error('Informe um título para o contrato');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('description', description);
    formData.append('source', source);
    formData.append('language', language);

    uploadMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-secondary-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-secondary-900">Enviar Novo Contrato</h2>
          <button onClick={onClose} className="p-2 hover:bg-secondary-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Arquivo do Contrato</label>
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
                dragActive ? 'border-primary-500 bg-primary-50' : 'border-secondary-300 hover:border-primary-400'
              )}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                className="hidden"
                id="contract-file"
              />
              <label htmlFor="contract-file" className="cursor-pointer">
                {file ? (
                  <div className="flex items-center justify-center gap-3 text-secondary-700">
                    <CheckCircle className="h-6 w-6 text-success-500" />
                    <span className="font-medium">{file.name}</span>
                    <span className="text-sm text-secondary-500">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-12 w-12 text-secondary-400" />
                    <p className="text-secondary-600">Clique ou arraste um arquivo aqui</p>
                    <p className="text-sm text-secondary-500">PDF, DOCX ou TXT (máx. 50MB)</p>
                  </div>
                )}
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Título do Contrato *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Contrato de Prestação de Serviços"
              className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Descrição</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descrição opcional do contrato"
              rows={3}
              className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-1">Origem</label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value as any)}
                className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="upload">Upload Direto</option>
                <option value="google_drive">Google Drive</option>
                <option value="onedrive">OneDrive</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-1">Idioma</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="pt-BR">Português (Brasil)</option>
                <option value="en">English</option>
                <option value="es">Español</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-secondary-200">
            <button
              type="button"
              onClick={onClose}
              disabled={uploadMutation.isPending}
              className="px-4 py-2 border border-secondary-300 rounded-lg hover:bg-secondary-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={uploadMutation.isPending || !file}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Enviando...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Enviar Contrato
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}