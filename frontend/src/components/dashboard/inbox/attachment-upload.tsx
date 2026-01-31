/**
 * AttachmentUpload - Upload de Anexos
 * ====================================
 *
 * Componente para upload de imagens, documentos, áudio e vídeo.
 * Suporta drag & drop e preview de imagens.
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Paperclip, X, FileText, Image as ImageIcon, Film, Music } from 'lucide-react';
import axios from 'axios';
import { cn } from '@/lib/utils';
import { getToken } from '@/lib/auth';

interface AttachmentData {
  type: 'image' | 'document' | 'audio' | 'video' | 'file';
  url: string;
  filename: string;
  mime_type: string;
  size: number;
  uploaded_at: string;
}

interface AttachmentUploadProps {
  leadId: number;
  onUploadComplete: (attachment: AttachmentData) => void;
  onUploadError?: (error: string) => void;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const ALLOWED_TYPES = [
  // Imagens
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  // Documentos
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  // Áudio
  'audio/mpeg',
  'audio/ogg',
  'audio/wav',
  // Vídeo
  'video/mp4',
  'video/quicktime'
];

export function AttachmentUpload({ leadId, onUploadComplete, onUploadError }: AttachmentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Valida arquivo
  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `Arquivo muito grande. Máximo: 10MB`;
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      return `Tipo de arquivo não permitido: ${file.type}`;
    }

    return null;
  };

  // Gera preview para imagens
  const generatePreview = (file: File) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setPreview(null);
    }
  };

  // Seleciona arquivo
  const handleFileSelect = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      onUploadError?.(error);
      return;
    }

    setSelectedFile(file);
    generatePreview(file);
  }, [onUploadError]);

  // Upload do arquivo
  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const token = getToken();
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/leads/${leadId}/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
            setUploadProgress(percentCompleted);
          }
        }
      );

      // Callback de sucesso
      onUploadComplete(response.data.attachment);

      // Limpa estado
      setSelectedFile(null);
      setPreview(null);
      setUploadProgress(0);

    } catch (error: any) {
      console.error('Erro no upload:', error);
      const errorMsg = error.response?.data?.detail || 'Erro ao fazer upload';
      onUploadError?.(errorMsg);
    } finally {
      setIsUploading(false);
    }
  };

  // Drag & Drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  // Ícone baseado no tipo
  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <ImageIcon className="h-12 w-12" />;
    if (type.startsWith('audio/')) return <Music className="h-12 w-12" />;
    if (type.startsWith('video/')) return <Film className="h-12 w-12" />;
    return <FileText className="h-12 w-12" />;
  };

  // Formata tamanho do arquivo
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-3">
      {/* Área de drop ou seleção */}
      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
            isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
          )}
          onClick={() => fileInputRef.current?.click()}
        >
          <Paperclip className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm font-medium">
            Arraste um arquivo ou clique para selecionar
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Imagens, PDFs, documentos, áudio ou vídeo (máx. 10MB)
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_TYPES.join(',')}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileSelect(file);
            }}
            className="hidden"
          />
        </div>
      ) : (
        // Preview do arquivo selecionado
        <div className="border rounded-lg p-4">
          <div className="flex items-start gap-3">
            {/* Preview ou ícone */}
            <div className="flex-shrink-0">
              {preview ? (
                <img src={preview} alt="Preview" className="h-16 w-16 object-cover rounded" />
              ) : (
                <div className="h-16 w-16 flex items-center justify-center text-muted-foreground">
                  {getFileIcon(selectedFile.type)}
                </div>
              )}
            </div>

            {/* Informações */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(selectedFile.size)}
              </p>

              {/* Progresso de upload */}
              {isUploading && (
                <div className="mt-2">
                  <Progress value={uploadProgress} className="h-1" />
                  <p className="text-xs text-muted-foreground mt-1">
                    Enviando... {uploadProgress}%
                  </p>
                </div>
              )}
            </div>

            {/* Botão remover */}
            {!isUploading && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedFile(null);
                  setPreview(null);
                }}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Botão de upload */}
          {!isUploading && (
            <Button
              onClick={handleUpload}
              className="w-full mt-3"
              size="sm"
            >
              Enviar Anexo
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
