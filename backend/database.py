"""
数据库连接与表结构定义
SQLite 数据库，使用 SQLAlchemy ORM
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text,
    DateTime, ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import enum

DATABASE_URL = "sqlite:///./smart_garden.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── 枚举类型 ─────────────────────────────────────────────

class TaskStatus(str, enum.Enum):
    PENDING = "pending"           # 待派发
    ASSIGNED = "assigned"         # 已派发
    IN_PROGRESS = "in_progress"   # 处置中
    COMPLETED = "completed"       # 已处置
    VERIFIED = "verified"         # 已验收
    REJECTED = "rejected"         # 已驳回


class PestSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FlightStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_FLIGHT = "in_flight"
    COMPLETED = "completed"
    ABORTED = "aborted"


# ─── 6 张业务表 ──────────────────────────────────────────

class Plant(Base):
    """苗木/植物知识库"""
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False, comment="植物名称")
    latin_name = Column(String(200), comment="拉丁学名")
    category = Column(String(50), comment="分类：乔木/灌木/草本/水生")
    family = Column(String(100), comment="科属")
    traits = Column(Text, comment="形态特征")
    care_standard = Column(Text, comment="养护标准（浇水/施肥/修剪/病虫害防治）")
    suitable_regions = Column(String(200), comment="适宜区域")
    image_url = Column(String(500), comment="图片链接")
    embedding_text = Column(Text, comment="用于 RAG 检索的文本向量源文本")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Pest(Base):
    """病虫害知识库"""
    __tablename__ = "pests"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False, comment="病虫害名称")
    latin_name = Column(String(200), comment="拉丁学名")
    category = Column(String(50), comment="类型：病害/虫害/草害")
    affected_plants = Column(Text, comment="危害植物")
    symptoms = Column(Text, comment="症状描述")
    cause = Column(Text, comment="发病原因")
    prevention = Column(Text, comment="防治方法")
    severity = Column(String(20), default=PestSeverity.MEDIUM.value, comment="严重程度")
    image_url = Column(String(500), comment="图片链接")
    embedding_text = Column(Text, comment="RAG 检索向量源文本")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Task(Base):
    """养护任务"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    title = Column(String(200), nullable=False, comment="任务标题")
    description = Column(Text, comment="任务描述")
    task_type = Column(String(50), comment="类型：浇水/施肥/修剪/病虫害防治/巡检")
    status = Column(String(20), default=TaskStatus.PENDING.value, comment="任务状态")
    priority = Column(Integer, default=0, comment="优先级 0-普通 1-紧急 2-特急")
    location = Column(String(200), comment="作业位置")
    plant_id = Column(Integer, ForeignKey("plants.id"), nullable=True, comment="关联植物")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, comment="指派人员")
    due_date = Column(DateTime, nullable=True, comment="截止日期")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    plant = relationship("Plant", lazy="joined")
    assignee = relationship("User", foreign_keys=[assigned_to], lazy="joined")


class WorkOrder(Base):
    """工单"""
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    order_no = Column(String(50), unique=True, nullable=False, index=True, comment="工单编号")
    title = Column(String(200), nullable=False, comment="工单标题")
    description = Column(Text, comment="工单描述")
    order_type = Column(String(50), comment="类型：养护/维修/巡检/应急")
    status = Column(String(20), default=TaskStatus.PENDING.value, comment="工单状态")
    priority = Column(Integer, default=0, comment="优先级")
    location = Column(String(200), comment="位置")
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="报单人")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, comment="处置人")
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, comment="关联任务")
    images = Column(JSON, default=list, comment="现场图片列表")
    cost = Column(Float, default=0.0, comment="处置成本")
    resolution = Column(Text, comment="处置方案")
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="验收人")
    remark = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    reporter = relationship("User", foreign_keys=[reporter_id], lazy="joined")
    assignee = relationship("User", foreign_keys=[assigned_to], lazy="joined")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="joined")
    task = relationship("Task", lazy="joined")


class DroneFlight(Base):
    """无人机巡检飞行记录"""
    __tablename__ = "drone_flights"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    flight_no = Column(String(50), unique=True, nullable=False, index=True, comment="飞行编号")
    mission_type = Column(String(50), comment="任务类型：常规巡检/病虫害扫描/测绘")
    status = Column(String(20), default=FlightStatus.SCHEDULED.value, comment="飞行状态")
    drone_model = Column(String(100), comment="无人机型号")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="操作员")
    area = Column(String(200), comment="巡检区域")
    coverage_area_sqm = Column(Float, default=0.0, comment="覆盖面积(m²)")
    flight_duration_min = Column(Float, default=0.0, comment="飞行时长(分钟)")
    images_captured = Column(Integer, default=0, comment="拍摄图片数")
    pest_detections = Column(JSON, default=list, comment="病虫害检测结果")
    flight_path = Column(JSON, default=list, comment="飞行轨迹坐标")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    operator = relationship("User", lazy="joined")


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, comment="真实姓名")
    role = Column(String(30), default="worker", comment="角色：admin/manager/worker/reporter")
    phone = Column(String(20), comment="电话")
    email = Column(String(100), comment="邮箱")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ─── 依赖注入 ─────────────────────────────────────────────

