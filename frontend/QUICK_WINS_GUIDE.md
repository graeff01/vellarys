# 🎨 Quick Wins - Guia de Uso

## Componentes Criados

### 1. **Skeleton** - Loading States

```typescript
import { Skeleton, SkeletonCard, SkeletonTable, SkeletonList } from '@/components/Skeleton';

// Uso básico
<Skeleton />
<Skeleton width="60%" />
<Skeleton variant="circular" width={48} height={48} />
<Skeleton count={3} />

// Presets prontos
<SkeletonCard />
<SkeletonTable rows={5} />
<SkeletonList items={5} />
```

### 2. **EmptyState** - Estados Vazios

```typescript
import { EmptyState, EmptyLeads, EmptySellers, EmptyMessages } from '@/components/EmptyState';

// Uso básico
<EmptyState
  icon="📭"
  title="Nenhum item"
  description="Descrição opcional"
  action={{
    label: 'Criar Novo',
    onClick: () => handleCreate()
  }}
/>

// Presets prontos
<EmptyLeads onCreateLead={() => router.push('/simulator')} />
<EmptySellers onCreateSeller={() => setShowModal(true)} />
<EmptyMessages />
```

### 3. **Toast** - Notificações

```typescript
import { useToast, ToastProvider } from '@/components/Toast';

// 1. Wrap app com ToastProvider (layout.tsx)
<ToastProvider>
  {children}
</ToastProvider>

// 2. Use no componente
const { success, error, info, warning } = useToast();

success('Vendedor criado com sucesso!', '🎉');
error('Erro ao criar vendedor', '❌');
info('Informação importante');
warning('Atenção!', '⚠️');
```

## Classes CSS Disponíveis

### Animações

```html
<!-- Slide in -->
<div class="animate-slide-in-right">Toast</div>

<!-- Fade in -->
<div class="animate-fade-in">Modal</div>

<!-- Scale in -->
<div class="animate-scale-in">Popup</div>

<!-- Bounce -->
<div class="animate-bounce-once">Success!</div>

<!-- Shake -->
<div class="animate-shake">Error!</div>

<!-- Pulse ring -->
<div class="animate-pulse-ring">Notification</div>
```

### Hover Effects

```html
<!-- Card hover -->
<div class="card-hover bg-white rounded-lg p-4">
  Card com hover suave
</div>

<!-- Link animado -->
<a href="#" class="link-animated">
  Link com underline animado
</a>

<!-- Badge com pulse -->
<span class="badge-pulse bg-red-500 text-white px-2 py-1 rounded-full">
  3
</span>
```

### Loading

```html
<!-- Spinner -->
<div class="spinner"></div>

<!-- Skeleton shimmer -->
<div class="skeleton-shimmer h-4 rounded"></div>
```

## Exemplos Práticos

### Substituir Alert por Toast

**Antes:**
```typescript
alert('Vendedor criado com sucesso!');
```

**Depois:**
```typescript
const { success } = useToast();
success('Vendedor criado com sucesso!', '🎉');
```

### Loading State em Lista

**Antes:**
```typescript
{loading && <div>Carregando...</div>}
```

**Depois:**
```typescript
{loading && <SkeletonTable rows={5} />}
```

### Empty State em Lista

**Antes:**
```typescript
{sellers.length === 0 && <div>Nenhum vendedor encontrado</div>}
```

**Depois:**
```typescript
{sellers.length === 0 && (
  <EmptySellers onCreateSeller={() => setShowModal(true)} />
)}
```

### Botão com Hover

**Antes:**
```html
<button class="bg-purple-600 text-white px-4 py-2 rounded">
  Criar
</button>
```

**Depois:**
```html
<button class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition-all hover:scale-105 hover:shadow-lg">
  Criar
</button>
```

## Checklist de Aplicação

- [ ] Adicionar ToastProvider no layout.tsx
- [ ] Substituir alerts por toasts em sellers
- [ ] Substituir alerts por toasts em leads
- [ ] Substituir alerts por toasts em clients
- [ ] Adicionar SkeletonTable em lista de leads
- [ ] Adicionar SkeletonTable em lista de vendedores
- [ ] Adicionar EmptyLeads quando vazio
- [ ] Adicionar EmptySellers quando vazio
- [ ] Adicionar hover effects em cards
- [ ] Adicionar transitions em botões
