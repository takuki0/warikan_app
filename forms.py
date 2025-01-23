from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, SubmitField, DateField, FieldList, BooleanField
from wtforms.validators import DataRequired, NumberRange

class GroupForm(FlaskForm):
    name = StringField('グループ名', validators=[DataRequired()])
    submit = SubmitField('作成')

class AddMemberForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired()])
    submit = SubmitField('追加')

class AddPaymentForm(FlaskForm):
    payer_id = SelectField('支払者', coerce=int, validators=[DataRequired()])
    amount = IntegerField('金額', validators=[DataRequired(), NumberRange(min=1)])
    date = DateField('日付', format='%Y-%m-%d', validators=[DataRequired()])
    memo = TextAreaField('メモ')
    participants = FieldList(BooleanField('参加者'))
    submit = SubmitField('追加')