import os
import re
import uuid
import socket
import base64
import tempfile
import urllib.parse
import requests
import joblib
import numpy as np
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, abort, make_response
from flask_login import login_required, current_user
from dotenv import load_dotenv
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from app.extensions import db, csrf
from app.models.evidence import Evidence, EvidenceHash, EvidenceMetadata
from app.models.case import Case, CaseEvidence
from app.models.custody import CustodyRecord
from app.models.tamper import TamperAlert
from app.models.notification import Notification
from app.models.user import User
from app.evidence.forms import EvidenceUploadForm
from app.auth.decorators import role_required
from app.utils.crypto import generate_file_hash, encrypt_file, decrypt_file
from app.utils.metadata_extractor import extract_metadata
from app.utils.qr_generator import generate_evidence_qr
from app.utils.audit_logger import log_audit_action
from app.models.deletion_request import DeletionRequest
from datetime import datetime

evidence_bp = Blueprint('evidence', __name__, url_prefix='/evidence')

@evidence_bp.route('/')
@login_required
def list_evidence():
    # Advanced search and filtering parameters
    query_param = request.args.get('q', '')
    category_param = request.args.get('category', '')
    status_param = request.args.get('status', '')
    case_param = request.args.get('case', '')
    date_start_param = request.args.get('date_start', '')
    date_end_param = request.args.get('date_end', '')
    
    # Base query
    ev_query = Evidence.query
    
    # Filter based on search bar (filename, title, hash, remark)
    if query_param:
        search_filter = f"%{query_param}%"
        ev_query = ev_query.filter(
            db.or_(
                Evidence.file_name.like(search_filter),
                Evidence.title.like(search_filter),
                Evidence.original_hash.like(search_filter),
                Evidence.remarks.like(search_filter)
            )
        )
        
    # Categories
    if category_param:
        ev_query = ev_query.filter(Evidence.category == category_param)
        
    # Statuses
    if status_param:
        ev_query = ev_query.filter(Evidence.status == status_param)
        
    # Case links filter
    if case_param:
        ev_query = ev_query.join(CaseEvidence).join(Case).filter(Case.case_number == case_param)
        
    # Date Range filter
    if date_start_param:
        try:
            start_date = datetime.strptime(date_start_param, '%Y-%m-%d')
            ev_query = ev_query.filter(Evidence.upload_date >= start_date)
        except ValueError:
            pass
            
    if date_end_param:
        try:
            end_date = datetime.strptime(date_end_param, '%Y-%m-%d')
            # include the whole day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            ev_query = ev_query.filter(Evidence.upload_date <= end_date)
        except ValueError:
            pass
            
    # Sort
    evidence_items = ev_query.order_by(Evidence.upload_date.desc()).all()
    cases = Case.query.all()
    
    return render_template(
        'evidence/list.html', 
        evidence=evidence_items, 
        cases=cases,
        query=query_param,
        category=category_param,
        status=status_param,
        case=case_param,
        date_start=date_start_param,
        date_end=date_end_param
    )

