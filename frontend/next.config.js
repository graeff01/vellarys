/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuração para PWA
  async headers() {
    return [
      {
        // Service Worker
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
      {
        // Manifest
        source: '/manifest.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=604800', // 1 semana
          },
        ],
      },
    ];
  },

  // Outras configurações existentes
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },

  // Ignorar erros de ESLint no build (opcional)
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Ignorar erros de TypeScript no build (opcional)
  typescript: {
    ignoreBuildErrors: true,
  },
};

module.exports = nextConfig;