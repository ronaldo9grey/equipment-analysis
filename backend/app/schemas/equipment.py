from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class AnalysisRecordBase(BaseModel):
    file_name: str
    file_size: int
    file_type: str
    table_count: int = 0
    record_count: int = 0
    status: str = "pending"

class AnalysisRecordCreate(AnalysisRecordBase):
    pass

class AnalysisRecordResponse(AnalysisRecordBase):
    id: str
    table_name: Optional[str] = None
    source_record_id: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TableInfo(BaseModel):
    table_name: str
    columns: List[str]
    row_count: int
    preview: List[Dict[str, Any]]

class FileParseResult(BaseModel):
    file_name: str
    file_size: int
    file_type: str
    tables: List[TableInfo]
    total_records: int
    parsed_at: str

class AnalyzeRequest(BaseModel):
    record_id: str
    table_name: Optional[str] = None
    query: Optional[str] = None
    use_local_model: bool = False

class AnalyzeResponse(BaseModel):
    record_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    message: str
