from flask import Blueprint

provider_bp = Blueprint('provider', __name__, url_prefix='/provider')

from app.blueprints.provider import routes
