
from src.domain.services.lead_qualifier import qualify_lead

class FakeLead:
    id = 999

class FakeMessage:
    def __init__(self, content, role="user"):
        self.content = content
        self.role = role

# Simula conversa
messages = [
    FakeMessage("Bom dia! Tenho 800 mil guardado e preciso comprar urgente, em 15 dias. Meu financiamento já foi aprovado pelo banco. Posso agendar visita pra amanhã?", "user"),
]

lead = FakeLead()

result = qualify_lead(lead, messages)

print("\n" + "=" * 80)
print("RESULTADO:")
print(f"Qualificação: {result['qualification']}")
print(f"Score: {result['score']}")
print(f"Confidence: {result['confidence']}")
print(f"Reasons: {result['reasons']}")
print(f"Signals HOT: {result['signals']['hot']}")
print("=" * 80)