"use client"

import { useState, useEffect } from 'react'
import { Plus, UserPlus, Mail, Lock, Phone, MapPin, Tag, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { api } from '@/lib/api'
import { toast, Toaster } from 'sonner'

interface Seller {
  id: number
  name: string
  whatsapp: string
  email: string | null
  cities: string[]
  specialties: string[]
  active: boolean
  available: boolean
  total_leads: number
  converted_leads: number
  conversion_rate: number
  user_id?: number | null
}

export default function VendedoresPage() {
  const [sellers, setSellers] = useState<Seller[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [email, setEmail] = useState('')
  const [cities, setCities] = useState('')
  const [specialties, setSpecialties] = useState('')
  const [createUserAccount, setCreateUserAccount] = useState(false)
  const [userEmail, setUserEmail] = useState('')
  const [userPassword, setUserPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadSellers()
  }, [])

  async function loadSellers() {
    try {
      const response = await api.get('/v1/sellers')
      setSellers(response.sellers)
    } catch (error) {
      console.error('Erro ao carregar vendedores:', error)
      toast.error('Erro ao carregar vendedores')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)

    try {
      const payload = {
        name,
        whatsapp,
        email: email || null,
        cities: cities ? cities.split(',').map(c => c.trim()) : [],
        specialties: specialties ? specialties.split(',').map(s => s.trim()) : [],
        max_leads_per_day: 0,
        priority: 5,
        notification_channels: ['whatsapp'],
        create_user_account: createUserAccount,
        user_email: createUserAccount ? (userEmail || email) : null,
        user_password: createUserAccount ? userPassword : null,
      }

      const response = await api.post('/v1/sellers', payload)

      toast.success(response.message)

      if (response.user_created) {
        toast.success(response.user_created.message, {
          description: `Email: ${response.user_created.email}`,
          duration: 5000,
        })
      }

      // Reset form
      setName('')
      setWhatsapp('')
      setEmail('')
      setCities('')
      setSpecialties('')
      setCreateUserAccount(false)
      setUserEmail('')
      setUserPassword('')
      setDialogOpen(false)

      // Reload sellers
      loadSellers()
    } catch (error: any) {
      console.error('Erro ao criar vendedor:', error)
      toast.error(error.response?.data?.detail || 'Erro ao criar vendedor')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <>
      <Toaster position="top-right" />
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Vendedores</h1>
            <p className="text-gray-600 mt-1">Gerencie sua equipe de vendas</p>
          </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Novo Vendedor
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Criar Novo Vendedor</DialogTitle>
              <DialogDescription>
                Adicione um novo vendedor à sua equipe. Você pode criar uma conta de usuário para que ele acesse o CRM.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              {/* Informações Básicas */}
              <div className="space-y-4">
                <h3 className="font-semibold text-sm text-gray-700">Informações Básicas</h3>

                <div>
                  <Label htmlFor="name">Nome Completo *</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="João Silva"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="whatsapp">WhatsApp *</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="whatsapp"
                      value={whatsapp}
                      onChange={(e) => setWhatsapp(e.target.value)}
                      placeholder="5511999999999"
                      className="pl-10"
                      required
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Formato: 5511999999999 (com DDI e DDD)</p>
                </div>

                <div>
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="joao@empresa.com"
                      className="pl-10"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="cities">Cidades (separadas por vírgula)</Label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="cities"
                      value={cities}
                      onChange={(e) => setCities(e.target.value)}
                      placeholder="São Paulo, Campinas, Santos"
                      className="pl-10"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="specialties">Especialidades (separadas por vírgula)</Label>
                  <div className="relative">
                    <Tag className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="specialties"
                      value={specialties}
                      onChange={(e) => setSpecialties(e.target.value)}
                      placeholder="Venda, Aluguel, Comercial"
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              {/* Criar Conta de Usuário */}
              <div className="border-t pt-4 space-y-4">
                <div className="flex items-start space-x-3">
                  <Checkbox
                    id="create-user"
                    checked={createUserAccount}
                    onCheckedChange={(checked) => setCreateUserAccount(checked as boolean)}
                  />
                  <div className="space-y-1">
                    <label
                      htmlFor="create-user"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex items-center gap-2"
                    >
                      <Shield className="h-4 w-4 text-blue-600" />
                      Criar conta de usuário (CRM Inbox)
                    </label>
                    <p className="text-xs text-gray-500">
                      O vendedor poderá fazer login no painel e gerenciar seus leads
                    </p>
                  </div>
                </div>

                {createUserAccount && (
                  <div className="ml-6 space-y-4 border-l-2 border-blue-200 pl-4">
                    <div>
                      <Label htmlFor="user-email">Email para Login</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                        <Input
                          id="user-email"
                          type="email"
                          value={userEmail}
                          onChange={(e) => setUserEmail(e.target.value)}
                          placeholder={email || "email@empresa.com"}
                          className="pl-10"
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Deixe vazio para usar o email principal
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="user-password">Senha *</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                        <Input
                          id="user-password"
                          type="password"
                          value={userPassword}
                          onChange={(e) => setUserPassword(e.target.value)}
                          placeholder="Mínimo 6 caracteres"
                          className="pl-10"
                          minLength={6}
                          required={createUserAccount}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? 'Criando...' : 'Criar Vendedor'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Lista de Vendedores */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sellers.map((seller) => (
          <Card key={seller.id} className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold text-lg">{seller.name}</h3>
                <p className="text-sm text-gray-600">{seller.whatsapp}</p>
                {seller.email && (
                  <p className="text-sm text-gray-600">{seller.email}</p>
                )}

                {seller.user_id && (
                  <div className="mt-2 flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded w-fit">
                    <Shield className="h-3 w-3" />
                    Tem acesso ao CRM
                  </div>
                )}
              </div>

              <div className={`px-2 py-1 rounded text-xs font-medium ${
                seller.active
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {seller.active ? 'Ativo' : 'Inativo'}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-2xl font-bold">{seller.total_leads}</div>
                <div className="text-xs text-gray-600">Leads</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{seller.converted_leads}</div>
                <div className="text-xs text-gray-600">Conversões</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{seller.conversion_rate.toFixed(1)}%</div>
                <div className="text-xs text-gray-600">Taxa</div>
              </div>
            </div>

            {(seller.cities.length > 0 || seller.specialties.length > 0) && (
              <div className="mt-4 pt-4 border-t space-y-2">
                {seller.cities.length > 0 && (
                  <div className="text-xs">
                    <span className="text-gray-600">Cidades:</span>{' '}
                    <span className="text-gray-900">{seller.cities.join(', ')}</span>
                  </div>
                )}
                {seller.specialties.length > 0 && (
                  <div className="text-xs">
                    <span className="text-gray-600">Especialidades:</span>{' '}
                    <span className="text-gray-900">{seller.specialties.join(', ')}</span>
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>

      {sellers.length === 0 && (
        <Card className="p-12 text-center">
          <UserPlus className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-semibold">Nenhum vendedor cadastrado</h3>
          <p className="text-gray-600 mt-2">Comece adicionando seu primeiro vendedor</p>
          <Button className="mt-4" onClick={() => setDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Adicionar Vendedor
          </Button>
        </Card>
      )}
      </div>
    </>
  )
}
