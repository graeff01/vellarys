'use client';

import { useState, useEffect } from 'react';
import { getProperties, type Property } from '@/lib/properties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Building2,
  Home,
  MapPin,
  Bed,
  Bath,
  Car,
  Maximize,
  Plus,
  Search,
  Filter
} from 'lucide-react';

export default function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchCity, setSearchCity] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    loadProperties();
  }, [filterType]);

  async function loadProperties() {
    try {
      setLoading(true);
      const filters: any = { is_available: true };

      if (filterType !== 'all') {
        filters.property_type = filterType;
      }

      const data = await getProperties(filters);
      setProperties(data);
    } catch (error) {
      console.error('Erro ao carregar imóveis:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredProperties = properties.filter(prop =>
    !searchCity || prop.city.toLowerCase().includes(searchCity.toLowerCase())
  );

  const getPropertyTypeIcon = (type: string) => {
    switch (type) {
      case 'casa':
        return Home;
      case 'apartamento':
        return Building2;
      default:
        return Building2;
    }
  };

  const getPropertyTypeBadge = (type: string) => {
    const config: Record<string, { label: string; className: string }> = {
      casa: { label: 'Casa', className: 'bg-green-100 text-green-800' },
      apartamento: { label: 'Apartamento', className: 'bg-blue-100 text-blue-800' },
      sobrado: { label: 'Sobrado', className: 'bg-purple-100 text-purple-800' },
      terreno: { label: 'Terreno', className: 'bg-yellow-100 text-yellow-800' },
      sala_comercial: { label: 'Comercial', className: 'bg-orange-100 text-orange-800' },
    };

    const { label, className } = config[type] || { label: type, className: 'bg-gray-100 text-gray-800' };
    const Icon = getPropertyTypeIcon(type);

    return (
      <Badge className={className}>
        <Icon className="w-3 h-3 mr-1" />
        {label}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-gray-500">Carregando imóveis...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Building2 className="w-8 h-8" />
            Catálogo de Imóveis
          </h1>
          <p className="text-gray-500 mt-1">Gerencie seus imóveis disponíveis</p>
        </div>

        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Novo Imóvel
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por cidade..."
            value={searchCity}
            onChange={(e) => setSearchCity(e.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex gap-2">
          <Button
            variant={filterType === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterType('all')}
          >
            Todos
          </Button>
          <Button
            variant={filterType === 'casa' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterType('casa')}
          >
            Casas
          </Button>
          <Button
            variant={filterType === 'apartamento' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterType('apartamento')}
          >
            Apartamentos
          </Button>
        </div>
      </div>

      {/* Properties Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProperties.length === 0 ? (
          <Card className="col-span-full p-12 text-center">
            <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              Nenhum imóvel encontrado
            </h3>
            <p className="text-gray-500">
              {searchCity ? 'Tente buscar outra cidade' : 'Cadastre seu primeiro imóvel!'}
            </p>
          </Card>
        ) : (
          filteredProperties.map((property) => (
            <Card key={property.id} className="overflow-hidden hover:shadow-lg transition-shadow">
              {/* Image */}
              <div className="h-48 bg-gradient-to-br from-blue-100 to-blue-50 relative">
                {property.images && property.images.length > 0 ? (
                  <img
                    src={property.images[0]}
                    alt={property.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Building2 className="w-16 h-16 text-blue-300" />
                  </div>
                )}
                <div className="absolute top-3 left-3">
                  {getPropertyTypeBadge(property.property_type)}
                </div>
                {property.sale_price && (
                  <div className="absolute bottom-3 left-3">
                    <Badge className="bg-white text-gray-900 font-bold text-lg">
                      R$ {(property.sale_price / 1000).toFixed(0)}k
                    </Badge>
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 mb-2 line-clamp-1">
                  {property.title}
                </h3>

                <div className="flex items-center gap-1 text-sm text-gray-600 mb-3">
                  <MapPin className="w-4 h-4" />
                  <span className="line-clamp-1">
                    {property.neighborhood ? `${property.neighborhood}, ` : ''}
                    {property.city} - {property.state}
                  </span>
                </div>

                {/* Features */}
                <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
                  {property.rooms && (
                    <div className="flex items-center gap-1">
                      <Bed className="w-4 h-4" />
                      <span>{property.rooms}</span>
                    </div>
                  )}
                  {property.bathrooms && (
                    <div className="flex items-center gap-1">
                      <Bath className="w-4 h-4" />
                      <span>{property.bathrooms}</span>
                    </div>
                  )}
                  {property.parking_spots && (
                    <div className="flex items-center gap-1">
                      <Car className="w-4 h-4" />
                      <span>{property.parking_spots}</span>
                    </div>
                  )}
                  {property.size_sqm && (
                    <div className="flex items-center gap-1">
                      <Maximize className="w-4 h-4" />
                      <span>{property.size_sqm}m²</span>
                    </div>
                  )}
                </div>

                {/* Additional Info */}
                {property.features && property.features.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {property.features.slice(0, 3).map((feature, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                    {property.features.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{property.features.length - 3}
                      </Badge>
                    )}
                  </div>
                )}

                <Button variant="outline" className="w-full">
                  Ver Detalhes
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
