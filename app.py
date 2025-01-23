from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import models
from forms import GroupForm, AddMemberForm, AddPaymentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # ここで'your_secret_key'をランダムな文字列に置き換えてください
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warikan.db'
db = SQLAlchemy(app)

@app.route('/')
def index():
    return render_template('index.html')  # index.html を表示する

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    form = GroupForm()
    if form.validate_on_submit():
        name = form.name.data
        # ユーザーIDは固定値を使用（例：1）
        user_id = 1  
        # グループを作成
        group = models.Group(name=name, creator_id=user_id)
        # データベースに保存
        db.session.add(group)
        db.session.commit()  # データベースにコミット

        # コミット後に group.id を参照
        print(group.id)  # group.id を出力

        # グループ作成完了ページにリダイレクト
        return redirect(url_for('group_detail', group_id=group.id))
    return render_template('create_group.html', form=form)

@app.route('/add_member/<int:group_id>', methods=['GET', 'POST'])
def add_member(group_id):
    form = AddMemberForm()
    if form.validate_on_submit():
        # ユーザーは固定値を使用（例：IDが1のユーザー）
        user = models.User.query.get(1)  
        if user:
            # グループメンバーを追加
            group_member = models.GroupMember(group_id=group_id, user_id=user.id)
            db.session.add(group_member)
            db.session.commit()
            # メンバー追加完了ページにリダイレクト
            return redirect(url_for('group_detail', group_id=group_id))
        else:
            flash('ユーザーが見つかりません')
    return render_template('add_member.html', form=form, group_id=group_id)

@app.route('/group/<int:group_id>')
def group_detail(group_id):
    group = models.Group.query.get_or_404(group_id)
    return render_template('group_detail.html', group=group)

@app.route('/add_payment/<int:group_id>', methods=['GET', 'POST'])
def add_payment(group_id):
    group = models.Group.query.get_or_404(group_id)
    form = AddPaymentForm()
    # 支払者選択の選択肢を設定
    form.payer_id.choices = [(member.id, member.name) for member in group.members]
    # 参加者チェックボックスの選択肢を設定
    form.participants.choices = [(member.id, member.name) for member in group.members]
    if form.validate_on_submit():
        # フォームから入力値を取得
        payer_id = form.payer_id.data
        amount = form.amount.data
        date = form.date.data
        memo = form.memo.data
        participant_ids = [participant[0] for participant in form.participants.data if participant[1]]  # チェックされた参加者のIDを取得
        # 支払い記録を作成
        payment = models.Payment(group_id=group_id, payer_id=payer_id, amount=amount, date=date, memo=memo)
        db.session.add(payment)
        db.session.commit()
        # 参加者を追加
        for participant_id in participant_ids:
            participant = models.PaymentParticipant(payment_id=payment.id, user_id=participant_id)
            db.session.add(participant)
        db.session.commit()
        # 支払い記録追加完了ページにリダイレクト
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('add_payment.html', form=form, group_id=group_id, members=group.members)

@app.route('/edit_payment/<int:group_id>/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(group_id, payment_id):
    group = models.Group.query.get_or_404(group_id)
    payment = models.Payment.query.get_or_404(payment_id)
    form = AddPaymentForm(obj=payment)  # 既存の支払い記録をフォームに設定
    # 支払者選択の選択肢を設定
    form.payer_id.choices = [(member.id, member.name) for member in group.members]
    # 参加者チェックボックスの選択肢を設定
    form.participants.choices = [(member.id, member.name) for member in group.members]
    if form.validate_on_submit():
        # フォームから入力値を取得
        payment.payer_id = form.payer_id.data
        payment.amount = form.amount.data
        payment.date = form.date.data
        payment.memo = form.memo.data
        # 参加者を更新
        participant_ids = [participant[0] for participant in form.participants.data if participant[1]]  # チェックされた参加者のIDを取得
        payment.participants = []  # 既存の参加者をクリア
        for participant_id in participant_ids:
            participant = models.PaymentParticipant(payment_id=payment.id, user_id=participant_id)
            db.session.add(participant)
        db.session.commit()
        # 支払い記録編集完了ページにリダイレクト
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('edit_payment.html', form=form, group_id=group_id, payment=payment, members=group.members)

@app.route('/delete_payment/<int:group_id>/<int:payment_id>', methods=['GET', 'POST'])
def delete_payment(group_id, payment_id):
    payment = models.Payment.query.get_or_404(payment_id)
    if request.method == 'POST':
        # 支払い記録を削除
        db.session.delete(payment)
        db.session.commit()
        # 支払い記録削除完了ページにリダイレクト
        return redirect(url_for('group_detail', group_id=group_id))
    return render_template('delete_payment.html', group_id=group_id, payment=payment)

#精算処理を行うための関数
import math
def calculate_settlement(group_id, rounding_method):
    """
    グループの精算金額を計算する

    Args:
        group_id (int): グループID
        rounding_method (str): 端数処理方法 ("ceil", "floor", "round")

    Returns:
        dict: 精算結果
    """
    group = models.Group.query.get(group_id)
    members = group.members
    payments = models.Payment.query.filter_by(group_id=group_id).all()
    # メンバーごとの支払額と参加回数を集計
    member_stats = {}
    for member in members:
        member_stats[member.id] = {
            "name": member.name,
            "total_paid": 0,
            "participated_count": 0
        }
    for payment in payments:
        member_stats[payment.payer_id]["total_paid"] += payment.amount
        for participant in payment.participants:
            member_stats[participant.user_id]["participated_count"] += 1
    # 各メンバーの1回あたりの支払額を計算
    for member_id, stats in member_stats.items():
        if stats["participated_count"] > 0:
            stats["paid_per_participation"] = stats["total_paid"] / stats["participated_count"]
        else:
            stats["paid_per_participation"] = 0
    # 平均支払額を計算
    total_paid = sum(stats["total_paid"] for stats in member_stats.values())
    total_participated_count = sum(stats["participated_count"] for stats in member_stats.values())
    average_paid = total_paid / total_participated_count if total_participated_count > 0 else 0
    # 各メンバーの精算金額を計算
    for member_id, stats in member_stats.items():
        settlement_amount = (stats["paid_per_participation"] - average_paid) * stats["participated_count"]
        if rounding_method == "ceil":
            stats["settlement_amount"] = math.ceil(settlement_amount)
        elif rounding_method == "floor":
            stats["settlement_amount"] = math.floor(settlement_amount)
        else:  # rounding_method == "round"
            stats["settlement_amount"] = round(settlement_amount)
    # 誰が誰にいくら支払うかを計算
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

#精算結果を表示するためのルート
@app.route('/settlement/<int:group_id>', methods=['GET', 'POST'])
def settlement(group_id):
    if request.method == 'POST':
        rounding_method = request.form.get('rounding_method', 'round')  # 端数処理方法を取得 (デフォルトは四捨五入)
    else:
        rounding_method = 'round'  # デフォルトは四捨五入

    settlement_pairs = calculate_settlement(group_id, rounding_method)
    return render_template('settlement.html', settlement_pairs=settlement_pairs)

if __name__ == '__main__':
    app.run(debug=True)