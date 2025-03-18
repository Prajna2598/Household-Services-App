import os
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, session, abort
from sqlalchemy import func
from datetime import datetime

from models import db, User, Staff, HouseholdServices, HouseholdServiceRequest

from werkzeug.utils import secure_filename
import config

import matplotlib
matplotlib.use('Agg') # this is to avoid the error: main thread is not in main loop

import matplotlib.pyplot as plt
import seaborn as sns

from app import app

# =========================== DECORATORS ===========================

def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs): 
        if 'user_id' not in session:
            flash('Please login to continue')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return inner

def admin_required(f):
    @wraps(f)
    def inner(*args, **kwargs):        
        if not session['is_admin']:
            flash('You are not authorized to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return inner

def professional_required(f):
    @wraps(f)
    def inner(*args, **kwargs):        
        if session['is_professional']:
            if not session['is_approved']:
                flash('Your account is not approved. Please wait for admin approval', 'danger')
                return redirect(url_for('index'))
            else:
                return f(*args, **kwargs)
        else:
            flash('You are not authorized to access this page')
            return redirect(url_for('index'))
    return inner

def customer_required(f):
    @wraps(f)
    def inner(*args, **kwargs):        
        if not session['is_customer']:
            flash('You are not authorized to access this page')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return inner

# =========================== INDEX PAGE ===========================

@app.route('/')
def index():
    return render_template('index.html')

# ===========================LOGIN AND LOGOUTPAGES===========================

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == '' or password == '':
        flash('Username or password cannot be empty', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=username).first()
    if not user:
        staff = Staff.query.filter_by(username=username).first()
        if not staff:
            flash('User with this username does not exist', 'danger')
            return redirect(url_for('login'))
        
        if not staff.check_password(password):
            flash('Incorrect password', 'danger')
            return redirect(url_for('login'))
        else:
            session['user_id'] = staff.id
            session['is_professional'] = staff.is_professional
            session['username'] = username
            
            if staff.is_professional:
                if not staff.is_approved:
                    session['is_approved'] = staff.is_approved
                    flash('Please wait for admin approval', 'danger')
                    return redirect(url_for('login'))
                # if staff.service_id == None:
                #     flash('Your service is no longer available. Please create a new account to choose a new service', 'danger')
                #     # INSTEAD OF CREATING A NEW ACCOUNT, CAN HE EDIT HIS PROFILE TO CHOOSE A NEW SERVICE?
                #     return redirect(url_for('login'))
                else:   
                    session['is_approved'] = staff.is_approved             
                    flash('Login successful', 'success')
                    return redirect(url_for('professional_dashboard'))
            else:
                flash('Please login from admin login', 'danger')
                return redirect(url_for('admin_login'))
    else:
        if not user.check_password(password):
            flash('Incorrect password', 'danger')
            return redirect(url_for('login'))
        else:
            session['user_id'] = user.id
            session['username'] = username
            session['is_customer'] = True
            flash('Login successful', 'success')
            return redirect(url_for('customer_dashboard'))

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['POST'])    
def admin_login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == '' or password == '':
        flash('Username or password cannot be empty', 'danger')
        return redirect(url_for('admin_login'))

    user = Staff.query.filter_by(is_admin=True, username=username).first()
    if not user:
        flash('You are not authorized to access this page', 'danger')
        return redirect(url_for('admin_login'))
    if not user.check_password(password):
        flash('Incorrect password', 'danger')
        return redirect(url_for('admin_login'))

    else:
        session['user_id'] = user.id
        session['username'] = username
        session['is_admin'] = True
        flash('Admin logged in successfully', 'success')
        return redirect(url_for('admin_dashboard'))

# user: Ben, ben10, 12345. Hereon all passwords are 1234
# professional: Dave, DedDave, 12345; Pro1; Pro2 All PWs are 12345
# admin: admin, Boss, 101010

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    session.pop('is_professional', None)
    return redirect(url_for('index'))

