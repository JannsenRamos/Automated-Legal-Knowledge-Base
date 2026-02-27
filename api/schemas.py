from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LegalMetadata(BaseModel):
    source_file: str
    jurisdiction: str    # "PH" or "HK"
    corpus_category: str # "wages", "contracts", etc.
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class LegalOrdinanceChunk(BaseModel):
    jurisdiction: str
    section_id: str      
    title: str
    content: str
    is_repealed: bool = False
    metadata: LegalMetadata

class ContractClause(BaseModel):
    category: str      # wages, hours, benefits, etc.
    original_text: str # The raw text from the contract
    risk_score: str = "Pending"
    rationale: str = ""

class ClauseAnalysis(BaseModel):
    category: str
    risk_score: float
    confidence: float
    violation_type: str
    extracted_text: str
    rationale: str = ""

class FullContractReport(BaseModel):
    total_risk: float
    analysis: List[ClauseAnalysis]
    status: str = "Completed"