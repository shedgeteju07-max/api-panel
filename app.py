from flask import Flask, request, redirect, session
import sqlite3, secrets, time

app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"

ADMIN_PASSWORD = "123456"   # <-- PANEL ŞİFRESİ
DB = "keys.db"

# ---------- DB ----------
def db():
    return sqlite3.connect(DB)

def init():
    c = db().cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT,
        active INTEGER,
        expire INTEGER,
        name TEXT
    )
    """)
    c.connection.commit()

init()

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/")
        return "<h3>❌ Şifre yanlış</h3><a href='/login'>Geri</a>"

    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body{background:#020617;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh}
    .box{border:1px solid #1f2937;padding:30px;border-radius:20px;width:300px;text-align:center}
    input{width:100%;padding:12px;border-radius:10px;border:1px solid #1f2937;background:#020617;color:white}
    button{margin-top:15px;width:100%;padding:12px;border:none;border-radius:10px;background:#22c55e;font-weight:bold}
    </style></head>
    <body>
    <form method="post" class="box">
    <h2>🔐 Admin Giriş</h2>
    <input type="password" name="password" placeholder="Şifre">
    <button>Giriş</button>
    </form>
    </body></html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth():
    return session.get("admin")

# ---------- API CHECK ----------
def api_ok(req):
    k = req.headers.get("x-api-key")
    if not k:
        return False
    c = db().cursor()
    c.execute("SELECT active, expire FROM keys WHERE key=?", (k,))
    r = c.fetchone()
    return bool(r and r[0] == 1 and r[1] > int(time.time()))

@app.route("/tool")
def tool():
    if not api_ok(request):
        return {"error": "API geçersiz"}, 403
    return {"ok": True}

# ---------- PANEL ----------
@app.route("/")
def panel():
    if not auth():
        return redirect("/login")

    c = db().cursor()
    c.execute("SELECT id, name, active, expire FROM keys ORDER BY id DESC")
    data = c.fetchall()

    rows = ""
    for i in data:
        rows += f"""
<tr>
<td>{i[0]}</td>
<td>{i[1]}</td>
<td>{"🟢" if i[2] else "🔴"}</td>
<td>{time.strftime("%Y-%m-%d %H:%M", time.localtime(i[3]))}</td>
<td>
<a href="/toggle/{i[0]}" class="btn yellow">Aç / Kapat</a>
<form action="/time/{i[0]}" method="post" class="inline">
<input name="h" placeholder="+/- Saat">
<input name="d" placeholder="+/- Gün">
<button class="btn green">Güncelle</button>
</form>
<a href="/delete/{i[0]}" class="btn red">Sil</a>
</td>
</tr>
"""

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Panel</title>
<style>
body{{background:#020617;color:white;font-family:Arial}}
.box{{max-width:1100px;margin:30px auto;padding:20px;border:1px solid #1f2937;border-radius:18px}}
h2{{text-align:center}}
table{{width:100%;border-spacing:0 12px}}
td,th{{border:1px solid #1f2937;padding:12px;text-align:center}}
.btn{{padding:10px;border-radius:10px;text-decoration:none;display:inline-block;margin:4px 0;font-weight:bold}}
.yellow{{background:#f59e0b;color:black}}
.green{{background:#22c55e;color:black}}
.red{{background:#ef4444;color:white}}
.inline{{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}}
input{{background:#020617;border:1px solid #1f2937;color:white;padding:8px;border-radius:8px;width:120px}}
@media(max-width:700px){{
table,thead,tbody,tr,td,th{{display:block}}
th{{display:none}}
.inline{{display:grid;grid-template-columns:1fr 1fr}}
.inline input{{grid-column:span 2}}
.inline button{{grid-column:span 2}}
}}
</style>
</head>
<body>
<div class="box">
<h2>🔐 API Yönetim Paneli</h2>
<a href="/logout" style="float:right;color:#ef4444">Çıkış</a>

<form action="/create" method="post" class="inline">
<input name="name" placeholder="API İsmi">
<input name="h" placeholder="Saat">
<input name="d" placeholder="Gün">
<button class="btn green">+ API</button>
</form>

<table>
<tr><th>ID</th><th>İsim</th><th>Durum</th><th>Bitiş</th><th>Kontrol</th></tr>
{rows}
</table>
</div>
</body>
</html>
"""

# ---------- ACTIONS ----------
@app.route("/create", methods=["POST"])
def create():
    if not auth(): return redirect("/login")
    name = request.form.get("name") or "İsimsiz"
    h = int(request.form.get("h") or 0)
    d = int(request.form.get("d") or 0)
    key = secrets.token_hex(16)
    exp = int(time.time()) + h*3600 + d*86400
    c = db().cursor()
    c.execute("INSERT INTO keys VALUES (NULL,?,?,?,?)",(key,1,exp,name))
    c.connection.commit()
    return f"<h3>API KEY</h3><p>{key}</p><a href='/'>Geri</a>"

@app.route("/toggle/<int:i>")
def toggle(i):
    if not auth(): return redirect("/login")
    c = db().cursor()
    c.execute("UPDATE keys SET active=1-active WHERE id=?", (i,))
    c.connection.commit()
    return redirect("/")

@app.route("/time/<int:i>", methods=["POST"])
def time_edit(i):
    if not auth(): return redirect("/login")
    h = int(request.form.get("h") or 0)
    d = int(request.form.get("d") or 0)
    c = db().cursor()
    c.execute("SELECT expire FROM keys WHERE id=?", (i,))
    old = c.fetchone()[0]
    c.execute("UPDATE keys SET expire=? WHERE id=?", (old+h*3600+d*86400,i))
    c.connection.commit()
    return redirect("/")

@app.route("/delete/<int:i>")
def delete(i):
    if not auth(): return redirect("/login")
    c = db().cursor()
    c.execute("DELETE FROM keys WHERE id=?", (i,))
    c.connection.commit()
    return redirect("/")

# ---------- RUN ----------
app.run("0.0.0.0", 8000)
