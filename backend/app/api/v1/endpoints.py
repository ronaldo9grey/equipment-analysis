from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime
import logging
import io

from app.core.database import get_db, init_db, AnalysisRecord, TableData
from app.core.config import settings
from app.schemas.equipment import (
    AnalysisRecordResponse,
    AnalyzeRequest,
    AnalyzeResponse
)
from app.services.file_parser import get_parser
from app.services.ai_analyzer import get_analyzer
from app.services.simulation_engine import simulation_engine

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".mdb", ".accdb", ".bak", ".sql", ".mysql"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "upload_dir": settings.UPLOAD_DIR
    }


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return "." in filename and \
           os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename: str) -> str:
    """获取文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    type_map = {
        ".mdb": "mdb",
        ".accdb": "mdb",
        ".bak": "sqlserver_bak",
        ".sql": "mysql_sql",
        ".mysql": "mysql_sql"
    }
    return type_map.get(ext, "unknown")


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()


@router.post("/upload", response_model=AnalysisRecordResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传并解析数据库文件"""
    try:
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        file_size = 0
        file_location = None

        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
            )

        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        file_location = os.path.join(
            settings.UPLOAD_DIR,
            f"{file_id}{file_ext}"
        )

        logger.info(f"开始保存文件: {file.filename}, 大小: {file_size} bytes")

        with open(file_location, "wb") as f:
            f.write(content)

        logger.info(f"文件保存成功: {file_location}, 实际大小: {os.path.getsize(file_location)} bytes")

        file_type = get_file_type(file.filename)

        logger.info(f"开始解析文件: {file_location}")

        parser = get_parser(file_location)
        parse_result = parser.parse(file_location)

        logger.info(f"解析完成: {len(parse_result.get('tables', []))} 个表, {parse_result.get('total_records', 0)} 条记录")

        record = AnalysisRecord(
            id=file_id,
            file_name=file.filename,
            file_size=file_size,
            file_type=file_type,
            table_count=len(parse_result.get("tables", [])),
            record_count=parse_result.get("total_records", 0),
            status="completed"
        )
        db.add(record)

        for table_info in parse_result.get("tables", []):
            table_data = TableData(
                record_id=file_id,
                table_name=table_info.get("table_name"),
                columns=table_info.get("columns"),
                data=table_info.get("preview"),
                row_count=table_info.get("row_count")
            )
            db.add(table_data)

        db.commit()

        return AnalysisRecordResponse(
            id=record.id,
            file_name=record.file_name,
            file_size=record.file_size,
            file_type=record.file_type,
            table_count=record.table_count,
            record_count=record.record_count,
            status=record.status,
            analysis_result=None,
            error_message=None,
            created_at=record.created_at,
            completed_at=record.completed_at
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        if file_location and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records", response_model=List[AnalysisRecordResponse])
async def get_records(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取分析记录列表"""
    records = db.query(AnalysisRecord).order_by(
        AnalysisRecord.created_at.desc()
    ).offset(skip).limit(limit).all()

    return [
        AnalysisRecordResponse(
            id=r.id,
            file_name=r.file_name,
            file_size=r.file_size,
            file_type=r.file_type,
            table_count=r.table_count,
            record_count=r.record_count,
            status=r.status,
            table_name=r.table_name,
            analysis_result=r.analysis_result,
            error_message=r.error_message,
            created_at=r.created_at,
            completed_at=r.completed_at
        )
        for r in records
    ]


@router.get("/records/{record_id}", response_model=AnalysisRecordResponse)
async def get_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """获取单条分析记录"""
    record = db.query(AnalysisRecord).filter(
        AnalysisRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return AnalysisRecordResponse(
        id=record.id,
        file_name=record.file_name,
        file_size=record.file_size,
        file_type=record.file_type,
        table_count=record.table_count,
        record_count=record.record_count,
        status=record.status,
        table_name=record.table_name,
        analysis_result=record.analysis_result,
        error_message=record.error_message,
        created_at=record.created_at,
        completed_at=record.completed_at
    )


@router.get("/records/{record_id}/tables")
async def get_record_tables(
    record_id: str,
    db: Session = Depends(get_db)
):
    """获取记录关联的表列表"""
    tables = db.query(TableData).filter(
        TableData.record_id == record_id
    ).all()

    return {
        "record_id": record_id,
        "tables": [
            {
                "table_name": t.table_name,
                "columns": t.columns,
                "row_count": t.row_count
            }
            for t in tables
        ]
    }


@router.get("/records/{record_id}/tables/{table_name}")
async def get_table_data(
    record_id: str,
    table_name: str,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db)
):
    """获取指定表的详细数据"""
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    
    actual_record_id = record_id
    if record and record.source_record_id:
        actual_record_id = record.source_record_id
    
    table_data = db.query(TableData).filter(
        TableData.record_id == actual_record_id,
        TableData.table_name == table_name
    ).first()

    if not table_data:
        raise HTTPException(status_code=404, detail="表不存在")

    all_data = table_data.data or []

    start = (page - 1) * page_size
    end = start + page_size
    page_data = all_data[start:end]

    return {
        "record_id": record_id,
        "table_name": table_name,
        "columns": table_data.columns,
        "row_count": table_data.row_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (table_data.row_count + page_size - 1) // page_size,
        "data": page_data
    }


@router.get("/records/{record_id}/tables/{table_name}/download")
async def download_table_data(
    record_id: str,
    table_name: str,
    db: Session = Depends(get_db)
):
    """下载表数据为Excel文件"""
    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(status_code=500, detail="pandas未安装，请运行: pip3 install pandas openpyxl")
    
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    
    actual_record_id = record_id
    if record and record.source_record_id:
        actual_record_id = record.source_record_id
    
    table_data = db.query(TableData).filter(
        TableData.record_id == actual_record_id,
        TableData.table_name == table_name
    ).first()

    if not table_data:
        raise HTTPException(status_code=404, detail=f"表不存在: record_id={actual_record_id}, table_name={table_name}")

    all_data = table_data.data or []
    
    if not all_data:
        raise HTTPException(status_code=404, detail="表中无数据")

    try:
        sheet_name = f"Sheet1"
        
        df = pd.DataFrame(all_data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        
        output.seek(0)
        
        from urllib.parse import quote
        
        filename = f"{table_name}_{record_id[:8]}.xlsx"
        encoded_filename = quote(filename)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f"attachment; filename={encoded_filename}"}
        )
    except Exception as e:
        logger.error(f"Excel生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Excel生成失败: {str(e)}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_data(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """使用AI分析数据"""
    try:
        logger.info(f"analyze请求参数: {request.record_id}, {request.query}, {request.use_local_model}, table_name: {request.table_name}")
        
        record = db.query(AnalysisRecord).filter(
            AnalysisRecord.id == request.record_id
        ).first()

        if not record:
            logger.warning(f"记录不存在: {request.record_id}")
            logger.warning(f"数据库中的记录ID列表: {[r.id for r in db.query(AnalysisRecord).all()]}")
            raise HTTPException(status_code=404, detail=f"记录不存在: {request.record_id}")

        # completed 或 analyzed 状态都可以再次分析
        if record.status not in ["completed", "analyzed"]:
            raise HTTPException(status_code=400, detail="数据尚未解析完成")

        logger.info(f"开始AI分析，记录状态: {record.status}")

        # 创建新的分析记录，保存历史
        new_record = AnalysisRecord(
            id=str(uuid.uuid4()),
            file_name=record.file_name,
            file_size=record.file_size,
            file_type=record.file_type,
            table_count=record.table_count,
            record_count=record.record_count,
            status="pending",
            table_name=request.table_name if request.table_name else None,
            analysis_type="table" if request.table_name else "general",
            source_record_id=request.record_id if request.table_name else None
        )
        db.add(new_record)
        db.flush()
        
        logger.info(f"新建记录: id={new_record.id}, table_name={new_record.table_name}, analysis_type={new_record.analysis_type}, source_record_id={new_record.source_record_id}")

        tables = db.query(TableData).filter(
            TableData.record_id == request.record_id
        ).all()

        if request.table_name:
            target_table = next((t for t in tables if t.table_name == request.table_name), None)
            if not target_table:
                raise HTTPException(status_code=404, detail=f"表 {request.table_name} 不存在")
            
            row_count = target_table.row_count or 0
            if row_count < 1000:
                table_data = target_table.data if target_table.data else []
                data_mode = "全量"
            else:
                table_data = target_table.data[:1000] if target_table.data else []
                data_mode = "采样"
            
            data = {
                "file_name": record.file_name,
                "table_name": target_table.table_name,
                "columns": target_table.columns,
                "row_count": row_count,
                "data": table_data,
                "data_mode": data_mode
            }
            analysis_type = "table"
            logger.info(f"分析特定表: {request.table_name}, 数据条数: {row_count}, 模式: {data_mode}")
        else:
            data = {
                "file_name": record.file_name,
                "total_records": record.record_count,
                "tables": [
                    {
                        "table_name": t.table_name,
                        "columns": t.columns,
                        "row_count": t.row_count,
                        "preview": t.data[:10] if t.data else []
                    }
                    for t in tables
                ]
            }
            analysis_type = "general"
            logger.info(f"分析整个文件，包含 {len(tables)} 个表")

        analyzer = get_analyzer(use_local_model=request.use_local_model)
        logger.info(f"调用AI分析器完成，准备分析")

        analysis_result = analyzer.analyze(
            data=data,
            user_query=request.query,
            analysis_type=analysis_type
        )
        logger.info(f"AI分析完成，结果状态: {analysis_result.get('status')}")

        new_record.analysis_result = analysis_result.get("result")
        new_record.completed_at = datetime.now()

        if analysis_result.get("status") == "success":
            new_record.status = "analyzed"
        else:
            new_record.status = "failed"
            new_record.error_message = analysis_result.get("message")

        db.commit()

        result_data = analysis_result.get("result")
        logger.info(f"准备返回响应: record_id={new_record.id}, status={new_record.status}, result_keys={list(result_data.keys()) if result_data else None}")

        response_data = {
            "record_id": new_record.id,
            "status": new_record.status,
            "result": result_data,
            "message": analysis_result.get("message", "分析完成")
        }
        
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response_data)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/records/{record_id}")
async def delete_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """删除分析记录"""
    record = db.query(AnalysisRecord).filter(
        AnalysisRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.query(TableData).filter(
        TableData.record_id == record_id
    ).delete()

    db.delete(record)
    db.commit()

    file_ext = os.path.splitext(record.file_name)[1]
    file_location = os.path.join(
        settings.UPLOAD_DIR,
        f"{record_id}{file_ext}"
    )
    if os.path.exists(file_location):
        os.remove(file_location)

    return {"message": "删除成功"}


@router.post("/simulation/start")
async def start_simulation(
    record_id: str,
    table_name: str,
    interval: int = 5,
    use_analysis_features: bool = True,
    db: Session = Depends(get_db)
):
    """启动数据模拟"""
    
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    actual_record_id = record_id
    if record.source_record_id:
        actual_record_id = record.source_record_id
    
    table_data = db.query(TableData).filter(
        TableData.record_id == actual_record_id,
        TableData.table_name == table_name
    ).first()
    
    if not table_data:
        raise HTTPException(status_code=404, detail="表不存在")
    
    columns = table_data.columns or []
    analysis_features = None
    
    if use_analysis_features and record.analysis_result:
        analysis_features = simulation_engine.extract_features_from_analysis(
            record.analysis_result
        )
    
    simulation_id = f"{record_id}_{table_name}"
    
    result = simulation_engine.start_simulation(
        simulation_id=simulation_id,
        columns=columns,
        interval=interval,
        analysis_features=analysis_features
    )
    
    return result


@router.post("/simulation/stop")
async def stop_simulation(simulation_id: str):
    """停止模拟"""
    result = simulation_engine.stop_simulation(simulation_id)
    return result


@router.get("/simulation/data")
async def get_simulation_data(
    simulation_id: str,
    row_count: int = 20
):
    """获取模拟数据"""
    
    status = simulation_engine.get_simulation_status(simulation_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="模拟不存在")
    
    columns = status.get('columns', [])
    analysis_features = status.get('analysis_features', {})
    
    data = simulation_engine.generate_simulation_data(
        columns=columns,
        row_count=row_count,
        analysis_features=analysis_features
    )
    
    return {
        "simulation_id": simulation_id,
        "status": status.get('status'),
        "data": data,
        "columns": columns,
        "data_count": len(data)
    }


@router.get("/simulation/status")
async def get_simulation_status(simulation_id: str):
    """获取模拟状态"""
    status = simulation_engine.get_simulation_status(simulation_id)
    
    if not status:
        return {
            "simulation_id": simulation_id,
            "status": "not_found",
            "message": "模拟不存在"
        }
    
    return {
        "simulation_id": simulation_id,
        "status": status.get('status'),
        "start_time": status.get('start_time'),
        "data_count": status.get('data_count', 0)
    }
