from flask import session

from .models import (
    ROLE_DESK_SGT,
    ROLE_FIELD_TRAINING,
    ROLE_PATROL_OFFICER,
    ROLE_RFI_PATROL_OFFICER,
    ROLE_RFI_WATCH_COMMANDER,
    ROLE_TRUCK_GATE_PATROL_OFFICER,
    ROLE_TRUCK_GATE_WATCH_COMMANDER,
    ROLE_WEBSITE_CONTROLLER,
    ROLE_WATCH_COMMANDER,
)


def effective_role(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    base_role = user.normalized_role
    if base_role == ROLE_WEBSITE_CONTROLLER:
        acting_role = session.get('acting_role')
        if acting_role in {ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER}:
            return acting_role
    return base_role


def watch_commander_scope_id(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    if user.normalized_role == ROLE_WEBSITE_CONTROLLER and effective_role(user) == ROLE_WATCH_COMMANDER:
        scoped_id = session.get('acting_watch_commander_id')
        if scoped_id:
            return scoped_id
    if effective_role(user) == ROLE_WATCH_COMMANDER:
        return user.id
    return None


def is_site_controller(user):
    return effective_role(user) == ROLE_WEBSITE_CONTROLLER


def is_watch_commander(user):
    return effective_role(user) == ROLE_WATCH_COMMANDER


def can_manage_site(user):
    return is_site_controller(user)


def can_grade_cleoc_reports(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return can_manage_site(user) or bool(getattr(user, 'can_grade_cleoc_reports', False))


def can_manage_team(user):
    return effective_role(user) in {ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER}


def can_access_truck_gate(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return user.has_any_role(
        ROLE_WEBSITE_CONTROLLER,
        ROLE_TRUCK_GATE_WATCH_COMMANDER,
        ROLE_TRUCK_GATE_PATROL_OFFICER,
    )


def can_manage_truck_gate(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return user.has_any_role(
        ROLE_WEBSITE_CONTROLLER,
        ROLE_TRUCK_GATE_WATCH_COMMANDER,
    )


def can_access_rfi(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return user.has_any_role(
        ROLE_WEBSITE_CONTROLLER,
        ROLE_RFI_WATCH_COMMANDER,
        ROLE_RFI_PATROL_OFFICER,
    )


def can_manage_rfi(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return user.has_any_role(
        ROLE_WEBSITE_CONTROLLER,
        ROLE_RFI_WATCH_COMMANDER,
    )


def can_access_armory(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return user.has_any_role(
        ROLE_WEBSITE_CONTROLLER,
        ROLE_WATCH_COMMANDER,
        ROLE_DESK_SGT,
    )


def can_manage_armory(user):
    return can_access_armory(user)


def can_view_user(user, target_user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.id == target_user.id:
        return True
    if can_manage_site(user):
        return True
    scope_id = watch_commander_scope_id(user)
    if scope_id:
        return target_user.supervisor_id == scope_id or target_user.id == scope_id
    return False


def can_manage_user(user, target_user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if can_manage_site(user):
        return True
    scope_id = watch_commander_scope_id(user)
    if scope_id:
        return target_user.supervisor_id == scope_id and target_user.id != scope_id
    return False


def visible_user_ids(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    if can_manage_site(user):
        return None
    scope_id = watch_commander_scope_id(user)
    if scope_id:
        return [scope_id]
    return [user.id]


def assignable_roles(user):
    if can_manage_site(user):
        return [
            ROLE_WEBSITE_CONTROLLER,
            ROLE_WATCH_COMMANDER,
            ROLE_DESK_SGT,
            ROLE_FIELD_TRAINING,
            ROLE_PATROL_OFFICER,
        ]
    if is_watch_commander(user):
        return [
            ROLE_DESK_SGT,
            ROLE_FIELD_TRAINING,
            ROLE_PATROL_OFFICER,
        ]
    return []
