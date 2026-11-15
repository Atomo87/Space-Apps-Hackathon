from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Insight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["observation", "interpretation", "suggested_review"]
    title: str = Field(min_length=1, max_length=180)
    explanation: str = Field(min_length=1, max_length=1800)
    fact_ids: list[str] = Field(min_length=1, max_length=24)
    reference_ids: list[str] = Field(max_length=6)
    limitations: list[str] = Field(max_length=8)
    questions_for_farmer: list[str] = Field(max_length=4)


class GeneratedInsights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    insights: list[Insight] = Field(max_length=3)


class InsightsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [
        {"analysis_id": "00000000-0000-4000-8000-000000000001", "use_gemini": False},
        {"analysis_id": "00000000-0000-4000-8000-000000000001", "use_gemini": True}
    ]})
    analysis_id: UUID = Field(description="ID devolvido por POST /v1/analysis. O resultado e carregado do servidor.")
    use_gemini: bool = Field(default=False, description="Opt-in. So chama Gemini se habilitado, com chave e modelo configurados. Pode consumir cota.")


class Fact(BaseModel):
    id: str
    label: str
    path: str = Field(description="JSON Pointer no snapshot armazenado; raiz result ou inputs.")
    value: float | str | None
    unit: str | None = None
    source: str
    period: str | None = None
    limitations: list[str] = Field(default_factory=list)


class Reference(BaseModel):
    id: str
    document_id: str
    title: str
    url: str
    section: str
    version: str
    content_hash: str
    text: str


class InsightsResponse(BaseModel):
    analysis_id: UUID
    status: Literal["checked", "fallback", "insufficient_evidence"]
    generation_mode: Literal["gemini", "deterministic"]
    model: str | None
    prompt_version: str
    prompt_hash: str
    knowledge_version: str
    snapshot_hash: str
    cache_hit: bool = False
    insights: list[Insight]
    resolved_evidence: list[Fact]
    references: list[Reference]
    validation_notes: list[str]
    fallback_reason: str | None = None


class AnalysisResponse(BaseModel):
    # O contrato do senior e preservado; so acrescentamos metadados do snapshot.
    model_config = ConfigDict(extra="allow")
    analysis_id: UUID
    created_at: datetime
    expires_at: datetime
    engine_version: str
    catalog_version: str
    disclaimer: str
    diagnosis: dict[str, Any]
    strategies: list[dict[str, Any]]
    warnings: list[str]


class ApiProblem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    errors: list[dict[str, Any]] | None = None


class InsightsCapabilities(BaseModel):
    enabled: bool
    gemini_configured: bool
    default_mode: str
    max_gemini_attempts_per_analysis: int
    snapshot_ttl_hours: int
    prompt_version: str
    knowledge_version: str
    approved_chunks: int
