interface BadgeProps {
  children: React.ReactNode;
  variant?: 
    | 'default'
    | 'hot'
    | 'warm'
    | 'cold'
    | 'success'
    | 'warning'
    | 'outline';
  className?: string; // <- necessário
}

const variants = {
  default: 'bg-gray-100 text-gray-800',
  hot: 'bg-red-100 text-red-800',
  warm: 'bg-yellow-100 text-yellow-800',
  cold: 'bg-blue-100 text-blue-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-orange-100 text-orange-800',

  // novo
  outline: 'border border-gray-300 text-gray-700 bg-white',
};

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
        ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
