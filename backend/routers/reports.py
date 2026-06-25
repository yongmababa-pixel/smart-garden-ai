"""
报表统计路由模块 —— 病虫害趋势 / 养护成本 / 巡检覆盖
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
from typing import Optional
from datetime import datetime, timedelta, timezone

from database import get_db, WorkOrder, DroneFlight, Pest
from models import (
    ReportRequest,
    PestTrendResponse, PestTrendItem,
    CostReportResponse, CostItem,
    CoverageReportResponse, CoverageItem,
)

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


# ─── 日期解析辅助 ─────────────────────────────────────────

def _parse_date_range(start: Optional[str], end: Optional[str]) -> tuple[datetime, datetime]:
    """解析日期范围，默认最近 12 个月"""
    now = datetime.now(timezone.utc)
    if end:
        end_date = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    else:
        end_date = now
    if start:
        start_date = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    else:
        start_date = end_date - timedelta(days=365)
    return start_date, end_date


def _format_period_group(period_col, group_by: str):
    """根据 group_by 生成 SQL 分组表达式"""
    if group_by == "day":
        return func.date(period_col)
    elif group_by == "week":
        return func.strftime("%Y-W%W", period_col)
    else:  # month
        return func.strftime("%Y-%m", period_col)


# ═══════════════════════════════════════════════════════════
# 病虫害趋势报表
# ═══════════════════════════════════════════════════════════

@router.get("/pest-trends", response_model=PestTrendResponse, summary="病虫害趋势统计")
def pest_trends(
    start_date: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    group_by: str = Query(default="month", description="聚合粒度：day/week/month"),
    db: Session = Depends(get_db),
):
    """
    统计病虫害检测趋势。
    数据来源于 DroneFlight 表中的 pest_detections JSON 字段（模拟）。
    """
    start_dt, end_dt = _parse_date_range(start_date, end_date)

    # 从飞行记录中提取病虫害检测数据
    flights = db.query(DroneFlight).filter(
        DroneFlight.started_at >= start_dt,
        DroneFlight.started_at <= end_dt,
    ).all()

    items: list[PestTrendItem] = []
    total_detections = 0

    period_map: dict[str, dict[str, int]] = {}  # {period: {pest_name: count}}

    for flight in flights:
        if not flight.started_at:
            continue
        if group_by == "day":
            period = flight.started_at.strftime("%Y-%m-%d")
        elif group_by == "week":
            period = flight.started_at.strftime("%Y-W%W")
        else:
            period = flight.started_at.strftime("%Y-%m")

        if period not in period_map:
            period_map[period] = {}

        detections = flight.pest_detections or []
        for det in detections:
            name = det.get("name", "未知") if isinstance(det, dict) else str(det)
            period_map[period][name] = period_map[period].get(name, 0) + 1
            total_detections += 1

    # 也统计知识库中病虫害的创建时间作为补充趋势
    pests = db.query(Pest).filter(
        Pest.created_at >= start_dt,
        Pest.created_at <= end_dt,
    ).all()
    for pest in pests:
        if group_by == "day":
            period = pest.created_at.strftime("%Y-%m-%d")
        elif group_by == "week":
            period = pest.created_at.strftime("%Y-W%W")
        else:
            period = pest.created_at.strftime("%Y-%m")
        if period not in period_map:
            period_map[period] = {}
        period_map[period][pest.name] = period_map[period].get(pest.name, 0) + 1
        total_detections += 1

    # 组装结果
    for period in sorted(period_map.keys()):
        for pest_name, count in period_map[period].items():
            items.append(PestTrendItem(
                period=period,
                pest_name=pest_name,
                count=count,
            ))

    return PestTrendResponse(
        items=items,
        total_detections=total_detections,
        period_range=f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}",
    )


# ═══════════════════════════════════════════════════════════
# 养护成本报表
# ═══════════════════════════════════════════════════════════

@router.get("/costs", response_model=CostReportResponse, summary="养护成本统计")
def cost_report(
    start_date: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    group_by: str = Query(default="month", description="聚合粒度：day/week/month"),
    order_type: Optional[str] = Query(None, description="工单类型筛选"),
    db: Session = Depends(get_db),
):
    """统计养护成本，按时间和工单类型聚合"""
    start_dt, end_dt = _parse_date_range(start_date, end_date)

    query = db.query(WorkOrder).filter(
        WorkOrder.created_at >= start_dt,
        WorkOrder.created_at <= end_dt,
    )
    if order_type:
        query = query.filter(WorkOrder.order_type == order_type)

    orders = query.all()

    # 内存聚合
    period_map: dict[str, dict[str, dict]] = {}  # {period: {order_type: {total_cost, order_count}}}

    for wo in orders:
        if group_by == "day":
            period = wo.created_at.strftime("%Y-%m-%d")
        elif group_by == "week":
            period = wo.created_at.strftime("%Y-W%W")
        else:
            period = wo.created_at.strftime("%Y-%m")

        if period not in period_map:
            period_map[period] = {}

        ot = wo.order_type or "其他"
        if ot not in period_map[period]:
            period_map[period][ot] = {"total_cost": 0.0, "order_count": 0}

        period_map[period][ot]["total_cost"] += wo.cost or 0.0
        period_map[period][ot]["order_count"] += 1

    items: list[CostItem] = []
    total_cost = 0.0
    total_orders = 0

    for period in sorted(period_map.keys()):
        for ot, data in period_map[period].items():
            items.append(CostItem(
                period=period,
                order_type=ot,
                total_cost=round(data["total_cost"], 2),
                order_count=data["order_count"],
            ))
            total_cost += data["total_cost"]
            total_orders += data["order_count"]

    return CostReportResponse(
        items=items,
        total_cost=round(total_cost, 2),
        total_orders=total_orders,
        period_range=f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}",
    )


# ═══════════════════════════════════════════════════════════
# 巡检覆盖报表
# ═══════════════════════════════════════════════════════════

@router.get("/coverage", response_model=CoverageReportResponse, summary="巡检覆盖统计")
def coverage_report(
    start_date: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    group_by: str = Query(default="month", description="聚合粒度：day/week/month"),
    db: Session = Depends(get_db),
):
    """统计无人机巡检覆盖情况"""
    start_dt, end_dt = _parse_date_range(start_date, end_date)

    flights = db.query(DroneFlight).filter(
        DroneFlight.started_at >= start_dt,
        DroneFlight.started_at <= end_dt,
    ).all()

    period_map: dict[str, dict[str, dict]] = {}  # {period: {area: {total_area, flight_count, images}}}

    for flight in flights:
        if not flight.started_at:
            continue
        if group_by == "day":
            period = flight.started_at.strftime("%Y-%m-%d")
        elif group_by == "week":
            period = flight.started_at.strftime("%Y-W%W")
        else:
            period = flight.started_at.strftime("%Y-%m")

        if period not in period_map:
            period_map[period] = {}

        area = flight.area or "未知区域"
        if area not in period_map[period]:
            period_map[period][area] = {"total_area_sqm": 0.0, "flight_count": 0, "images_total": 0}

        period_map[period][area]["total_area_sqm"] += flight.coverage_area_sqm or 0.0
        period_map[period][area]["flight_count"] += 1
        period_map[period][area]["images_total"] += flight.images_captured or 0

    items: list[CoverageItem] = []
    total_area = 0.0
    total_flights = 0

    for period in sorted(period_map.keys()):
        for area, data in period_map[period].items():
            items.append(CoverageItem(
                period=period,
                area=area,
                total_area_sqm=round(data["total_area_sqm"], 2),
                flight_count=data["flight_count"],
                images_total=data["images_total"],
            ))
            total_area += data["total_area_sqm"]
            total_flights += data["flight_count"]

    return CoverageReportResponse(
        items=items,
        total_area_sqm=round(total_area, 2),
        total_flights=total_flights,
        period_range=f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}",
    )
