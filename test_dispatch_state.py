from dispatch_state import DispatchStatus, Decision, apply_decision

def test_escalate_transitions_in_progress():
    result = apply_decision(DispatchStatus.IN_PROGRESS, Decision.ESCALATE)
    assert result == DispatchStatus.ESCALATED

def test_complete_transitions_dispatched():
    result = apply_decision(DispatchStatus.DISPATCHED, Decision.COMPLETE)
    assert result == DispatchStatus.COMPLETED

def test_no_change_on_same():
    result = apply_decision(DispatchStatus.COMPLETED, Decision.COMPLETE)
    assert result == DispatchStatus.COMPLETED