# ===========================REGISTRATION PAGES===========================

@app.route('/customer_register')
def customer_register():
    return render_template('customer_register.html')

@app.route('/customer_register', methods=['POST'])
def customer_register_post():
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password')
    address = request.form.get('address')
    pincode = request.form.get('pincode')

    print(username[0].isalpha())
    print(name, username, password, address, pincode)

    if username == '' or password == '' or address == '' or pincode == '':
        flash('Username or password cannot be empty')
        return redirect(url_for('customer_register'))

    if not username[0].isalpha():
        flash('Username must start with a letter', 'danger')
        return redirect(url_for('customer_register'))

    user = User.query.filter_by(username=username).first()
    if user:
        flash('User with this username already exists. Please use a different username', 'danger')
        return redirect(url_for('customer_register'))
    
    new_user = User(name = name, username=username, password=password, address=address, pincode=pincode)
    db.session.add(new_user)
    db.session.commit()
    flash('User successfully registered', 'success')
    return redirect(url_for('login'))

@app.route('/professional_register')
def professional_register():
    services = HouseholdServices.query.all()

    return render_template('professional_register.html', services=services)

@app.route('/professional_register', methods=['POST'])
def professional_register_post():
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password')
    address = request.form.get('address')
    pincode = request.form.get('pincode')
    service = request.form.get('service')
    service_file = request.files.get('service_file')

    service_experience = request.form.get('service_experience')
    service_id = HouseholdServices.query.filter_by(service_name=service).first().id

    if username == '' or password == '' or address == '' or pincode == '':
        flash('Please fill all the required fields', 'danger')
        return redirect(url_for('professional_register'))

    user = Staff.query.filter_by(username=username).first()
    if user:
        flash('User with this username already exists. Please use a different username', 'danger')
        return redirect(url_for('professional_register'))
    
    else:
        file_name = secure_filename(service_file.filename) 
        if file_name != '':
            file_ext = os.path.splitext(file_name)[1] 
            new_filename = name + file_ext 
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                abort(400) 
            else:
                service_file.save(os.path.join(app.config['UPLOAD_PATH'], new_filename))
        else:
            flash('Please upload a file', 'danger')
            return redirect(url_for('professional_register'))

    new_user = Staff(name = name, username=username, password=password, address=address, pincode=pincode, is_professional=True, service_file=new_filename, service_experience=service_experience, service_id=service_id)
    db.session.add(new_user)
    db.session.commit()
    flash('User successfully registered', 'success')
    return redirect(url_for('login'))

# ============================PROFILE PAGES===========================

