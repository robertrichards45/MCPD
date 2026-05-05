"""
Phase 9 — Officer Performance / Element Tracking System
Routes prefix: /performance/
"""
from datetime import date, datetime, timezone

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    PERF_STATUS_APPROVED, PERF_STATUS_PENDING, PERF_STATUS_REJECTED,
    User, YearCycle, YearElement, YearSubmission,
)
from ..permissions import can_manage_team, can_supervisor_review, is_watch_commander, can_manage_site

bp = Blueprint('performance', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _today():
    return date.today().isoformat()

def _active_year():
    """Return the year of the active YearCycle, or current calendar year if none exists."""
    cycle = YearCycle.query.filter_by(is_active=True).order_by(YearCycle.year.desc()).first()
    return cycle.year if cycle else date.today().year

def _can_manage_elements(user):
    """Only Watch Commander or Site Controller may define/edit elements."""
    return can_manage_team(user)  # WC + site controller

def _can_approve(user):
    return can_supervisor_review(user)  # WC, Desk Sgt, Site Controller

def _calc_stats(officer_id, year):
    """Return a list of dicts: one per active element with approved totals."""
    elements = (
        YearElement.query
        .filter_by(year=year, active=True)
        .order_by(YearElement.category, YearElement.name)
        .all()
    )
    rows = []
    for el in elements:
        approved = (
            db.session.query(func.sum(YearSubmission.quantity))
            .filter(
                YearSubmission.element_id == el.id,
                YearSubmission.officer_id == officer_id,
                YearSubmission.status == PERF_STATUS_APPROVED,
            )
            .scalar() or 0
        )
        pct = min(100, int(approved * 100 / el.goal_value)) if el.goal_value > 0 else 0
        rows.append({
            'element':   el,
            'approved':  approved,
            'goal':      el.goal_value,
            'pct':       pct,
            'remaining': max(0, el.goal_value - approved),
        })
    return rows


# ── Officer: my stats dashboard ───────────────────────────────────────────────

@bp.route('/performance/')
@bp.route('/performance/my-stats')
@login_required
def my_stats():
    year = _active_year()
    rows = _calc_stats(current_user.id, year)
    pending_count = YearSubmission.query.filter_by(
        officer_id=current_user.id, year=year, status=PERF_STATUS_PENDING
    ).count()
    return render_template(
        'perf_my_stats.html',
        title='My Performance — MCPD Portal',
        year=year,
        rows=rows,
        pending_count=pending_count,
        can_approve=_can_approve(current_user),
        can_manage=_can_manage_elements(current_user),
        user=current_user,
    )


# ── Officer: submit an entry ──────────────────────────────────────────────────

@bp.route('/performance/submit', methods=['GET', 'POST'])
@login_required
def submit_entry():
    year = _active_year()
    elements = (
        YearElement.query
        .filter_by(year=year, active=True)
        .order_by(YearElement.category, YearElement.name)
        .all()
    )
    if not elements:
        flash('No active elements are defined for this year. Contact your Watch Commander.', 'warning')
        return redirect(url_for('performance.my_stats'))

    if request.method == 'POST':
        element_id = request.form.get('element_id', type=int)
        quantity   = request.form.get('quantity',   type=int)
        notes      = (request.form.get('notes') or '').strip() or None

        element = YearElement.query.get(element_id) if element_id else None
        if not element or element.year != year or not element.active:
            flash('Invalid element selection.', 'danger')
        elif not quantity or quantity < 1:
            flash('Quantity must be at least 1.', 'danger')
        else:
            sub = YearSubmission(
                officer_id=current_user.id,
                element_id=element.id,
                quantity=quantity,
                notes=notes,
                submitted_date=_today(),
                year=year,
                status=PERF_STATUS_PENDING,
            )
            db.session.add(sub)
            db.session.commit()
            flash(f'Submitted {quantity} × {element.name} — pending supervisor approval.', 'success')
            return redirect(url_for('performance.my_stats'))

    preselect = request.args.get('element_id', type=int)
    return render_template(
        'perf_submit.html',
        title='Submit Activity — MCPD Portal',
        elements=elements,
        preselect=preselect,
        year=year,
        user=current_user,
    )


# ── Officer: my submission history ────────────────────────────────────────────

@bp.route('/performance/my-history')
@login_required
def my_history():
    year = _active_year()
    subs = (
        YearSubmission.query
        .filter_by(officer_id=current_user.id, year=year)
        .order_by(YearSubmission.created_at.desc())
        .all()
    )
    return render_template(
        'perf_my_history.html',
        title='My Submissions — MCPD Portal',
        subs=subs,
        year=year,
        PERF_STATUS_PENDING=PERF_STATUS_PENDING,
        PERF_STATUS_APPROVED=PERF_STATUS_APPROVED,
        PERF_STATUS_REJECTED=PERF_STATUS_REJECTED,
        user=current_user,
    )


# ── Supervisor: pending approvals ─────────────────────────────────────────────

@bp.route('/performance/pending')
@login_required
def pending():
    if not _can_approve(current_user):
        abort(403)
    year = _active_year()
    filter_officer = request.args.get('officer_id', type=int)

    q = (
        YearSubmission.query
        .filter_by(year=year, status=PERF_STATUS_PENDING)
        .order_by(YearSubmission.created_at)
    )
    if filter_officer:
        q = q.filter_by(officer_id=filter_officer)

    subs = q.all()
    officers = (
        User.query
        .filter(User.id.in_(
            db.session.query(YearSubmission.officer_id)
            .filter_by(year=year, status=PERF_STATUS_PENDING)
            .distinct()
        ))
        .order_by(User.last_name, User.first_name, User.username)
        .all()
    )
    return render_template(
        'perf_pending.html',
        title='Pending Approvals — MCPD Portal',
        subs=subs,
        officers=officers,
        filter_officer=filter_officer,
        year=year,
        user=current_user,
    )


@bp.route('/performance/submission/<int:sub_id>/approve', methods=['POST'])
@login_required
def approve_submission(sub_id):
    if not _can_approve(current_user):
        abort(403)
    sub = YearSubmission.query.get_or_404(sub_id)
    comment = (request.form.get('comment') or '').strip() or None
    sub.status         = PERF_STATUS_APPROVED
    sub.reviewed_by    = current_user.id
    sub.review_comment = comment
    sub.reviewed_at    = _now()
    db.session.commit()
    flash(f'Approved: {sub.quantity} × {sub.element.name} for {sub.officer.display_name}.', 'success')
    return redirect(request.referrer or url_for('performance.pending'))


@bp.route('/performance/submission/<int:sub_id>/reject', methods=['POST'])
@login_required
def reject_submission(sub_id):
    if not _can_approve(current_user):
        abort(403)
    sub = YearSubmission.query.get_or_404(sub_id)
    comment = (request.form.get('comment') or '').strip() or None
    sub.status         = PERF_STATUS_REJECTED
    sub.reviewed_by    = current_user.id
    sub.review_comment = comment
    sub.reviewed_at    = _now()
    db.session.commit()
    flash('Submission rejected.', 'warning')
    return redirect(request.referrer or url_for('performance.pending'))


# ── Supervisor: team overview ─────────────────────────────────────────────────

@bp.route('/performance/team')
@login_required
def team_overview():
    if not _can_approve(current_user):
        abort(403)
    year = _active_year()
    filter_officer = request.args.get('officer_id', type=int)
    filter_element = request.args.get('element_id', type=int)

    officers = (
        User.query.filter_by(active=True)
        .order_by(User.last_name, User.first_name, User.username)
        .all()
    )
    elements = (
        YearElement.query.filter_by(year=year, active=True)
        .order_by(YearElement.category, YearElement.name)
        .all()
    )

    if filter_officer:
        display_officers = [o for o in officers if o.id == filter_officer]
    else:
        display_officers = officers

    grid = []
    for officer in display_officers:
        rows = _calc_stats(officer.id, year)
        if filter_element:
            rows = [r for r in rows if r['element'].id == filter_element]
        pending = YearSubmission.query.filter_by(
            officer_id=officer.id, year=year, status=PERF_STATUS_PENDING
        ).count()
        worst_pct = min((r['pct'] for r in rows), default=100)
        grid.append({'officer': officer, 'rows': rows, 'pending': pending, 'worst_pct': worst_pct})

    grid.sort(key=lambda g: g['worst_pct'])

    return render_template(
        'perf_team.html',
        title='Team Overview — MCPD Portal',
        grid=grid,
        officers=officers,
        elements=elements,
        filter_officer=filter_officer,
        filter_element=filter_element,
        year=year,
        can_manage=_can_manage_elements(current_user),
        user=current_user,
    )


# ── Watch Commander: manage elements ─────────────────────────────────────────

@bp.route('/performance/elements')
@login_required
def elements():
    if not _can_manage_elements(current_user):
        abort(403)
    year = _active_year()
    elems = (
        YearElement.query.filter_by(year=year)
        .order_by(YearElement.category, YearElement.name)
        .all()
    )
    cycle = YearCycle.query.filter_by(year=year).first()
    past_years = (
        db.session.query(YearElement.year)
        .filter(YearElement.year != year)
        .distinct()
        .order_by(YearElement.year.desc())
        .all()
    )
    return render_template(
        'perf_elements.html',
        title='Element Management — MCPD Portal',
        elems=elems,
        year=year,
        cycle=cycle,
        past_years=[r[0] for r in past_years],
        user=current_user,
    )


@bp.route('/performance/elements/new', methods=['GET', 'POST'])
@login_required
def element_new():
    if not _can_manage_elements(current_user):
        abort(403)
    year = _active_year()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Name is required.', 'danger')
        else:
            el = YearElement(
                name=name,
                category=(request.form.get('category') or '').strip() or None,
                goal_value=int(request.form.get('goal_value') or 0),
                description=(request.form.get('description') or '').strip() or None,
                year=year,
                active=True,
                created_by=current_user.id,
            )
            db.session.add(el)
            db.session.commit()
            flash(f'"{name}" added for {year}.', 'success')
            return redirect(url_for('performance.elements'))
    return render_template('perf_element_form.html', title='New Element', el=None, year=year, user=current_user)


@bp.route('/performance/elements/<int:el_id>/edit', methods=['GET', 'POST'])
@login_required
def element_edit(el_id):
    if not _can_manage_elements(current_user):
        abort(403)
    el = YearElement.query.get_or_404(el_id)
    if request.method == 'POST':
        el.name        = (request.form.get('name') or '').strip() or el.name
        el.category    = (request.form.get('category') or '').strip() or None
        el.goal_value  = int(request.form.get('goal_value') or el.goal_value)
        el.description = (request.form.get('description') or '').strip() or None
        el.active      = request.form.get('active') == '1'
        db.session.commit()
        flash('Element updated.', 'success')
        return redirect(url_for('performance.elements'))
    return render_template('perf_element_form.html', title='Edit Element', el=el, year=el.year, user=current_user)


@bp.route('/performance/elements/<int:el_id>/deactivate', methods=['POST'])
@login_required
def element_deactivate(el_id):
    if not _can_manage_elements(current_user):
        abort(403)
    el = YearElement.query.get_or_404(el_id)
    el.active = False
    db.session.commit()
    flash(f'"{el.name}" deactivated.', 'success')
    return redirect(url_for('performance.elements'))


# ── Watch Commander: year reset ───────────────────────────────────────────────

@bp.route('/performance/year-reset', methods=['GET', 'POST'])
@login_required
def year_reset():
    if not _can_manage_elements(current_user):
        abort(403)

    current_year = _active_year()

    if request.method == 'POST':
        action    = request.form.get('action')
        new_year  = request.form.get('new_year', type=int)
        copy_elements = request.form.get('copy_elements') == '1'

        if action == 'reset' and new_year and new_year > current_year:
            # Archive current cycle
            old_cycle = YearCycle.query.filter_by(year=current_year, is_active=True).first()
            if old_cycle:
                old_cycle.is_active   = False
                old_cycle.archived_at = _now()
                old_cycle.archived_by = current_user.id

            # Create new active cycle
            new_cycle = YearCycle(year=new_year, is_active=True)
            db.session.add(new_cycle)

            # Optionally copy elements from previous year
            if copy_elements:
                prev_elements = YearElement.query.filter_by(year=current_year, active=True).all()
                for pe in prev_elements:
                    db.session.add(YearElement(
                        name=pe.name,
                        category=pe.category,
                        goal_value=pe.goal_value,
                        description=pe.description,
                        year=new_year,
                        active=True,
                        created_by=current_user.id,
                    ))

            db.session.commit()
            flash(
                f'Year reset complete. Active year is now {new_year}.'
                + (' Elements copied from previous year.' if copy_elements else ''),
                'success',
            )
            return redirect(url_for('performance.elements'))
        else:
            flash('New year must be greater than the current active year.', 'danger')

    cycles = YearCycle.query.order_by(YearCycle.year.desc()).all()
    return render_template(
        'perf_year_reset.html',
        title='Year Reset — MCPD Portal',
        current_year=current_year,
        next_year=current_year + 1,
        cycles=cycles,
        user=current_user,
    )
