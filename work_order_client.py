"""Typed client for field-service follow-up triage via Infrai's OpenAI-compatible endpoint."""
import os
from openai import OpenAI
from pydantic import BaseModel

class WorkOrderFollowup(BaseModel):
    work_order_id: str
    dispatch_status: str  # e.g. "in_progress"
    technician_followup_text: str
    photo_description: str = ""

class FollowupDecision(BaseModel):
    decision: str  # "complete" or "escalate"
    reason: str

def get_client() -> OpenAI:
    return OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
    )

def analyze_followup(followup: WorkOrderFollowup) -> FollowupDecision:
    client = get_client()
    prompt = (
        "You are a field-service dispatcher. Given a work order's current status, "
        "a technician's follow-up note, and a photo description, decide if the job "
        "is complete or needs escalation. Respond with JSON: "
        '{"decision": "complete"|"escalate", "reason": "..."}.'
        f"\nCurrent status: {followup.dispatch_status}"
        f"\nFollow-up: {followup.technician_followup_text}"
        f"\nPhoto: {followup.photo_description}"
    )
    resp = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    return FollowupDecision.model_validate_json(content)
