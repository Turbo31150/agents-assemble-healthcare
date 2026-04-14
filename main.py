"""
Agents Assemble Healthcare — Multi-agent orchestration for medical triage and diagnosis.
Hackathon: Healthcare AI Endgame | Target Prize: $25K
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import uuid
from datetime import datetime

app = FastAPI(
    title="Agents Assemble Healthcare",
    description="Multi-agent orchestration platform for healthcare AI",
    version="1.0.0",
)


# --- Models ---


class PatientIntakeRequest(BaseModel):
    patient_id: Optional[str] = None
    symptoms: List[str]
    age: int
    sex: str  # "M" | "F" | "other"
    medical_history: Optional[List[str]] = []
    vital_signs: Optional[dict] = {}


class DiagnosisChainRequest(BaseModel):
    patient_id: str
    symptoms: List[str]
    lab_results: Optional[dict] = {}
    imaging_notes: Optional[str] = None
    specialties: Optional[List[str]] = ["general", "cardiology", "neurology"]


class CareCoordinatorRequest(BaseModel):
    patient_id: str
    primary_diagnosis: str
    required_specialties: List[str]
    urgency_level: str  # "low" | "medium" | "high" | "critical"
    patient_location: Optional[str] = "unknown"


# --- Agent stubs (replace with real LLM calls / JARVIS cluster) ---


async def triage_agent(symptoms: List[str], vital_signs: dict) -> dict:
    """Agent 1: Rapid triage scoring based on symptoms and vitals."""
    await asyncio.sleep(0.05)  # simulate async LLM call
    critical_keywords = {
        "chest pain",
        "difficulty breathing",
        "unconscious",
        "severe bleeding",
    }
    urgency = (
        "critical"
        if any(s.lower() in critical_keywords for s in symptoms)
        else "medium"
    )
    return {
        "agent": "triage_agent",
        "urgency": urgency,
        "triage_score": 8 if urgency == "critical" else 4,
        "flags": [s for s in symptoms if s.lower() in critical_keywords],
    }


async def symptom_analysis_agent(symptoms: List[str], history: List[str]) -> dict:
    """Agent 2: Deep symptom analysis cross-referenced with medical history."""
    await asyncio.sleep(0.05)
    return {
        "agent": "symptom_analysis_agent",
        "symptom_clusters": {"primary": symptoms[:2], "secondary": symptoms[2:]},
        "history_relevance": len(history) > 0,
        "red_flags": [s for s in symptoms if "pain" in s.lower()],
    }


async def recommendation_agent(triage: dict, analysis: dict, age: int) -> dict:
    """Agent 3: Final recommendation synthesis."""
    await asyncio.sleep(0.05)
    urgency = triage["urgency"]
    route = (
        "ED"
        if urgency == "critical"
        else ("urgent_care" if urgency == "medium" else "primary_care")
    )
    return {
        "agent": "recommendation_agent",
        "recommended_route": route,
        "specialist_referral": age > 60 or urgency == "critical",
        "follow_up_hours": 1
        if urgency == "critical"
        else (24 if urgency == "medium" else 72),
    }


async def differential_agent(
    symptoms: List[str], specialty: str, lab_results: dict
) -> dict:
    """Differential diagnosis agent per specialty."""
    await asyncio.sleep(0.05)
    diagnoses = {
        "general": ["Viral infection", "Dehydration", "Anxiety disorder"],
        "cardiology": ["Arrhythmia", "Angina pectoris", "Heart failure"],
        "neurology": ["Migraine", "TIA", "Multiple sclerosis"],
    }
    return {
        "specialty": specialty,
        "top_differentials": diagnoses.get(specialty, ["Undetermined"])[:3],
        "confidence": 0.72,
        "recommended_tests": ["CBC", "CMP", "ECG"]
        if specialty == "cardiology"
        else ["MRI", "EEG"],
    }


# --- Routes ---


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "agents-assemble-healthcare",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/patient-intake")
async def patient_intake(req: PatientIntakeRequest):
    """
    Multi-agent patient intake pipeline.
    Runs triage, symptom analysis, and recommendation agents in parallel.
    """
    patient_id = req.patient_id or str(uuid.uuid4())

    triage_result, analysis_result = await asyncio.gather(
        triage_agent(req.symptoms, req.vital_signs),
        symptom_analysis_agent(req.symptoms, req.medical_history),
    )
    recommendation = await recommendation_agent(triage_result, analysis_result, req.age)

    return {
        "patient_id": patient_id,
        "timestamp": datetime.utcnow().isoformat(),
        "pipeline": "patient-intake-v1",
        "agents_run": 3,
        "triage": triage_result,
        "analysis": analysis_result,
        "recommendation": recommendation,
    }


@app.post("/diagnosis-chain")
async def diagnosis_chain(req: DiagnosisChainRequest):
    """
    Parallel differential diagnosis chain across multiple specialties.
    Each specialty runs its own diagnostic agent concurrently.
    """
    tasks = [
        differential_agent(req.symptoms, specialty, req.lab_results)
        for specialty in req.specialties
    ]
    results = await asyncio.gather(*tasks)

    merged = sorted(results, key=lambda x: x["confidence"], reverse=True)
    primary = merged[0] if merged else {}

    return {
        "patient_id": req.patient_id,
        "timestamp": datetime.utcnow().isoformat(),
        "pipeline": "diagnosis-chain-v1",
        "agents_run": len(req.specialties),
        "primary_diagnosis": primary,
        "differential_matrix": merged,
        "consensus_confidence": sum(r["confidence"] for r in results)
        / max(len(results), 1),
    }


@app.post("/care-coordinator")
async def care_coordinator(req: CareCoordinatorRequest):
    """
    Multi-specialty care coordination agent.
    Routes patient to appropriate specialists and resources.
    """
    urgency_map = {"low": 72, "medium": 24, "high": 4, "critical": 1}
    hours = urgency_map.get(req.urgency_level, 24)

    specialists_available = {
        s: {
            "available_in_hours": hours,
            "location": "on-site" if hours <= 4 else "teleconsult",
        }
        for s in req.required_specialties
    }

    care_plan = {
        "patient_id": req.patient_id,
        "timestamp": datetime.utcnow().isoformat(),
        "pipeline": "care-coordinator-v1",
        "primary_diagnosis": req.primary_diagnosis,
        "urgency_level": req.urgency_level,
        "specialists_scheduled": specialists_available,
        "estimated_first_contact_hours": hours,
        "care_setting": "inpatient"
        if req.urgency_level == "critical"
        else "outpatient",
        "follow_up_plan": {
            "next_review_hours": hours * 2,
            "remote_monitoring": req.urgency_level in ("high", "critical"),
        },
    }
    return care_plan
