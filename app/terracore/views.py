from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, jsonify, session
from flask_login import login_required, current_user
from .models import Prospect, db, User, Partner, FinancialAssumptions, Watchlist, Comment, AuditLog
import openai
import os
from functools import wraps
import json
from sqlalchemy import Text
import numpy as np
from werkzeug.utils import secure_filename
import csv
from io import StringIO
import logging
from flask_session import Session

main_bp = Blueprint('main', __name__)

# RBAC decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def index():
    logging.info("[AUTH_DEBUG] index: current_user.is_authenticated=%s", current_user.is_authenticated)
    logging.info("[AUTH_DEBUG] index: session=%s", dict(session))
    logging.info("[AUTH_DEBUG] index: request.cookies=%s", request.cookies)
    return render_template('index.html')

@main_bp.route('/prospects', methods=['GET', 'POST'])
@login_required
def prospects():
    if request.method == 'POST':
        zillow_url = request.form.get('zillow_url')
        if not zillow_url:
            flash('Please provide a Zillow URL.', 'warning')
            return redirect(url_for('main.prospects'))
        # Check if already exists
        existing = Prospect.query.filter_by(zillow_url=zillow_url).first()
        if existing:
            flash('This prospect already exists.', 'info')
        else:
            prospect = Prospect(zillow_url=zillow_url, created_by=current_user.id)
            db.session.add(prospect)
            db.session.commit()
            flash('Prospect added!', 'success')
        return redirect(url_for('main.prospects'))
    # Advanced Pagination, search, filter
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    min_price = request.args.get('min_price', '', type=str)
    max_price = request.args.get('max_price', '', type=str)
    min_rent = request.args.get('min_rent', '', type=str)
    max_rent = request.args.get('max_rent', '', type=str)
    beds = request.args.get('beds', '', type=str)
    baths = request.args.get('baths', '', type=str)
    query = Prospect.query
    # Filtering by address substring
    if search:
        query = query.filter(Prospect.address.ilike(f'%{search}%'))
    # Filtering by price/rent/beds/baths (in Python, since data is in JSON)
    prospects_all = query.order_by(Prospect.created_at.desc()).all()
    filtered = []
    for p in prospects_all:
        d = parse_prospect_data(p)
        try:
            price = float(str(d.get('price', 0)).replace('$','').replace(',',''))
            rent = float(str(d.get('estimated_rent', 0)).replace('$','').replace(',',''))
            _beds = int(d.get('beds', 0))
            _baths = float(d.get('baths', 0))
        except Exception:
            price = rent = _beds = _baths = 0
        if min_price and price < float(min_price):
            continue
        if max_price and price > float(max_price):
            continue
        if min_rent and rent < float(min_rent):
            continue
        if max_rent and rent > float(max_rent):
            continue
        if beds and _beds != int(beds):
            continue
        if baths and _baths != float(baths):
            continue
        filtered.append(p)
    # Manual pagination
    per_page = 10
    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    items = filtered[start:end]
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1
            self.next_num = page + 1
    prospects = Pagination(items, page, per_page, total)
    return render_template('prospects.html', prospects=prospects, search=search, min_price=min_price, max_price=max_price, min_rent=min_rent, max_rent=max_rent, beds=beds, baths=baths)

