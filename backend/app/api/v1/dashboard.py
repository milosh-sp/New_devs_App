from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from typing import Dict, Any, List
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user
from app.core.database_pool import db_pool

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User does not belong to a tenant")

    revenue_data = await get_revenue_summary(property_id, tenant_id)
    
    # round first to whole cent, since floats cannot hold values like 1.001 or something, rounding here
    # can cut off a cent
    total_revenue = Decimal(revenue_data['total']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": float(total_revenue),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }

@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """
    Lists the properties of the user's own tenant, for the dashboard property selector.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User does not belong to a tenant")

    if not db_pool.session_factory:
        await db_pool.initialize()

    async with db_pool.get_session() as session:
        result = await session.execute(
            text("SELECT id, name FROM properties WHERE tenant_id = :tenant_id ORDER BY id"),
            {"tenant_id": tenant_id}
        )
        return [{"id": row.id, "name": row.name} for row in result]
