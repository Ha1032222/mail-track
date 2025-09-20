from flask import Flask, request, g, render_template_string, redirect, url_for, session
import sqlite3
from datetime import datetime
import os

# --- Configuration Production ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'votre_cle_secrete_tres_longue_ici_changez_moi_123456')

# --- Chemin base de données SQLite ---
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'reponses.db')

# --- Identifiants admin ---
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'ChangezMoi123!')  # 🔒 À CHANGER

# --- Connexion à la DB SQLite ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        try:
            db = g._database = sqlite3.connect(DATABASE_PATH)
            db.row_factory = sqlite3.Row
            print("✅ Connexion à SQLite réussie")
        except Exception as e:
            print(f"❌ Erreur de connexion à la base de données: {e}")
            raise
    return db

# --- Initialisation DB ---
def init_db():
    try:
        db = sqlite3.connect(DATABASE_PATH)
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate TEXT,
                status TEXT,
                email_id TEXT UNIQUE,
                source TEXT,
                ip TEXT,
                user_agent TEXT,
                date TEXT
            )
        """)
        db.commit()
        cursor.close()
        db.close()
        print("✅ Table 'responses' créée ou déjà existante")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")

# --- Fermeture de connexion ---
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Page d'accueil ---
@app.route("/")
def home():
    return """
    <h2 style='font-family:Arial; color:#2c3e50;'>Serveur de test - Tracker de candidatures</h2>
    <p>Endpoints :</p>
    <ul>
      <li><a href="/responses">/responses</a> — Voir toutes les réponses (protégé)</li>
      <li>/response?cand=Hassan&status=accepted&email_id=ABC123 — Simule un clic</li>
    </ul>
    """

# --- Page de login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("responses"))
        else:
            error = "Identifiants incorrects"

    return render_template_string("""
    <!doctype html>
    <html lang="fr">
    <head>
      <meta charset="utf-8">
      <title>Login</title>
      <style>
        body {font-family: Arial; background:#f0f2f5; display:flex; justify-content:center; align-items:center; height:100vh;}
        .card {background:#fff; padding:30px; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.1); width:300px;}
        h2 {margin-bottom:20px; color:#2c3e50; text-align:center;}
        input {width:100%; padding:10px; margin:8px 0; border:1px solid #ccc; border-radius:6px;}
        button {width:100%; padding:10px; background:#2196F3; color:#fff; border:none; border-radius:6px; font-weight:bold;}
        .error {color:red; font-size:14px; text-align:center; margin-top:10px;}
      </style>
    </head>
    <body>
      <div class="card">
        <h2>🔐 Connexion</h2>
        <form method="post">
          <input type="text" name="username" placeholder="Utilisateur" required>
          <input type="password" name="password" placeholder="Mot de passe" required>
          <button type="submit">Se connecter</button>
        </form>
        {% if error %}
          <p class="error">{{ error }}</p>
        {% endif %}
      </div>
    </body>
    </html>
    """, error=error)

# --- Déconnexion ---
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# --- Endpoint pour recevoir les clics ---
@app.route("/response")
def response():
    candidate = request.args.get("cand", "Inconnu")
    status = request.args.get("status", "no_status").lower()
    email_id = request.args.get("email_id", "unknown")
    source = request.args.get("src", "email")
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")

    try:
        db = get_db()
        cursor = db.cursor()

        # Supprimer ancienne réponse pour ce mail
        cursor.execute("DELETE FROM responses WHERE email_id = ?", (email_id,))
        db.commit()

        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        cursor.execute(
            "INSERT INTO responses (candidate, status, email_id, source, ip, user_agent, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (candidate, status, email_id, source, ip, ua, now)
        )
        db.commit()
        print(f"✅ Donnée enregistrée: {candidate} - {status}")

    except Exception as e:
        print(f"❌ Erreur lors de l'enregistrement: {e}")

    if status == "accepted":
        polite_message = f"✅ Merci beaucoup pour votre intérêt.<br>Je serai ravi d'échanger avec vous pour convenir d'un entretien sur le numéro 📞 <strong>0767855205</strong>."
    elif status == "rejected":
        polite_message = f"Merci pour votre retour que j'apprécie vraiment.<br>Je comprends votre décision et reste ouvert à de futures opportunités."
    else:
        polite_message = "ℹ️ Merci pour votre retour."

    return render_template_string("""
    <!doctype html>
    <html lang="fr">
      <head>
        <meta charset="utf-8">
        <title>Réponse enregistrée</title>
        <style>
          body {font-family: 'Segoe UI', Arial, sans-serif; background:#f0f2f5; text-align:center; padding:50px;}
          h2 {color:#2c3e50; font-size:26px;}
          p {color:#555; font-size:15px;}
          .card {
              margin:30px auto; padding:25px; background:#fff;
              border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.1);
              max-width:500px; text-align:center;
          }
          .status {font-weight:bold; color:#2196F3;}
          .message {
              margin-top:20px; padding:20px;
              background:#e3f2fd; border-left:5px solid #2196F3;
              border-radius:8px; font-size:15px; color:#333;
          }
        </style>
      </head>
      <body>
        <div class="card">
          <h2>Merci !</h2>
          <p>Votre réponse pour <strong>{{candidate}}</strong> a été enregistrée comme : 
             <span class="status">{{status}}</span>.</p>
          <div class="message">{{polite_message|safe}}</div>
        </div>
      </body>
    </html>
    """, candidate=candidate, status=status, polite_message=polite_message)

# --- Page pour afficher toutes les réponses (protégée par login) ---
@app.route("/responses")
def responses():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM responses ORDER BY id DESC")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des données: {e}")
        rows = []

    return render_template_string("""
    <!doctype html>
    <html lang="fr">
      <head>
        <meta charset="utf-8">
        <title>Réponses reçues</title>
        <style>
          body {font-family:'Segoe UI', Arial, sans-serif; background:#f0f2f5; margin:0; padding:20px;}
          h2 {color:#2c3e50; text-align:center; margin-bottom:30px; font-size:28px;}
          table {border-collapse:collapse; width:100%; max-width:1200px; margin:auto; background:#fff;
                 border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.1);}
          th, td {padding:12px 15px; text-align:left; font-size:14px;}
          thead th {background:#2196F3; color:#fff; position:sticky; top:0;}
          tbody tr:nth-child(even) {background:#f9f9f9;}
          tbody tr:hover {background:#e3f2fd;}
          td {max-width:200px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;}
          .topbar {text-align:center; margin-bottom:20px;}
          .logout {display:inline-block; padding:8px 16px; background:#e74c3c; color:#fff; border-radius:20px; text-decoration:none;}
        </style>
      </head>
      <body>
        <div class="topbar">
          <h2>📋 Réponses reçues</h2>
          <a href="{{ url_for('logout') }}" class="logout">🚪 Déconnexion</a>
        </div>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Candidat</th>
              <th>Status</th>
              <th>Email ID</th>
              <th>Source</th>
              <th>IP</th>
              <th>User-Agent</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {% for r in rows %}
              <tr>
                <td>{{r['id']}}</td>
                <td>{{r['candidate']}}</td>
                <td>{{r['status']}}</td>
                <td>{{r['email_id']}}</td>
                <td>{{r['source']}}</td>
                <td>{{r['ip']}}</td>
                <td>{{r['user_agent']}}</td>
                <td>{{r['date']}}</td>
              </tr>
            {% else %}
              <tr><td colspan="8" style="text-align:center; color:#888;">Aucune réponse reçue.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </body>
    </html>
    """, rows=rows)

# --- Lancement ---
if __name__ == "__main__":
    print("🚀 Démarrage de l'application...")
    print(f"📊 Base de données: {DATABASE_PATH}")
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)