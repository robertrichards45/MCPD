"""Shared MCPD service package initialization.

The call-type v2 adapter keeps the original service API stable for existing
routes while adding richer packet guidance for newer workflows.
"""

from . import call_type_rules_v2

call_type_rules_v2.activate()
