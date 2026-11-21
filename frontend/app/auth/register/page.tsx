'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Shield, Mail, Lock, User, Building, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { toast } from 'react-hot-toast';
import { cn } from '@/lib/utils';

const registerSchema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(8, 'Senha deve ter pelo menos 8 caracteres'),
  confirmPassword: z.string(),
  fullName: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  organizationName: z.string().min(2, 'Nome da organização deve ter pelo menos 2 caracteres'),
  organizationSlug: z.string().min(3, 'Slug deve ter pelo menos 3 caracteres').regex(/^[a-z0-9-]+$/, 'Slug deve conter apenas letras minúsculas, números e hífen'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'As senhas não coincidem',
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register: authRegister } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const password = watch('password');

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    setError('');

    try {
      await authRegister(
        data.email,
        data.password,
        data.fullName,
        data.organizationName,
        data.organizationSlug,
      );
      toast.success('Organização criada com sucesso! Redirecionando...');
      router.push('/');
    } catch (error: any) {
      setError(error.response?.data?.message || 'Erro ao criar organização');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl border border-secondary-200 p-8 shadow-sm">
          <div className="text-center mb-8">
            <Link href="/" className="inline-flex items-center gap-2 font-semibold text-2xl text-primary-600 mb-6">
              <Shield className="h-10 w-10" />
              <span>ContractAI</span>
            </Link>
            <h1 className="text-2xl font-bold text-secondary-900">Criar sua organização</h1>
            <p className="text-secondary-600 mt-2">Comece a analisar contratos com IA em minutos</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-center gap-2 text-danger-700">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="fullName" className="block text-sm font-medium text-secondary-700 mb-1">
                  Nome Completo
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                  <input
                    {...register('fullName')}
                    type="text"
                    id="fullName"
                    placeholder="João Silva"
                    className={cn(
                      'w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                      errors.fullName && 'border-danger-500 focus:ring-danger-500'
                    )}
                  />
                  {errors.fullName && (
                    <p className="mt-1 text-sm text-danger-600">{errors.fullName.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-secondary-700 mb-1">
                  E-mail
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                  <input
                    {...register('email')}
                    type="email"
                    id="email"
                    autoComplete="email"
                    placeholder="seu@email.com"
                    className={cn(
                      'w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                      errors.email && 'border-danger-500 focus:ring-danger-500'
                    )}
                  />
                  {errors.email && (
                    <p className="mt-1 text-sm text-danger-600">{errors.email.message}</p>
                  )}
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-secondary-700 mb-1">
                Senha
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className={cn(
                    'w-full pl-10 pr-12 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.password && 'border-danger-500 focus:ring-danger-500'
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary-400 hover:text-secondary-600"
                  aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
                {errors.password && (
                  <p className="mt-1 text-sm text-danger-600">{errors.password.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-secondary-700 mb-1">
                Confirmar Senha
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                <input
                  {...register('confirmPassword')}
                  type={showPassword ? 'text' : 'password'}
                  id="confirmPassword"
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className={cn(
                    'w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.confirmPassword && 'border-danger-500 focus:ring-danger-500'
                  )}
                />
                {errors.confirmPassword && (
                  <p className="mt-1 text-sm text-danger-600">{errors.confirmPassword.message}</p>
                )}
              </div>
            </div>

          <div className="border-t border-secondary-200 pt-6">
            <h3 className="text-lg font-semibold text-secondary-900 mb-4">Informações da Organização</h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="organizationName" className="block text-sm font-medium text-secondary-700 mb-1">
                  Nome da Organização
                </label>
                <div className="relative">
                  <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                  <input
                    {...register('organizationName')}
                    type="text"
                    id="organizationName"
                    placeholder="Minha Empresa Ltda"
                    className={cn(
                      'w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                      errors.organizationName && 'border-danger-500 focus:ring-danger-500'
                    )}
                  />
                  {errors.organizationName && (
                    <p className="mt-1 text-sm text-danger-600">{errors.organizationName.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="organizationSlug" className="block text-sm font-medium text-secondary-700 mb-1">
                  Slug da Organização (URL)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary-400 text-sm">
                    app.contractai.com/
                  </span>
                  <input
                    {...register('organizationSlug')}
                    type="text"
                    id="organizationSlug"
                    placeholder="minha-empresa"
                    className={cn(
                      'w-full pl-12 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                      errors.organizationSlug && 'border-danger-500 focus:ring-danger-500'
                    )}
                  />
                  {errors.organizationSlug && (
                    <p className="mt-1 text-sm text-danger-600">{errors.organizationSlug.message}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-4">
            <input
              type="checkbox"
              required
              className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-2 focus:ring-primary-500"
            />
            <span className="text-sm text-secondary-600">
              Li e concordo com os{' '}
              <Link href="/terms" className="text-primary-600 hover:underline">
                Termos de Uso
              </Link>{' '}
              e{' '}
              <Link href="/privacy" className="text-primary-600 hover:underline">
                Política de Privacidade
              </Link>
            </span>
          </div>

          {error && (
            <div className="p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-center gap-2 text-danger-700">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 px-4 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Criando organização...
              </span>
            ) : (
              'Criar organização e entrar'
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-secondary-600">
            Já tem conta?{' '}
            <Link href="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              Entrar
            </Link>
          </p>
        </div>

        <div className="mt-6 pt-6 border-t border-secondary-200">
          <p className="text-xs text-secondary-500 text-center">
            Ao criar sua conta, você concorda com nossos{' '}
            <Link href="/terms" className="text-primary-600 hover:underline">
              Termos de Uso
            </Link>{' '}
            e{' '}
            <Link href="/privacy" className="text-primary-600 hover:underline">
              Política de Privacidade
            </Link>
          </p>
        </div>
        </div>
      </div>
    </div>
  );
}