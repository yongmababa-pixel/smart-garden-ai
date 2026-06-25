"""
工单路由模块 —— 创建 / 派发 / 处置 / 验收（完整工单生命周期）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import datetime, timezone
import math

from database import get_db, WorkOrder, Task, TaskStatus
from models import (
    WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse, WorkOrderListResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["工单"])


# ═══════════════════════════════════════════════════════════
# 工单 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/work-orders", response_model=WorkOrderListResponse, summary="工单列表")
def list_work_orders(
    status: Optional[str] = Query(None, description="状态筛选"),
    order_type: Optional[str] = Query(None, description="类型筛选"),
    assigned_to: Optional[int] = Query(None, description="处置人 ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索（标题/描述）"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    if order_type:
        query = query.filter(WorkOrder.order_type == order_type)
    if assigned_to:
        query = query.filter(WorkOrder.assigned_to == assigned_to)
    if keyword:
        query = query.filter(
            or_(
                WorkOrder.title.contains(keyword),
                WorkOrder.description.contains(keyword),
                WorkOrder.order_no.contains(keyword),
            )
        )

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    items = query.order_by(WorkOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return WorkOrderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[WorkOrderResponse.model_validate(wo) for wo in items],
    )


@router.get("/work-orders/{order_id}", response_model=WorkOrderResponse, summary="工单详情")
def get_work_order(order_id: int, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail=f"工单 id={order_id} 不存在")
    return WorkOrderResponse.model_validate(wo)


@router.post("/work-orders", response_model=WorkOrderResponse, status_code=201, summary="创建工单")
def create_work_order(data: WorkOrderCreate, db: Session = Depends(get_db)):
    """创建新工单，状态自动设为 pending（待派发）"""
    existing = db.query(WorkOrder).filter(WorkOrder.order_no == data.order_no).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"工单编号 {data.order_no} 已存在")

    wo = WorkOrder(**data.model_dump(), status=TaskStatus.PENDING.value)
    db.add(wo)
    db.commit()
    db.refresh(wo)
    return WorkOrderResponse.model_validate(wo)


@router.put("/work-orders/{order_id}", response_model=WorkOrderResponse, summary="更新工单")
def update_work_order(order_id: int, data: WorkOrderUpdate, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail=f"工单 id={order_id} 不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wo, key, value)
    db.commit()
    db.refresh(wo)
    return WorkOrderResponse.model_validate(wo)


@router.delete("/work-orders/{order_id}", response_model=MessageResponse, summary="删除工单")
def delete_work_order(order_id: int, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail=f"工单 id={order_id} 不存在")
    db.delete(wo)
    db.commit()
    return MessageResponse(message="删除成功", detail=f"工单 {wo.order_no} 已删除")


# ═══════════════════════════════════════════════════════════
# 工单生命周期操作
# ═══════════════════════════════════════════════════════════

class DispatchRequest(BaseModel):
    """派发请求"""
    assigned_to: int = Field(..., description="处置人 ID")
    due_date: Optional[datetime] = None
    remark: Optional[str] = None


class ResolveRequest(BaseModel):
    """处置请求"""
    resolution: str = Field(..., min_length=1, description="处置方案")
    cost: float = Field(default=0.0, description="处置成本")
    images: List[str] = Field(default=[], description="现场图片")


class VerifyRequest(BaseModel):
    """验收请求"""
    verified_by: int = Field(..., description="验收人 ID")
    approved: bool = Field(default=True, description="是否通过")
    remark: Optional[str] = None

from pydantic import BaseModel as PydanticBase, Field
from typing import List


class DispatchRequest(PydanticBase):
    assigned_to: int = Field(..., description="处置人 ID")
    due_date: Optional[datetime] = None
    remark: Optional[str] = None


class ResolveRequest(PydanticBase):
    resolution: str = Field(..., min_length=1, description="处置方案")
    cost: float = Field(default=0.0, description="处置成本")
    images: List[str] = Field(default=[], description="现场图片")


class VerifyRequest(PydanticBase):
    verified_by: int = Field(..., description="验收人 ID")
    approved: bool = Field(default=True, description="是否通过")
    remark: Optional[str] = None


@router.post("/work-orders/{order_id}/dispatch", response_model=WorkOrderResponse, summary="派发工单")
def dispatch_work_order(order_id: int, request: DispatchRequest, db: Session = Depends(get_db)):
    """将工单派发给指定处置人，状态变为 assigned"""
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail=f"工单 id={order_id} 不存在")
    if wo.status != TaskStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"工单当前状态为 {wo.status}，无法派发（需为 pending）")

    wo.assigned_to = request.assigned_to
    wo.due_date = request.due_date
    wo.status = TaskStatus.ASSIGNED.value
    if request.remark:
        wo.remark = (wo.remark or "") + f"\n[派发备注] {request.remark}"

    db.commit()
    db.refresh(wo)
    return WorkOrderResponse.model_validate(wo)


@router.post("/work-orders/{order_id}/resolve", response_model=WorkOrderResponse, summary="处置工单")
def resolve_work_order(order_id: int, request: ResolveRequest, db: Session = Depends(get_db)):
    """提交处置方案，状态变为 completed"""
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail=f"工单 id={order_id} 不存在")
    if wo.status not in (TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value):
        raise HTTPException(status_code=400, detail=f"工单当前状态为 {wo.status}，无法处置（需为 assigned/in_progress）")

    wo.resolution = request.resolution
    wo.cost = request.cost
    wo.images = request.images
    wo.status = TaskStatus.COMPLETED.value
    wo.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(wo)
    return WorkOrderResponse.model_validate(wo)


@router.post("/work-orders/{order_id}/verify", response_model=WorkOrderResponse, summary="验收工单")
def verify_work_order(order_id: int, request: VerifyRequest, db: Session = Depends(get_db)):
    """验收工单，通过变为 verified，驳回变为 rejected"""
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail=f"工单 id={order_id} 不存在")
    if wo.status != TaskStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail=f"工单当前状态为 {wo.status}，无法验收（需为 completed）")

    wo.verified_by = request.verified_by
    wo.verified_at = datetime.now(timezone.utc)

    if request.approved:
        wo.status = TaskStatus.VERIFIED.value
    else:
        wo.status = TaskStatus.REJECTED.value

    if request.remark:
        wo.remark = (wo.remark or "") + f"\n[验收备注] {request.remark}"

    db.commit()
    db.refresh(wo)
    return WorkOrderResponse.model_validate(wo)


# ═══════════════════════════════════════════════════════════
# 任务统计
# ═══════════════════════════════════════════════════════════

@router.get("/stats", summary="工单统计")
def work_order_stats(db: Session = Depends(get_db)):
    """按状态统计工单数量"""
    stats = {}
    for status in TaskStatus:
        count = db.query(WorkOrder).filter(WorkOrder.status == status.value).count()
        stats[status.value] = count
    stats["total"] = sum(stats.values())
    return stats
