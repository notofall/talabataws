from typing import Any, Dict

from app.requests.domain.models import MaterialRequest


def material_request_to_response(request: MaterialRequest) -> Dict[str, Any]:
    return {
        "id": request.id,
        "request_number": request.request_number,
        "request_seq": request.request_seq,
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "estimated_price": item.estimated_price,
            }
            for item in request.items
        ],
        "project_id": request.project_id,
        "project_name": request.project_name,
        "reason": request.reason,
        "supervisor_id": request.supervisor_id,
        "supervisor_name": request.supervisor_name,
        "engineer_id": request.engineer_id,
        "engineer_name": request.engineer_name,
        "status": request.status,
        "rejection_reason": request.rejection_reason,
        "expected_delivery_date": request.expected_delivery_date,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "updated_at": request.updated_at.isoformat() if request.updated_at else None,
    }
