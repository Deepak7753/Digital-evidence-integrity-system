from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from app.models.case import Case

class EvidenceUploadForm(FlaskForm):
    title = StringField('Evidence Item Name', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Evidence Category', choices=[
        ('Image', 'Digital Image (EXIF/GPS)'),
        ('Video', 'Video Recording (MP4/Codec)'),
        ('Audio', 'Audio Recording (WAV/Duration)'),
        ('Document', 'Forensic Document (PDF/Metadata)'),
        ('Malware Sample', 'Malware / Executable binary'),
        ('Network Capture', 'Network Packet Capture (PCAP)'),
        ('Mobile Evidence', 'Mobile DB / Plist File')
    ], validators=[DataRequired()])
    case_id = SelectField('Link to Case File', coerce=int, validators=[DataRequired()])
    remarks = TextAreaField('Custody & Acquisition Remarks', validators=[Length(max=500)])
    submit = SubmitField('Upload & Encrypt Evidence')

    def __init__(self, *args, **kwargs):
        super(EvidenceUploadForm, self).__init__(*args, **kwargs)
        # Populate cases list dynamically
        active_cases = Case.query.filter(Case.status.in_(['Open', 'Active', 'Pending', 'Complete'])).all()
        self.case_id.choices = [(c.id, f"{c.case_number} - {c.name}") for c in active_cases]
