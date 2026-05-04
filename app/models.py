from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLE_WEBSITE_CONTROLLER = 'WEBSITE_CONTROLLER'
ROLE_WATCH_COMMANDER = 'WATCH_COMMANDER'
ROLE_DESK_SGT = 'DESK_SGT'
ROLE_FIELD_TRAINING = 'FIELD_TRAINING_OFFICER'
ROLE_OFFICER = 'OFFICER'
ROLE_PATROL_OFFICER = 'PATROL_OFFICER'
ROLE_TRUCK_GATE_WATCH_COMMANDER = 'TRUCK_GATE_WATCH_COMMANDER'
ROLE_TRUCK_GATE_PATROL_OFFICER = 'TRUCK_GATE_PATROL_OFFICER'
ROLE_RFI_WATCH_COMMANDER = 'RFI_WATCH_COMMANDER'
ROLE_RFI_PATROL_OFFICER = 'RFI_PATROL_OFFICER'

ROLE_LABELS = {
    'ADMIN': 'Website Controller',
    ROLE_WEBSITE_CONTROLLER: 'Website Controller',
    ROLE_WATCH_COMMANDER: 'Watch Commander',
    ROLE_DESK_SGT: 'Desk Sgt',
    'FIELD_TRAINING': 'Field Training Officer',
    ROLE_FIELD_TRAINING: 'Field Training Officer',
    ROLE_OFFICER: 'Patrol Officer',
    ROLE_PATROL_OFFICER: 'Patrol Officer',
    ROLE_TRUCK_GATE_WATCH_COMMANDER: 'Truck Gate Watch Commander',
    ROLE_TRUCK_GATE_PATROL_OFFICER: 'Truck Gate Patrol Officer',
    ROLE_RFI_WATCH_COMMANDER: 'RFI Watch Commander',
    ROLE_RFI_PATROL_OFFICER: 'RFI Patrol Officer',
}

ALL_PORTAL_ROLES = [
    ROLE_WEBSITE_CONTROLLER,
    ROLE_WATCH_COMMANDER,
    ROLE_DESK_SGT,
    ROLE_FIELD_TRAINING,
    ROLE_PATROL_OFFICER,
    ROLE_TRUCK_GATE_WATCH_COMMANDER,
    ROLE_TRUCK_GATE_PATROL_OFFICER,
    ROLE_RFI_WATCH_COMMANDER,
    ROLE_RFI_PATROL_OFFICER,
]

USMC_INSTALLATIONS = [
    ('MCAS_BEAUFORT',       'MCAS Beaufort, SC'),
    ('MCAS_CHERRY_POINT',   'MCAS Cherry Point, NC'),
    ('MCAS_MIRAMAR',        'MCAS Miramar, CA'),
    ('MCAS_NEW_RIVER',      'MCAS New River, NC'),
    ('MCAS_YUMA',           'MCAS Yuma, AZ'),
    ('MCB_CAMP_LEJEUNE',    'MCB Camp Lejeune, NC'),
    ('MCB_CAMP_PENDLETON',  'MCB Camp Pendleton, CA'),
    ('MCB_HAWAII',          'MCB Hawaii'),
    ('MCB_QUANTICO',        'MCB Quantico, VA'),
    ('MCRD_PARRIS_ISLAND',  'MCRD Parris Island, SC'),
    ('MCRD_SAN_DIEGO',      'MCRD San Diego, CA'),
    ('MCLB_ALBANY',         'MCLB Albany, GA'),
    ('MCLB_BARSTOW',        'MCLB Barstow, CA'),
    ('MCB_29_PALMS',        'MCB Twentynine Palms, CA'),
    ('MCB_CAMP_BUTLER',     'MCB Camp Butler, Japan'),
    ('MCAS_IWAKUNI',        'MCAS Iwakuni, Japan'),
    ('OTHER',               'Other / Not Listed'),
]

INSTALLATION_LABELS = {k: v for k, v in USMC_INSTALLATIONS}


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    users = db.relationship('User', secondary='user_role', back_populates='roles')


