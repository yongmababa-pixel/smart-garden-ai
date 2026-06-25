"""
Pydantic 数据模型——请求体 & 响应体
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# 通用
# ═══════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    """分页响应基类"""
    total: int
    page: int
    page_size: int
    total_pages: int


# ═══════════════════════════════════════════════════════════
# 用户
# ═══════════════════════════════════════════════════════════

class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="worker")
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: int = 1


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[int] = None


class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# 植物（知识库）
# ═══════════════════════════════════════════════════════════

class PlantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    latin_name: Optional[str] = None
    category: Optional[str] = None
    family: Optional[str] = None
    traits: Optional[str] = None
    care_standard: Optional[str] = None
    suitable_regions: Optional[str] = None
    image_url: Optional[str] = None
    embedding_text: Optional[str] = None


class PlantCreate(PlantBase):
    pass


class PlantUpdate(BaseModel):
    name: Optional[str] = None
    latin_name: Optional[str] = None
    category: Optional[str] = None
    family: Optional[str] = None
    traits: Optional[str] = None
    care_standard: Optional[str] = None
    suitable_regions: Optional[str] = None
    image_url: Optional[str] = None
    embedding_text: Optional[str] = None


class PlantResponse(PlantBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PlantListResponse(PaginatedResponse):
    items: List[PlantResponse]


# ═══════════════════════════════════════════════════════════
# 病虫害（知识库）
# ═══════════════════════════════════════════════════════════

class PestBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    latin_name: Optional[str] = None
    category: Optional[str] = None
    affected_plants: Optional[str] = None
    symptoms: Optional[str] = None
    cause: Optional[str] = None
    prevention: Optional[str] = None
    severity: Optional[str] = "medium"
    image_url: Optional[str] = None
    embedding_text: Optional[str] = None


class PestCreate(PestBase):
    pass


class PestUpdate(BaseModel):
    name: Optional[str] = None
    latin_name: Optional[str] = None
    category: Optional[str] = None
    affected_plants: Optional[str] = None
    symptoms: Optional[str] = None
    cause: Optional[str] = None
    prevention: Optional[str] = None
    severity: Optional[str] = None
    image_url: Optional[str] = None
    embedding_text: Optional[str] = None


class PestResponse(PestBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PestListResponse(PaginatedResponse):
    items: List[PestResponse]


# ═══════════════════════════════════════════════════════════
# 养护任务
# ═══════════════════════════════════════════════════════════

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    task_type: Optional[str] = None
    status: str = "pending"
    priority: int = 0
    location: Optional[str] = None
    plant_id: Optional[int] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None
    remark: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    location: Optional[str] = None
    plant_id: Optional[int] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    remark: Optional[str] = None


class TaskResponse(TaskBase):
    id: int
    created_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskListResponse(PaginatedResponse):
    items: List[TaskResponse]


# ═══════════════════════════════════════════════════════════
# 工单
# ═══════════════════════════════════════════════════════════

class WorkOrderBase(BaseModel):
    order_no: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    order_type: Optional[str] = None
    status: str = "pending"
    priority: int = 0
    location: Optional[str] = None
    reporter_id: Optional[int] = None
    assigned_to: Optional[int] = None
    task_id: Optional[int] = None
    images: List[str] = []
    cost: float = 0.0
    resolution: Optional[str] = None
    due_date: Optional[datetime] = None
    remark: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    location: Optional[str] = None
    assigned_to: Optional[int] = None
    task_id: Optional[int] = None
    images: Optional[List[str]] = None
    cost: Optional[float] = None
    resolution: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[int] = None
    remark: Optional[str] = None


class WorkOrderResponse(WorkOrderBase):
    id: int
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkOrderListResponse(PaginatedResponse):
    items: List[WorkOrderResponse]


# ═══════════════════════════════════════════════════════════
# 无人机飞行
# ═══════════════════════════════════════════════════════════

class DroneFlightBase(BaseModel):
    flight_no: str = Field(..., min_length=1, max_length=50)
    mission_type: Optional[str] = None
    status: str = "scheduled"
    drone_model: Optional[str] = None
    operator_id: Optional[int] = None
    area: Optional[str] = None
    coverage_area_sqm: float = 0.0
    flight_duration_min: float = 0.0
    images_captured: int = 0
    pest_detections: List[Any] = []
    flight_path: List[Any] = []


class DroneFlightCreate(DroneFlightBase):
    pass


class DroneFlightUpdate(BaseModel):
    mission_type: Optional[str] = None
    status: Optional[str] = None
    drone_model: Optional[str] = None
    operator_id: Optional[int] = None
    area: Optional[str] = None
    coverage_area_sqm: Optional[float] = None
    flight_duration_min: Optional[float] = None
    images_captured: Optional[int] = None
    pest_detections: Optional[List[Any]] = None
    flight_path: Optional[List[Any]] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class DroneFlightResponse(DroneFlightBase):
    id: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# 知识库检索
# ═══════════════════════════════════════════════════════════

class KBQueryRequest(BaseModel):
    """知识库查询请求"""
    keyword: str = Field(..., min_length=1, description="搜索关键词")
    category: Optional[str] = Field(None, description="筛选分类")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AIQARequest(BaseModel):
    """AI 问答请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    context_type: Optional[str] = Field(default="all", description="检索范围：plant/pest/all")


class AIQAResponse(BaseModel):
    """AI 问答响应"""
    question: str
    answer: str
    references: List[dict] = []
    confidence: float = 0.0


class RAGRetrieveRequest(BaseModel):
    """RAG 检索请求"""
    query: str = Field(..., min_length=1, description="检索查询文本")
    top_k: int = Field(default=5, ge=1, le=50)
    search_type: str = Field(default="all", description="检索类型：plant/pest/all")


class RAGRetrieveResponse(BaseModel):
    """RAG 检索响应"""
    query: str
    results: List[dict]
    total: int


# ═══════════════════════════════════════════════════════════
# 报表
# ═══════════════════════════════════════════════════════════

class ReportRequest(BaseModel):
    """报表请求"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    group_by: str = Field(default="month", description="聚合粒度：day/week/month")


class PestTrendItem(BaseModel):
    """病虫害趋势项"""
    period: str
    pest_name: str
    count: int
    severity: Optional[str] = None


class PestTrendResponse(BaseModel):
    items: List[PestTrendItem]
    total_detections: int
    period_range: str


class CostItem(BaseModel):
    """养护成本项"""
    period: str
    order_type: str
    total_cost: float
    order_count: int


class CostReportResponse(BaseModel):
    items: List[CostItem]
    total_cost: float
    total_orders: int
    period_range: str


class CoverageItem(BaseModel):
    """巡检覆盖项"""
    period: str
    area: str
    total_area_sqm: float
    flight_count: int
    images_total: int


class CoverageReportResponse(BaseModel):
    items: List[CoverageItem]
    total_area_sqm: float
    total_flights: int
    period_range: str
