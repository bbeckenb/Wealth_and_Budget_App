"""Forms for our demo Flask app."""

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField
from wtforms.fields.html5 import URLField
from wtforms.validators import InputRequired, Optional #Email

# EXAMPLES
# states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
#           "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
#           "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
#           "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
#           "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

# class AddSnackForm(FlaskForm):
#     """Form for adding snacks."""

#     name = StringField("Snack Name")
#     price = FloatField("Price in USD")
#     # quantity = FloatField("Amount of Snack")

# class EmployeeForm(FlaskForm):
#     name = StringField("Employee Name", validators=[
#                        InputRequired(message="Name cannot be blank")])
#     state = SelectField('State', choices=[(st, st) for st in states])
#     dept_code = SelectField("Department Code")