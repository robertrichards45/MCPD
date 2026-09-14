from datetime import datetime

from .extensions import db


def _utcnow():
    return datetime.utcnow()


class FTOProgramAssignment(db.Model):
    __tablename__ = 'fto_program_assignment'

    id = db.Column(db.Integer, primary_key=True)
    trainee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    assigned_fto_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    program_type = db.Column(db.String(20), nullable=False, default='standard', index=True)
    status = db.Column(db.String(24), nullable=False, default='ACTIVE', index=True)
    current_week = db.Column(db.Integer, nullable=False, default=1)
    progress_percent = db.Column(db.Integer, nullable=False, default=0)
    extension_weeks = db.Column(db.Integer, nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=True, index=True)
    expected_completion_date = db.Column(db.Date, nullable=True, index=True)
    completed_at = db.Column(db.DateTime, nullable=True, index=True)
    completion_recommendation = db.Column(db.String(40), nullable=True, index=True)
    completion_note = db.Column(db.Text, nullable=True)
    curriculum_json = db.Column(db.Text, nullable=False, default='{}')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow, index=True)

    trainee = db.relationship('User', foreign_keys=[trainee_id])
    assigned_fto = db.relationship('User', foreign_keys=[assigned_fto_id])
    supervisor = db.relationship('User', foreign_keys=[supervisor_id])
    creator = db.relationship('User', foreign_keys=[created_by])


class FTODailyObservation(db.Model):
    __tablename__ = 'fto_daily_observation'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('fto_program_assignment.id'), nullable=False, index=True)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    training_date = db.Column(db.Date, nullable=False, index=True)
    week_number = db.Column(db.Integer, nullable=False, default=1, index=True)
    scenario_id = db.Column(db.String(40), nullable=True, index=True)
    ratings_json = db.Column(db.Text, nullable=False, default='{}')
    overall_rating = db.Column(db.Float, nullable=True, index=True)
    strengths = db.Column(db.Text, nullable=True)
    development_areas = db.Column(db.Text, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='DRAFT', index=True)
    finalized_at = db.Column(db.DateTime, nullable=True, index=True)
    supervisor_reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    supervisor_reviewed_at = db.Column(db.DateTime, nullable=True, index=True)
    supervisor_note = db.Column(db.String(1000), nullable=True)
    trainee_acknowledged_at = db.Column(db.DateTime, nullable=True, index=True)
    trainee_acknowledgment_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow, index=True)

    assignment = db.relationship('FTOProgramAssignment', backref=db.backref('daily_observations', lazy='dynamic'))
    evaluator = db.relationship('User', foreign_keys=[evaluator_id])
    supervisor_reviewer = db.relationship('User', foreign_keys=[supervisor_reviewed_by])


class FTORemediation(db.Model):
    __tablename__ = 'fto_remediation'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('fto_program_assignment.id'), nullable=False, index=True)
    area = db.Column(db.String(120), nullable=False, index=True)
    plan = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='OPEN', index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    verified_at = db.Column(db.DateTime, nullable=True, index=True)
    verification_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow, index=True)

    assignment = db.relationship('FTOProgramAssignment', backref=db.backref('remediation_items', lazy='dynamic'))
    creator = db.relationship('User', foreign_keys=[created_by])
    verifier = db.relationship('User', foreign_keys=[verified_by])
