from typing import List
from typing_extensions import TypedDict

class TranscriptionSegment(TypedDict):
    speaker: str
    text: str

class SingleCallAnalysis(TypedDict):
    call_title: str
    compliance_score: float
    transcription: List[TranscriptionSegment]
    detailed_analysis: str
    recommendations: str
    contragent: str

class CallsList(TypedDict):
    call_name: str
    score: float
    text: str

class SingleManagerSummary(TypedDict):
    manager_name: str
    all_score: List[CallsList]
    date: str
    total_calls: int
    summary: str