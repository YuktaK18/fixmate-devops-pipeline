from app.extensions import db
from app.models.notification import Notification


class NotificationService:
    """Manages creation, unread count tracking, and promotional message filtering."""

    @staticmethod
    def send(user_id: int, title: str, message: str, notification_type: str = 'BOOKING',
             is_promotional: bool = False, link_url: str = None) -> Notification:
        """Creates an in-app notification."""
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            is_promotional=is_promotional,
            link_url=link_url
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def get_unread_count(user_id: int, allow_promotional: bool = True) -> int:
        """Returns the number of unread alerts for the user."""
        query = Notification.query.filter_by(user_id=user_id, is_read=False)
        if not allow_promotional:
            query = query.filter_by(is_promotional=False)
        return query.count()
