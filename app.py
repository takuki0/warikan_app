from flask import Flask, render_template, request, redirect, url_for, flash
from extensions import db
from models import User, Group, GroupMember, Payment, PaymentParticipant
from forms import GroupForm, AddMemberForm, AddPaymentForm
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warikan.db'
db.init_app(app)

# データベースの初期化
with app.app_context():
    db.create_all()
    # 固定値のユーザーを追加
    if not User.query.get(1):
        user = User(id=1, name="固定ユーザー")
        db.session.add(user)
        db.session.commit()

@app.route('/')
def index():
    groups = Group.query.all()
    return render_template('index.html', groups=groups)

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    form = GroupForm()
    if form.validate_on_submit():
        name = form.name.data
        user_id = 1  # 固定値
        group = Group(name=name, creator_id=user_id)
        db.session.add(group)
        db.session.commit()
        return redirect(url_for('group_detail', group_id=group.id))
    return render_template('create_group.html', form=form)

@app.route('/add_member/<int:group_id>', methods=['GET', 'POST'])
def add_member(group_id):
    form = AddMemberForm()
    if form.validate_on_submit():
        name = form.name.data
        user = User(name=name)
        db.session.add(user)
        db.session.commit()
        group_member = GroupMember(group_id=group_id, user_id=user.id)
        db.session.add(group_member)
        db.session.commit()
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('add_member.html', form=form, group_id=group_id)

@app.route('/group/<int:group_id>')
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    return render_template('group_detail.html', group=group)

@app.route('/add_payment/<int:group_id>', methods=['GET', 'POST'])
def add_payment(group_id):
    group = Group.query.get_or_404(group_id)
    form = AddPaymentForm()
    # GroupMember から User を経由して name を取得
    form.payer_id.choices = [(member.user.id, member.user.name) for member in group.members]
    form.participants.choices = [(member.user.id, member.user.name) for member in group.members]
    if form.validate_on_submit():
        payment = Payment(
            group_id=group_id,
            payer_id=form.payer_id.data,
            amount=form.amount.data,
            date=form.date.data,
            memo=form.memo.data
        )
        db.session.add(payment)
        db.session.commit()
        for participant_id in form.participants.data:
            participant = PaymentParticipant(payment_id=payment.id, user_id=participant_id)
            db.session.add(participant)
        db.session.commit()
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('add_payment.html', form=form, group_id=group_id, members=group.members)

@app.route('/edit_payment/<int:group_id>/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(group_id, payment_id):
    group = Group.query.get_or_404(group_id)
    payment = Payment.query.get_or_404(payment_id)
    form = AddPaymentForm(obj=payment)
    # GroupMember から User を経由して name を取得
    form.payer_id.choices = [(member.user.id, member.user.name) for member in group.members]
    form.participants.choices = [(member.user.id, member.user.name) for member in group.members]
    if form.validate_on_submit():
        payment.payer_id = form.payer_id.data
        payment.amount = form.amount.data
        payment.date = form.date.data
        payment.memo = form.memo.data
        participant_ids = form.participants.data
        payment.participants = []
        for participant_id in participant_ids:
            participant = PaymentParticipant(payment_id=payment.id, user_id=participant_id)
            db.session.add(participant)
        db.session.commit()
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('edit_payment.html', form=form, group_id=group_id, payment=payment, members=group.members)

@app.route('/delete_payment/<int:group_id>/<int:payment_id>', methods=['GET', 'POST'])
def delete_payment(group_id, payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if request.method == 'POST':
        db.session.delete(payment)
        db.session.commit()
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('delete_payment.html', group_id=group_id, payment=payment)

@app.route('/settlement/<int:group_id>')
def settlement(group_id):
    group = Group.query.get_or_404(group_id)
    settlement_pairs = calculate_settlement(group_id, 'round')
    return render_template('settlement.html', group=group, settlement_pairs=settlement_pairs)

def calculate_settlement(group_id, rounding_method):
    group = Group.query.get(group_id)
    members = group.members
    payments = Payment.query.filter_by(group_id=group_id).all()
    member_stats = {}
    for member in members:
        member_stats[member.user.id] = {  # member.user.id を使用
            "name": member.user.name,  # member.user.name を使用
            "total_paid": 0,
            "participated_count": 0
        }
    for payment in payments:
        member_stats[payment.payer_id]["total_paid"] += payment.amount
        for participant in payment.participants:
            member_stats[participant.user_id]["participated_count"] += 1
    for member_id, stats in member_stats.items():
        if stats["participated_count"] > 0:
            stats["paid_per_participation"] = stats["total_paid"] / stats["participated_count"]
        else:
            stats["paid_per_participation"] = 0
    total_paid = sum(stats["total_paid"] for stats in member_stats.values())
    total_participated_count = sum(stats["participated_count"] for stats in member_stats.values())
    average_paid = total_paid / total_participated_count if total_participated_count > 0 else 0
    for member_id, stats in member_stats.items():
        settlement_amount = (stats["paid_per_participation"] - average_paid) * stats["participated_count"]
        if rounding_method == "ceil":
            stats["settlement_amount"] = math.ceil(settlement_amount)
        elif rounding_method == "floor":
            stats["settlement_amount"] = math.floor(settlement_amount)
        else:
            stats["settlement_amount"] = round(settlement_amount)
    settlement_pairs = []
    payers = [member_id for member_id, stats in member_stats.items() if stats["settlement_amount"] > 0]
    receivers = [member_id for member_id, stats in member_stats.items() if stats["settlement_amount"] < 0]
    payers.sort(key=lambda member_id: member_stats[member_id]["settlement_amount"], reverse=True)
    receivers.sort(key=lambda member_id: member_stats[member_id]["settlement_amount"])
    while payers and receivers:
        payer_id = payers[0]
        receiver_id = receivers[0]
        amount = min(member_stats[payer_id]["settlement_amount"], -member_stats[receiver_id]["settlement_amount"])
        settlement_pairs.append({
            "payer": member_stats[payer_id]["name"],
            "receiver": member_stats[receiver_id]["name"],
            "amount": amount
        })
        member_stats[payer_id]["settlement_amount"] -= amount
        member_stats[receiver_id]["settlement_amount"] += amount
        if member_stats[payer_id]["settlement_amount"] == 0:
            payers.pop(0)
        if member_stats[receiver_id]["settlement_amount"] == 0:
            receivers.pop(0)
    return settlement_pairs

if __name__ == '__main__':
    app.run(debug=True)