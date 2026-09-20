"""Pure dispatch state transition rules for work-order follow-ups."""
from enum import Enum

class DispatchStatus(str, Enum):
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"

class Decision(str, Enum):
    COMPLETE = "complete"
    ESCALATE = "escalate"

def apply_decision(current: DispatchStatus, decision: Decision) -> DispatchStatus:
    if decision == Decision.ESCALATE:
        return DispatchStatus.ESCALATED
    if decision == Decision.COMPLETE:
        return DispatchStatus.COMPLETED
    return current
