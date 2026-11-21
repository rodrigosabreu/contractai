'use client';

import { cn } from '@/lib/utils';
import { Bell, Moon, Sun, LogOut, User, Menu, ChevronDown, Shield } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { useState } from 'react';
import Link from 'next/link';

interface HeaderProps {
  user: any;
  onMenuClick: () => void;
}

export function Header({ user, onMenuClick }: HeaderProps) {
  const { logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  return (
    <header className="sticky top-0 z-30 w-full bg-white border-b border-secondary-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={onMenuClick}
              className="lg:hidden p-2 rounded-lg text-secondary-600 hover:bg-secondary-100"
              aria-label="Abrir menu"
            >
              <Menu className="h-6 w-6" />
            </button>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-4">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-lg text-secondary-600 hover:bg-secondary-100"
              aria-label={darkMode ? 'Modo claro' : 'Modo escuro'}
            >
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>

            <button className="relative p-2 rounded-lg text-secondary-600 hover:bg-secondary-100">
              <Bell className="h-5 w-5" />
              <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-danger-500 text-[10px] font-medium text-white flex items-center justify-center">
                3
              </span>
            </button>

            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 p-2 rounded-lg hover:bg-secondary-100"
                aria-expanded={dropdownOpen}
                aria-haspopup="true"
              >
                <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-700">
                    {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                  </span>
                </div>
                <ChevronDown className="h-4 w-4 text-secondary-500" />
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-secondary-200 py-1 z-50">
                  <div className="px-4 py-2 border-b border-secondary-100">
                    <p className="text-sm font-medium text-secondary-900">{user?.full_name}</p>
                    <p className="text-xs text-secondary-500">{user?.email}</p>
                  </div>
                  <Link
                    href="/settings/profile"
                    className="flex items-center gap-2 px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-50"
                  >
                    <User className="h-4 w-4" />
                    Perfil
                  </Link>
                  <Link
                    href="/settings/security"
                    className="flex items-center gap-2 px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-50"
                  >
                    <Shield className="h-4 w-4" />
                    Segurança
                  </Link>
                  <hr className="my-1 border-secondary-100" />
                  <button
                    onClick={logout}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-danger-600 hover:bg-danger-50"
                  >
                    <LogOut className="h-4 w-4" />
                    Sair
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}