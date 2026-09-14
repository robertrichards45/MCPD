"""Install handbook-grounded Scenario Lab extensions at app startup.

Kept separate from official FTO/DOR records. This module mutates the simulator's
training registries only; it does not create performance ratings or personnel
actions.
"""

from . import scenario_cast, scenario_lab, scenario_legal_context, scenario_state_engine, scenario_variants
from .scenario_handbook_catalog import (
    HANDBOOK_CAST,
    HANDBOOK_NEXT,
    HANDBOOK_SCENARIOS,
    HANDBOOK_VARIANTS,
)
from .scenario_handbook_rubrics import HANDBOOK_RUBRICS
from .scenario_handbook_runtime import (
    HANDBOOK_BRANCH_EVENTS,
    HANDBOOK_PROFILES,
    extend_truth,
    handbook_branch_after_core,
    handbook_legal_rows,
)


# Data registries used by already-imported route functions are mutable dicts, so
# extending them here updates the live simulator without replacing the official
# FTO program or DOR models.
scenario_lab.SCENARIOS.update(HANDBOOK_SCENARIOS)
scenario_lab.SCENARIO_RUBRICS.update(HANDBOOK_RUBRICS)
scenario_variants.VARIANTS.update(HANDBOOK_VARIANTS)
scenario_variants.NEXT_SCENARIO.update(HANDBOOK_NEXT)
scenario_cast.SCENARIO_META.update(HANDBOOK_CAST)
scenario_state_engine.SCENARIO_PROFILES.update(HANDBOOK_PROFILES)
scenario_state_engine.BRANCH_EVENTS.update(HANDBOOK_BRANCH_EVENTS)


# Patch the live route globals after it has loaded. This is intentionally done at
# startup so existing six-scenario behavior remains unchanged.
from . import scenario_lab_live  # noqa: E402

_ORIGINAL_BUILD_TRUTH = scenario_lab_live.build_scenario_truth
_ORIGINAL_APPLY_CORE = scenario_lab_live.apply_core_decision
_ORIGINAL_LEGAL_CONTEXT = scenario_lab_live.legal_context_for


def _build_truth(scenario_id, run_context):
    truth = _ORIGINAL_BUILD_TRUTH(scenario_id, run_context)
    if scenario_id in HANDBOOK_SCENARIOS:
        extend_truth(truth, scenario_id, run_context)
    return truth


def _apply_core(state, scenario_id, turn, text, accepted):
    consequences = list(_ORIGINAL_APPLY_CORE(state, scenario_id, turn, text, accepted) or [])
    if scenario_id in HANDBOOK_SCENARIOS:
        consequences.extend(
            handbook_branch_after_core(
                state,
                scenario_id,
                turn,
                text,
                accepted,
                scenario_state_engine._set_pending_event,
            )
        )
    return consequences


def _legal_context(scenario_id, run_context, turn, engine=None):
    rows = list(_ORIGINAL_LEGAL_CONTEXT(scenario_id, run_context, turn, engine) or [])
    if scenario_id in HANDBOOK_SCENARIOS:
        rows.extend(handbook_legal_rows(scenario_id, run_context, turn, engine))
    return rows


scenario_lab_live.build_scenario_truth = _build_truth
scenario_lab_live.apply_core_decision = _apply_core
scenario_lab_live.legal_context_for = _legal_context
scenario_legal_context.legal_context_for = _legal_context
