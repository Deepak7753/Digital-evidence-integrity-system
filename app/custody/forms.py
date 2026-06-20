from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from app.models.user import User

class TransferCustodyForm(FlaskForm):
    to_user_id = SelectField('Transfer Custody To', coerce=int, validators=[DataRequired()])
    remarks = TextAreaField('Custody Transfer Reason / Remarks', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Authorize Custody Transfer')

    def __init__(self, *args, **kwargs):
        super(TransferCustodyForm, self).__init__(*args, **kwargs)
        # Populate active users list who can receive custody
        users = User.query.filter(User.is_active == True).all()
        self.to_user_id.choices = [(u.id, f"{u.fullname} ({u.primary_role.upper() if u.primary_role else 'USER'})") for u in users]
