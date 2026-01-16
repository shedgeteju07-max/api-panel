from flask import Flask, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)

def db():
    return sqlite3.connect("data.db")

@app.route("/")
def home():
    return "API Panel Calisiyor"

@app.route("/check")
def check():
    key = request.args.get("key")
    if not key:
        return jsonify({"status": "error", "msg": "key yok"})

    con = db()
    cur = con.cursor()
    cur.execute("SELECT expire FROM api_keys WHERE key=?", (key,))
    row = cur.fetchone()
    con.close()

    if not row:
        return jsonify({"status": "invalid"})

    expire = datetime.datetime.fromisoformat(row[0])
    if expire < datetime.datetime.now():
        return jsonify({"status": "expired"})

    return jsonify({"status": "active", "expire": row[0]})

@app.route("/create", methods=["POST"])
def create():
    name = request.json.get("name", "")
    hours = int(request.json.get("hours", 1))

    key = name + "_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    expire = datetime.datetime.now() + datetime.timedelta(hours=hours)

    con = db()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS api_keys (key TEXT, expire TEXT)")
    cur.execute("INSERT INTO api_keys VALUES (?,?)", (key, expire.isoformat()))
    con.commit()
    con.close()

    return jsonify({"key": key, "expire": expire.isoformat()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
