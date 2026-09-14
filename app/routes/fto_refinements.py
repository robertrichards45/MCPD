import json
from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..fto_models import FTODailyObservation
from .fto_program import (
    RATING_AREAS,
    RATING_CHOICES,
    _audit,
    _json_dict,
    _parse_date,
    _text,
    can_evaluate_assignment,
)

bp = Blueprint('fto_refinements', __name__, url_prefix='/sentinel/fto-center')


def _ratings_from_form():
    ratings = {}
    observed = []
    for index, area in enumerate(RATING_AREAS):
        try:
            rating = int(request.form.get(f'rating_{index}') or 0)
        except (TypeError, ValueError):
            rating = 0
        rating = max(0, min(5, rating))
        ratings[area] = rating
        if rating:
            observed.append(rating)
    return ratings, observed


@bp.route('/dor/<int:dor_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_dor(dor_id):
    dor = FTODailyObservation.query.get_or_404(dor_id)
    assignment = dor.assignment

    if not can_evaluate_assignment(current_user, assignment):
        abort(403)
    if dor.status != 'DRAFT' or assignment.status == 'COMPLETED':
        abort(403)

    if request.method == 'POST':
        ratings, observed = _ratings_from_form()
        action = _text(request.form.get('action')).lower()
        finalize = action == 'finalize'
        if finalize and not observed:
            flash('Rate at least one observed performance area before finalizing a DOR.', 'danger')
            return redirect(url_for('reports.fto_refinements.edit_dor', dor_id=dor.id))

        dor.training_date = _parse_date(request.form.get('training_date'), dor.training_date or date.today()) or date.today()
        dor.scenario_id = _text(request.form.get('scenario_id')) or None
        dor.ratings_json = json.dumps(ratings, sort_keys=True)
        dor.overall_rating = round(sum(observed) / len(observed), 2) if observed else None
        dor.strengths = _text(request.form.get('strengths')) or None
        dor.development_areas = _text(request.form.get('development_areas')) or None
        dor.comments = (request.form.get('comments') or '').strip() or None

        if finalize:
            dor.status = 'FINALIZED'
            dor.finalized_at = datetime.utcnow()
            action_name = 'fto_dor_finalized'
            message = 'DOR finalized.'
        else:
            action_name = 'fto_dor_updated'
            message = 'DOR draft updated.'

        _audit(
            action_name,
            f'dor={dor.id}|assignment={assignment.id}|week={dor.week_number}|editor={current_user.id}',
        )
        db.session.commit()
        flash(message, 'success')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))

    return render_template(
        'fto_dor_edit.html',
        user=current_user,
        dor=dor,
        assignment=assignment,
        ratings=_json_dict(dor.ratings_json),
        rating_areas=RATING_AREAS,
        rating_choices=RATING_CHOICES,
    )
