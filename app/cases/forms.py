from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from app.models.case import Case
from app.models.user import User

class CaseForm(FlaskForm):
    case_number = StringField('Case Number ID', validators=[DataRequired(), Length(max=50)])
    name = StringField('Case Title Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Case Narrative / Description', validators=[Length(max=1000)])
    status = SelectField('Case Status', choices=[
        ('Open', 'Open / Intake'),
        ('Active', 'Active Investigation'),
        ('Pending', 'Pending'),
        ('Complete', 'Complete'),
        ('Closed', 'Closed / Resolved'),
        ('Archived', 'Archived')
    ], validators=[DataRequired()])
    investigator_id = SelectField('Assigned Investigator', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Case')

    def __init__(self, *args, **kwargs):
        super(CaseForm, self).__init__(*args, **kwargs)
        # Populate investigators list dynamically
        investigators = User.query.filter(User.roles.any(name='investigator')).all()
        self.investigator_id.choices = [(u.id, f"{u.fullname} ({u.username})") for u in investigators]
        # Allow admin/system fallback if no investigator is registered yet
        admins = User.query.filter(User.roles.any(name='admin')).all()
        for admin in admins:
            if (admin.id, f"{admin.fullname} ({admin.username})") not in self.investigator_id.choices:
                self.investigator_id.choices.append((admin.id, f"{admin.fullname} ({admin.username}) (Admin)"))
