import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_NAME = "fraud_history.db"

# تهيئة قاعدة البيانات لحفظ سجل التحليلات
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                risk TEXT NOT NULL,
                probability INTEGER NOT NULL
            )
        """)

init_db()

# دالة تحليل الاحتيال المالي (نموذج تقييم المخاطر للسوق الجزائري)
def evaluate_transaction(amount, hour, distance, international):
    score = 5
    factors = []

    # 1. تحليل قيمة المبلغ بالدينار الجزائري (دج)
    if amount >= 200000:
        score += 35
        factors.append("مبلغ المعاملة مرتفع جداً (أكثر من 200,000 دج) مقارنة بالمعدل المعتاد.")
    elif amount >= 80000:
        score += 20
        factors.append("مبلغ المعاملة متوسط إلى مرتفع (بين 80,000 و 200,000 دج).")
    else:
        factors.append("قيمة المبلغ ضمن النطاق الطبيعي للمعاملات اليومية.")

    # 2. تحليل توقيت المعاملة
    if 0 <= hour <= 5:
        score += 25
        factors.append(f"توقيت المعاملة مشبوه (الساعة {hour}:00 فجراً - خارج أوقات النشاط المعتادة).")
    elif hour >= 23:
        score += 15
        factors.append("المعاملة تمت في وقت متأخر من الليل.")

    # 3. تحليل المسافة الجغرافية (كم)
    if distance > 300:
        score += 25
        factors.append(f"موقع جغرافي بعيد جداً ({distance} كم) عن موقع آخر استخدام للبطاقة/الحساب.")
    elif distance > 80:
        score += 12
        factors.append(f"تغير ملحوظ في الموقع الجغرافي ({distance} كم).")

    # 4. تحليل المعاملات الدولية
    if international:
        score += 20
        factors.append("معاملة دولية أو عبر بوابة دفع أجنبية تتطلب تحققاً إضافياً.")

    probability = min(max(score, 1), 99)

    if probability >= 65:
        risk = "مرتفع"
    elif probability >= 35:
        risk = "متوسط"
    else:
        risk = "منخفض"

    return {
        "probability": probability,
        "risk": risk,
        "factors": factors,
        "disclaimer": "تنبيه: هذا التقييم استرشادي مبني على خوارزمية تحليل المخاطر ولا يغني عن التحقق الأمني المباشر من البنك أو بريد الجزائر."
    }

# واجهة المستخدم الكاملة (HTML + CSS + JS)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fraud-Detector-DZ | كاشف الاحتيال المالي</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 750px; margin: auto; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h2 { margin-top: 0; color: #38bdf8; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
        label { display: block; margin-bottom: 6px; font-size: 14px; color: #cbd5e1; }
        input, select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }
        button { background: #0284c7; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; margin-top: 15px; font-size: 16px; }
        button:hover { background: #0369a1; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-small { width: auto; padding: 6px 14px; font-size: 13px; margin-top: 0; background: #334155; }
        .progress-bg { background: #334155; height: 12px; border-radius: 6px; overflow: hidden; margin: 12px 0; }
        .progress-bar { height: 100%; background: linear-gradient(90deg, #22c55e, #eab308, #ef4444); width: 0%; transition: width 0.4s ease; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th, td { padding: 10px; text-align: right; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; }
        .note { font-size: 12px; color: #94a3b8; margin-top: 12px; background: #0f172a; padding: 10px; border-radius: 6px; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h1>🛡️ Fraud-Detector-DZ</h1>
        <p style="color:#94a3b8;">نظام ذكي لتحليل وكشف مخاطر الاحتيال في المعاملات المالية بالجزائر</p>
        <form id="form">
            <div class="grid">
                <div>
                    <label>مبلغ المعاملة (دج)</label>
                    <input type="number" id="amount" required min="1" placeholder="مثال: 45000">
                </div>
                <div>
                    <label>ساعة المعاملة (0 - 23)</label>
                    <input type="number" id="hour" required min="0" max="23" placeholder="مثال: 14">
                </div>
                <div>
                    <label>المسافة عن آخر موقع معتاد (كم)</label>
                    <input type="number" id="distance" required min="0" placeholder="مثال: 15">
                </div>
                <div>
                    <label>نوع المعاملة</label>
                    <select id="international">
                        <option value="false">محلية (الجزائر - CIB / Edahabia)</option>
                        <option value="true">دولية / خارج الوطن</option>
                    </select>
                </div>
            </div>
            <button type="submit" id="submit">تحليل المعاملة ←</button>
        </form>
    </div>

    <div class="card">
        <h2>نتيجة التحليل</h2>
        <div id="empty" style="color:#64748b; text-align:center; padding:15px;">أدخل بيانات المعاملة أعلاه واضغط على تحليل لعرض النتيجة.</div>
        <div id="result" hidden>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span id="risk" style="font-size:20px; font-weight:bold; color:#38bdf8;"></span>
                <span id="score" style="font-size:24px; font-weight:bold;"></span>
            </div>
            <div class="progress-bg"><div id="bar" class="progress-bar"></div></div>
            <ul id="factors" style="padding-right:20px; line-height:1.7;"></ul>
            <div id="note" class="note"></div>
        </div>
    </div>

    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h2 style="margin:0;">سجل التحليلات الأخيرة</h2>
            <button id="refresh" class="btn-small">تحديث ↻</button>
        </div>
        <table>
            <thead>
                <tr><th>التاريخ</th><th>المبلغ</th><th>مستوى الخطر</th><th>الاحتمالية</th></tr>
            </thead>
            <tbody id="history">
                <tr><td colspan="4">جارٍ التحميل...</td></tr>
            </tbody>
        </table>
    </div>
</div>

<script>
const form = document.getElementById('form'), labels = {low:'خطر منخفض', medium:'خطر متوسط', high:'خطر مرتفع'};

async function history() {
    try {
        let r = await fetch('/api/history'), rows = await r.json();
        document.getElementById('history').innerHTML = rows.length
            ? rows.map(x => `<tr><td>${x.date}</td><td>${Number(x.amount).toLocaleString('ar-DZ')} دج</td><td>${x.risk}</td><td>${x.probability}%</td></tr>`).join('')
            : '<tr><td colspan="4">لا توجد تحليلات بعد.</td></tr>';
    } catch (e) {}
}

form.addEventListener('submit', async e => {
    e.preventDefault();
    let b = document.getElementById('submit');
    b.disabled = true;
    b.textContent = 'جارٍ التحليل...';
    try {
        let r = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                amount: amount.value,
                hour: hour.value,
                distance: distance.value,
                international: international.value
            })
        });
        let d = await r.json();
        if (!r.ok) throw Error(d.error);
        document.getElementById('empty').hidden = true;
        document.getElementById('result').hidden = false;
        document.getElementById('score').textContent = d.probability + '%';
        document.getElementById('risk').textContent = d.risk + ' الخطورة';
        document.getElementById('bar').style.width = d.probability + '%';
        document.getElementById('factors').innerHTML = d.factors.map(x => '<li>' + x + '</li>').join('');
        document.getElementById('note').textContent = d.disclaimer;
        await history();
    } catch (e) {
        alert(e.message);
    } finally {
        b.disabled = false;
        b.textContent = 'تحليل المعاملة ←';
    }
});

document.getElementById('refresh').addEventListener('click', history);
history();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
        hour = int(data.get("hour", 0))
        distance = float(data.get("distance", 0))
        international = str(data.get("international", "false")).lower() == "true"

        if amount <= 0 or not (0 <= hour <= 23) or distance < 0:
            return jsonify({"error": "يرجى إدخال قيم صحيحة ومنطقية للمعاملة."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "بيانات الإدخال غير صالحة."}), 400

    result = evaluate_transaction(amount, hour, distance, international)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO history (date, amount, risk, probability) VALUES (?, ?, ?, ?)",
            (now_str, amount, result["risk"], result["probability"])
        )

    return jsonify(result)

@app.route("/api/history", methods=["GET"])
def get_history():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT date, amount, risk, probability FROM history ORDER BY id DESC LIMIT 15"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
const form=document.getElementById('form'), labels={low:'خطر منخفض',medium:'خطر متوسط',high:'خطر مرتفع'};
async function history(){try{let r=await fetch('/api/history'),rows=await r.json();document.getElementById('history').innerHTML=rows.length?rows.map(x=>`<tr><td>${x.date}</td><td>${Number(x.amount).toLocaleString('ar-DZ')} دج</td><td>${x.risk}</td><td>${x.probability}%</td></tr>`).join(''):'<tr><td colspan="4">لا توجد تحليلات بعد.</td></tr>'}catch(e){}}
form.addEventListener('submit',async e=>{e.preventDefault();let b=document.getElementById('submit');b.disabled=true;b.textContent='جارٍ التحليل...';try{let r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:amount.value,hour:hour.value,distance:distance.value,international:international.value})});let d=await r.json();if(!r.ok)throw Error(d.error);document.getElementById('empty').hidden=true;document.getElementById('result').hidden=false;document.getElementById('score').textContent=d.probability+'%';document.getElementById('risk').textContent=d.risk+' الخطورة';document.getElementById('bar').style.width=d.probability+'%';document.getElementById('factors').innerHTML=d.factors.map(x=>'<li>'+x+'</li>').join('');document.getElementById('note').textContent=d.disclaimer;await history()}catch(e){alert(e.message)}finally{b.disabled=false;b.textContent='تحليل المعاملة ←'}});
document.getElementById('refresh').addEventListener('click',history);history();
