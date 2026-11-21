
import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_PATH = "fraud_dz.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            hour INTEGER,
            wilaya TEXT,
            device TEXT,
            tx_type TEXT,
            risk_score INTEGER,
            risk_level TEXT,
            reasons TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def evaluate_fraud(amount, hour, wilaya, device, tx_type):
    score = 0
    reasons = []

    if amount >= 500000:
        score += 45
        reasons.append("مبلغ ضخم جداً يتجاوز 500,000 دج")
    elif amount >= 150000:
        score += 25
        reasons.append("مبلغ مرتفع يتجاوز 150,000 دج")

    if 0 <= hour <= 5:
        score += 25
        reasons.append("توقيت مريب في ساعات الفجر المتأخرة")

    if device == "new_device":
        score += 20
        reasons.append("استخدام جهاز جديد غير مسجل مسبقاً")

    if tx_type == "baridimob_transfer" and amount >= 100000:
        score += 15
        reasons.append("تحويل بريدي موب بمبلغ كبير")

    if wilaya in ["خارج الوطن / VPN", "غير محدد"]:
        score += 35
        reasons.append("موقع جغرافي غير معتاد أو استخدام VPN")

    score = min(score, 100)
    if score >= 65:
        level = "high"
    elif score >= 35:
        level = "medium"
    else:
        level = "low"

    return score, level, reasons

HTML_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fraud-Detector-DZ | كاشف الاحتيال المالي</title>
<style>
body{font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;margin:0;padding:16px}
.container{max-width:600px;margin:auto}
.card{background:#1e293b;padding:20px;border-radius:12px;margin-bottom:16px;box-shadow:0 4px 12px rgba(0,0,0,.3)}
h1{font-size:1.4rem;color:#38bdf8;margin-top:0}
label{display:block;margin:10px 0 4px;font-size:.9rem;color:#cbd5e1}
input,select,button{width:100%;padding:12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#fff;font-size:1rem;box-sizing:border-box}
button{background:#0284c7;border:none;font-weight:bold;margin-top:16px;cursor:pointer}
button:hover{background:#0369a1}
.res{padding:14px;border-radius:8px;margin-top:14px;display:none}
.low{background:#064e3b;border:1px solid #10b981}
.medium{background:#78350f;border:1px solid #f59e0b}
.high{background:#7f1d1d;border:1px solid #ef4444}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:10px}
td,th{padding:8px;border-bottom:1px solid #334155;text-align:right}
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <h1>🛡️ Fraud-Detector-DZ</h1>
    <p style="color:#94a3b8;font-size:.9rem">نظام تحليل مخاطر المعاملات المالية في الجزائر (دج)</p>
    <form id="txForm">
      <label>المبلغ (بالدينار الجزائري DZD)</label>
      <input type="number" id="amount" value="25000" required>
      <label>ساعة تنفيذ العملية (0 - 23)</label>
      <input type="number" id="hour" min="0" max="23" value="14" required>
      <label>الولاية / الموقع</label>
      <select id="wilaya">
        <option value="الجزائر العاصمة">الجزائر العاصمة</option>
        <option value="وهران">وهران</option>
        <option value="قسنطينة">قسنطينة</option>
        <option value="سطيف">سطيف</option>
        <option value="بسكرة">بسكرة</option>
        <option value="خارج الوطن / VPN">خارج الوطن / VPN</option>
      </select>
      <label>حالة الجهاز</label>
      <select id="device">
        <option value="known_device">جهاز معروف وموثوق</option>
        <option value="new_device">جهاز جديد غير مسجل</option>
      </select>
      <label>نوع المعاملة</label>
      <select id="tx_type">
        <option value="cib_payment">دفع إلكتروني CIB / الذهبية</option>
        <option value="baridimob_transfer">تحويل BaridiMob</option>
        <option value="atm_withdrawal">سحب نقدي ATM</option>
      </select>
      <button type="submit">فحص المعاملة الآن</button>
    </form>
    <div id="result" class="res"></div>
  </div>
  <div class="card">
    <h2 style="font-size:1.1rem;margin-top:0">📋 آخر العمليات المفحوصة</h2>
    <table>
      <thead><tr><th>المبلغ</th><th>المستوى</th><th>الدرجة</th></tr></thead>
      <tbody id="history"></tbody>
    </table>
  </div>
</div>
<script>
const labels = {low: "خطر منخفض", medium: "خطر متوسط", high: "خطر مرتفع"};
async function loadHistory(){
  const r = await fetch("/api/history");
  const rows = await r.json();
  document.getElementById("history").innerHTML = rows.map(x =>
    `<tr><td>${x.amount} دج</td><td>${labels[x.risk_level]}</td><td>${x.risk_score}%</td></tr>`
  ).join("");
}
document.getElementById("txForm").onsubmit = async (e) => {
  e.preventDefault();
  const payload = {
    amount: parseFloat(document.getElementById("amount").value),
    hour: parseInt(document.getElementById("hour").value),
    wilaya: document.getElementById("wilaya").value,
    device: document.getElementById("device").value,
    tx_type: document.getElementById("tx_type").value
  };
  const r = await fetch("/api/analyze", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const data = await r.json();
  const box = document.getElementById("result");
  box.className = "res " + data.risk_level;
  box.style.display = "block";
  box.innerHTML = `<strong>النتيجة: ${labels[data.risk_level]} (${data.risk_score}%)</strong><br>` +
    (data.reasons.length ? data.reasons.join(" • ") : "المعاملة تبدو طبيعية وآمنة.");
  loadHistory();
};
loadHistory();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    amount = float(data.get("amount", 0))
    hour = int(data.get("hour", 12))
    wilaya = data.get("wilaya", "الجزائر العاصمة")
    device = data.get("device", "known_device")
    tx_type = data.get("tx_type", "cib_payment")

    score, level, reasons = evaluate_fraud(amount, hour, wilaya, device, tx_type)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (amount, hour, wilaya, device, tx_type, risk_score, risk_level, reasons, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (amount, hour, wilaya, device, tx_type, score, level, " | ".join(reasons), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return jsonify({"risk_score": score, "risk_level": level, "reasons": reasons})

@app.route("/api/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT amount, risk_level, risk_score FROM transactions ORDER BY id DESC LIMIT 10")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