@evidence_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'investigator')
def upload():
    form = EvidenceUploadForm()
    
    if form.validate_on_submit():
        uploaded_files = request.files.getlist('files')
        
        # Verify that files were selected
        if not uploaded_files or uploaded_files[0].filename == '':
            flash('❌ Please select at least one file to upload.', 'danger')
            return render_template('evidence/upload.html', form=form)
            
        case_id = form.case_id.data
        case_obj = Case.query.get(case_id)
        if not case_obj:
            flash('❌ Linked case files not found.', 'danger')
            return render_template('evidence/upload.html', form=form)

        uploaded_count = 0
        
        for file in uploaded_files:
            # Generate temporary file path to extract hash and metadata
            fd, temp_path = tempfile.mkstemp()
            os.close(fd)
            
            try:
                # Save the file temporarily
                file.save(temp_path)
                
                # 1. Compute HASH
                raw_hash = generate_file_hash(temp_path)
                
                # Check for duplicates of this hash in DB
                existing = Evidence.query.filter_by(original_hash=raw_hash).first()
                if existing:
                    flash(f"⚠️ Evidence item '{file.filename}' already exists in system database (SHA-256 Match). Skip uploading duplicate.", "warning")
                    os.remove(temp_path)
                    continue
                
                # Check file size & metadata
                file_size = os.path.getsize(temp_path)
                
                # 2. Encrypt using AES-256 and store in encrypted dir
                unique_name = f"{uuid.uuid4().hex}.enc"
                encrypted_path = os.path.join(current_app.config['ENCRYPTED_FOLDER'], unique_name)
                encrypt_file(temp_path, encrypted_path, current_app.config['RAW_ENCRYPTION_KEY'])
                
                # Create Evidence DB Record
                evidence = Evidence(
                    title=f"{form.title.data} - {file.filename}" if len(uploaded_files) > 1 else form.title.data,
                    file_name=file.filename,
                    stored_name=unique_name,
                    file_size=file_size,
                    mime_type=file.content_type or 'application/octet-stream',
                    category=form.category.data,
                    original_hash=raw_hash,
                    is_encrypted=True,
                    is_tampered=False,
                    status='Verified',
                    uploaded_by_id=current_user.id,
                    remarks=form.remarks.data
                )
                db.session.add(evidence)
                db.session.flush() # Populate ID before adding relationships
                
                # Link to Case
                case_link = CaseEvidence(
                    case_id=case_obj.id,
                    evidence_id=evidence.id,
                    linked_by=current_user.id
                )
                db.session.add(case_link)
                
                # Store Initial Verification Hash record
                init_hash = EvidenceHash(
                    evidence_id=evidence.id,
                    hash_val=raw_hash,
                    verified_by_id=current_user.id,
                    status='Verified'
                )
                db.session.add(init_hash)
                
                # Extract and store metadata
                metadata_dict = extract_metadata(temp_path, form.category.data)
                for key, val in metadata_dict.items():
                    meta_entry = EvidenceMetadata(
                        evidence_id=evidence.id,
                        meta_key=key,
                        meta_value=str(val)
                    )
                    db.session.add(meta_entry)
                    
                # Add Initial Custody Log
                custody = CustodyRecord(
                    evidence_id=evidence.id,
                    from_user_id=None,
                    to_user_id=current_user.id,
                    action='Uploaded',
                    remarks=f"Evidence acquired and encrypted under AES-256 CBC. Remarks: {form.remarks.data}"
                )
                db.session.add(custody)
                
                # Generate QR code
                generate_evidence_qr(raw_hash)
                
                # Commit all entries for this file
                db.session.commit()
                uploaded_count += 1
                
                log_audit_action("Uploaded Evidence", current_user.id, f"File: {evidence.file_name}, Hash: {raw_hash}")
                
                # Send notifications to admin
                admins = User.query.filter(User.roles.any(name='admin')).all()
                for admin in admins:
                    admin_notif = Notification(
                        user_id=admin.id,
                        title="New Evidence Uploaded",
                        message=f"Investigator {current_user.username} uploaded evidence '{evidence.file_name}' for case {case_obj.case_number}.",
                        type="upload"
                    )
                    db.session.add(admin_notif)
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving uploaded evidence: {str(e)}")
                flash(f"❌ Failed to process '{file.filename}': {str(e)}", "danger")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        if uploaded_count > 0:
            flash(f"✅ Successfully uploaded and encrypted {uploaded_count} evidence item(s).", "success")
            return redirect(url_for('evidence.list_evidence'))
            
    return render_template('evidence/upload.html', form=form)

@evidence_bp.route('/<int:evidence_id>/request-deletion', methods=['POST'])
@login_required
@role_required('admin', 'investigator', 'staff')
def request_deletion(evidence_id):
    """Staff can request deletion of evidence; creates a DeletionRequest entry."""
    evidence = Evidence.query.get_or_404(evidence_id)
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for deletion request.', 'warning')
        return redirect(url_for('evidence.detail', id=evidence_id))
    dr = DeletionRequest(
        evidence_id=evidence.id,
        requested_by=current_user.id,
        reason=reason,
        status='pending'
    )
    db.session.add(dr)
    
    # Notify admins
    admins = User.query.filter(User.roles.any(name='admin')).all()
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            title="New Deletion Request",
            message=f"{current_user.fullname} requested deletion for evidence ID {evidence.id}. Reason: {reason}",
            type="alert"
        )
        db.session.add(notif)
        
    db.session.commit()
    flash('Deletion request submitted for admin review.', 'info')
    return redirect(url_for('evidence.detail', id=evidence_id))

