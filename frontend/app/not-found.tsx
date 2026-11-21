'use client';

import Link from 'next/link';
import { Home, Search, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 px-4">
      <div className="w-full max-w-md text-center">
        <div className="mb-8">
          <span className="text-9xl font-bold text-primary-100">404</span>
        </div>
        <h1 className="text-3xl font-bold text-secondary-900 mb-4">Página não encontrada</h1>
        <p className="text-secondary-600 mb-8 max-w-md mx-auto">
          A página que você procura não existe ou foi movida. Verifique o endereço ou use a navegação abaixo.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/"
            className="flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Home className="h-5 w-5" />
            Voltar ao Início
          </Link>
          <button
            onClick={() => window.history.back()}
            className="flex items-center justify-center gap-2 px-6 py-3 border border-secondary-300 text-secondary-700 rounded-lg hover:bg-secondary-50 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
            Voltar
          </button>
        </div>
        <div className="mt-12 text-center">
          <p className="text-secondary-500 text-sm mb-4">Ou explore nossas seções principais:</p>
          <div className="flex flex-wrap justify-center gap-2">
            <Link href="/contracts" className="px-4 py-2 bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 transition-colors">
              Contratos
            </Link>
            <Link href="/analysis" className="px-4 py-2 bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 transition-colors">
              Análises
            </Link>
            <Link href="/reports" className="px-4 py-2 bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 transition-colors">
              Relatórios
            </Link>
            <Link href="/settings" className="px-4 py-2 bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 transition-colors">
              Configurações
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}