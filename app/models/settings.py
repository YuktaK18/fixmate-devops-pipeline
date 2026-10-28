from datetime import datetime, timezone
from app.extensions import db


class SystemSetting(db.Model):
    """Admin-configurable system settings and business rule parameters."""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @classmethod
    def get_value(cls, key: str, default: str = None) -> str:
        """Retrieves a setting value by key, falling back to provided default."""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_value(cls, key: str, value: str, description: str = None):
        """Sets or updates a setting key-value pair."""
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        else:
            setting.value = str(value)
            if description:
                setting.description = description
        db.session.commit()

    def __repr__(self):
        return f"<SystemSetting key='{self.key}' val='{self.value}'>"
