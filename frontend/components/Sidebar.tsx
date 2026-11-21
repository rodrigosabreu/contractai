'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FileText,
  Search,
  BarChart3,
  HardDrive,
  Settings,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  Shield,
  Users,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';

interface SidebarProps {
  currentView: 'contracts' | 'analysis' | 'reports' | 'connectors' | 'settings';
  onViewChange: (view: 'contracts' | 'analysis' | 'reports' | 'connectors' | 'settings') => void;
  open: boolean;
  onClose: () => void;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, view: 'contracts' as const },
  { name: 'Contratos', href: '/contracts', icon: FileText, view: 'contracts' as const },
  { name: 'Análises', href: '/analysis', icon: Search, view: 'analysis' as const },
  { name: 'Relatórios', href: '/reports', icon: BarChart3, view: 'reports' as const },
  { name: 'Conectores', href: '/connectors', icon: HardDrive, view: 'connectors' as const },
  { name: 'Configurações', href: '/settings', icon: Settings, view: 'settings' as const },
];

export function Sidebar({ currentView, onViewChange, open, onClose }: SidebarProps) {
  const { user } = useAuth();

  if (!open) {
    return (
      <button
        onClick={onClose}
        className="fixed top-4 left-4 z-50 lg:hidden p-2 rounded-lg bg-white shadow-lg hover:bg-secondary-100"
        aria-label="Abrir menu"
      >
        <ChevronRight className="h-6 w-6" />
      </button>
    );
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-40 w-64 lg:w-64 bg-white border-r border-secondary-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0">
      <div className="flex h-16 items-center justify-between px-4 border-b border-secondary-200">
        <Link href="/" className="flex items-center gap-2 font-semibold text-xl text-primary-600">
          <Shield className="h-8 w-8" />
          <span>ContractAI</span>
        </Link>
        <button
          onClick={onClose}
          className="lg:hidden p-2 rounded-lg hover:bg-secondary-100"
          aria-label="Fechar menu"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-4 space-y-1" aria-label="Navegação principal">
        {navigation.map((item) => {
          const isActive = currentView === item.view;
          return (
            <button
              key={item.name}
              onClick={() => onViewChange(item.view)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
              <span className="truncate">{item.name}</span>
            </button>
          );
        })}

        <div className="pt-4 border-t border-secondary-200">
          <p className="px-3 text-xs font-semibold text-secondary-500 uppercase tracking-wider">
            Organização
          </p>
          <Link
            href="/settings"
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
            )}
          >
            <Users className="h-5 w-5 flex-shrink-0" />
            <span>Usuários</span>
          </Link>
          <Link
            href="/settings/billing"
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
            )}
          >
            <Shield className="h-5 w-5 flex-shrink-0" />
            <span>Plano e Faturamento</span>
          </Link>
        </div>
      </nav>

      <div className="p-4 border-t border-secondary-200">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-secondary-900 truncate">
              {user?.full_name || 'Usuário'}
            </p>
            <p className="text-xs text-secondary-500 truncate">
              {user?.email || 'email@exemplo.com'}
            </p>
          </div>
        </div>
      </div>
  </aside>
);
}