import sys
sys.path.append(".")

from src.infrastructure.services.property_lookup_service import PropertyLookupService

lookup = PropertyLookupService()

print(lookup.buscar_por_codigo("123456"))
