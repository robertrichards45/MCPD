"""
Command messaging and real-time notification delivery.

SSE stream: GET  /notifications/stream        — persistent event stream per officer
Send:       POST /notifications/send          — commander sends message
Unread:     GET  /notifications/unread        — JSON count + latest messages
Mark read:  POST /notifications/read/<id>     — mark one message read
Inbox:      GET  /notifications/inbox         — HTML message list
"""
import json
import queue
import threading
import time

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    CommandMessage,
    CommandMessageRead,
    ROLE_ASSISTANT_OPERATIONS_OFFICER,
    ROLE_DESK_SGT,
    ROLE_WATCH_COMMANDER,
    ROLE_WEBSITE_CONTROLLER,
    User,
    utcnow_naive,
)
from ..permissions import can_manage_site, effective_role

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

# ── In-process SSE broker ──────────────────────────────────────────────────
# Maps user_id → list of Queue objects (one per open tab)
_subscribers: dict[int, list[queue.Queue]] = {}
_lock = threading.Lock()

_COMMAND_ROLES = {ROLE_WATCH_COMMANDER, ROLE_DESK_SGT, ROLE_ASSISTANT_OPERATIONS_OFFICER, ROLE_WEBSITE_CONTROLLER}


def _can_send(user) -> bool:
    return (
        effective_role(user) in _COMMAND_ROLES
        or can_manage_site(user)
        or bool(getattr(user, 'builder_mode_access', False))
    )


def _subscribe(user_id: int) -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=20)
    with _lock:
        _subscribers.setdefault(user_id, []).append(q)
    return q


def _unsubscribe(user_id: int, q: queue.Queue) -> None:
    with _lock:
        lst = _subscribers.get(user_id, [])
        if q in lst:
            lst.remove(q)
        if not lst:
            _subscribers.pop(user_id, None)


def push_to_user(user_id: int, event_type: str, payload: dict) -> None:
    """Push an SSE event to all open tabs for a given user (called from send route)."""
    data = json.dumps(payload)
    with _lock:
        queues = list(_subscribers.get(user_id, []))
    for q in queues:
        try:
            q.put_nowait({'event': event_type, 'data': data})
        except queue.Full:
            pass


def broadcast(event_type: str, payload: dict) -> None:
    """Broadcast to ALL connected users."""
    data = json.dumps(payload)
    with _lock:
        all_queues = [(uid, q) for uid, qs in _subscribers.items() for q in qs]
    for _, q in all_queues:
        try:
            q.put_nowait({'event': event_type, 'data': data})
        except queue.Full:
            pass


# ── SSE stream ─────────────────────────────────────────────────────────────

@bp.route('/stream')
@login_required
def stream():
    user_id = current_user.id
    q = _subscribe(user_id)

    def generate():
        # Send an immediate heartbeat so the client knows the connection is live
        yield 'event: connected\ndata: {}\n\n'
        try:
            while True:
                try:
                    item = q.get(timeout=25)
                    yield f'event: {item["event"]}\ndata: {item["data"]}\n\n'
                except queue.Empty:
                    # keepalive heartbeat every 25 s
                    yield ': keepalive\n\n'
        except GeneratorExit:
            pass
        finally:
            _unsubscribe(user_id, q)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


# ── Send message ───────────────────────────────────────────────────────────

@bp.route('/send', methods=['POST'])
@login_required
def send():
    if not _can_send(current_user):
        abort(403)

    body = (request.form.get('body') or '').strip()
    subject = (request.form.get('subject') or '').strip() or None
    priority = (request.form.get('priority') or 'Normal').strip()
    recipient_id = request.form.get('recipient_id', type=int)
    is_broadcast = not bool(recipient_id)

    if not body:
        return jsonify({'error': 'Message body required'}), 400

    if priority not in ('Normal', 'Urgent', 'Emergency'):
        priority = 'Normal'

    if recipient_id:
        recipient = User.query.get(recipient_id)
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404
        msg = CommandMessage(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            priority=priority,
            is_broadcast=False,
        )
        db.session.add(msg)
        db.session.commit()
        _deliver(msg, [recipient])
    else:
        # Broadcast to all active users (not just field roles)
        recipients = User.query.filter(User.active.is_(True)).all()
        msg = CommandMessage(
            sender_id=current_user.id,
            recipient_id=None,
            subject=subject,
            body=body,
            priority=priority,
            is_broadcast=True,
        )
        db.session.add(msg)
        db.session.commit()
        _deliver(msg, recipients)

    if request.headers.get('X-Requested-With') == 'fetch':
        return jsonify({'ok': True, 'id': msg.id})
    return redirect(request.referrer or url_for('watch_commander.dashboard'))


