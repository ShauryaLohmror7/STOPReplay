"""Optional fail-closed semantic review after deterministic evidence validation.

The verifier is trusted application code, never a field accepted from model output.
Its accuracy must be evaluated separately; citations alone do not prove entailment.
"""

from dataclasses import dataclass
from typing import Callable

from .models import AnalysisError, AnalysisRequest, AnalysisResult


@dataclass(frozen=True)
class SemanticVerdict:
    supported: bool
    explanation: str


SemanticVerifier = Callable[[AnalysisRequest, AnalysisResult], SemanticVerdict]


def verify_result(request: AnalysisRequest, result: AnalysisResult,
                  verifier: SemanticVerifier) -> None:
    """Review statement, uncertainty AND reason, including no-change explanations."""
    try:
        verdict = verifier(request, result)
    except Exception:
        raise AnalysisError("provider_failure", "Semantic verification failed; result withheld.") from None
    if (not isinstance(verdict, SemanticVerdict) or verdict.supported is not True
            or not isinstance(verdict.explanation, str) or not verdict.explanation.strip()):
        raise AnalysisError("invalid_output", "Semantic support was not established; result withheld.")
