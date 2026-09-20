"""CLI: read a work-order follow-up JSON, get LLM decision, print new dispatch status."""
import sys
import json
from work_order_client import WorkOrderFollowup, analyze_followup
from dispatch_state import DispatchStatus, Decision, apply_decision

def main():
    if len(sys.argv) < 2:
        print("usage: python run_followup.py '<json>'")
        sys.exit(1)
    raw = json.loads(sys.argv[1])
    followup = WorkOrderFollowup(**raw)
    decision = analyze_followup(followup)
    new_status = apply_decision(
        DispatchStatus(followup.dispatch_status),
        Decision(decision.decision),
    )
    print(json.dumps({
        "work_order_id": followup.work_order_id,
        "decision": decision.decision,
        "reason": decision.reason,
        "new_dispatch_status": new_status.value,
    }))

if __name__ == "__main__":
    main()
