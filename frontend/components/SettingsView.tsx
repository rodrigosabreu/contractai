'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  User, Shield, Bell, Key, Globe, CreditCard, FolderOpen,
  UserPlus, Mail, Lock, Users, Settings as SettingsIcon,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useAuth } from '@/lib/auth';

export function SettingsView() {
  const { user, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'notifications' | 'organization' | 'billing' | 'users'>('profile');
  const [loading, setLoading] = useState(false);

  const tabs = [
    { id: 'profile', label: 'Perfil', icon: User },
    { id: 'security', label: 'Segurança', icon: Shield },
    { id: 'notifications', label: 'Notificações', icon: Bell },
    { id: 'organization', label: 'Organização', icon: Globe },
    { id: 'billing', label: 'Faturamento', icon: CreditCard },
    { id: 'users', label: 'Usuários', icon: Users },
  ];

  const updateProfileMutation = useMutation({
    mutationFn: (data: { full_name?: string }) => api.updateProfile(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      toast.success('Perfil atualizado');
    },
    onError: () => toast.error('Erro ao atualizar perfil'),
  });

  const changePasswordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) => api.changePassword(data),
    onSuccess: () => toast.success('Senha alterada com sucesso'),
    onError: (error: any) => toast.error(error.response?.data?.message || 'Erro ao alterar senha'),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Configurações</h1>
        <p className="text-secondary-600 mt-1">Gerencie sua conta e preferências</p>
      </div>

      <div className="bg-white rounded-lg border border-secondary-200">
        <div className="border-b border-secondary-200">
          <nav className="flex overflow-x-auto px-4 -mb-px" aria-label="Configurações">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={cn(
                  'flex items-center gap-2 px-4 py-4 text-sm font-medium border-b-2 transition-colors',
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

        <div className="p-6">
          {activeTab === 'profile' && (
            <div className="max-w-2xl space-y-6">
              <h2 className="text-lg font-semibold text-secondary-900">Informações do Perfil</h2>
              <form className="space-y-4" onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                updateProfileMutation.mutate({ full_name: String(formData.get('full_name') || '') });
              }}>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">Nome Completo</label>
                  <input
                    defaultValue={user?.full_name}
                    name="full_name"
                    className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">E-mail</label>
                  <input
                    defaultValue={user?.email}
                    disabled
                    className="w-full px-4 py-2 border border-secondary-300 rounded-lg bg-secondary-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">Função</label>
                  <input
                    defaultValue={user?.role}
                    disabled
                    className="w-full px-4 py-2 border border-secondary-300 rounded-lg bg-secondary-50"
                  />
                </div>
                <button type="submit" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                  Salvar Alterações
                </button>
              </form>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="max-w-2xl space-y-6">
              <h2 className="text-lg font-semibold text-secondary-900">Segurança da Conta</h2>
              <div className="bg-white rounded-lg border border-secondary-200 p-6 space-y-4">
                <h3 className="font-medium text-secondary-900">Alterar Senha</h3>
                <form className="space-y-4 mt-4" onSubmit={(e) => {
                  e.preventDefault();
                  const formData = new FormData(e.currentTarget);
                  changePasswordMutation.mutate({
                    current_password: String(formData.get('current_password') || ''),
                    new_password: String(formData.get('new_password') || ''),
                  });
                }}>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-1">Senha Atual</label>
                    <input name="current_password" type="password" required className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-1">Nova Senha</label>
                    <input name="new_password" type="password" required minLength={8} className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-1">Confirmar Nova Senha</label>
                    <input type="password" required minLength={8} className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                  </div>
                  <button type="submit" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                    Alterar Senha
                  </button>
                </form>
              </div>

              <div className="bg-white rounded-lg border border-secondary-200 p-6 space-y-4">
                <h3 className="font-medium text-secondary-900">Autenticação de Dois Fatores (MFA)</h3>
                <p className="text-sm text-secondary-600">Adicione uma camada extra de segurança à sua conta.</p>
                <button className="px-4 py-2 border border-secondary-300 rounded-lg hover:bg-secondary-50">
                  Configurar MFA
                </button>
              </div>
            </div>
          )}

          {activeTab === 'organization' && (
            <div className="max-w-2xl space-y-6">
              <h2 className="text-lg font-semibold text-secondary-900">Configurações da Organização</h2>
              <div className="bg-white rounded-lg border border-secondary-200 p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">Nome da Organização</label>
                  <input defaultValue="Minha Organização" className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">Slug</label>
                  <input defaultValue="minha-org" disabled className="w-full px-4 py-2 border border-secondary-300 rounded-lg bg-secondary-50" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">Plano Atual</label>
                  <select className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
                    <option>Free</option>
                    <option selected>Pro</option>
                    <option>Enterprise</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'billing' && (
            <div className="max-w-2xl space-y-6">
              <h2 className="text-lg font-semibold text-secondary-900">Faturamento</h2>
              <div className="bg-white rounded-lg border border-secondary-200 p-6">
                <h3 className="font-medium text-secondary-900 mb-4">Plano Atual: Pro</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="p-4 bg-secondary-50 rounded-lg">
                    <p className="text-sm text-secondary-600">Usuários</p>
                    <p className="text-2xl font-bold text-secondary-900">5/10</p>
                  </div>
                  <div className="p-4 bg-secondary-50 rounded-lg">
                    <p className="text-sm text-secondary-600">Contratos/Mês</p>
                    <p className="text-2xl font-bold text-secondary-900">45/100</p>
                  </div>
                  <div className="p-4 bg-secondary-50 rounded-lg">
                    <p className="text-sm text-secondary-600">Armazenamento</p>
                    <p className="text-2xl font-bold text-secondary-900">2.3/10 GB</p>
                  </div>
                </div>
                <button className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                  Gerenciar Assinatura
                </button>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="max-w-4xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-secondary-900">Gerenciar Usuários</h2>
                <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  Convidar Usuário
                </button>
              </div>
              <div className="bg-white rounded-lg border border-secondary-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-secondary-50 border-b border-secondary-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Usuário</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Função</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-secondary-600 uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-secondary-600 uppercase tracking-wider">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-secondary-100">
                    <tr className="hover:bg-secondary-50">
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-primary-700">J</span>
                          </div>
                          <div>
                            <p className="font-medium text-secondary-900">João Silva</p>
                            <p className="text-sm text-secondary-500">joao@empresa.com</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-700">Admin</span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-success-100 text-success-700">Ativo</span>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <button className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-600">Editar</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}