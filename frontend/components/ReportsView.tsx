'use client';

import { BarChart3, TrendingUp, Users, FileText, Shield, Clock } from 'lucide-react';

export function ReportsView() {
  const stats = [
    { name: 'Total de Contratos', value: '1.234', change: '+12%', icon: FileText, color: 'primary' },
    { name: 'Análises Realizadas', value: '567', change: '+8%', icon: BarChart3, color: 'success' },
    { name: 'Riscos Detectados', value: '89', change: '-5%', icon: Shield, color: 'danger' },
    { name: 'Tempo Economizado', value: '234h', change: '+23%', icon: Clock, color: 'warning' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Relatórios</h1>
        <p className="text-secondary-600 mt-1">Visão geral e métricas da organização</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white rounded-lg border border-secondary-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">{stat.name}</p>
                <p className="text-3xl font-bold text-secondary-900 mt-1">{stat.value}</p>
                <p className="text-sm text-success-600 mt-1">{stat.change} vs mês anterior</p>
              </div>
              <div className={`p-3 rounded-lg bg-${stat.color}-100`}>
                <stat.icon className={`h-6 w-6 text-${stat.color}-600`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-secondary-200 p-6">
        <h2 className="text-lg font-semibold text-secondary-900 mb-4">Resumo da Organização</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 bg-secondary-50 rounded-lg">
            <p className="text-sm text-secondary-600">Total de Usuários</p>
            <p className="text-2xl font-bold text-secondary-900">24</p>
          </div>
          <div className="p-4 bg-secondary-50 rounded-lg">
            <p className="text-sm text-secondary-600">Contratos Este Mês</p>
            <p className="text-2xl font-bold text-secondary-900">45</p>
          </div>
          <div className="p-4 bg-secondary-50 rounded-lg">
            <p className="text-sm text-secondary-600">Taxa de Sucesso</p>
            <p className="text-2xl font-bold text-success-600">94.2%</p>
          </div>
        </div>
      </div>
    </div>
  );
}