def _deliver(msg: CommandMessage, recipients: list) -> None:
    """Push SSE event to each recipient's open connections."""
    payload = {
        'id': msg.id,
        'sender': msg.sender.display_name,
        'subject': msg.subject or '',
        'body': msg.body,
        'priority': msg.priority,
        'is_broadcast': msg.is_broadcast,
        'ts': msg.created_at.strftime('%H:%M') if msg.created_at else '',
    }
    for r in recipients:
        if r.id == msg.sender_id:
            continue
        push_to_user(r.id, 'command_message', payload)


# ── Unread count / inbox JSON ──────────────────────────────────────────────

@bp.route('/unread')
@login_required
def unread():
    uid = current_user.id
    # Personal messages not yet read
    personal = CommandMessage.query.filter(
        CommandMessage.recipient_id == uid,
        CommandMessage.read_at.is_(None),
    ).order_by(CommandMessage.created_at.desc()).limit(10).all()

    # Broadcasts not yet individually acknowledged by this user
    read_broadcast_ids = {
        r.message_id for r in
        CommandMessageRead.query.filter_by(user_id=uid).all()
    }
    broadcasts = CommandMessage.query.filter(
        CommandMessage.is_broadcast.is_(True),
        CommandMessage.sender_id != uid,
        CommandMessage.id.notin_(read_broadcast_ids) if read_broadcast_ids else db.true(),
    ).order_by(CommandMessage.created_at.desc()).limit(5).all()

    msgs = personal + broadcasts
    msgs.sort(key=lambda m: m.created_at, reverse=True)

    return jsonify({
        'count': len(msgs),
        'messages': [
            {
                'id': m.id,
                'sender': m.sender.display_name,
                'subject': m.subject or '',
                'body': m.body[:120],
                'priority': m.priority,
                'is_broadcast': m.is_broadcast,
                'ts': m.created_at.strftime('%Y-%m-%d %H:%M') if m.created_at else '',
            }
            for m in msgs[:8]
        ],
    })


# ── Mark read ──────────────────────────────────────────────────────────────

@bp.route('/read/<int:msg_id>', methods=['POST'])
@login_required
def mark_read(msg_id):
    msg = CommandMessage.query.get_or_404(msg_id)
    uid = current_user.id
    if msg.is_broadcast:
        # Per-user read receipt for broadcasts
        exists = CommandMessageRead.query.filter_by(message_id=msg.id, user_id=uid).first()
        if not exists:
            db.session.add(CommandMessageRead(message_id=msg.id, user_id=uid))
            db.session.commit()
    else:
        if msg.recipient_id and msg.recipient_id != uid:
            abort(403)
        if not msg.read_at:
            msg.read_at = utcnow_naive()
            db.session.commit()
    return jsonify({'ok': True})


# ── Inbox page ─────────────────────────────────────────────────────────────

@bp.route('/inbox')
@login_required
def inbox():
    uid = current_user.id
    messages = (
        CommandMessage.query.filter(
            db.or_(
                CommandMessage.recipient_id == uid,
                CommandMessage.is_broadcast.is_(True),
            )
        )
        .order_by(CommandMessage.created_at.desc())
        .limit(60)
        .all()
    )
    can_compose = _can_send(current_user)
    field_users = (
        User.query.filter(User.active.is_(True), User.id != uid)
        .order_by(User.last_name.asc(), User.first_name.asc())
        .all()
        if can_compose else []
    )
    return render_template(
        'notifications/inbox.html',
        title='Command Messages',
        user=current_user,
        messages=messages,
        can_compose=can_compose,
        field_users=field_users,
    )
