import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';


export const metadata: Metadata = {
  title: 'ContractAI - Intelligent Contract Analysis',
  description: 'AI-powered contract analysis platform for legal teams',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}