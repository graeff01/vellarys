import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ServiceWorkerRegistration } from '@/components/pwa/service-worker-registration';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: {
    default: 'Vellarys - Gestão Inteligente de Leads',
    template: '%s | Vellarys'
  },
  description: 'Plataforma de IA para automação, atendimento e qualificação de leads via WhatsApp.',
  applicationName: 'Vellarys',
  authors: [{ name: 'Vellarys Team' }],
  generator: 'Next.js',
  keywords: ['leads', 'whatsapp', 'ia', 'crm', 'vendas', 'automação'],
  referrer: 'origin-when-cross-origin',

  // PWA
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Vellarys',
  },
  formatDetection: {
    telephone: false,
  },

  // Open Graph (Social Sharing)
  openGraph: {
    type: 'website',
    siteName: 'Vellarys',
    title: 'Vellarys - Gestão de Leads com IA',
    description: 'Aumente sua conversão com atendimento automatizado e inteligente.',
    locale: 'pt_BR',
    url: 'https://vellarys.com',
  },

  // Twitter
  twitter: {
    card: 'summary_large_image',
    title: 'Vellarys - Gestão de Leads com IA',
    description: 'Atendimento e qualificação de leads via WhatsApp em escala.',
  },

  // Icons
  icons: {
    icon: [
      { url: '/icons/icon-96x96.png', sizes: '96x96', type: 'image/png' },
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: '#2563eb',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5, // Permite zoom até 5x para acessibilidade
  userScalable: true, // Permite zoom manual
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="antialiased">
      <body className={inter.className}>
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}