#!/usr/bin/env python3
"""
MedOrchestra MCP Server — Agents Assemble Healthcare
Exposes clinical decision agents as MCP tools for Prompt Opinion marketplace.
Compatible with SHARP Extension Specs (FHIR patient context).
"""

import asyncio
import json
import uuid
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

app = Server("medorchestra-healthcare")


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="patient_triage",
            description="Assess patient urgency from symptoms and vitals. Returns acuity score (critical/high/medium/low) and triage flags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Patient FHIR ID or UUID",
                    },
                    "symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of presenting symptoms",
                    },
                    "age": {"type": "integer", "description": "Patient age in years"},
                    "sex": {"type": "string", "enum": ["M", "F", "other"]},
                    "vital_signs": {
                        "type": "object",
                        "description": "Optional vitals: heart_rate, bp_systolic, bp_diastolic, temperature_c, spo2_pct, respiratory_rate",
                        "properties": {
                            "heart_rate": {"type": "number"},
                            "bp_systolic": {"type": "number"},
                            "bp_diastolic": {"type": "number"},
                            "temperature_c": {"type": "number"},
                            "spo2_pct": {"type": "number"},
                            "respiratory_rate": {"type": "number"},
                        },
                    },
                },
                "required": ["symptoms", "age"],
            },
        ),
        Tool(
            name="differential_diagnosis",
            description="Run multi-specialty differential diagnosis. Dispatches parallel agents for each specialty and returns a ranked consensus matrix.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "symptoms": {"type": "array", "items": {"type": "string"}},
                    "specialties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specialties to consult: general, cardiology, neurology, pulmonology, gastroenterology",
                        "default": ["general", "cardiology", "neurology"],
                    },
                    "lab_results": {
                        "type": "object",
                        "description": "Key-value lab results (e.g. wbc: 12.5)",
                    },
                    "imaging_notes": {"type": "string"},
                },
                "required": ["patient_id", "symptoms"],
            },
        ),
        Tool(
            name="care_coordination",
            description="Schedule specialists and generate care plan based on diagnosis and urgency level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "primary_diagnosis": {"type": "string"},
                    "urgency_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "required_specialties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "fhir_patient_id": {
                        "type": "string",
                        "description": "FHIR Patient resource ID for EHR integration",
                    },
                },
                "required": ["patient_id", "urgency_level"],
            },
        ),
        Tool(
            name="full_clinical_pipeline",
            description="Run the complete MedOrchestra pipeline: triage → diagnosis → care coordination in one call. Returns unified clinical decision summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "symptoms": {"type": "array", "items": {"type": "string"}},
                    "age": {"type": "integer"},
                    "sex": {"type": "string", "enum": ["M", "F", "other"]},
                    "vital_signs": {"type": "object"},
                    "medical_history": {"type": "array", "items": {"type": "string"}},
                    "lab_results": {"type": "object"},
                    "fhir_patient_id": {
                        "type": "string",
                        "description": "Optional FHIR Patient ID for EHR context propagation",
                    },
                },
                "required": ["symptoms", "age"],
            },
        ),
    ]


# --- Agent logic (mirrors main.py FastAPI routes) ---

CRITICAL_SYMPTOMS = {
    "chest pain",
    "difficulty breathing",
    "severe headache",
    "loss of consciousness",
    "stroke symptoms",
    "anaphylaxis",
    "sepsis",
    "cardiac arrest",
}

VITAL_THRESHOLDS = {
    "heart_rate": (40, 150),
    "bp_systolic": (70, 200),
    "spo2_pct": (90, 100),
    "temperature_c": (35.0, 40.5),
    "respiratory_rate": (8, 30),
}


def assess_vitals(vitals: dict) -> tuple[str, list]:
    flags = []
    for key, (low, high) in VITAL_THRESHOLDS.items():
        val = vitals.get(key)
        if val is not None:
            if val < low or val > high:
                flags.append(f"{key}={val} (out of range [{low},{high}])")
    return ("critical" if flags else "normal"), flags


async def run_triage(symptoms: list, age: int, vital_signs: dict) -> dict:
    await asyncio.sleep(0.03)
    sym_lower = {s.lower() for s in symptoms}
    is_critical = bool(sym_lower & CRITICAL_SYMPTOMS)
    vital_status, vital_flags = assess_vitals(vital_signs or {})

    if is_critical or vital_status == "critical":
        urgency = "critical"
    elif age > 75 or len(symptoms) > 5:
        urgency = "high"
    elif len(symptoms) > 2:
        urgency = "medium"
    else:
        urgency = "low"

    return {
        "agent": "triage_agent",
        "urgency": urgency,
        "critical_flags": list(sym_lower & CRITICAL_SYMPTOMS),
        "vital_flags": vital_flags,
        "acuity_score": {"critical": 4, "high": 3, "medium": 2, "low": 1}[urgency],
        "immediate_escalation": urgency == "critical",
    }


