"""
知识库路由模块 —— 苗木/病虫害/养护标准查询 + AI问答 + RAG检索
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import math

from database import get_db, Plant, Pest
from models import (
    PlantCreate, PlantUpdate, PlantResponse, PlantListResponse,
    PestCreate, PestUpdate, PestResponse, PestListResponse,
    KBQueryRequest, AIQARequest, AIQAResponse,
    RAGRetrieveRequest, RAGRetrieveResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/v1/kb", tags=["知识库"])


# ─── 辅助 ─────────────────────────────────────────────────

def _simulate_rag(query: str, db: Session, search_type: str, top_k: int) -> list[dict]:
    """模拟 RAG 检索：基于关键词匹配返回相关知识条目"""
    results = []

    if search_type in ("plant", "all"):
        plants = db.query(Plant).filter(
            or_(
                Plant.name.contains(query),
                Plant.embedding_text.contains(query),
                Plant.care_standard.contains(query),
                Plant.traits.contains(query),
            )
        ).limit(top_k).all()
        for p in plants:
            results.append({
                "type": "plant",
                "id": p.id,
                "name": p.name,
                "latin_name": p.latin_name,
                "category": p.category,
                "snippet": p.care_standard[:200] if p.care_standard else p.traits[:200] if p.traits else "",
                "score": 0.85,
            })

    if search_type in ("pest", "all"):
        pests = db.query(Pest).filter(
            or_(
                Pest.name.contains(query),
                Pest.embedding_text.contains(query),
                Pest.symptoms.contains(query),
                Pest.prevention.contains(query),
            )
        ).limit(top_k).all()
        for p in pests:
            results.append({
                "type": "pest",
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "symptom_snippet": p.symptoms[:200] if p.symptoms else "",
                "prevention_snippet": p.prevention[:200] if p.prevention else "",
                "score": 0.82,
            })

    # 按模拟分数排序，取 top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def _simulate_ai_answer(question: str, references: list[dict]) -> str:
    """模拟 AI 回答（基于检索到的参考资料生成答案）"""
    if not references:
        return "抱歉，未找到与您问题相关的知识库条目。请尝试更换关键词搜索。"

    ref = references[0]
    if ref["type"] == "plant":
        return (
            f"根据知识库检索，与您问题最相关的是「{ref['name']}」（{ref.get('latin_name', '')}），"
            f"属于{ref.get('category', '')}类植物。"
            f"养护要点：{ref.get('snippet', '请查阅完整养护标准。')}"
        )
    else:
        return (
            f"根据知识库检索，与您问题最相关的是「{ref['name']}」，"
            f"属于{ref.get('category', '')}类型。"
            f"防治方法：{ref.get('prevention_snippet', '请查阅完整防治方案。')}"
        )


# ═══════════════════════════════════════════════════════════
# 苗木 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/plants", response_model=PlantListResponse, summary="苗木列表")
def list_plants(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="植物分类"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Plant)
    if keyword:
        query = query.filter(
            or_(
                Plant.name.contains(keyword),
                Plant.latin_name.contains(keyword),
                Plant.traits.contains(keyword),
            )
        )
    if category:
        query = query.filter(Plant.category == category)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    items = query.order_by(Plant.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PlantListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[PlantResponse.model_validate(p) for p in items],
    )


@router.get("/plants/{plant_id}", response_model=PlantResponse, summary="苗木详情")
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"苗木 id={plant_id} 不存在")
    return PlantResponse.model_validate(plant)


@router.post("/plants", response_model=PlantResponse, status_code=201, summary="新增苗木")
def create_plant(data: PlantCreate, db: Session = Depends(get_db)):
    plant = Plant(**data.model_dump())
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return PlantResponse.model_validate(plant)


@router.put("/plants/{plant_id}", response_model=PlantResponse, summary="更新苗木")
def update_plant(plant_id: int, data: PlantUpdate, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"苗木 id={plant_id} 不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plant, key, value)
    db.commit()
    db.refresh(plant)
    return PlantResponse.model_validate(plant)


@router.delete("/plants/{plant_id}", response_model=MessageResponse, summary="删除苗木")
def delete_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"苗木 id={plant_id} 不存在")
    db.delete(plant)
    db.commit()
    return MessageResponse(message="删除成功", detail=f"苗木 {plant.name} 已删除")


# ═══════════════════════════════════════════════════════════
# 病虫害 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/pests", response_model=PestListResponse, summary="病虫害列表")
def list_pests(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="类型：病害/虫害/草害"),
    severity: Optional[str] = Query(None, description="严重程度：low/medium/high/critical"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Pest)
    if keyword:
        query = query.filter(
            or_(
                Pest.name.contains(keyword),
                Pest.symptoms.contains(keyword),
                Pest.affected_plants.contains(keyword),
            )
        )
    if category:
        query = query.filter(Pest.category == category)
    if severity:
        query = query.filter(Pest.severity == severity)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    items = query.order_by(Pest.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PestListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[PestResponse.model_validate(p) for p in items],
    )


@router.get("/pests/{pest_id}", response_model=PestResponse, summary="病虫害详情")
def get_pest(pest_id: int, db: Session = Depends(get_db)):
    pest = db.query(Pest).filter(Pest.id == pest_id).first()
    if not pest:
        raise HTTPException(status_code=404, detail=f"病虫害 id={pest_id} 不存在")
    return PestResponse.model_validate(pest)


@router.post("/pests", response_model=PestResponse, status_code=201, summary="新增病虫害")
def create_pest(data: PestCreate, db: Session = Depends(get_db)):
    pest = Pest(**data.model_dump())
    db.add(pest)
    db.commit()
    db.refresh(pest)
    return PestResponse.model_validate(pest)


@router.put("/pests/{pest_id}", response_model=PestResponse, summary="更新病虫害")
def update_pest(pest_id: int, data: PestUpdate, db: Session = Depends(get_db)):
    pest = db.query(Pest).filter(Pest.id == pest_id).first()
    if not pest:
        raise HTTPException(status_code=404, detail=f"病虫害 id={pest_id} 不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pest, key, value)
    db.commit()
    db.refresh(pest)
    return PestResponse.model_validate(pest)


@router.delete("/pests/{pest_id}", response_model=MessageResponse, summary="删除病虫害")
def delete_pest(pest_id: int, db: Session = Depends(get_db)):
    pest = db.query(Pest).filter(Pest.id == pest_id).first()
    if not pest:
        raise HTTPException(status_code=404, detail=f"病虫害 id={pest_id} 不存在")
    db.delete(pest)
    db.commit()
    return MessageResponse(message="删除成功", detail=f"病虫害 {pest.name} 已删除")


# ═══════════════════════════════════════════════════════════
# 养护标准查询
# ═══════════════════════════════════════════════════════════

@router.get("/care-standards", summary="养护标准查询")
def get_care_standards(
    plant_name: Optional[str] = Query(None, description="植物名称"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """按植物名称查询养护标准"""
    query = db.query(Plant)
    if plant_name:
        query = query.filter(Plant.name.contains(plant_name))

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    plants = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [
        {
            "id": p.id,
            "name": p.name,
            "latin_name": p.latin_name,
            "category": p.category,
            "care_standard": p.care_standard,
            "suitable_regions": p.suitable_regions,
        }
        for p in plants
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": items,
    }


# ═══════════════════════════════════════════════════════════
# AI 问答
# ═══════════════════════════════════════════════════════════

@router.post("/ai-qa", response_model=AIQAResponse, summary="AI 智能问答")
def ai_qa(request: AIQARequest, db: Session = Depends(get_db)):
    """
    AI 问答接口：基于知识库内容回答问题。
    实际项目可接入 LLM（如 GPT / 文心一言），当前为基于关键词匹配的模拟实现。
    """
    references = _simulate_rag(
        query=request.question,
        db=db,
        search_type=request.context_type or "all",
        top_k=5,
    )
    answer = _simulate_ai_answer(request.question, references)
    confidence = 0.85 if references else 0.1

    return AIQAResponse(
        question=request.question,
        answer=answer,
        references=references,
        confidence=confidence,
    )


# ═══════════════════════════════════════════════════════════
# RAG 检索
# ═══════════════════════════════════════════════════════════

@router.post("/rag-retrieve", response_model=RAGRetrieveResponse, summary="RAG 语义检索")
def rag_retrieve(request: RAGRetrieveRequest, db: Session = Depends(get_db)):
    """
    RAG 检索接口：基于查询文本从知识库中检索相关内容。
    实际项目应使用向量数据库 + Embedding 模型，当前为关键词匹配模拟实现。
    """
    results = _simulate_rag(
        query=request.query,
        db=db,
        search_type=request.search_type,
        top_k=request.top_k,
    )

    return RAGRetrieveResponse(
        query=request.query,
        results=results,
        total=len(results),
    )
