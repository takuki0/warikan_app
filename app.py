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

        # 合計金額を計算
        total_amount = sum(individual_payments)

        # 1人あたりの金額を計算
        amount_per_person = total_amount / num_people

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