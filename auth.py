import secrets
import bcrypt
from database import (
    get_db, get_setting, get_user_by_username, get_user_by_id,
    log_event,
)


def hash_password(plaintext):
    return bcrypt.hashpw(plaintext.encode('utf-8'), bcrypt.gensalt(rounds=12))


def verify_password(plaintext, hashed):
    if isinstance(hashed, str):
        hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(plaintext.encode('utf-8'), hashed)


def generate_token_c():
    return secrets.token_hex(16)


def create_user(username, email, password_a, password_b, is_admin=False):
    db = get_db()
    a_hash = hash_password(password_a).decode('utf-8')
    b_hash = hash_password(password_b).decode('utf-8')
    token_c = generate_token_c()

    db.execute(
        """INSERT INTO users (username, email, password_a_hash, password_b_hash, token_c, is_admin)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (username, email, a_hash, b_hash, token_c, 1 if is_admin else 0),
    )
    db.commit()
    return token_c


def verify_password_a(username, password_a, ip_address=None):
    user = get_user_by_username(username)

    if user is None:
        return {'success': False, 'error': 'Invalid credentials'}

    if user['is_locked']:
        return {'success': False, 'locked': True, 'error': 'Account is locked. Contact your administrator with your recovery token.'}

    if verify_password(password_a, user['password_a_hash']):
        db = get_db()
        db.execute("UPDATE users SET failed_a_count = 0, updated_at = datetime('now') WHERE id = ?", (user['id'],))
        db.commit()
        return {'success': True, 'requires_b': True, 'user_id': user['id']}

    # Password A failed
    db = get_db()
    new_count = user['failed_a_count'] + 1
    max_attempts = int(get_setting('max_failed_a_attempts') or 5)

    if new_count >= max_attempts:
        db.execute(
            "UPDATE users SET failed_a_count = ?, is_locked = 1, updated_at = datetime('now') WHERE id = ?",
            (new_count, user['id']),
        )
        db.commit()
        log_event(user['id'], 'A_LOCKOUT',
                  f"Account locked after {new_count} failed Password A attempts",
                  ip_address)
        return {
            'success': False,
            'locked': True,
            'error': 'Account locked due to too many failed attempts. Contact your administrator.',
            'notify': True,
            'user_id': user['id'],
            'event_type': 'A_LOCKOUT',
        }
    else:
        db.execute(
            "UPDATE users SET failed_a_count = ?, updated_at = datetime('now') WHERE id = ?",
            (new_count, user['id']),
        )
        db.commit()
        log_event(user['id'], 'A_FAIL',
                  f"Password A failed (attempt {new_count}/{max_attempts})",
                  ip_address)
        remaining = max_attempts - new_count
        return {
            'success': False,
            'error': 'Invalid credentials',
            'remaining': remaining,
        }


def verify_password_b(user_id, password_b, ip_address=None):
    user = get_user_by_id(user_id)

    if user is None:
        return {'success': False, 'error': 'Session expired. Please start over.'}

    if verify_password(password_b, user['password_b_hash']):
        log_event(user['id'], 'LOGIN_SUCCESS', 'Successful two-factor login', ip_address)
        return {'success': True, 'user_id': user['id'], 'is_admin': bool(user['is_admin'])}

    # Password B failed - immediate notification
    log_event(user['id'], 'B_FAIL',
              'Password B verification failed - possible unauthorized access attempt',
              ip_address)
    return {
        'success': False,
        'error': 'Verification failed. Security alert has been triggered.',
        'notify': True,
        'user_id': user['id'],
        'event_type': 'B_FAIL',
    }


def verify_token_c(user_id, provided_token):
    user = get_user_by_id(user_id)
    if user is None:
        return False
    return secrets.compare_digest(user['token_c'], provided_token)


def reset_user(user_id, new_password_a, new_password_b):
    db = get_db()
    a_hash = hash_password(new_password_a).decode('utf-8')
    b_hash = hash_password(new_password_b).decode('utf-8')
    new_token_c = generate_token_c()

    db.execute(
        """UPDATE users
           SET password_a_hash = ?, password_b_hash = ?, token_c = ?,
               is_locked = 0, failed_a_count = 0, updated_at = datetime('now')
           WHERE id = ?""",
        (a_hash, b_hash, new_token_c, user_id),
    )
    db.commit()
    log_event(user_id, 'PASSWORD_RESET', 'Passwords A and B reset by administrator. New Token C generated.')
    return new_token_c
