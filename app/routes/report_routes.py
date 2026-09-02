from fastapi import APIRouter, Depends

from app.controllers import report_controller
from app.core.rbac import require_role
from app.models.user import User, UserRole
from app.schemas.report_schema import MonthlyReportGenerateRequest, ReportRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/monthly/generate", response_model=ReportRead)
async def generate_report(
    data: MonthlyReportGenerateRequest,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await report_controller.generate_monthly_impact_report(data, current_user)


@router.get("/mine", response_model=list[ReportRead])
async def list_my_reports(
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await report_controller.list_restaurant_reports(current_user)


@router.get("/{report_id}/download")
async def download_report_csv(
    report_id: str,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await report_controller.export_report_csv(report_id, current_user)


@router.get("/{report_id}/view")
async def view_report_certificate(
    report_id: str,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await report_controller.export_report_print_view(report_id, current_user)