class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    display_name_override = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    officer_number = db.Column(db.String(30), unique=True, nullable=True)
    edipi = db.Column(db.String(20), unique=True, nullable=True)
    badge_employee_id = db.Column(db.String(40), nullable=True)
    section_unit = db.Column(db.String(120), nullable=True)
    profile_image_path = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    cac_identifier = db.Column(db.String(255), unique=True, nullable=True)
    cac_enabled = db.Column(db.Boolean, default=False)
    cac_linked_at = db.Column(db.DateTime, nullable=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    role = db.Column(db.String(30), default=ROLE_PATROL_OFFICER, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    pin_hash = db.Column(db.String(255), nullable=True)
    can_grade_cleoc_reports = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True)
    pending_approval = db.Column(db.Boolean, default=False, nullable=False)
    installation = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    supervisor = db.relationship('User', remote_side=[id], backref='direct_reports', foreign_keys=[supervisor_id])
    roles = db.relationship('Role', secondary='user_role', back_populates='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_pin(self, pin_value):
        self.pin_hash = generate_password_hash(pin_value)

    def check_pin(self, pin_value):
        if not self.pin_hash:
            return False
        return check_password_hash(self.pin_hash, pin_value)

    @property
    def normalized_role(self):
        if self.role == 'ADMIN':
            return ROLE_WEBSITE_CONTROLLER
        if self.role == ROLE_OFFICER:
            return ROLE_PATROL_OFFICER
        if self.role == 'FIELD_TRAINING':
            return ROLE_FIELD_TRAINING
        if self.role in ROLE_LABELS:
            return self.role
        return ROLE_PATROL_OFFICER

    @property
    def role_label(self):
        return ROLE_LABELS.get(self.normalized_role, self.normalized_role.replace('_', ' ').title())

    @property
    def display_name(self):
        if self.display_name_override:
            return self.display_name_override
        parts = [part for part in [self.first_name, self.last_name] if part]
        if parts:
            return ' '.join(parts)
        if self.name:
            return self.name
        return self.username

    @property
    def role_keys(self):
        keys = {self.normalized_role}
        keys.update(role.key for role in self.roles if role and role.key)
        return keys

    def has_role(self, role_key):
        return role_key in self.role_keys

    def has_any_role(self, *role_keys):
        return any(role_key in self.role_keys for role_key in role_keys)

    def can_manage_site(self):
        return self.has_role(ROLE_WEBSITE_CONTROLLER)

    def can_manage_team(self):
        return self.has_any_role(ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER, ROLE_DESK_SGT)

    def can_manage_roster(self):
        return self.normalized_role in {ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER, ROLE_DESK_SGT}

class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    version_label = db.Column(db.String(50), nullable=True)
    contains_pii = db.Column(db.Boolean, default=False, nullable=False)
    retention_mode = db.Column(db.String(40), default='full_save_allowed', nullable=False, index=True)
    allow_email = db.Column(db.Boolean, default=True, nullable=False)
    allow_download = db.Column(db.Boolean, default=True, nullable=False)
    allow_completed_save = db.Column(db.Boolean, default=True, nullable=False)
    allow_blank_print = db.Column(db.Boolean, default=True, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    official_source_url = db.Column(db.String(500), nullable=True)
    official_source_version = db.Column(db.String(80), nullable=True)
    official_source_hash = db.Column(db.String(64), nullable=True)
    official_source_last_checked_at = db.Column(db.DateTime, nullable=True)
    official_source_last_status = db.Column(db.Text, nullable=True)
    source_auto_update_enabled = db.Column(db.Boolean, default=False, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)


class SavedForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False, index=True)
    officer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='DRAFT', index=True)
    title = db.Column(db.String(200), nullable=True)
    field_data_json = db.Column(db.Text, nullable=False, default='{}')
    rendered_output_path = db.Column(db.String(255), nullable=True)
    access_scope = db.Column(db.String(40), nullable=False, default='OFFICER_AND_WATCH_COMMAND')
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive, index=True)

    form = db.relationship('Form', foreign_keys=[form_id], backref='saved_records')
    officer = db.relationship('User', foreign_keys=[officer_user_id], backref='saved_forms')


class SavedFormAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    saved_form_id = db.Column(db.Integer, db.ForeignKey('saved_form.id'), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)

    saved_form = db.relationship('SavedForm', foreign_keys=[saved_form_id], backref='audits')
    actor = db.relationship('User', foreign_keys=[actor_user_id])


class OrderDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=True, index=True)
    source_type = db.Column(db.String(40), nullable=True, index=True)
    source_group = db.Column(db.String(80), nullable=True, index=True)
    order_number = db.Column(db.String(80), nullable=True, index=True)
    memo_number = db.Column(db.String(80), nullable=True, index=True)
    issuing_authority = db.Column(db.String(120), nullable=True)
    issue_date = db.Column(db.DateTime, nullable=True, index=True)
    revision_date = db.Column(db.DateTime, nullable=True, index=True)
    source_version = db.Column(db.String(80), nullable=True, index=True)
    audience_tags = db.Column(db.String(255), nullable=True)
    topic_tags = db.Column(db.String(255), nullable=True)
    version_label = db.Column(db.String(50), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)
    parser_confidence = db.Column(db.Float, nullable=True)
    superseded_by_id = db.Column(db.Integer, db.ForeignKey('order_document.id'), nullable=True, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive, index=True)
    last_indexed_at = db.Column(db.DateTime, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)

    uploader = db.relationship('User', foreign_keys=[uploaded_by], backref='order_uploads')
    superseded_by = db.relationship('OrderDocument', remote_side=[id], foreign_keys=[superseded_by_id])


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    scope = db.Column(db.String(40), nullable=False, default='ALL', index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)

    creator = db.relationship('User', foreign_keys=[created_by], backref='announcements_created')

class TrainingRoster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path_original = db.Column(db.String(255), nullable=False)
    file_path_compiled = db.Column(db.String(255), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)
    status = db.Column(db.String(20), default='ACTIVE')

class TrainingSignature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roster_id = db.Column(db.Integer, db.ForeignKey('training_roster.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    signature_path = db.Column(db.String(255), nullable=False)
    signed_at = db.Column(db.DateTime, default=utcnow_naive)
    comment = db.Column(db.String(255), nullable=True)

class StatCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    target_value = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

class OfficerStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('stat_category.id'))
    year_key = db.Column(db.String(9), nullable=False)
    value = db.Column(db.Integer, default=0)

class StatsUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    parse_summary_json = db.Column(db.Text, nullable=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)


class EnrollmentCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    user = db.relationship('User', foreign_keys=[user_id], backref='enrollment_codes')


class OfficerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    rank = db.Column(db.String(50), nullable=True)
    unit = db.Column(db.String(120), nullable=True)
    duty_phone = db.Column(db.String(30), nullable=True)
    personal_phone = db.Column(db.String(30), nullable=True)
    personal_email = db.Column(db.String(120), nullable=True)
    emergency_contact_name = db.Column(db.String(120), nullable=True)
    emergency_contact_relationship = db.Column(db.String(80), nullable=True)
    emergency_contact_phone = db.Column(db.String(30), nullable=True)
    emergency_contact_address = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class EmergencyContact(db.Model):
    __tablename__ = 'emergency_contact'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    relationship = db.Column(db.String(80), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    secondary_phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    officer = db.relationship('User', backref=db.backref('emergency_contacts', lazy='dynamic', order_by='EmergencyContact.id'))


class CleoFormData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    page_key = db.Column(db.String(100), nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive)

class CleoFormLayout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_key = db.Column(db.String(100), nullable=False, unique=True)
    layout_json = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive)

class CleoFormFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    page_key = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    enclosure_no = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)

class CleoReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='DRAFT', index=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)
    returned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    graded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive)

    owner = db.relationship('User', foreign_keys=[user_id], backref='cleo_reports')
    submitter = db.relationship('User', foreign_keys=[submitted_by])
    returner = db.relationship('User', foreign_keys=[returned_by])
    grader = db.relationship('User', foreign_keys=[graded_by])

class CleoReportPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('cleo_report.id'))
    page_key = db.Column(db.String(100), nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive)


class CleoReportGrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('cleo_report.id'), nullable=False, index=True)
    grader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=True)
    disposition = db.Column(db.String(20), nullable=False, default='RETURNED', index=True)
    summary = db.Column(db.Text, nullable=True)
    officer_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)

    report = db.relationship('CleoReport', foreign_keys=[report_id], backref='grades')
    grader = db.relationship('User', foreign_keys=[grader_id])


class CleoReportAnnotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('cleo_report.id'), nullable=False, index=True)
    grade_id = db.Column(db.Integer, db.ForeignKey('cleo_report_grade.id'), nullable=False, index=True)
    page_key = db.Column(db.String(100), nullable=False, index=True)
    field_idx = db.Column(db.Integer, nullable=False)
    field_label = db.Column(db.String(255), nullable=True)
    field_value_snapshot = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=False, default='REQUIRED_FIX', index=True)
    note = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)

    report = db.relationship('CleoReport', foreign_keys=[report_id], backref='annotations')
    grade = db.relationship('CleoReportGrade', foreign_keys=[grade_id], backref='annotations')
    creator = db.relationship('User', foreign_keys=[created_by])

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='DRAFT')
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive)

class ReportAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))
    file_path = db.Column(db.String(255), nullable=False)
    page_key = db.Column(db.String(100), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)

class ReportPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=True)

class ReportCoAuthor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class ReportGrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))
    grader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    score = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    required_fixes = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, default=utcnow_naive)


class ReconstructionCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    incident_date = db.Column(db.String(10), nullable=True)  # YYYY-MM-DD (string keeps UI simple)
    location = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive)


class ReconstructionVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('reconstruction_case.id'))
    unit = db.Column(db.String(50), nullable=True)  # Vehicle 1 / Unit 12 / etc
    make_model = db.Column(db.String(120), nullable=True)
    direction = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)


class ReconstructionMeasurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('reconstruction_case.id'))
    label = db.Column(db.String(120), nullable=False)
    value = db.Column(db.String(50), nullable=True)
    units = db.Column(db.String(20), nullable=True)  # ft, m, mph, deg, etc.
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)


class ReconstructionAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('reconstruction_case.id'))
    file_path = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(30), nullable=True)  # photo, pdf, video, diagram
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)


class TruckGateCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    normalized_name = db.Column(db.String(200), unique=True, nullable=False)
    phone_number = db.Column(db.String(30), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class TruckGateDriver(db.Model):
    __table_args__ = (
        db.UniqueConstraint('license_number', 'license_state', name='uq_truck_gate_driver_license'),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('truck_gate_company.id'), nullable=True, index=True)
    full_name = db.Column(db.String(200), nullable=False)
    normalized_name = db.Column(db.String(200), nullable=False, index=True)
    license_number = db.Column(db.String(40), nullable=True)
    license_state = db.Column(db.String(10), nullable=True)
    phone_number = db.Column(db.String(30), nullable=True)
    vehicle_type = db.Column(db.String(30), nullable=True)
    visit_type = db.Column(db.String(50), nullable=True)
    destination = db.Column(db.String(120), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    company = db.relationship('TruckGateCompany', backref='drivers')


class TruckGateVehicle(db.Model):
    __table_args__ = (
        db.UniqueConstraint('plate_number', 'plate_state', name='uq_truck_gate_vehicle_plate'),
    )

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('truck_gate_driver.id'), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('truck_gate_company.id'), nullable=True, index=True)
    plate_number = db.Column(db.String(30), nullable=True)
    plate_state = db.Column(db.String(10), nullable=True)
    make_model_color = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    driver = db.relationship('TruckGateDriver', backref='vehicles')
    company = db.relationship('TruckGateCompany', backref='vehicles')


class TruckGateImportRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(255), nullable=False)
    source_path = db.Column(db.String(255), nullable=True)
    row_count = db.Column(db.Integer, default=0)
    inserted_count = db.Column(db.Integer, default=0)
    updated_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class TruckGateLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('truck_gate_driver.id'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('truck_gate_company.id'), nullable=True, index=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('truck_gate_vehicle.id'), nullable=True, index=True)
    log_date = db.Column(db.String(10), nullable=False, index=True)
    daily_file_name = db.Column(db.String(255), nullable=True)
    inspection_type = db.Column(db.String(50), nullable=True)
    scan_token = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)

    driver = db.relationship('TruckGateDriver', backref='gate_logs')
    company = db.relationship('TruckGateCompany', backref='gate_logs')
    vehicle = db.relationship('TruckGateVehicle', backref='gate_logs')


