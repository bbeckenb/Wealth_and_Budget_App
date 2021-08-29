"""Forms for our demo Flask app."""

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, IntegerField
from wtforms.fields.core import FormField
from wtforms.fields.html5 import URLField
from wtforms.fields.simple import PasswordField
from wtforms.validators import InputRequired, Length, NumberRange, Optional, Regexp #Email

# EXAMPLES
# states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
#           "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
#           "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
#           "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
#           "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

# class TelephoneForm(FlaskForm):
#     country_code = IntegerField("Country Code", validators=[InputRequired(message="Country Code is required")])
#     area_code    = IntegerField('Area Code', validators=[InputRequired(message="Area Code is required")])
#     number       = 

class SignUpUserForm(FlaskForm):
    """Form for user sign up"""
    username = StringField("Username", validators=[InputRequired(message="Username is required")])
    password = PasswordField("Password", validators=[InputRequired(message="Password is required")])
    phone_number = StringField("Phone Number", validators=[InputRequired(message="10 digit sequential phone number required, ex: 1234567890"), Regexp("^[0-9]*$", message="10 digit sequential phone number required, ex: 1234567890"), Length(min=10, max=10, message="10 digit sequential phone number required, ex: 1234567890")])
    first_name = StringField("First name", validators=[InputRequired(message="First name is required")])
    last_name = StringField("Last name", validators=[InputRequired(message="Last name is required")])

class LoginForm(FlaskForm):
    """Login form."""

    username = StringField("Username", validators=[InputRequired(message="Username is required")])
    password = PasswordField("Password", validators=[InputRequired(message="Password is required")])

class UpdateUserForm(FlaskForm):
    """Form for user to update their profile"""
    username = StringField("Username")
    phone_number = StringField("Phone Number", validators=[InputRequired(message="10 digit sequential phone number required, ex: 1234567890"), Regexp("^[0-9]*$", message="10 digit sequential phone number required, ex: 1234567890"), Length(min=10, max=10, message="10 digit sequential phone number required, ex: 1234567890")])
    first_name = StringField("First name")
    last_name = StringField("Last name")
    password = PasswordField("Authorize update with your Password", validators=[InputRequired(message="Password is required")])

class CreateBudgetTrackerForm(FlaskForm):
    """Form for user to create budget tracker for their account"""
    budget_threshold = FloatField("Monthly Budget Threshold", validators=[InputRequired(message="Threshold amount required"), NumberRange(min=0, message="Minimum threshold $0")])
    notification_frequency = IntegerField("Notification Frequency (Days between notifications)", validators=[InputRequired(message="Notification Frequency required"), NumberRange(min=1, max=15, message="Notification Frequency must be between 1 and 15 days")])

class UpdateBudgetTrackerForm(FlaskForm): 
    """Form for user to update budget tracker for their account"""
    budget_threshold = FloatField("Monthly Budget Threshold", validators=[InputRequired(message="Threshold amount required"), NumberRange(min=0, message="Minimum threshold $0")])
    notification_frequency = IntegerField("Notification Frequency (Days between notifications)", validators=[InputRequired(message="Notification Frequency required"), NumberRange(min=1, max=15, message="Notification Frequency must be between 1 and 15 days")])  
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