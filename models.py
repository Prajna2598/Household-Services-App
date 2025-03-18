from flask_sqlalchemy import SQLAlchemy
from app import app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy(app)

class PasswordMixin:
    @property
    def password(self):
        raise AttributeError('you cannot read the password attribute directly')

    @password.setter
    def password(self, password):
        self.passhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passhash, password)

class User(PasswordMixin,db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    passhash = db.Column(db.String(256), nullable=False)
    address = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.Integer, nullable=False)
    
    # relationship between customer and request: this is the ONE side
    # one to many: ie one customer can make many requests, but a request can be associated with only one user
    requests_sent = db.relationship('HouseholdServiceRequest', back_populates = 'customer', foreign_keys = 'HouseholdServiceRequest.customer_id', cascade='all, delete')
    # when a User (customer) is deleted, all associated HouseholdServiceRequest objects will also be deleted.

class Staff(PasswordMixin,db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    passhash = db.Column(db.String(256), nullable=False)
    address = db.Column(db.String(80), nullable=True)
    pincode = db.Column(db.Integer, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_professional = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    service_file = db.Column(db.String(80), nullable=True)
    service_experience = db.Column(db.String(80), nullable=True)
    avg_rating = db.Column(db.Float, default = 0.0)
    rating_count = db.Column(db.Integer, default = 0)
    service_id = db.Column(db.Integer, db.ForeignKey('household_services.id', ondelete='SET NULL'), nullable=True) 
    # ondelete = 'SET NULL' sets the service_id to null if the service is deleted

    # relationship between professional and service: this is the MANY side
    # one to many: ie one service can be given by many professionals
    service = db.relationship('HouseholdServices', back_populates='professionals')

    # relationship between professional and request: this is the MANY side
    # one to many: a professional can receive multiple requests, but a request can be sent to only one professional, ie one request can't be given to two professionals simultaneously
    requests_received = db.relationship('HouseholdServiceRequest', back_populates = 'professional', foreign_keys = 'HouseholdServiceRequest.professional_id')

class HouseholdServices(db.Model):
    __tablename__ = 'household_services'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_name = db.Column(db.String(80), unique=True, nullable=False)
    service_description = db.Column(db.String(80), nullable=False)
    base_price = db.Column(db.Float, default = 0.0, nullable=False)
    time_required = db.Column(db.String(80), nullable=False)

    # relationship between service and professional: this is the ONE side
    # one to many: ie one service can be given by many professionals
    professionals = db.relationship('Staff', back_populates = 'service')

    '''
    service.professionals = [<professional1>, <professional2>, <professional3>]
    professional.service = <service object>
    '''

    # relationship between service and request: this is the MANY side
    # one to many: ie one service can be requested by many customers, but one customer can request only one service
    requests = db.relationship('HouseholdServiceRequest', back_populates = 'req_service', cascade='all, delete')
    # if a service is deleted, all the requests for that service will be deleted

class HouseholdServiceRequest(db.Model):
    __tablename__ = 'household_service_request'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.Integer, db.ForeignKey('household_services.id'), nullable=False) 
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    request_type = db.Column(db.String(10), nullable=False) # private/public
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(80), nullable=False) #pending, accepted, rejected, closed
    date_created = db.Column(db.Date, nullable = False, default=datetime.now().date())
    date_closed = db.Column(db.Date, nullable = True)
    customer_rating = db.Column(db.Float, default = 0.0)
    customer_review = db.Column(db.String(80), nullable=True)

    # relationship between customer and request: this is the MANY side
    # one to many: ie one customer can make many requests, but a request can be associated with only one user
    customer = db.relationship('User', back_populates = 'requests_sent')
    
    # relationship between service and request: this is the ONE side
    # one to many: ie one service can be requested by many customers, but one customer can request only one service
    req_service = db.relationship('HouseholdServices', back_populates = 'requests')

    # relationship between professional and request: this is the ONE side
    # one to many: a professional can receive multiple requests, but a request can be sent to only one professional, ie one request can't be given to two professionals simultaneously
    professional = db.relationship('Staff', back_populates = 'requests_received')

with app.app_context():
    db.create_all()

# create admin if admin doesn't exist(within app context)
    admin = Staff.query.filter_by(is_admin=True).first()
    
    if not admin:
        admin = Staff(username = 'admin', password = 'admin', is_admin = True)        
        db.session.add(admin)
        db.session.commit()