@app.route('/admin_dashboard/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    admin = Staff.query.filter_by(is_admin=session['is_admin']).first()
    # The .first() method is important in this case because Staff.query.filter_by(is_admin=session['is_admin']) returns a Query object, which is essentially a list of results that match the filter criteria.
    
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')

        admin.name = name
        admin.username = username
        admin.password = password
        db.session.commit()
        session['username'] = username
        flash('Profile updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template('admin_profile.html', admin = admin)    

@app.route('/professional_dashboard/profile', methods=['GET', 'POST'])
@professional_required
def professional_profile():
    professional = Staff.query.get(session['user_id'])
    service_requests = HouseholdServiceRequest.query.filter_by(professional_id=session['user_id']).all()
    services = HouseholdServices.query.all()

    if request.method == 'POST':

        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        service_name = request.form.get('service_name')
        service_experience = request.form.get('service_experience')

        if service_name == '':
            flash('Please enter service name', 'danger')
            return redirect(url_for('professional_profile'))

        service_id = HouseholdServices.query.filter_by(service_name=service_name).first().id

        rec = Staff.query.filter_by(username=username).first()
        if rec:
            flash('User with this username already exists. Please use a different username', 'danger')
            return redirect(url_for('professional_profile'))
        else:
            professional.name = name
            professional.username = username
            professional.password = password
            professional.address = address
            professional.pincode = pincode
            professional.service_experience = service_experience
            db.session.commit()

            # seek approval if you change service

            if service_id != professional.service.id:
                professional.is_approved = False
                professional.service_id = service_id
                db.session.commit()
                flash('Profile updated successfully. Please wait for approval', 'success')
                return redirect(url_for('login'))
            else:
                professional.is_approved = True
                professional.service_id = service_id
                db.session.commit()
                session['username'] = username
                flash('Profile updated successfully', 'success')
                return redirect(url_for('professional_dashboard'))
    
    else:
        return render_template('professional_profile.html', professional = professional, service_requests = service_requests, services = services)

@app.route('/customer_dashboard/profile', methods=['GET', 'POST'])
@customer_required
def customer_profile():
    customer = User.query.get(session['user_id'])

    if request.method == 'POST':

        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        rec = User.query.filter_by(username=username).first()
        if rec:
            flash('User with this username already exists. Please use a different username', 'danger')
            return redirect(url_for('customer_dashboard'))
        else:
            customer.name = name
            customer.username = username
            customer.password = password
            customer.address = address
            customer.pincode = pincode
            db.session.commit()
            session['username'] = username
            flash('Profile updated successfully', 'success')
            return redirect(url_for('customer_dashboard'))
    
    else:
        return render_template('customer_profile.html', customer = customer)

# ============================ADMIN DASHBOARD==========================

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    services = HouseholdServices.query.all()
    service_requests = HouseholdServiceRequest.query.all()
    to_be_approved = Staff.query.filter_by(is_professional=True, is_approved=False).all()

    return render_template('admin_dashboard.html', services=services, service_requests=service_requests, to_be_approved=to_be_approved, admin_name=session['username'])

@app.route('/admin_dashbard/create_service', methods=['GET', 'POST'])
@admin_required
def create_service():
    service_name = request.form.get('service_name')
    service_description = request.form.get('service_description')
    base_price = request.form.get('base_price')
    time_required = request.form.get('time_required')

    if not service_name or not base_price or not time_required:
        flash('All fields are required', 'danger')
        return redirect(url_for('admin_dashboard'))

    existing_service = HouseholdServices.query.filter_by(service_name=service_name).first()
    if existing_service:
        flash('Service with this name already exists', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_service = HouseholdServices(service_name=service_name, service_description=service_description, base_price=base_price, time_required=time_required)
    db.session.add(new_service)
    db.session.commit()
    flash('Service created successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard/<int:service_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_service(service_id):
    service_name = request.form.get('service_name')
    service_description = request.form.get('service_description')
    base_price = request.form.get('base_price')
    time_required = request.form.get('time_required')

    if service_name == '':
        flash('Service name cannot be empty')
        return redirect(url_for('edit_service'))
    if base_price == '':
        flash('Base price cannot be empty')
        return redirect(url_for('edit_service'))
    base_price = float(base_price)
    if time_required == '':
        flash('Time required cannot be empty')
        return redirect(url_for('edit_service'))

    service = HouseholdServices.query.get(service_id)

    if not service:
        flash('Service not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    else:
        service.service_name = service_name
        service.service_description = service_description
        service.base_price = base_price
        service.time_required = time_required
        db.session.commit()
        flash('Service updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard/<int:service_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_service(service_id):
    service = HouseholdServices.query.get(service_id)

    if not service:
        flash('Service not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    else:
        professionals = Staff.query.filter_by(service_id=service_id).all()
        for professional in professionals:
            professional.avg_rating = 0.0
            professional.rating_count = 0
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
@app.route('/admin_dashboard/<int:staff_id>/approve', methods=['GET', 'POST'])
@admin_required
def approve_professional(staff_id):
    user = Staff.query.get(staff_id)
    user.is_approved = True
    db.session.commit()
    flash('Professional approved successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard/<int:staff_id>/reject', methods=['GET', 'POST'])
@admin_required
def reject_professional(staff_id):    
    user = Staff.query.get(staff_id)

    file = user.service_file

    if not user.is_approved:
        if file:
            file_path = os.path.join(app.config['UPLOAD_PATH'], file) 
            if os.path.exists(file_path):
                try:
                    os.remove(file_path) 
                    print("File deleted successfully")
                except Exception as e:
                    print(f"Error deleting file: {e}")
            else:
                print("File does not exist")
        else:
            flash('No file found', 'danger')
            return redirect(url_for('admin_dashboard'))

        db.session.delete(user)
        db.session.commit()
    
    else:        
        user.is_approved = False
        db.session.commit()

    # if the staff was approved before, he's no longer approved: he can be approved again or rejected again which will delete him
    # if the staff was not approved before, he's deleted
    
    flash('Professional rejected successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard/delete_customer/<int:customer_id>', methods=['GET', 'POST'])
@admin_required
def delete_customer(customer_id):
    user = User.query.get(customer_id)

    if not user:
        flash('Customer not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    else:
        db.session.delete(user)
        db.session.commit()
        flash('Customer deleted successfully', 'success')
        return redirect(url_for('admin_search'))

@app.route('/admin_dashboard/search', methods=['GET', 'POST'])
@admin_required
def admin_search():
    # show all the professionals and customers in a particular address or pincode 
    # order professionals by average rating

    parameter = request.args.get('search_type')
    query = request.args.get('query')

    if parameter == 'address':
        professionals = Staff.query.filter(Staff.address.ilike('%' + query + '%'), 
                                           Staff.is_professional == True, Staff.is_approved == True).order_by(Staff.avg_rating.desc())
        customers = User.query.filter(User.address.ilike('%' + query + '%')).all()

    elif parameter == 'pincode':
        professionals = Staff.query.filter(Staff.pincode.ilike('%' + query + '%'),
                                           Staff.is_professional == True, Staff.is_approved == True).order_by(Staff.avg_rating.desc())
        customers = User.query.filter(User.pincode.ilike('%' + query + '%')).all()

    else:
        professionals = Staff.query.filter_by(is_professional=True, is_approved=True).order_by(Staff.avg_rating.desc()).all()
        customers = User.query.all()
    

    return render_template('admin_search.html', customers=customers, professionals=professionals, query = query)

@app.route('/admin_dashboard/<int:professional_id>/service_history')
@admin_required
def professional_service_history(professional_id):
    professional = Staff.query.get(professional_id)

    pending_requests = HouseholdServiceRequest.query.filter_by(professional_id = professional.id, status = 'pending').all()
                                            
    accepted_requests = HouseholdServiceRequest.query.filter_by(professional_id = professional.id, status = 'accepted').all()
                                                        
    rejected_requests = HouseholdServiceRequest.query.filter_by(professional_id = professional.id, status = 'rejected').all()

    closed_requests = HouseholdServiceRequest.query.filter_by(professional_id = professional.id, status = 'closed').all()

    return render_template('professional_service_history.html', professional=professional, pending_requests=pending_requests, accepted_requests=accepted_requests, rejected_requests=rejected_requests, closed_requests=closed_requests)

@app.route('/admin_dashboard/<int:customer_id>/sevice_history')
@admin_required
def customer_service_history(customer_id):
    customer = User.query.get(customer_id)

    pending_requests = HouseholdServiceRequest.query.filter_by(customer_id = customer.id, 
                                                               status = 'pending').all()
                                            
    accepted_requests = HouseholdServiceRequest.query.filter_by(customer_id = customer.id, 
                                                               status = 'accepted').all()
                                                        
    rejected_requests = HouseholdServiceRequest.query.filter_by(customer_id = customer.id, 
                                                               status = 'rejected').all()

    closed_requests = HouseholdServiceRequest.query.filter_by(customer_id = customer.id, 
                                                               status = 'closed').all()

    return render_template('customer_service_history.html', customer=customer, pending_requests=pending_requests, accepted_requests=accepted_requests, rejected_requests=rejected_requests, closed_requests=closed_requests)

# ============================SUMMARY PAGE==========================
@app.route('/admin_dashboard/summary')
@admin_required
def admin_summary():
    customer_count = User.query.count()
    app_professional_count = Staff.query.filter_by(is_professional=True, is_approved=True).count()
    rej_professional_count = Staff.query.filter_by(is_professional=True, is_approved=False).count()

    accepted_request_count = HouseholdServiceRequest.query.filter_by(status='accepted').count()
    pending_request_count = HouseholdServiceRequest.query.filter_by(status='pending').filter(HouseholdServiceRequest.request_type == 'private').count()
    public_request_count = HouseholdServiceRequest.query.filter_by(request_type='public').count()
    rejected_request_count = HouseholdServiceRequest.query.filter_by(status='rejected').count()
    closed_request_count = HouseholdServiceRequest.query.filter_by(status='closed').count()

    services = HouseholdServices.query.all()
    names = [service.service_name for service in services]
    professionals = [service.professionals for service in services]
    service_requests = [service.requests for service in services]

    # to find max requests sent by a customer and their name

    max_requests = HouseholdServiceRequest.query.group_by(HouseholdServiceRequest.customer_id).order_by(func.count(HouseholdServiceRequest.id).desc()).first()
    
    max_request_count = 0
    customer_name = ''

    if max_requests:
        max_request_count = HouseholdServiceRequest.query.filter_by(customer_id=max_requests.customer_id).count()
        customer_name = User.query.get(max_requests.customer_id).username

    # to find max requests sent to a professional and their name

    max_rating = Staff.query.order_by(Staff.avg_rating.desc()).first().avg_rating
    highest_rated_professionals = Staff.query.filter_by(avg_rating=max_rating).all()

    rating = 0.0
    max_professionals = []

    if max_rating:
        rating = max_rating
        max_professionals = [professional.name for professional in highest_rated_professionals]

    p_count = []
    r_count = []

    for professional in professionals:
        p_count.append(len(professional))

    for request in service_requests:
        r_count.append(len(request))

    if not p_count and not names:
        img_1 = os.path.join(config.current_directory, 'static', 'images', 'img_1.png')
        plt.clf()
        plt.figure(figsize=(6,4))
        plt.axis('off')
        plt.title('Professionals by Service')
        plt.text(0.5, 0.5, 'No data available', ha='center')
        plt.savefig(img_1, format='png')
        plt.close()
        
    else:
        img_1 = os.path.join(config.current_directory, 'static', 'images', 'img_1.png')
        plt.clf()
        plt.figure(figsize=(6,4))
        sns.barplot(x=names, y=p_count, palette='viridis')
        plt.title('Professional Count by Service')
        plt.savefig(img_1, format='png')
        plt.close()

    if not r_count and not names:
        img_2 = os.path.join(config.current_directory, 'static', 'images', 'img_2.png')
        plt.clf()
        plt.figure(figsize=(6,4))
        plt.pie([1], labels=['No data available'], colors=['gray'], autopct=None)
        plt.title('Requests by Status')
        plt.savefig(img_2, format='png')
        plt.close()

    else:
        img_2 = os.path.join(config.current_directory, 'static', 'images', 'img_2.png')
        plt.clf()
        autopct = '%1.1f%%'
        plt.figure(figsize=(6,4))
        patches, texts, autotexts = plt.pie(r_count, labels=None, autopct=autopct)
        plt.title('Request Distribution by Service')
        plt.legend(patches, names, loc="upper right", bbox_to_anchor=(1.46, 1))
        plt.savefig(img_2, format='png', bbox_inches=None)
        plt.close()    


    return render_template('admin_summary.html', customer_count=customer_count, app_professional_count=app_professional_count, rej_professional_count=rej_professional_count, accepted_request_count=accepted_request_count, pending_request_count=pending_request_count, public_request_count=public_request_count, rejected_request_count=rejected_request_count, closed_request_count=closed_request_count, max_request_count=max_request_count, customer_name=customer_name, rating=rating, max_professionals=max_professionals)

# ============================PROFESSIONAL DASHBOARD==========================

@app.route('/professional_dashbord')
@professional_required
def professional_dashboard():
    pid = session['user_id']

    professional = Staff.query.get(pid)

    if professional.service_id == None:
        flash('Your service is no longer available, please select a new service', 'danger')
        return redirect(url_for('professional_profile'))

    pending_requests = HouseholdServiceRequest.query.filter_by(professional_id=pid, status='pending', request_type='private').all()

    accepted_requests = HouseholdServiceRequest.query.filter_by(professional_id=pid, status='accepted').all()

    rejected_requests = HouseholdServiceRequest.query.filter_by(professional_id=pid, status='rejected').all()

    closed_requests = HouseholdServiceRequest.query.filter_by(professional_id=pid, status='closed').all()

    return render_template('professional_dashboard.html', pending_requests=pending_requests, accepted_requests=accepted_requests, rejected_requests=rejected_requests, closed_requests=closed_requests)

@app.route('/professional_dashbord/<int:service_request_id>/accept', methods=['GET', 'POST'])
@professional_required
def accept_request(service_request_id):
    service_request = HouseholdServiceRequest.query.filter_by(id = service_request_id, status='pending').first()

    service_request.status = 'accepted'
    db.session.commit()
    flash('Request accepted successfully', 'success')
    return redirect(url_for('professional_dashboard'))

@app.route('/professional_dashbord/<int:service_request_id>/reject', methods=['GET', 'POST'])
@professional_required
def reject_request(service_request_id):
    service_request = HouseholdServiceRequest.query.get(service_request_id)

    service_request.status = 'rejected'
    db.session.commit()
    flash('Request rejected successfully', 'success')
    return redirect(url_for('professional_dashboard'))

@app.route('/professional_dashboard_search', methods=['GET', 'POST'])
@professional_required
def professional_search():
# searching for public requests based on address and pincode

    search_type = request.args.get('search_type')
    query = request.args.get('query')

    professional = Staff.query.get(session.get('user_id'))

    onclause = HouseholdServiceRequest.customer_id == User.id 
    
    if query:
        if search_type == 'address':
            service_requests = HouseholdServiceRequest.query.join(User, onclause).filter(User.address.ilike('%' + query + '%'), 
            HouseholdServiceRequest.status == 'pending',
            HouseholdServiceRequest.request_type == 'public',
            HouseholdServiceRequest.professional_id == None,
            HouseholdServiceRequest.service_id == professional.service_id).all()
        
        elif search_type == 'pincode':
            service_requests = HouseholdServiceRequest.query.join(User, onclause).filter(User.pincode.ilike('%' + query + '%'),
            HouseholdServiceRequest.status == 'pending',
            HouseholdServiceRequest.request_type == 'public',
            HouseholdServiceRequest.professional_id == None,
            HouseholdServiceRequest.service_id == professional.service_id).all()
    else:
        service_requests = HouseholdServiceRequest.query.join(User, onclause).filter(HouseholdServiceRequest.status == 'pending',
        HouseholdServiceRequest.request_type == 'public',
        HouseholdServiceRequest.professional_id == None,
        HouseholdServiceRequest.service_id == professional.service_id).all()

    return render_template('professional_search.html', service_requests=service_requests)

@app.route('/professional_dashboard/sent_requests', methods=['GET', 'POST'])
@professional_required
def sent_requests():
    pid = session['user_id']

    sent_requests = HouseholdServiceRequest.query.filter_by(professional_id=pid, status='pending', request_type='public',).filter(HouseholdServiceRequest.description != None).all()

    return render_template('sent_requests.html', sent_requests=sent_requests)

@app.route('/professional_dashboard/bid_request/<int:service_request_id>', methods=['GET', 'POST'])
@professional_required
def bid_request(service_request_id):
    service_request = HouseholdServiceRequest.query.get(service_request_id)

    description = request.form['description']

    pid = Staff.query.get(session.get('user_id')).id
    service_id = Staff.query.get(pid).service_id
    cid = HouseholdServiceRequest.query.get(service_request_id).customer_id

    new_request = HouseholdServiceRequest(customer_id=cid, professional_id=pid, service_id=service_id, description=description, status='pending', request_type='public')
    db.session.add(new_request)
    db.session.commit()
    flash('Bid request successfully sent to customer', 'success')
    return redirect(url_for('professional_dashboard'))

# ============================CUSTOMER DASHBOARD==========================

@app.route('/customer_dashboard')
@customer_required
def customer_dashboard():
    cid = session['user_id']

    services = HouseholdServices.query.join(Staff).filter_by(is_professional=True, is_approved=True).all()

    customer_requests = HouseholdServiceRequest.query.filter_by(customer_id=cid).filter(HouseholdServiceRequest.professional_id != None).all()

    professionals = Staff.query.filter_by(is_professional=True, is_approved=True).all()

    return render_template('customer_dashboard.html', services=services, professionals=professionals, customer_requests=customer_requests)

@app.route('/customer_dashboard/create_request/<int:service_id>', methods=['GET', 'POST'])
@customer_required
def create_request(service_id):
    cid = session['user_id']

    service = HouseholdServices.query.get(service_id)

    professional_name = request.form.get('professional')
    description = request.form.get('description')

    professional = Staff.query.filter_by(name=professional_name).first()

    new_request = HouseholdServiceRequest(customer_id=cid, service_id=service.id, professional_id=professional.id, description=description, status='pending', request_type='private', date_created=datetime.now().date())
    db.session.add(new_request)
    db.session.commit()
    flash('Request created successfully', 'success')
    return redirect(url_for('customer_dashboard'))
        
@app.route('/customer_dashboard/open_request/<int:service_id>', methods=['GET', 'POST'])
@customer_required
def open_request(service_id):
    cid = session['user_id']

    service = HouseholdServices.query.get(service_id)

    open_request = HouseholdServiceRequest(customer_id=cid, service_id=service_id, status='pending', request_type='public', date_created=datetime.now().date())
    db.session.add(open_request)
    db.session.commit()
    flash('Open request created successfully', 'success')
    return redirect(url_for('customer_dashboard'))

@app.route('/customer_dashboard/edit_request/<int:service_request_id>', methods=['GET', 'POST'])
@customer_required
def edit_request(service_request_id):
    service_request = HouseholdServiceRequest.query.get(service_request_id)

    if service_request.status != 'pending':
        flash('You cannot edit a request that is not pending', 'danger')
        return redirect(url_for('customer_dashboard'))

    if request.method == 'POST':
        description = request.form.get('description')
        service_request.description = description
        db.session.commit()
        flash('Request updated successfully', 'success')
        return redirect(url_for('customer_dashboard'))
    else:
        return render_template('edit_request.html', service_request=service_request)

@app.route('/customer_dashboard/delete_request/<int:service_request_id>', methods=['GET', 'POST'])
@customer_required
def delete_request(service_request_id):
    service_request = HouseholdServiceRequest.query.get(service_request_id)

    if service_request.status == 'accepted':
        flash('You cannot delete a request that is accepted', 'danger')
        return redirect(url_for('customer_dashboard'))

    db.session.delete(service_request)
    db.session.commit()
    flash('Request deleted successfully', 'success')
    return redirect(url_for('customer_dashboard'))

@app.route('/customer_dashboard/close_request/<int:service_request_id>', methods=['GET', 'POST'])
@customer_required
def close_request(service_request_id):  
    service_request = HouseholdServiceRequest.query.get(service_request_id)
    date_created = service_request.date_created

    if request.method == 'POST':
        rating = request.form.get('rating')
        review = request.form.get('review')
        date_closed_str = request.form.get('date_closed')
        date_closed = datetime.strptime(date_closed_str, '%Y-%m-%d').date()

        service_request.customer_rating = float(rating)
        service_request.customer_review = review
        service_request.status = 'closed'
        service_request.date_closed = date_closed

        professional = service_request.professional
        rating_count = professional.rating_count
        avg = professional.avg_rating

        if avg == 0.0 and rating_count == 0:
            avg = float(rating)
            rating_count = 1
        else:
            avg = ((avg * rating_count) + float(rating)) / (rating_count + 1)
            rating_count += 1

        professional.rating_count = rating_count
        professional.avg_rating = avg

        db.session.commit()
        flash('Request closed successfully', 'success')
        return redirect(url_for('customer_dashboard'))
    else:
        return render_template('close_request.html', service_request=service_request, today = datetime.now(), date_created=date_created)


@app.route('/customer_dashboard/search', methods=['GET', 'POST'])
@customer_required
def customer_search():

    parameter = request.args.get('search_type')
    query = request.args.get('query')

    if parameter == 'service_name':
        professionals = Staff.query.join(HouseholdServices).filter(HouseholdServices.service_name.ilike('%' + query + '%'), Staff.is_professional == True, Staff.is_approved == True)
        services = [professional.service for professional in professionals]

    elif parameter == 'address':
        professionals = Staff.query.filter(Staff.address.ilike('%' + query + '%'), Staff.is_professional == True, Staff.is_approved == True).order_by(Staff.service_id)
        services = [professional.service for professional in professionals]

    elif parameter == 'pincode':
        professionals = Staff.query.filter(Staff.pincode.ilike('%' + query + '%'), Staff.is_professional == True, Staff.is_approved == True).order_by(Staff.service_id)
        services = [professional.service for professional in professionals]

    else:
        professionals = Staff.query.filter_by(is_professional=True, is_approved=True).order_by(Staff.service_id).all()
        services = [professional.service for professional in professionals]
    
    # you're searching for professionals first and then displaying service details based on the professional 

    return render_template('customer_search.html', services=services, professionals=professionals, query = query)

@app.route('/customer_dashboard/public_requests', methods=['GET', 'POST'])
@customer_required
def customer_public_requests():
    cid = session['user_id']

    public_requests = HouseholdServiceRequest.query.filter_by(customer_id=cid, request_type='public', status='pending').filter(HouseholdServiceRequest.professional_id == None).all()

    bid_requests = HouseholdServiceRequest.query.filter_by(customer_id=cid, request_type='public', status='pending').filter(HouseholdServiceRequest.professional_id != None).all()
    # all the request bids sent by the professionals

    return render_template('customer_public_requests.html', public_requests=public_requests, bid_requests=bid_requests)

@app.route('/customer_dashboard/accept_request/<int:service_request_id>', methods=['GET', 'POST'])
@customer_required
def accept_professional_request(service_request_id):
    service_request = HouseholdServiceRequest.query.get(service_request_id)

    cid = session['user_id']
    service_id = service_request.service_id

    service_request.status = 'accepted'

    public_request = HouseholdServiceRequest.query.filter_by(customer_id = cid, request_type = 'public', service_id = service_id, status = 'pending').all()
    for i in public_request:
        db.session.delete(i)
    # when you accept a bid, you have to delete the sent request, ie the one with no contractor assgined to it, and the bid requests sent to the customer from other professionals of the service

    db.session.commit()
    flash('Request accepted successfully', 'success')
    return redirect(url_for('customer_public_requests'))

@app.route('/customer_dashboard/reject_request/<int:service_request_id>', methods=['GET', 'POST'])
@customer_required
def reject_professional_request(service_request_id):
    service_request = HouseholdServiceRequest.query.get(service_request_id)

    service_request.status = 'rejected'
    db.session.commit()
    flash('Request rejected successfully', 'success')
    return redirect(url_for('customer_public_requests'))
