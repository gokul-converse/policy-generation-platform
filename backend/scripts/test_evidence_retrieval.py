import json

from app.services.evidence_service import retrieve_evidence


description = "Create a leave policy for our company"

result = retrieve_evidence(description)

print(json.dumps(result, indent=2, ensure_ascii=False))