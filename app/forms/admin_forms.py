from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp


class ProviderVerificationForm(FlaskForm):
    """Admin action form to approve or reject provider KYC application."""
    action = SelectField('Decision', choices=[('APPROVE', 'Approve Application'), ('REJECT', 'Reject Application')], validators=[DataRequired()])
    rejection_reason = TextAreaField('Reason (Mandatory if Rejecting)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Submit Decision')


class CategoryForm(FlaskForm):
    """Admin form to create or edit service categories."""
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    slug = StringField('URL Slug', validators=[DataRequired(), Length(min=2, max=100), Regexp(r'^[a-z0-9\-]+$', message="Use lowercase letters, numbers, and hyphens.")])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    icon = StringField('Bootstrap Icon Name (e.g. bi-tools, bi-lightning)', validators=[DataRequired(), Length(max=100)])
    min_base_price = DecimalField('Minimum Allowed Price (₹)', places=2, validators=[DataRequired(), NumberRange(min=50, max=50000)])
    max_base_price = DecimalField('Maximum Allowed Price (₹)', places=2, validators=[DataRequired(), NumberRange(min=50, max=50000)])
    is_active = BooleanField('Active in Catalog', default=True)
    submit = SubmitField('Save Category')


class ComplaintResolutionForm(FlaskForm):
    """Admin dispute handling form."""
    status = SelectField(
        'Update Ticket Status',
        choices=[
            ('IN_REVIEW', 'In Review (Investigating)'),
            ('RESOLVED', 'Resolved (Action taken / Settled)'),
            ('REJECTED', 'Rejected (Invalid claim)')
        ],
        validators=[DataRequired()]
    )
    resolution_notes = TextAreaField('Resolution Summary & Notes to Customer', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Update Ticket')


class SystemSettingsForm(FlaskForm):
    """Admin-configurable platform settings and business rules."""
    commission_percentage = DecimalField('Platform Commission (%)', places=2, validators=[DataRequired(), NumberRange(min=0, max=50)])
    cancellation_fee_percentage = DecimalField('Cancellation Fee (%)', places=2, validators=[DataRequired(), NumberRange(min=0, max=50)])
    cancellation_window_minutes = IntegerField('Cancellation Penalty Window (Minutes)', validators=[DataRequired(), NumberRange(min=5, max=120)])
    gst_percentage = DecimalField('Goods & Services Tax GST (%)', places=2, validators=[DataRequired(), NumberRange(min=0, max=30)])
    submit = SubmitField('Update Platform Settings')


class RefundForm(FlaskForm):
    """Issue full or partial refund for a disputed payment."""
    refund_amount = DecimalField('Refund Amount (₹)', places=2, validators=[DataRequired(), NumberRange(min=1, max=50000)])
    refund_reason = TextAreaField('Refund Reason', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Process Refund')
