# Agents Assemble Healthcare

> **Hackathon:** Agents Assemble — Healthcare AI | $25,000 prize pool | Deadline: May 11, 2026

Multi-agent orchestration platform for real-time clinical decision support. Five specialized AI agents run **in parallel** to triage patients, generate differential diagnoses, and coordinate care — in under 200ms.

---

## Architecture

```
Patient Data
     │
     ▼
POST /patient-intake    → triage_agent + symptom_analysis_agent + recommendation_agent
POST /diagnosis-chain   → cardiology_agent + neurology_agent + general_agent (parallel)
POST /care-coordinator  → scheduling_agent → care_plan
```

All agents execute via `asyncio.gather()` — true parallelism, no sequential bottlenecks.

---

## Agents

| Agent | Role |
|---|---|
| `triage_agent` | Urgency scoring from vitals + symptom keywords |
| `symptom_analysis_agent` | Cluster symptoms, detect red flags |
| `recommendation_agent` | Route to ED / urgent care / primary care |
| `diagnosis_agent` (per specialty) | Parallel differential diagnosis per specialty |
| `care_coordinator_agent` | Schedule specialists, generate care plan |

---

## Quickstart

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Example — Patient Intake

```bash
curl -X POST http://localhost:8000/patient-intake \
  -H "Content-Type: application/json" \
  -d '{"symptoms":["chest pain","shortness of breath"],"age":58,"sex":"M","vital_signs":{"bp":"140/90","hr":105}}'
```

### Example — Diagnosis Chain

```bash
curl -X POST http://localhost:8000/diagnosis-chain \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"P001","symptoms":["chest pain","left arm pain"],"specialties":["cardiology","general"]}'
```

---

## Tech Stack

- **FastAPI** — async REST API
- **Python asyncio** — parallel agent execution
- **Pydantic v2** — strict request/response schemas
- **Ollama / LM Studio** — optional local LLM augmentation

---

## Why Multi-Agent for Healthcare?

Real clinical decisions involve multiple specialists. This system mirrors that reality:
- **Cardiologist** + **Neurologist** + **GP** each run independently
- Results are merged into a consensus differential sorted by confidence
- No single point of failure — if one agent is uncertain, others compensate

---

## API Docs

Run the server and visit: `http://localhost:8000/docs`

---

## Team

**Turbo31150** — Multi-agent systems engineer, GPU cluster operator.
GitHub: https://github.com/Turbo31150
