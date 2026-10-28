from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from app.models.user import User

EMAIL_REGEX = Regexp(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message="Enter a valid email address.")


class RegistrationForm(FlaskForm):
    """User registration form strictly limited to Customer and Provider roles (SRS 4.1)."""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(), EMAIL_REGEX, Length(max=120)])
    phone = StringField(
        'Phone Number',
        validators=[
            DataRequired(),
            Regexp(r'^[6-9]\d{9}$', message="Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")
        ]
    )
    role = SelectField(
        'Registering As',
        choices=[('customer', 'Customer (Looking for Home Services)'), ('provider', 'Service Provider (Skilled Professional)')],
        validators=[DataRequired()]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password', message="Passwords must match.")
        ]
    )
    terms_accepted = BooleanField(
        'I accept the Terms of Service and Privacy Policy',
        validators=[DataRequired(message="You must accept the Terms of Service to register.")]
    )
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('An account with this email address already exists.')

    def validate_phone(self, field):
        if User.query.filter_by(phone=field.data.strip()).first():
            raise ValidationError('An account with this phone number already exists.')


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email Address', validators=[DataRequired(), EMAIL_REGEX])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class PasswordResetRequestForm(FlaskForm):
    """Initiates secure password reset."""
    email = StringField('Registered Email Address', validators=[DataRequired(), EMAIL_REGEX])
    submit = SubmitField('Send Password Reset Link')


class PasswordResetForm(FlaskForm):
    """Sets a new password using a verified token."""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match.")])
    submit = SubmitField('Update Password')
