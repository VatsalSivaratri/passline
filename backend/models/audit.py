from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import uuid


class FacilityInfo(BaseModel):
    state: str
    facility_type: str  # restaurant | retail | office | medical | hotel | other
    building_age: str   # pre-1992 | 1992-2012 | post-2012
    recent_renovation: bool
    renovation_cost: Optional[float] = None
    parking_spaces: int = 0


class RemediationCost(BaseModel):
    low: float
    high: float


class Violation(BaseModel):
    violation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module_id: str
    module_type: str
    rule_id: str
    code: str
    element: str
    finding: str
    severity: str  # critical | high | medium | low
    measurement_value: Optional[Any] = None
    measurement_unit: Optional[str] = None
    required_value: Optional[Any] = None
    calibrated: bool = False
    confidence: float = 0.5
    remediation_cost: RemediationCost


class ViolationWithNarrative(Violation):
    description: str = ""
    remediation: str = ""
    priority_rationale: str = ""


class AuditModule(BaseModel):
    module_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module_type: str
    status: str = "uploading"  # uploading | extracting_frames | classifying | analyzing | checking_compliance | complete | error
    progress: int = 0
    video_path: Optional[str] = None
    key_frames: List[str] = []
    gemini_analysis: Optional[dict] = None
    depth_measurements: Optional[dict] = None
    calibrated: bool = False
    violations: List[dict] = []
    annotated_frames: List[str] = []
    depth_map_frames: List[str] = []
    error_message: Optional[str] = None
    warnings: List[str] = []


class ReportSummary(BaseModel):
    overall_score: float = 0.0
    total_violations: int = 0
    critical_violations: int = 0
    modules_audited: int = 0
    estimated_remediation_total: RemediationCost = RemediationCost(low=0, high=0)
    generated_at: Optional[datetime] = None
    pdf_path: Optional[str] = None


class AuditDocument(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    facility: Optional[FacilityInfo] = None
    applicable_rules: List[str] = []
    modules: List[dict] = []
    report: Optional[dict] = None


# Request/Response models

class QuestionnaireRequest(BaseModel):
    state: str
    facility_type: str
    building_age: str
    recent_renovation: bool
    renovation_cost: Optional[float] = None
    parking_spaces: int = 0


class QuestionnaireResponse(BaseModel):
    audit_id: str
    applicable_modules: List[str]
    rule_count: int


class CreateModuleRequest(BaseModel):
    module_type: str


class CreateModuleResponse(BaseModel):
    module_id: str
    instructions: str


class ModuleStatusResponse(BaseModel):
    status: str
    progress: int
    module_type: Optional[str] = None
    violations_found: Optional[int] = None
    error_message: Optional[str] = None


class ModuleResultsResponse(BaseModel):
    module_type: str
    gemini_analysis: Optional[dict] = None
    depth_measurements: Optional[dict] = None
    calibrated: bool
    violations: List[dict]
    annotated_frames: List[str]
    depth_map_frames: List[str]
    warnings: List[str] = []


class ReportResponse(BaseModel):
    overall_score: float
    total_violations: int
    critical_violations: int
    modules_audited: int
    violations: List[dict]
    estimated_remediation_total: RemediationCost
    pdf_url: Optional[str] = None
