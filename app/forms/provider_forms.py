from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp, Optional


class ProviderProfileForm(FlaskForm):
    """Provider professional details and service locality."""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Regexp(r'^[6-9]\d{9}$', message="Enter a valid 10-digit mobile number.")])
    bio = TextAreaField('Professional Summary / Bio', validators=[Optional(), Length(max=800)])
    experience_years = IntegerField('Years of Experience', validators=[DataRequired(), NumberRange(min=0, max=50)])
    service_pincode = StringField('Base Service Pincode', validators=[DataRequired(), Regexp(r'^\d{6}$', message="Enter a valid 6-digit PIN code.")])
    service_area_name = StringField('Service Area / Locality', validators=[DataRequired(), Length(min=2, max=100)])
    service_radius_km = IntegerField('Operating Radius (km)', validators=[DataRequired(), NumberRange(min=1, max=50)])
    availability_status = SelectField(
        'Current Availability Status',
        choices=[
            ('AVAILABLE', 'Available (Ready to take jobs)'),
            ('BUSY', 'Busy (Temporarily engaged)'),
            ('OFFLINE', 'Offline (Not accepting jobs)')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Save Profile Details')


class DocumentUploadForm(FlaskForm):
    """KYC document uploads (Govt ID and Address Proof)."""
    id_proof = FileField(
        'Government-issued Photo ID (Aadhaar / PAN / Voter ID)',
        validators=[
            Optional(),
            FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'Allowed formats: PDF, PNG, JPG, JPEG (Max 5MB)')
        ]
    )
    address_proof = FileField(
        'Proof of Address (Electricity bill / Rent agreement / Aadhaar)',
        validators=[
            Optional(),
            FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'Allowed formats: PDF, PNG, JPG, JPEG (Max 5MB)')
        ]
    )
    submit = SubmitField('Upload Documents for Verification')


class ProviderServiceForm(FlaskForm):
    """Assign service category and set custom pricing within admin limits."""
    category_id = SelectField('Select Service Category', coerce=int, validators=[DataRequired()])
    custom_price = DecimalField('Your Service Rate (₹)', places=2, validators=[DataRequired(), NumberRange(min=50, max=10000)])
    description = TextAreaField('Description of Services Included', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Service Offering')


class JobCompleteForm(FlaskForm):
    """Technician completion form confirming final billable amount."""
    final_amount = DecimalField('Final Confirmed Bill Amount (₹)', places=2, validators=[DataRequired(), NumberRange(min=50, max=25000)])
    notes = TextAreaField('Completion Notes for Customer', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Mark Job Completed')
