'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DataSourcesRedirect() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/dashboard/settings?tab=datasources');
    }, [router]);

    return (
        <div className="flex items-center justify-center min-h-[400px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            <span className="ml-3 text-gray-600">Redirecionando para Fontes de Dados...</span>
        </div>
    );
}