def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表 + 种子数据）"""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 检查是否已有数据，避免重复初始化
        if db.query(User).count() == 0:
            seed_users(db)
        if db.query(Plant).count() == 0:
            seed_plants(db)
        if db.query(Pest).count() == 0:
            seed_pests(db)
        db.commit()
    finally:
        db.close()


def seed_users(db):
    users = [
        User(username="admin", name="系统管理员", role="admin", phone="13800000001"),
        User(username="manager", name="园林经理", role="manager", phone="13800000002"),
        User(username="worker1", name="养护员张三", role="worker", phone="13800000003"),
        User(username="worker2", name="养护员李四", role="worker", phone="13800000004"),
        User(username="reporter", name="巡检员王五", role="reporter", phone="13800000005"),
    ]
    db.add_all(users)
    db.flush()


def seed_plants(db):
    plants = [
        Plant(
            name="银杏", latin_name="Ginkgo biloba", category="乔木", family="银杏科",
            traits="落叶乔木，叶扇形，秋叶金黄色，树形优美。",
            care_standard="喜光，耐寒，适应性强。春季施肥一次，夏季干旱时浇水，秋季扫落叶。病虫害较少，注意防治叶枯病。",
            suitable_regions="全国大部分地区", embedding_text="银杏 Ginkgo biloba 落叶乔木 秋叶金黄 耐寒 适应性强"
        ),
        Plant(
            name="香樟", latin_name="Cinnamomum camphora", category="乔木", family="樟科",
            traits="常绿乔木，树冠广卵形，枝叶茂密，有樟脑香气。",
            care_standard="喜温暖湿润气候，不耐寒。春季修剪整形，夏季注意防虫（樟巢螟），每年施肥2次。",
            suitable_regions="长江流域及以南", embedding_text="香樟 Cinnamomum camphora 常绿乔木 樟脑香气 温暖湿润 防樟巢螟"
        ),
        Plant(
            name="月季", latin_name="Rosa chinensis", category="灌木", family="蔷薇科",
            traits="常绿或半常绿灌木，花色丰富，花期长。",
            care_standard="喜光，喜肥沃排水良好的土壤。生长期每半月施肥一次，花后及时修剪。重点防治白粉病、黑斑病和蚜虫。",
            suitable_regions="全国", embedding_text="月季 Rosa chinensis 灌木 花色丰富 花期长 防治白粉病黑斑病蚜虫"
        ),
        Plant(
            name="草坪（高羊茅）", latin_name="Festuca arundinacea", category="草本", family="禾本科",
            traits="冷季型草坪草，耐践踏，绿色期长。",
            care_standard="定期修剪保持高度5-8cm，春秋季施肥，夏季注意浇水和防治褐斑病。",
            suitable_regions="长江以北", embedding_text="草坪 高羊茅 Festuca arundinacea 冷季型 耐践踏 定期修剪 防治褐斑病"
        ),
    ]
    db.add_all(plants)


def seed_pests(db):
    pests = [
        Pest(
            name="白粉病", latin_name="Erysiphales", category="病害",
            affected_plants="月季、紫薇、瓜叶菊等多种花卉",
            symptoms="叶片、嫩梢出现白色粉状物，严重时叶片卷曲、枯黄。",
            cause="高湿度、通风不良、氮肥过多。",
            prevention="合理修剪通风，增施磷钾肥。发病初期喷施三唑酮或多菌灵。",
            severity="medium", embedding_text="白粉病 月季 紫薇 白色粉状物 叶片卷曲 高湿度 三唑酮 多菌灵"
        ),
        Pest(
            name="蚜虫", latin_name="Aphidoidea", category="虫害",
            affected_plants="月季、菊花、桃树等多种植物",
            symptoms="群集于嫩梢、叶背刺吸汁液，造成叶片卷曲变形，分泌蜜露诱发煤污病。",
            cause="温暖干燥气候繁殖快，天敌减少。",
            prevention="保护瓢虫等天敌，喷施吡虫啉或啶虫脒。",
            severity="high", embedding_text="蚜虫 月季 菊花 桃树 嫩梢 叶片卷曲 蜜露 煤污病 吡虫啉"
        ),
        Pest(
            name="樟巢螟", latin_name="Orthaga achatina", category="虫害",
            affected_plants="香樟",
            symptoms="幼虫吐丝缀叶成巢，取食叶片，严重时整株叶片被吃光。",
            cause="越冬基数大，防治不及时。",
            prevention="冬季清园清除虫巢，幼虫期喷施高效氯氰菊酯。",
            severity="high", embedding_text="樟巢螟 香樟 吐丝缀叶 吃光叶片 高效氯氰菊酯"
        ),
    ]
    db.add_all(pests)
