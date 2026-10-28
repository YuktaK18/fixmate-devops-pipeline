from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateField, IntegerField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp, Optional
from datetime import datetime, timezone, timedelta


class CustomerProfileForm(FlaskForm):
    """Customer profile details update."""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Regexp(r'^[6-9]\d{9}$', message="Enter a valid 10-digit mobile number.")])
    submit = SubmitField('Update Profile')


class BookingCreateForm(FlaskForm):
    """Booking creation form."""
    provider_id = HiddenField('Provider ID', validators=[DataRequired()])
    category_id = HiddenField('Category ID', validators=[DataRequired()])
    
    scheduled_date = DateField('Service Date', validators=[DataRequired()], format='%Y-%m-%d')
    scheduled_time_slot = SelectField(
        'Preferred Time Slot',
        choices=[
            ('09:00 - 11:00 AM', '09:00 - 11:00 AM (Morning)'),
            ('11:00 - 01:00 PM', '11:00 - 01:00 PM (Late Morning)'),
            ('02:00 - 04:00 PM', '02:00 - 04:00 PM (Afternoon)'),
            ('04:00 - 06:00 PM', '04:00 - 06:00 PM (Evening)'),
            ('06:00 - 08:00 PM', '06:00 - 08:00 PM (Late Evening)'),
        ],
        validators=[DataRequired()]
    )
    service_address = TextAreaField('Service Location Address', validators=[DataRequired(), Length(min=10, max=500)])
    pincode = StringField('Pincode', validators=[DataRequired(), Regexp(r'^\d{6}$', message="Enter a valid 6-digit Indian PIN code.")])
    special_instructions = TextAreaField('Special Instructions / Notes for Technician', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Confirm and Book Service')


class RescheduleRequestForm(FlaskForm):
    """Request appointment reschedule."""
    proposed_date = DateField('Proposed New Date', validators=[DataRequired()], format='%Y-%m-%d')
    proposed_time_slot = SelectField(
        'Proposed Time Slot',
        choices=[
            ('09:00 - 11:00 AM', '09:00 - 11:00 AM (Morning)'),
            ('11:00 - 01:00 PM', '11:00 - 01:00 PM (Late Morning)'),
            ('02:00 - 04:00 PM', '02:00 - 04:00 PM (Afternoon)'),
            ('04:00 - 06:00 PM', '04:00 - 06:00 PM (Evening)'),
            ('06:00 - 08:00 PM', '06:00 - 08:00 PM (Late Evening)'),
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Submit Reschedule Request')


class ReviewForm(FlaskForm):
    """Post-job rating and review submission."""
    rating = SelectField(
        'Rating (Stars)',
        choices=[('5', '★★★★★ — Outstanding (5 Stars)'),
                 ('4', '★★★★☆ — Very Good (4 Stars)'),
                 ('3', '★★★☆☆ — Satisfactory (3 Stars)'),
                 ('2', '★★☆☆☆ — Needs Improvement (2 Stars)'),
                 ('1', '★☆☆☆☆ — Poor (1 Star)')],
        validators=[DataRequired()]
    )
    comment = TextAreaField('Review & Experience Comments (Optional)', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Review')


class ComplaintForm(FlaskForm):
    """Dispute ticket submission within 7 days of service."""
    subject = StringField('Complaint Subject', validators=[DataRequired(), Length(min=5, max=150)])
    description = TextAreaField('Detailed Description of Problem', validators=[DataRequired(), Length(min=20, max=2000)])
    photo = FileField('Attach Evidence Photo (Optional)', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only (JPG, PNG)')])
    submit = SubmitField('File Complaint Ticket')
