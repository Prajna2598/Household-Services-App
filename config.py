import os

from dotenv import load_dotenv

from app import app

load_dotenv()

current_directory = os.path.dirname(os.path.abspath(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///homemakers.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
app.config["SECRET_KEY"] = os.getenv('SECRET_KEY')

app.config['UPLOAD_EXTENSIONS'] = ['.pdf']
app.config['UPLOAD_PATH'] = os.path.join(current_directory, 'static', 'pdf') 

print('Configured successfully')