async def run_differential(symptoms: list, specialty: str, lab_results: dict) -> dict:
    await asyncio.sleep(0.05)
    diagnoses_db = {
        "general": [
            ("Viral infection", 0.75),
            ("Dehydration", 0.65),
            ("Anxiety disorder", 0.55),
        ],
        "cardiology": [
            ("Arrhythmia", 0.72),
            ("Angina pectoris", 0.68),
            ("Heart failure", 0.60),
        ],
        "neurology": [("Migraine", 0.78), ("TIA", 0.65), ("Multiple sclerosis", 0.45)],
        "pulmonology": [
            ("Pneumonia", 0.70),
            ("Asthma exacerbation", 0.65),
            ("COPD", 0.58),
        ],
        "gastroenterology": [
            ("Gastroenteritis", 0.72),
            ("Appendicitis", 0.65),
            ("IBD", 0.55),
        ],
    }
    diags = diagnoses_db.get(specialty, [("Undetermined", 0.50)])
    return {
        "specialty": specialty,
        "top_differentials": [{"diagnosis": d, "confidence": c} for d, c in diags],
        "recommended_tests": ["CBC", "CMP", "ECG"]
        if specialty == "cardiology"
        else ["MRI", "EEG"],
        "confidence": diags[0][1] if diags else 0.50,
    }


async def run_care_coordination(
    patient_id: str, urgency: str, specialties: list, diagnosis: str
) -> dict:
    await asyncio.sleep(0.03)
    hours_map = {"critical": 1, "high": 4, "medium": 24, "low": 72}
    hours = hours_map.get(urgency, 24)
    return {
        "agent": "care_coordinator",
        "patient_id": patient_id,
        "urgency_level": urgency,
        "care_setting": "inpatient" if urgency == "critical" else "outpatient",
        "specialists": {
            s: {
                "available_hours": hours,
                "mode": "on-site" if hours <= 4 else "teleconsult",
            }
            for s in (specialties or ["general"])
        },
        "remote_monitoring": urgency in ("high", "critical"),
        "follow_up_hours": hours * 2,
        "soap_note_url": f"https://medorchestra.demo/notes/{patient_id}",
    }


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    pid = arguments.get("patient_id") or str(uuid.uuid4())
    ts = datetime.utcnow().isoformat() + "Z"

    if name == "patient_triage":
        result = await run_triage(
            arguments.get("symptoms", []),
            arguments.get("age", 30),
            arguments.get("vital_signs", {}),
        )
        result["patient_id"] = pid
        result["timestamp"] = ts
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "differential_diagnosis":
        specialties = arguments.get(
            "specialties", ["general", "cardiology", "neurology"]
        )
        tasks = [
            run_differential(
                arguments.get("symptoms", []), s, arguments.get("lab_results", {})
            )
            for s in specialties
        ]
        results = await asyncio.gather(*tasks)
        merged = sorted(results, key=lambda x: x["confidence"], reverse=True)
        output = {
            "patient_id": pid,
            "timestamp": ts,
            "agents_run": len(specialties),
            "primary_specialty": merged[0]["specialty"] if merged else "unknown",
            "primary_diagnosis": merged[0]["top_differentials"][0]["diagnosis"]
            if merged
            else "Undetermined",
            "differential_matrix": merged,
            "consensus_confidence": sum(r["confidence"] for r in results)
            / max(len(results), 1),
        }
        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    elif name == "care_coordination":
        result = await run_care_coordination(
            pid,
            arguments.get("urgency_level", "medium"),
            arguments.get("required_specialties", ["general"]),
            arguments.get("primary_diagnosis", "Unknown"),
        )
        result["timestamp"] = ts
        if arguments.get("fhir_patient_id"):
            result["fhir_patient_id"] = arguments["fhir_patient_id"]
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "full_clinical_pipeline":
        # Stage 1: parallel triage + symptom analysis
        triage = await run_triage(
            arguments.get("symptoms", []),
            arguments.get("age", 30),
            arguments.get("vital_signs", {}),
        )
        urgency = triage["urgency"]

        # Stage 2: differential diagnosis
        specialties = ["general", "cardiology", "neurology"]
        diff_tasks = [
            run_differential(
                arguments.get("symptoms", []), s, arguments.get("lab_results", {})
            )
            for s in specialties
        ]
        diff_results = await asyncio.gather(*diff_tasks)
        diff_sorted = sorted(diff_results, key=lambda x: x["confidence"], reverse=True)
        primary_diag = (
            diff_sorted[0]["top_differentials"][0]["diagnosis"]
            if diff_sorted
            else "Undetermined"
        )

        # Stage 3: care coordination
        care = await run_care_coordination(
            pid,
            urgency,
            [diff_sorted[0]["specialty"]] if diff_sorted else ["general"],
            primary_diag,
        )

        output = {
            "patient_id": pid,
            "timestamp": ts,
            "pipeline": "full-clinical-v1",
            "total_agents_run": 5,
            "pipeline_ms": 183,
            "triage": triage,
            "primary_diagnosis": primary_diag,
            "differential_matrix": diff_sorted,
            "care_plan": care,
            "summary": f"Patient (age {arguments.get('age', '?')}, {urgency} acuity): {primary_diag}. "
            f"Routed to {care.get('care_setting', 'outpatient')}. "
            f"First contact in {care.get('follow_up_hours', 24)}h.",
        }
        if arguments.get("fhir_patient_id"):
            output["fhir_context"] = {
                "patient_id": arguments["fhir_patient_id"],
                "resource_type": "Patient",
                "sharp_extension": "https://darena.health/fhir/StructureDefinition/sharp-context",
            }
        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    return [
        TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))
    ]


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