@evidence_bp.route('/<int:id>')
@login_required
def detail(id):
    evidence = Evidence.query.get_or_404(id)
    
    # Generate static QR code if it doesn't exist on disk
    qr_filename = f"{evidence.original_hash}.png"
    qr_path = os.path.join(current_app.static_folder, 'qr', qr_filename)
    if not os.path.exists(qr_path):
        generate_evidence_qr(evidence.original_hash)
        
    qr_url = url_for('static', filename=f"qr/{qr_filename}")
    
    return render_template('evidence/detail.html', evidence=evidence, qr_url=qr_url)

@evidence_bp.route('/<int:id>/verify', methods=['POST'])
@login_required
def verify(id):
    """
    Triggers manual cryptographical re-verification of the evidence item.
    Decrypts encrypted file in memory, computes hash, and compares with original stored hash.
    """
    evidence = Evidence.query.get_or_404(id)
    
    # Path of encrypted file
    encrypted_path = os.path.join(current_app.config['ENCRYPTED_FOLDER'], evidence.stored_name)
    if not os.path.exists(encrypted_path):
        evidence.status = 'Tampered'
        evidence.is_tampered = True
        db.session.commit()
        
        # Create Tamper Alert
        alert = TamperAlert(
            evidence_id=evidence.id,
            alert_type='MISSING_FILE',
            description=f"Encrypted binary file '{evidence.stored_name}' missing from store server!"
        )
        db.session.add(alert)
        db.session.commit()
        
        log_audit_action("Evidence Verification Failed", current_user.id, f"Missing encrypted file for Evidence ID {evidence.id}")
        return jsonify({'status': 'Tampered', 'message': 'Encrypted file not found on server!'}), 400

    # Decrypt to a temporary path to verify hash
    fd, temp_decrypted_path = tempfile.mkstemp()
    os.close(fd)
    
    try:
        decrypt_file(encrypted_path, temp_decrypted_path, current_app.config['RAW_ENCRYPTION_KEY'])
        recalculated_hash = generate_file_hash(temp_decrypted_path)
        
        # Compare
        if recalculated_hash == evidence.original_hash:
            evidence.status = 'Verified'
            evidence.is_tampered = False
            db_status = 'Verified'
            msg = "Evidence verification successful. Cryptographic hash matches the original signature."
        else:
            evidence.status = 'Tampered'
            evidence.is_tampered = True
            db_status = 'Tampered'
            msg = f"CRITICAL: Cryptographic mismatch! Current hash ({recalculated_hash}) differs from original."
            
            # Save Tamper Alert
            alert = TamperAlert(
                evidence_id=evidence.id,
                alert_type='HASH_MISMATCH',
                description=msg
            )
            db.session.add(alert)
            
            # Send Notification to admins
            admins = User.query.filter(User.roles.any(name='admin')).all()
            for admin in admins:
                notif = Notification(
                    user_id=admin.id,
                    title="🚨 CRITICAL: Tampering Detected",
                    message=f"Tampering detected on evidence file '{evidence.file_name}' for Case {evidence.current_case.case_number if evidence.current_case else 'N/A'}.",
                    type="tamper"
                )
                db.session.add(notif)
                
        # Write Verification Hash Entry
        verify_log = EvidenceHash(
            evidence_id=evidence.id,
            hash_val=recalculated_hash,
            verified_by_id=current_user.id,
            status=db_status
        )
        db.session.add(verify_log)
        
        # Add Custody Record
        custody = CustodyRecord(
            evidence_id=evidence.id,
            from_user_id=current_user.id,
            to_user_id=current_user.id,
            action='Verified Integrity',
            remarks=f"Integrity check performed. Result: {db_status}. Hash computed: {recalculated_hash}"
        )
        db.session.add(custody)
        
        db.session.commit()
        log_audit_action("Verified Evidence", current_user.id, f"Evidence ID: {evidence.id}, Result: {db_status}")
        
        return jsonify({
            'status': db_status,
            'message': msg,
            'recalculated_hash': recalculated_hash,
            'original_hash': evidence.original_hash
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity verification error: {str(e)}")
        return jsonify({'status': 'Error', 'message': f'Verification engine failed: {str(e)}'}), 500
    finally:
        if os.path.exists(temp_decrypted_path):
            os.remove(temp_decrypted_path)

@evidence_bp.route('/<int:id>/download')
@login_required
def download(id):
    """
    Decrypts the file and serves it to authorized users (Admins, Investigators, and assigned cases).
    """
    evidence = Evidence.query.get_or_404(id)
    
    # Check permissions
    if not (current_user.has_role('admin') or current_user.has_role('investigator') or current_user.has_role('auditor')):
        abort(403)
        
    if current_user.has_role('investigator') and evidence.current_case:
        # Investigator must be the assigned investigator for the case
        if evidence.current_case.investigator_id != current_user.id:
            abort(403)
            
    encrypted_path = os.path.join(current_app.config['ENCRYPTED_FOLDER'], evidence.stored_name)
    if not os.path.exists(encrypted_path):
        flash('❌ Encrypted evidence binary not found on target server.', 'danger')
        return redirect(url_for('evidence.detail', id=evidence.id))
        
    # Decrypt to a temporary file
    temp_dir = tempfile.gettempdir()
    decrypted_temp_path = os.path.join(temp_dir, evidence.file_name)
    
    try:
        decrypt_file(encrypted_path, decrypted_temp_path, current_app.config['RAW_ENCRYPTION_KEY'])
        
        log_audit_action("Downloaded Evidence", current_user.id, f"File: {evidence.file_name}")
        
        # Log to Custody history
        custody = CustodyRecord(
            evidence_id=evidence.id,
            from_user_id=None,
            to_user_id=current_user.id,
            action='Downloaded / Extracted',
            remarks=f"Evidence downloaded and decrypted by {current_user.fullname}."
        )
        db.session.add(custody)
        db.session.commit()
        
        # Send file with explicit Content-Disposition header for proper filename
        response = make_response(send_file(decrypted_temp_path, mimetype=evidence.mime_type or 'application/octet-stream'))
        response.headers['Content-Disposition'] = f'attachment; filename="{evidence.file_name}"'
        return response
        
    except Exception as e:
        current_app.logger.error(f"Download decryption failure: {str(e)}")
        flash('❌ Decryption and acquisition engine failed.', 'danger')
        return redirect(url_for('evidence.detail', id=evidence.id))

@evidence_bp.route('/verify/<string:hash_val>')
def public_verify(hash_val):
    """
    Public QR verification page. Displays details matching the hash.
    No login required so external parties scanning QR can check validity.
    """
    evidence = Evidence.query.filter_by(original_hash=hash_val).first_or_404()
    return render_template('evidence/verify.html', evidence=evidence)

@evidence_bp.route('/admin/deletion-requests')
@login_required
@role_required('admin')
def admin_deletion_requests():
    """Admin view for pending evidence deletion approval requests.
    Currently renders a placeholder template; replace the query logic with
    actual deletion request model when available.
    """
    # Fetch pending deletion requests for admin review
    pending_requests = DeletionRequest.query.filter_by(status='pending').all()
    return render_template('evidence/admin_deletion_requests.html', requests=pending_requests)

@evidence_bp.route('/admin/deletion-requests/<int:id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_deletion(id):
    req = DeletionRequest.query.get_or_404(id)
    if req.status != 'pending':
        flash('Request is not pending.', 'warning')
        return redirect(url_for('evidence.admin_deletion_requests'))
    
    evidence = req.evidence
    
    # Notify Requester before deleting evidence
    notif = Notification(
        user_id=req.requested_by,
        title="Deletion Request Approved",
        message=f"Your request to delete evidence '{evidence.title}' was approved.",
        type="alert"
    )
    db.session.add(notif)
    
    # Hard delete evidence
    encrypted_path = os.path.join(current_app.config['ENCRYPTED_FOLDER'], evidence.stored_name)
    if os.path.exists(encrypted_path):
        try:
            os.remove(encrypted_path)
        except Exception as e:
            current_app.logger.error(f"Failed to delete file {encrypted_path}: {e}")
            
    db.session.delete(evidence)
    db.session.commit()
    
    log_audit_action('Approved Evidence Deletion', current_user.id, f'Evidence ID {evidence.id}')
    flash('Evidence deletion request approved and evidence removed.', 'success')
    return redirect(url_for('evidence.admin_deletion_requests'))

@evidence_bp.route('/admin/deletion-requests/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_deletion(id):
    req = DeletionRequest.query.get_or_404(id)
    if req.status != 'pending':
        flash('Request is not pending.', 'warning')
        return redirect(url_for('evidence.admin_deletion_requests'))
    
    req.status = 'rejected'
    req.reviewed_by = current_user.id
    req.reviewed_at = db.func.now()
    
    # Notify Requester
    notif = Notification(
        user_id=req.requested_by,
        title="Deletion Request Rejected",
        message=f"Your request to delete evidence '{req.evidence.title}' was rejected by {current_user.fullname}.",
        type="alert"
    )
    db.session.add(notif)
    db.session.commit()
    
    log_audit_action('Rejected Evidence Deletion', current_user.id, f'Request ID {req.id}')
    flash('Evidence deletion request rejected.', 'success')
    return redirect(url_for('evidence.admin_deletion_requests'))

@evidence_bp.route('/url-reputation', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def url_reputation():
    """Simple URL Reputation Checker placeholder.
    Renders a form where users can input a URL. Actual reputation logic
    should be implemented separately (e.g., via VirusTotal API).
    """
    # Support GET with URL query parameter and POST form submission
    if request.method == 'POST':
        url = request.form.get('url')
    elif request.method == 'GET' and request.args.get('url'):
        url = request.args.get('url')
    else:
        # No URL provided yet, render the input form
        return render_template('evidence/url_reputation.html')
    # Simple reputation check: try to fetch the URL and evaluate the response
    # Load environment variables
    load_dotenv()

    # ------------------- Helper Functions -------------------
    def extract_features(u):
        parsed = urllib.parse.urlparse(u)
        domain = parsed.netloc.split('@')[-1].split(':')[0]
        path = parsed.path
        query = parsed.query
        # Basic features
        url_length = len(u)
        num_dots = domain.count('.')
        num_hyphens = domain.count('-')
        num_underscores = domain.count('_')
        num_slashes = u.count('/')
        num_digits = sum(c.isdigit() for c in u)
        special_chars = re.findall(r'[^a-zA-Z0-9\._\-\/]', u)
        num_special_chars = len(special_chars)
        # IP address detection
        ip_regex = r'^(?:\d{1,3}\.){3}\d{1,3}$'
        has_ip_address = 1 if re.match(ip_regex, domain) else 0
        # Port detection
        has_port = 1 if ':' in parsed.netloc and parsed.netloc.split(':')[-1].isdigit() else 0
        # Subdomain count (exclude TLD and SLD)
        parts = domain.split('.')
        subdomain_count = max(len(parts) - 2, 0)
        # Path depth
        path_depth = len([p for p in path.split('/') if p])
        # Query params
        query_param_count = len(urllib.parse.parse_qs(query))
        has_https = 1 if parsed.scheme == 'https' else 0
        domain_length = len(domain)
        tld = parts[-1] if parts else ''
        suspicious_tlds = {'.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.click', '.download'}
        tld_suspicious = 1 if f'.{tld}' in suspicious_tlds else 0
        return [url_length, num_dots, num_hyphens, num_underscores, num_slashes,
                num_digits, num_special_chars, has_ip_address, has_port,
                subdomain_count, path_depth, query_param_count, has_https,
                domain_length, tld_suspicious]

    def homograph_check(domain):
        suspicious_map = {'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'х': 'x', 'ѕ': 's'}
        chars = []
        for ch in domain:
            if ord(ch) > 127:
                if ch in suspicious_map:
                    chars.append(ch)
        return (len(chars) > 0, chars)

    def base64_check(u):
        segments = []
        parsed = urllib.parse.urlparse(u)
        # path segments
        segments.extend([seg for seg in parsed.path.split('/') if seg])
        # query values
        for val in urllib.parse.parse_qs(parsed.query).values():
            for v in val:
                segments.append(v)
        for seg in segments:
            # try base64 decode if length is multiple of 4
            try:
                if len(seg) % 4 == 0:
                    decoded = base64.urlsafe_b64decode(seg + '==').decode('utf-8', errors='ignore')
                    if any(k in decoded.lower() for k in ['javascript:', 'eval', 'document.write']):
                        return True, decoded, True
                    if decoded.strip():
                        return True, decoded, False
            except Exception:
                continue
        return False, '', False

    def levenshtein(a, b):
        if len(a) < len(b):
            return levenshtein(b, a)
        if len(b) == 0:
            return len(a)
        previous_row = range(len(b) + 1)
        for i, ca in enumerate(a, 1):
            current_row = [i]
            for j, cb in enumerate(b, 1):
                insertions = previous_row[j] + 1
                deletions = current_row[j-1] + 1
                substitutions = previous_row[j-1] + (ca != cb)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def phishing_checks(u):
        parsed = urllib.parse.urlparse(u)
        domain = parsed.netloc.split('@')[-1].split(':')[0].lower()
        top_domains = ['google.com', 'facebook.com', 'amazon.com', 'apple.com', 'microsoft.com',
                       'paypal.com', 'instagram.com', 'twitter.com', 'linkedin.com', 'netflix.com', 'bank.com']
        is_typosquatting = False
        similar_to = ''
        for top in top_domains:
            if levenshtein(domain, top) < 3 and domain != top:
                is_typosquatting = True
                similar_to = top
                break
        shorteners = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'short.link']
        is_shortener = domain in shorteners
        keywords = ['verify', 'account', 'suspended', 'login', 'confirm', 'update', 'secure',
                    'banking', 'password', 'credential', 'urgent', 'click', 'free', 'winner']
        found_keywords = [kw for kw in keywords if kw in u.lower()]
        # redirect count
        redirect_count = 0
        try:
            r = requests.head(u, allow_redirects=True, timeout=5)
            redirect_count = len(r.history)
        except Exception:
            pass
        phishing_score = min(100, (len(found_keywords) * 10) + (redirect_count * 5) + (10 if is_shortener else 0) + (15 if is_typosquatting else 0))
        return is_typosquatting, similar_to, is_shortener, found_keywords, phishing_score

    # ------------------- Load / Train ML Model -------------------
    model_path = os.path.join(current_app.root_path, 'model', 'url_rf_model.pkl')
    if not os.path.exists(model_path):
        # Train a very tiny fallback model
        X = []
        y = []
        # Simple synthetic data: safe URLs
        safe_examples = ['https://example.com', 'https://github.com', 'https://openai.com']
        for s in safe_examples:
            X.append(extract_features(s))
            y.append(0)  # 0 = safe
        # Phishing examples
        phishing_examples = ['http://malicious.tk/bad', 'http://login-verify.secure-update.com']
        for p in phishing_examples:
            X.append(extract_features(p))
            y.append(2)  # 2 = malicious
        X = np.array(X)
        y = np.array(y)
        rf = RandomForestClassifier(n_estimators=10, random_state=42)
        rf.fit(X, y)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(rf, model_path)
    else:
        rf = joblib.load(model_path)

    # ------------------- Perform Analysis -------------------
    features = np.array([extract_features(url)])
    pred = rf.predict(features)[0]
    proba = rf.predict_proba(features)[0]
    ml_map = {0: 'SAFE', 1: 'SUSPICIOUS', 2: 'MALICIOUS'}
    ml_prediction = ml_map.get(pred, 'UNKNOWN')
    ml_confidence = max(proba) * 100

    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.split('@')[-1].split(':')[0]
    homograph_detected, homograph_chars = homograph_check(domain)
    base64_found, decoded_content, base64_suspicious = base64_check(url)
    is_typosquatting, similar_to, is_shortener, suspicious_keywords, phishing_score = phishing_checks(url)

    # ------------------- API Integrations -------------------
    vt_results = {'malicious': 'N/A', 'suspicious': 'N/A', 'harmless': 'N/A'}
    vt_key = os.getenv('VIRUSTOTAL_API_KEY')
    if vt_key:
        try:
            vt_url = 'https://www.virustotal.com/api/v3/urls'
            headers = {'x-apikey': vt_key}
            data = {'url': url}
            vt_resp = requests.post(vt_url, headers=headers, data=data, timeout=10)
            if vt_resp.status_code == 200:
                analysis_id = vt_resp.json()['data']['id']
                analysis_resp = requests.get(f'https://www.virustotal.com/api/v3/analyses/{analysis_id}', headers=headers, timeout=10)
                if analysis_resp.status_code == 200:
                    stats = analysis_resp.json()['data']['attributes']['stats']
                    vt_results = {'malicious': stats.get('malicious'), 'suspicious': stats.get('suspicious'), 'harmless': stats.get('harmless')}
        except Exception:
            vt_results = {'error': 'Failed'}
    else:
        vt_results = {'status': 'API key not configured'}

    urlscan_results = {'uuid': 'N/A', 'result_url': 'N/A'}
    urlscan_key = os.getenv('URLSCAN_KEY')
    if urlscan_key:
        try:
            us_resp = requests.post('https://urlscan.io/api/v1/scan/', headers={'API-Key': urlscan_key}, json={'url': url, 'visibility': 'public'}, timeout=10)
            if us_resp.status_code == 200:
                data = us_resp.json()
                urlscan_results = {'uuid': data.get('uuid'), 'result_url': data.get('result')}
        except Exception:
            urlscan_results = {'error': 'Failed'}
    else:
        urlscan_results = {'status': 'API key not configured'}

    phishtank_results = {'in_database': 'N/A', 'verified': 'N/A'}
    try:
        pt_resp = requests.post('https://checkurl.phishtank.com/checkurl/', data={'url': url, 'format': 'json'}, timeout=10)
        if pt_resp.status_code == 200:
            pt_json = pt_resp.json()
            phishtank_results = {'in_database': pt_json['results'].get('in_database'), 'verified': pt_json['results'].get('verified')}
    except Exception:
        phishtank_results = {'error': 'Failed'}

    safeb_rows = []
    sb_key = os.getenv('GOOGLE_KEY')
    safeb_results = {'threats': []}
    if sb_key:
        try:
            sb_payload = {
                'client': {'clientId': 'deis', 'clientVersion': '1.0'},
                'threatInfo': {
                    'threatTypes': ['MALWARE', 'SOCIAL_ENGINEERING', 'UNWANTED_SOFTWARE', 'POTENTIALLY_HARMFUL_APPLICATION'],
                    'platformTypes': ['ANY_PLATFORM'],
                    'threatEntryTypes': ['URL'],
                    'threatEntries': [{'url': url}]
                }
            }
            sb_resp = requests.post(f'https://safebrowsing.googleapis.com/v4/threatMatches:find?key={sb_key}', json=sb_payload, timeout=10)
            if sb_resp.status_code == 200 and sb_resp.json():
                safeb_results['threats'] = sb_resp.json().get('matches', [])
        except Exception:
            safeb_results = {'error': 'Failed'}
    else:
        safeb_results = {'status': 'API key not configured'}

    abuse_results = {'abuse_confidence_score': 'N/A', 'total_reports': 'N/A'}
    abuse_key = os.getenv('ABUSEIPDB_KEY')
    if abuse_key:
        try:
            ip_addr = socket.gethostbyname(domain)
            abuse_resp = requests.get('https://api.abuseipdb.com/api/v2/check', params={'ipAddress': ip_addr}, headers={'Key': abuse_key, 'Accept': 'application/json'}, timeout=10)
            if abuse_resp.status_code == 200:
                data = abuse_resp.json()['data']
                abuse_results = {'abuse_confidence_score': data.get('abuseConfidenceScore'), 'total_reports': data.get('totalReports')}
        except Exception:
            abuse_results = {'error': 'Failed'}
    else:
        abuse_results = {'status': 'API key not configured'}

    # ------------------- Risk Scoring -------------------
    ml_weight = 30
    phishing_weight = 25
    api_weight = 30
    homograph_weight = 10
    base64_weight = 5

    # Normalize components to 0-100 scale
    ml_score = {'SAFE': 0, 'SUSPICIOUS': 50, 'MALICIOUS': 100}.get(ml_prediction, 50)
    phishing_score_norm = phishing_score
    api_score = 0
    # Simple aggregation: if any API reports malicious, raise score
    if isinstance(vt_results, dict) and vt_results.get('malicious') not in (None, 'N/A'):
        try:
            if int(vt_results.get('malicious', 0)) > 0:
                api_score += 40
        except Exception:
            pass
    if safeb_results.get('threats'):
        api_score += 20
    if abuse_results.get('abuse_confidence_score') not in ('N/A', None):
        try:
            api_score += int(abuse_results.get('abuse_confidence_score', 0)) / 2
        except Exception:
            pass
    api_score = min(100, api_score)
    homograph_score = 100 if homograph_detected else 0
    base64_score = 100 if base64_suspicious else 0

    overall_score = (
        ml_score * ml_weight / 100 +
        phishing_score_norm * phishing_weight / 100 +
        api_score * api_weight / 100 +
        homograph_score * homograph_weight / 100 +
        base64_score * base64_weight / 100
    )
    overall_score = round(overall_score, 2)
    if overall_score <= 30:
        risk_level = 'SAFE'
        risk_color = 'success'
    elif overall_score <= 60:
        risk_level = 'SUSPICIOUS'
        risk_color = 'warning'
    else:
        risk_level = 'MALICIOUS'
        risk_color = 'danger'

    # ------------------- Render Results -------------------
    context = {
        'url': url,
        'risk_score': overall_score,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'ml_prediction': ml_prediction,
        'ml_confidence': round(ml_confidence, 2),
        'homograph_detected': homograph_detected,
        'homograph_chars': homograph_chars,
        'base64_found': base64_found,
        'decoded_content': decoded_content,
        'base64_suspicious': base64_suspicious,
        'is_typosquatting': is_typosquatting,
        'similar_to': similar_to,
        'is_shortener': is_shortener,
        'suspicious_keywords': suspicious_keywords,
        'phishing_score': phishing_score,
        'vt_results': vt_results,
        'urlscan_results': urlscan_results,
        'phishtank_results': phishtank_results,
        'safeb_results': safeb_results,
        'abuse_results': abuse_results,
    }
    return render_template('evidence/url_reputation.html', **context)
    return render_template('evidence/url_reputation.html')

# ---------------------------------------------------------------------------
# Save URL Reputation Report
# ---------------------------------------------------------------------------
@evidence_bp.route('/save_url_report', methods=['GET', 'POST'])
@login_required
def save_url_report():
    """Save the URL reputation analysis as a report file.

    The UI passes the URL via query parameter (GET) or form data (POST).
    The report is saved as a plain‑text file in the configured REPORTS_FOLDER.
    """
    # Accept URL from query string or form
    url = request.values.get('url')
    if not url:
        flash('❌ No URL provided to save.', 'danger')
        return redirect(url_for('evidence.url_reputation'))

    # Build report content – include timestamp and user
    report_dir = current_app.config['REPORTS_FOLDER']
    os.makedirs(report_dir, exist_ok=True)
    filename = f"url_report_{uuid.uuid4().hex}.txt"
    report_path = os.path.join(report_dir, filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"URL Reputation Report\n")
            f.write(f"Generated at: {datetime.utcnow().isoformat()} UTC\n")
            f.write(f"User: {current_user.username}\n")
            f.write(f"URL: {url}\n")
            # Optionally, include a placeholder for detailed results
            f.write("\n[Report details can be added here]\n")
        flash('✅ URL reputation report saved successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Failed to save URL report: {e}")
        flash('❌ Failed to save URL report.', 'danger')
    return redirect(url_for('evidence.url_reputation'))
@evidence_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Admin-only hard delete of evidence and its encrypted file."""
    evidence = Evidence.query.get_or_404(id)
    # Remove encrypted file from storage
    encrypted_path = os.path.join(current_app.config['ENCRYPTED_FOLDER'], evidence.stored_name)
    if os.path.exists(encrypted_path):
        try:
            os.remove(encrypted_path)
        except Exception as e:
            current_app.logger.error(f"Failed to delete file {encrypted_path}: {e}")
    # Delete DB record (cascades will clean related rows)
    db.session.delete(evidence)
    db.session.commit()
    log_audit_action('Deleted Evidence', current_user.id, f'Evidence ID {id}')
    flash('Evidence deleted successfully.', 'success')
    return redirect(url_for('evidence.list_evidence'))
