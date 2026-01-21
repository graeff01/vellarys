/**
 * SKELETON LOADER - Loading States Bonitos
 * ==========================================
 * 
 * Componente reutilizável para estados de loading.
 * Muito melhor que "Carregando..."
 */

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  count?: number;
}

export function Skeleton({ 
  className = '', 
  variant = 'text',
  width,
  height,
  count = 1
}: SkeletonProps) {
  const baseClasses = 'animate-pulse bg-gray-200 rounded';
  
  const variantClasses = {
    text: 'h-4',
    circular: 'rounded-full',
    rectangular: 'h-32',
  };

  const skeletonClasses = `${baseClasses} ${variantClasses[variant]} ${className}`;
  
  const style = {
    width: width || (variant === 'text' ? '100%' : undefined),
    height: height || undefined,
  };

  if (count > 1) {
    return (
      <div className="space-y-3">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={skeletonClasses} style={style} />
        ))}
      </div>
    );
  }

  return <div className={skeletonClasses} style={style} />;
}

/**
 * SKELETON PRESETS - Layouts prontos
 */

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
      <div className="flex items-center gap-4 mb-4">
        <Skeleton variant="circular" width={48} height={48} />
        <div className="flex-1">
          <Skeleton width="60%" className="mb-2" />
          <Skeleton width="40%" />
        </div>
      </div>
      <Skeleton count={3} />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
        <div className="flex gap-4">
          <Skeleton width="25%" />
          <Skeleton width="20%" />
          <Skeleton width="15%" />
          <Skeleton width="20%" />
          <Skeleton width="20%" />
        </div>
      </div>
      
      {/* Rows */}
      <div className="divide-y divide-gray-100">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="px-6 py-4">
            <div className="flex gap-4 items-center">
              <Skeleton variant="circular" width={40} height={40} />
              <Skeleton width="20%" />
              <Skeleton width="15%" />
              <Skeleton width="10%" />
              <Skeleton width="15%" />
              <div className="flex gap-2 ml-auto">
                <Skeleton width={80} height={32} />
                <Skeleton width={80} height={32} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonList({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width={40} height={40} />
            <div className="flex-1">
              <Skeleton width="70%" className="mb-2" />
              <Skeleton width="40%" />
            </div>
            <Skeleton width={60} height={24} />
          </div>
        </div>
      ))}
    </div>
  );
}
