from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired

class GroupForm(FlaskForm):
    name = StringField('グループ名', validators=[DataRequired()])

class AddMemberForm(FlaskForm):
    name = StringField('メンバー名', validators=[DataRequired()])

class AddPaymentForm(FlaskForm):
    payer_id = SelectField('支払者', coerce=int, validators=[DataRequired()])
    amount = FloatField('金額', validators=[DataRequired()])
    date = DateField('日付', validators=[DataRequired()])
    memo = StringField('メモ')
    participants = SelectMultipleField('参加者', coerce=int, validators=[DataRequired()])