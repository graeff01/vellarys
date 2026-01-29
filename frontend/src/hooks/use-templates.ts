/**
 * useTemplates - Hook para Templates de Respostas Rápidas
 * ========================================================
 *
 * Gerencia templates de respostas rápidas com interpolação de variáveis.
 *
 * Funcionalidades:
 * - Carrega templates do backend
 * - Filtra por categoria/busca
 * - Interpola variáveis ({{lead_name}}, {{seller_name}}, etc)
 * - Incrementa contador de uso
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export interface ResponseTemplate {
  id: number;
  name: string;
  shortcut: string | null;
  content: string;
  category: string | null;
  is_active: boolean;
  usage_count: number;
  created_at: string;
}

interface UseTemplatesOptions {
  autoLoad?: boolean;
  category?: string;
  search?: string;
}

export function useTemplates(options: UseTemplatesOptions = {}) {
  const { autoLoad = true, category, search } = options;

  const [templates, setTemplates] = useState<ResponseTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Carrega templates do backend
  const loadTemplates = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();

      if (category) {
        params.append('category', category);
      }

      if (search) {
        params.append('search', search);
      }

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/templates?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setTemplates(response.data);
    } catch (err: any) {
      console.error('[Templates] Erro ao carregar:', err);
      setError(err.response?.data?.detail || 'Erro ao carregar templates');
    } finally {
      setIsLoading(false);
    }
  }, [category, search]);

  // Auto-load na montagem
  useEffect(() => {
    if (autoLoad) {
      loadTemplates();
    }
  }, [autoLoad, loadTemplates]);

  // Usa template e retorna conteúdo interpolado
  const useTemplate = async (templateId: number, leadId: number): Promise<string> => {
    try {
      const token = localStorage.getItem('token');

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/templates/${templateId}/interpolate?lead_id=${leadId}`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      return response.data.content;
    } catch (err: any) {
      console.error('[Templates] Erro ao usar template:', err);
      throw new Error(err.response?.data?.detail || 'Erro ao usar template');
    }
  };

  // Cria novo template
  const createTemplate = async (data: {
    name: string;
    shortcut?: string;
    content: string;
    category?: string;
  }): Promise<ResponseTemplate> => {
    try {
      const token = localStorage.getItem('token');

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/templates`,
        data,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Recarrega lista
      await loadTemplates();

      return response.data;
    } catch (err: any) {
      console.error('[Templates] Erro ao criar:', err);
      throw new Error(err.response?.data?.detail || 'Erro ao criar template');
    }
  };

  // Atualiza template
  const updateTemplate = async (
    templateId: number,
    data: Partial<{
      name: string;
      shortcut: string;
      content: string;
      category: string;
      is_active: boolean;
    }>
  ): Promise<ResponseTemplate> => {
    try {
      const token = localStorage.getItem('token');

      const response = await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/templates/${templateId}`,
        data,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Recarrega lista
      await loadTemplates();

      return response.data;
    } catch (err: any) {
      console.error('[Templates] Erro ao atualizar:', err);
      throw new Error(err.response?.data?.detail || 'Erro ao atualizar template');
    }
  };

  // Exclui template (soft-delete)
  const deleteTemplate = async (templateId: number): Promise<void> => {
    try {
      const token = localStorage.getItem('token');

      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/templates/${templateId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Recarrega lista
      await loadTemplates();
    } catch (err: any) {
      console.error('[Templates] Erro ao excluir:', err);
      throw new Error(err.response?.data?.detail || 'Erro ao excluir template');
    }
  };

  // Filtra templates localmente por shortcut
  const findByShortcut = (shortcut: string): ResponseTemplate | undefined => {
    return templates.find(t => t.shortcut?.toLowerCase() === shortcut.toLowerCase());
  };

  return {
    templates,
    isLoading,
    error,
    loadTemplates,
    useTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    findByShortcut
  };
}
