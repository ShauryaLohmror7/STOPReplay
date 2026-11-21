"""Provisional analysis-only contracts; see docs/analysis-handoff.md."""

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Protocol

SCHEMA_VERSION = "analysis-proposal-v1.1"


class AnalysisError(Exception):
    """An explicit, serializable failure. A failed call produces no finding."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class ModelRefusal(Exception):
    """The shared adapter should translate a provider refusal to this exception."""


@dataclass(frozen=True)
class Event:
    run_id: str
    event_id: str
    sequence: int
    source_ref: str
    text: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Event":
        fields = {"run_id", "event_id", "sequence", "source_ref", "text"}
        if not isinstance(value, Mapping) or set(value) != fields:
            raise AnalysisError("invalid_input", "Event must contain exactly the five shared fields.")
        event = cls(**value)
        event.validate()
        return event

    def validate(self) -> None:
        for name in ("run_id", "event_id", "source_ref", "text"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise AnalysisError("invalid_input", f"Event {name} must be a nonempty string.")
        if type(self.sequence) is not int or self.sequence < 1:
            raise AnalysisError("invalid_input", "Event sequence must be a positive integer.")


@dataclass(frozen=True)
class Citation:
    event_id: str
    source_ref: str
    quote: str


@dataclass(frozen=True)
class Finding:
    finding_id: str
    finding_index: int
    run_id: str
    analysis_id: str
    sequence: int
    statement: str
    kind: Literal["observation", "inference"]
    status: Literal["supported", "unresolved"]
    evidence: tuple[Citation, ...]
    revises: str | None
    uncertainty: str | None


@dataclass(frozen=True)
class RuntimeMetadata:
    provider: str
    model_version: str
    prompt_version: str
    # JSON text keeps the metadata immutable and supports nested configuration.
    parameters_json: str = "{}"


@dataclass(frozen=True)
class AnalysisRequest:
    analysis_id: str
    event: Event
    previous_events: tuple[Event, ...]
    previous_findings: tuple[Finding, ...]


class ModelAdapter(Protocol):
    """Local seam for Shaurya's future shared adapter, not a provider client."""

    metadata: RuntimeMetadata

    def generate(self, request: AnalysisRequest) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class AnalysisResult:
    run_id: str
    analysis_id: str
    event_id: str
    sequence: int
    outcome: Literal["new", "revision", "conflict", "no_change"]
    finding: Finding | None
    reason: str
    runtime: RuntimeMetadata | None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        import json

        value = asdict(self)
        if value["runtime"] is not None:
            value["runtime"]["parameters"] = json.loads(value["runtime"].pop("parameters_json"))
        return value
