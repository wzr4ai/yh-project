from datetime import datetime
from fastapi import APIRouter

from app.models import schemas

router = APIRouter()


@router.post("/import/products", response_model=schemas.ProductImportJob)
async def import_products(file_name: str):
    job = schemas.ProductImportJob(
        id=f"job-{int(datetime.utcnow().timestamp())}",
        file_name=file_name,
        status="processing",
        total_rows=120,
        success_rows=0,
        error_rows=0,
    )
    return job


@router.get("/import/{job_id}", response_model=schemas.ProductImportJob)
async def get_import_job(job_id: str):
    return schemas.ProductImportJob(
        id=job_id,
        file_name="mock.xlsx",
        status="success",
        total_rows=120,
        success_rows=118,
        error_rows=2,
        error_report_url="/mock/error-report.xlsx",
    )
