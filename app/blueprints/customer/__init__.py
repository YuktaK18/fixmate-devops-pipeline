from flask import Blueprint

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

from app.blueprints.customer import routes
