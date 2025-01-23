from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # フォームから入力値を取得
        num_people = int(request.form["num_people"])
        individual_payments = [
            int(x) for x in request.form["individual_payments"].split(",")
        ]
        rounding_method = request.form["rounding_method"]  # 端数処理方法を取得

        # 合計金額を計算
        total_amount = sum(individual_payments)

        # 1人あたりの金額を計算
        amount_per_person = total_amount / num_people

        # 端数処理
        if rounding_method == "ceil":
            amount_per_person = math.ceil(amount_per_person)  # 切り上げ
        elif rounding_method == "floor":
            amount_per_person = math.floor(amount_per_person)  # 切り捨て
        elif rounding_method == "round":
            amount_per_person = round(amount_per_person)  # 四捨五入

        # 結果を辞書に格納
        result = {
            "num_people": num_people,
            "individual_payments": individual_payments,
            "total_amount": total_amount,
            "amount_per_person": amount_per_person,
        }
        return render_template("result.html", result=result)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)