class RfiWeaponProfile(db.Model):
    __table_args__ = (
        db.UniqueConstraint('officer_number', name='uq_rfi_profile_officer_number'),
        db.UniqueConstraint('radio_identifier', name='uq_rfi_profile_radio_identifier'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False, index=True)
    officer_number = db.Column(db.String(30), nullable=True, index=True)
    role_level = db.Column(db.String(40), nullable=True)
    rack_number = db.Column(db.String(30), nullable=True, index=True)
    weapon_serial_number = db.Column(db.String(80), nullable=True, index=True)
    weapon_type = db.Column(db.String(60), nullable=True)
    oc_identifier = db.Column(db.String(30), nullable=True, index=True)
    radio_identifier = db.Column(db.String(30), nullable=True, index=True)
    is_command_level = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    user = db.relationship('User', foreign_keys=[user_id], backref='rfi_weapon_profile')

    @property
    def display_name(self):
        return ' '.join(part for part in [self.first_name, self.last_name] if part).strip()


class RfiAppointmentUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default='PENDING_REVIEW')
    extracted_first_name = db.Column(db.String(80), nullable=True)
    extracted_last_name = db.Column(db.String(80), nullable=True)
    extracted_officer_number = db.Column(db.String(30), nullable=True)
    extracted_weapon_serial_number = db.Column(db.String(80), nullable=True)
    extracted_rack_number = db.Column(db.String(30), nullable=True)
    committed_profile_id = db.Column(db.Integer, db.ForeignKey('rfi_weapon_profile.id'), nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    committed_profile = db.relationship('RfiWeaponProfile', foreign_keys=[committed_profile_id], backref='source_appointment_uploads')


class ArmoryAsset(db.Model):
    __table_args__ = (
        db.UniqueConstraint('asset_type', 'serial_number', name='uq_armory_asset_type_serial'),
    )

    id = db.Column(db.Integer, primary_key=True)
    asset_type = db.Column(db.String(40), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    rack_number = db.Column(db.String(30), nullable=True, index=True)
    serial_number = db.Column(db.String(80), nullable=False, index=True)
    radio_identifier = db.Column(db.String(30), nullable=True, index=True)
    oc_identifier = db.Column(db.String(30), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='AVAILABLE', nullable=False, index=True)
    current_holder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    current_holder = db.relationship('User', foreign_keys=[current_holder_id], backref='armory_assets_held')


class ArmoryOfficerCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    revoked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    revoked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='armory_cards')


class ArmoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('armory_asset.id'), nullable=False, index=True)
    card_id = db.Column(db.Integer, db.ForeignKey('armory_officer_card.id'), nullable=True, index=True)
    action = db.Column(db.String(20), nullable=False, index=True)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False, index=True)
    rounds_count = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, index=True)
    voided_at = db.Column(db.DateTime, nullable=True)
    void_reason = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='armory_transactions')
    asset = db.relationship('ArmoryAsset', foreign_keys=[asset_id], backref='transactions')
    card = db.relationship('ArmoryOfficerCard', foreign_keys=[card_id], backref='transactions')


class VehicleInspection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inspection_date = db.Column(db.String(10), nullable=False, index=True)
    vehicle_number = db.Column(db.String(40), nullable=False, index=True)
    mileage = db.Column(db.String(40), nullable=True)
    fuel_level = db.Column(db.String(20), nullable=True)
    condition_json = db.Column(db.Text, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    officer_signature = db.Column(db.Text, nullable=True)
    officer_signed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    officer_signed_at = db.Column(db.DateTime, nullable=True)
    sgt_signature = db.Column(db.Text, nullable=True)
    sgt_signed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    sgt_signed_at = db.Column(db.DateTime, nullable=True)
    watch_commander_signature = db.Column(db.Text, nullable=True)
    watch_commander_signed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    watch_commander_signed_at = db.Column(db.DateTime, nullable=True)
    correction_reason = db.Column(db.String(255), nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='DRAFT', nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)


# Approval statuses for IncidentPacket
PACKET_APPROVAL_PENDING = 'PENDING'
PACKET_APPROVAL_APPROVED = 'APPROVED'
PACKET_APPROVAL_NEEDS_CORRECTION = 'NEEDS_CORRECTION'


class IncidentPacket(db.Model):
    """Lightweight record of a submitted mobile incident packet for supervisor review."""
    id = db.Column(db.Integer, primary_key=True)
    officer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    submitted_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False, index=True)
    call_type = db.Column(db.String(80), nullable=True)
    occurred_date = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.String(500), nullable=True)
    form_count = db.Column(db.Integer, default=0)
    statement_count = db.Column(db.Integer, default=0)
    packet_json = db.Column(db.Text, nullable=True)
    validation_json = db.Column(db.Text, nullable=True)
    approval_status = db.Column(db.String(20), default=PACKET_APPROVAL_PENDING, nullable=False, index=True)
    reviewer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    supervisor_notes = db.Column(db.Text, nullable=True)

    officer = db.relationship('User', foreign_keys=[officer_user_id], backref='incident_packets')
    reviewer = db.relationship('User', foreign_keys=[reviewer_user_id], backref='reviewed_packets')


BOLO_STATUS_ACTIVE = 'ACTIVE'
BOLO_STATUS_LOCATED = 'LOCATED'
BOLO_STATUS_CANCELLED = 'CANCELLED'

BOLO_THREAT_LOW = 'LOW'
BOLO_THREAT_MODERATE = 'MODERATE'
BOLO_THREAT_HIGH = 'HIGH'
BOLO_THREAT_ARMED = 'ARMED'