# ChatGPT analysis utility
def analyze_prospect(prospect):
    if prospect.data:
        return prospect.data
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    prompt = f"""
    Given the following Zillow URL, extract the address, price, beds, baths, and estimate the monthly rent and any other relevant investment data for a real estate investment analysis. Return as JSON.
    Zillow URL: {prospect.zillow_url}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        raw = response.choices[0].message['content']
        # Try to parse JSON
        try:
            parsed = json.loads(raw)
            prospect.data = parsed
            prospect.raw_data = raw
            prospect.status = 'approved'
        except Exception:
            prospect.data = None
            prospect.raw_data = raw
            prospect.status = 'needs_review'
        db.session.commit()
        return prospect.data
    except Exception as e:
        flash(f"ChatGPT analysis failed: {e}", "danger")
        return None

@main_bp.route('/admin/analyze', methods=['POST'])
@login_required
@admin_required
def analyze_all_prospects():
    prospects = Prospect.query.filter((Prospect.data == None) | (Prospect.data == '')).all()
    for prospect in prospects:
        analyze_prospect(prospect)
    flash(f"Analyzed {len(prospects)} prospects.", "success")
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/prospect_review')
@login_required
@admin_required
def prospect_review():
    prospects = Prospect.query.filter_by(status='needs_review').all()
    return render_template('prospect_review.html', prospects=prospects)

@main_bp.route('/admin/prospect_review/<int:prospect_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def review_prospect(prospect_id):
    import json
    prospect = Prospect.query.get_or_404(prospect_id)
    if request.method == 'POST':
        data = request.form.get('data')
        try:
            parsed = json.loads(data)
            prospect.data = parsed
            prospect.status = 'approved'
            db.session.commit()
            flash('Prospect data approved and saved.', 'success')
            return redirect(url_for('main.prospect_review'))
        except Exception as e:
            flash(f'Invalid JSON: {e}', 'danger')
    return render_template('review_prospect.html', prospect=prospect)

def parse_prospect_data(prospect):
    try:
        if not prospect.data:
            return {}
        if isinstance(prospect.data, dict):
            return prospect.data
        return json.loads(prospect.data)
    except Exception:
        return {}

# Helper to get or create singleton assumptions
def get_assumptions():
    a = FinancialAssumptions.query.order_by(FinancialAssumptions.created_at.desc()).first()
    if not a:
        a = FinancialAssumptions()
        db.session.add(a)
        db.session.commit()
    return a

@main_bp.route('/admin/assumptions', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_assumptions():
    a = get_assumptions()
    if request.method == 'POST':
        a.expense_ratio = float(request.form.get('expense_ratio', a.expense_ratio))
        a.interest_rate = float(request.form.get('interest_rate', a.interest_rate))
        a.down_payment = float(request.form.get('down_payment', a.down_payment))
        a.appreciation_rate = float(request.form.get('appreciation_rate', a.appreciation_rate))
        a.years = int(request.form.get('years', a.years))
        db.session.commit()
        flash('Financial assumptions updated.', 'success')
        return redirect(url_for('main.admin_dashboard'))
    return render_template('edit_assumptions.html', a=a)

# Update aggregate_financials to use assumptions
def aggregate_financials(prospects, assumptions=None):
    if assumptions is None:
        assumptions = get_assumptions()
    total_price = 0
    total_rent = 0
    total_noi = 0
    total_cash_flow = 0
    count = 0
    details = []
    projections = []
    for p in prospects:
        d = parse_prospect_data(p)
        try:
            price = float(str(d.get('price', 0)).replace('$','').replace(',',''))
            rent = float(str(d.get('estimated_rent', 0)).replace('$','').replace(',',''))
            beds = int(d.get('beds', 0))
            baths = float(d.get('baths', 0))
        except Exception:
            price = rent = beds = baths = 0
        if price > 0 and rent > 0:
            noi = rent * 12 * (1 - assumptions.expense_ratio)
            loan = price * (1 - assumptions.down_payment)
            # Approximate annual debt service (interest only for simplicity)
            debt_service = loan * assumptions.interest_rate
            cash_flow = noi - debt_service
            cap_rate = (noi / price) * 100 if price else 0
            total_price += price
            total_rent += rent
            total_noi += noi
            total_cash_flow += cash_flow
            count += 1
            # Multi-year projections
            years = assumptions.years
            appreciation = assumptions.appreciation_rate
            proj = {
                'address': d.get('address', '—'),
                'yearly': []
            }
            v = price
            r = rent
            equity = price * assumptions.down_payment
            loan_balance = loan
            cash_flows = [-price * assumptions.down_payment]  # Initial investment (negative)
            for y in range(1, years+1):
                v = v * (1 + appreciation)
                r = r * (1 + appreciation)
                noi_y = r * 12 * (1 - assumptions.expense_ratio)
                debt_service_y = loan * assumptions.interest_rate
                cash_flow_y = noi_y - debt_service_y
                equity = equity + (debt_service_y * 0.2) + (v - price) / years  # crude equity build
                cash_flows.append(cash_flow_y)
                proj['yearly'].append({
                    'year': y,
                    'value': v,
                    'rent': r,
                    'noi': noi_y,
                    'cash_flow': cash_flow_y,
                    'equity': equity
                })
            # IRR calculation
            try:
                irr = np.irr(cash_flows)
            except Exception:
                irr = None
            details.append({
                'address': d.get('address', '—'),
                'price': price,
                'rent': rent,
                'noi': noi,
                'cash_flow': cash_flow,
                'cap_rate': cap_rate,
                'beds': beds,
                'baths': baths,
                'irr': irr,
                'projections': proj['yearly']
            })
            projections.append(proj)
    avg_price = total_price / count if count else 0
    avg_rent = total_rent / count if count else 0
    avg_cap_rate = (total_noi / total_price) * 100 if total_price else 0
    partner_split = total_cash_flow / 3 if count else 0
    return {
        'total_price': total_price,
        'total_rent': total_rent,
        'total_noi': total_noi,
        'total_cash_flow': total_cash_flow,
        'avg_price': avg_price,
        'avg_rent': avg_rent,
        'avg_cap_rate': avg_cap_rate,
        'partner_split': partner_split,
        'count': count,
        'details': details,
        'assumptions': assumptions,
        'projections': projections
    }

@main_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    prospects = Prospect.query.order_by(Prospect.created_at.desc()).all()
    users = User.query.all()
    partners = Partner.query.all()
    assumptions = get_assumptions()
    financials = aggregate_financials(prospects, assumptions)
    # Prepare chart data for Chart.js
    chart_data = {
        'labels': [d['address'] for d in financials['details']],
        'prices': [d['price'] for d in financials['details']],
        'rents': [d['rent'] for d in financials['details']],
        'nois': [d['noi'] for d in financials['details']],
        'cash_flows': [d['cash_flow'] for d in financials['details']],
        'cap_rates': [d['cap_rate'] for d in financials['details']],
    }
    return render_template('admin_dashboard.html', prospects=prospects, users=users, partners=partners, financials=financials, chart_data=chart_data, assumptions=assumptions)

@main_bp.route('/admin/partners')
@login_required
@admin_required
def manage_partners():
    partners = Partner.query.all()
    users = User.query.all()
    return render_template('partners.html', partners=partners, users=users)

@main_bp.route('/admin/partners/promote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('User is already an admin.', 'info')
    else:
        user.role = 'admin'
        db.session.commit()
        flash(f'Promoted {user.email} to admin.', 'success')
    return redirect(url_for('main.manage_partners'))

@main_bp.route('/admin/partners/demote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot demote yourself.', 'danger')
        return redirect(url_for('main.manage_partners'))
    if user.role != 'admin':
        flash('User is not an admin.', 'info')
    else:
        user.role = 'user'
        db.session.commit()
        flash(f'Demoted {user.email} to standard user.', 'success')
    return redirect(url_for('main.manage_partners'))

@main_bp.route('/admin/partners/remove/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot remove yourself.', 'danger')
        return redirect(url_for('main.manage_partners'))
    db.session.delete(user)
    db.session.commit()
    flash(f'Removed user {user.email}.', 'success')
    return redirect(url_for('main.manage_partners'))

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user
    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        phone = request.form.get('phone', '').strip()
        user.name = user.name  # Full name from Google SSO, read-only
        user.display_name = display_name
        user.phone = phone
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('main.profile'))
    prospects = Prospect.query.filter_by(created_by=user.id).order_by(Prospect.created_at.desc()).all()
    return render_template('profile.html', user=user, prospects=prospects)

@main_bp.route('/admin/scenario', methods=['POST'])
@login_required
@admin_required
def scenario_analysis():
    # Get scenario values from form
    try:
        expense_ratio = float(request.form.get('expense_ratio'))
        interest_rate = float(request.form.get('interest_rate'))
        down_payment = float(request.form.get('down_payment'))
        appreciation_rate = float(request.form.get('appreciation_rate'))
        years = int(request.form.get('years'))
    except Exception:
        return jsonify({'error': 'Invalid input'}), 400
    class Scenario:
        pass
    scenario = Scenario()
    scenario.expense_ratio = expense_ratio
    scenario.interest_rate = interest_rate
    scenario.down_payment = down_payment
    scenario.appreciation_rate = appreciation_rate
    scenario.years = years
    prospects = Prospect.query.order_by(Prospect.created_at.desc()).all()
    results = aggregate_financials(prospects, scenario)
    # Return only the summary and projections for display
    return render_template('scenario_results.html', financials=results)

UPLOAD_FOLDER = 'app/terracore/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/prospect/<int:prospect_id>', methods=['GET', 'POST'])
@login_required
def prospect_detail(prospect_id):
    prospect = Prospect.query.get_or_404(prospect_id)
    # Handle image upload
    if request.method == 'POST' and 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{prospect_id}_" + file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            # Store filenames in notes for now (could use a separate model)
            if not prospect.data:
                prospect.data = {}
            if 'images' not in prospect.data:
                prospect.data['images'] = []
            prospect.data['images'].append(filename)
            db.session.commit()
            flash('Image uploaded.', 'success')
            return redirect(url_for('main.prospect_detail', prospect_id=prospect_id))
    # Handle notes
    if request.method == 'POST' and 'note' in request.form:
        note = request.form.get('note').strip()
        if note:
            if not prospect.data:
                prospect.data = {}
            if 'notes' not in prospect.data:
                prospect.data['notes'] = []
            prospect.data['notes'].append({'user': current_user.email, 'note': note})
            db.session.commit()
            flash('Note added.', 'success')
            return redirect(url_for('main.prospect_detail', prospect_id=prospect_id))
    # Images and notes
    images = []
    notes = []
    d = parse_prospect_data(prospect)
    if d:
        images = d.get('images', [])
        notes = d.get('notes', [])
    return render_template('prospect_detail.html', prospect=prospect, pdata=d, images=images, notes=notes)

# Watchlist add/remove
@main_bp.route('/prospect/<int:prospect_id>/watch', methods=['POST'])
@login_required
def add_to_watchlist(prospect_id):
    if not Watchlist.query.filter_by(user_id=current_user.id, prospect_id=prospect_id).first():
        w = Watchlist(user_id=current_user.id, prospect_id=prospect_id)
        db.session.add(w)
        db.session.commit()
    flash('Added to watchlist.', 'success')
    return redirect(url_for('main.prospect_detail', prospect_id=prospect_id))

@main_bp.route('/prospect/<int:prospect_id>/unwatch', methods=['POST'])
@login_required
def remove_from_watchlist(prospect_id):
    w = Watchlist.query.filter_by(user_id=current_user.id, prospect_id=prospect_id).first()
    if w:
        db.session.delete(w)
        db.session.commit()
    flash('Removed from watchlist.', 'info')
    return redirect(url_for('main.prospect_detail', prospect_id=prospect_id))

@main_bp.route('/watchlist')
@login_required
def watchlist():
    items = Watchlist.query.filter_by(user_id=current_user.id).all()
    prospects = [Prospect.query.get(w.prospect_id) for w in items]
    return render_template('watchlist.html', prospects=prospects)

# Comments
@main_bp.route('/prospect/<int:prospect_id>/comment', methods=['POST'])
@login_required
def add_comment(prospect_id):
    text = request.form.get('comment', '').strip()
    if text:
        c = Comment(prospect_id=prospect_id, user_id=current_user.id, text=text)
        db.session.add(c)
        db.session.commit()
    flash('Comment added.', 'success')
    return redirect(url_for('main.prospect_detail', prospect_id=prospect_id))

# Audit log helper

def log_action(user, action, target, details=None):
    db.session.add(AuditLog(user_id=user.id, action=action, target=target, details=details))
    db.session.commit()

# Update admin actions to log
# (Example for promote/demote/remove, assumptions edit)
# ... in promote_user ...
# log_action(current_user, 'promote', user.email)
# ... in demote_user ...
# log_action(current_user, 'demote', user.email)
# ... in remove_user ...
# log_action(current_user, 'remove', user.email)
# ... in edit_assumptions ...
# log_action(current_user, 'edit_assumptions', 'FinancialAssumptions', details=str({
#     'expense_ratio': a.expense_ratio, 'interest_rate': a.interest_rate, 'down_payment': a.down_payment, 'appreciation_rate': a.appreciation_rate, 'years': a.years
# }))

@main_bp.route('/admin/auditlog')
@login_required
@admin_required
def auditlog():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('auditlog.html', logs=logs)

# Export CSV
@main_bp.route('/admin/export')
@login_required
@admin_required
def export_csv():
    prospects = Prospect.query.order_by(Prospect.created_at.desc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Address', 'Price', 'Rent', 'Beds', 'Baths', 'Added'])
    for p in prospects:
        d = parse_prospect_data(p)
        writer.writerow([
            d.get('address', ''),
            d.get('price', ''),
            d.get('estimated_rent', ''),
            d.get('beds', ''),
            d.get('baths', ''),
            p.created_at.strftime('%Y-%m-%d')
        ])
    output = si.getvalue()
    return (output, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=prospects.csv'}) 