class BOLOEntry(db.Model):
    __tablename__ = 'bolo_entry'
    id = db.Column(db.Integer, primary_key=True)

    subject_name = db.Column(db.String(120), nullable=False, index=True)
    aliases = db.Column(db.String(255), nullable=True)
    race = db.Column(db.String(40), nullable=True)
    sex = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    height = db.Column(db.String(20), nullable=True)
    weight = db.Column(db.String(20), nullable=True)
    hair = db.Column(db.String(40), nullable=True)
    eyes = db.Column(db.String(40), nullable=True)

    offense = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    vehicle_description = db.Column(db.String(255), nullable=True)
    vehicle_plate = db.Column(db.String(40), nullable=True)

    threat_level = db.Column(db.String(20), default=BOLO_THREAT_LOW, nullable=False, index=True)
    photo_path = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(20), default=BOLO_STATUS_ACTIVE, nullable=False, index=True)
    expiration_date = db.Column(db.String(20), nullable=True)

    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    creator = db.relationship('User', foreign_keys=[created_by], backref='bolo_entries')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_bolos')


class QualificationCategory(db.Model):
    """Defines a required qualification type (e.g. Annual Firearms, CPR, Use of Force)."""
    __tablename__ = 'qualification_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    validity_days = db.Column(db.Integer, default=365, nullable=False)
    warn_days_before = db.Column(db.Integer, default=30, nullable=False)
    required_roles = db.Column(db.Text, nullable=True)  # JSON list of role keys, null = all roles
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    records = db.relationship('OfficerQualification', backref='category', lazy='dynamic')


class OfficerQualification(db.Model):
    """A qualification completion record for one officer."""
    __tablename__ = 'officer_qualification'
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('qualification_category.id'), nullable=False, index=True)
    completed_date = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    expiration_date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    notes = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    logged_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    officer = db.relationship('User', foreign_keys=[officer_id], backref='qualifications')
    logger = db.relationship('User', foreign_keys=[logged_by], backref='logged_qualifications')


# ---------------------------------------------------------------------------
# Phase 9 — Officer Performance / Element Tracking
# ---------------------------------------------------------------------------

PERF_STATUS_PENDING  = 'PENDING'
PERF_STATUS_APPROVED = 'APPROVED'
PERF_STATUS_REJECTED = 'REJECTED'


class YearCycle(db.Model):
    """Tracks which performance year is active; old years are archived, not deleted."""
    __tablename__ = 'year_cycle'
    id          = db.Column(db.Integer, primary_key=True)
    year        = db.Column(db.Integer, unique=True, nullable=False, index=True)
    is_active   = db.Column(db.Boolean, default=True, nullable=False, index=True)
    started_at  = db.Column(db.DateTime, default=utcnow_naive)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class YearElement(db.Model):
    """A performance element (e.g. Traffic Stops) defined for a specific year."""
    __tablename__ = 'year_element'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    category    = db.Column(db.String(80),  nullable=True)
    goal_value  = db.Column(db.Integer,     nullable=False, default=0)
    description = db.Column(db.Text,        nullable=True)
    year        = db.Column(db.Integer,     nullable=False, index=True)
    active      = db.Column(db.Boolean,     default=True, nullable=False)
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=utcnow_naive)

    creator     = db.relationship('User', foreign_keys=[created_by])
    submissions = db.relationship('YearSubmission', backref='element', lazy='dynamic')


class YearSubmission(db.Model):
    """One officer's activity entry. Only APPROVED entries count toward stats."""
    __tablename__ = 'year_submission'
    id             = db.Column(db.Integer, primary_key=True)
    officer_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    element_id     = db.Column(db.Integer, db.ForeignKey('year_element.id'), nullable=False, index=True)
    quantity       = db.Column(db.Integer, nullable=False, default=1)
    notes          = db.Column(db.Text,    nullable=True)
    submitted_date = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    year           = db.Column(db.Integer, nullable=False, index=True)
    status         = db.Column(db.String(20), default=PERF_STATUS_PENDING, nullable=False, index=True)
    reviewed_by    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    review_comment = db.Column(db.Text,    nullable=True)
    reviewed_at    = db.Column(db.DateTime, nullable=True)
    created_at     = db.Column(db.DateTime, default=utcnow_naive)

    officer  = db.relationship('User', foreign_keys=[officer_id],  backref='perf_submissions')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='perf_reviewed')

