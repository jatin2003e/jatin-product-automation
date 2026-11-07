import os, sqlite3, secrets, functools
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_file, jsonify
from dotenv import load_dotenv
load_dotenv()
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH']=5*1024*1024
DATA=Path('instance');DATA.mkdir(exist_ok=True)
DB=DATA/'app.sqlite3'
APP_NAME='Product Automation'
@app.context_processor
def context():return dict(app_name=APP_NAME)
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init(sql):
 with conn() as c:c.executescript(sql)
def admin_required(fn):
 @functools.wraps(fn)
 def wrapped(*args,**kwargs):
  if not session.get('admin'):return redirect('/login')
  return fn(*args,**kwargs)
 return wrapped
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  if os.getenv('ADMIN_PASSWORD') and secrets.compare_digest(request.form.get('password',''),os.getenv('ADMIN_PASSWORD')):
   session.clear();session['admin']=True;return redirect('/dashboard')
  flash('Incorrect password')
 return render_template('login.html',title='Admin login')
@app.post('/logout')
def logout():session.clear();return redirect('/')

import hmac,hashlib,json,smtplib,ssl
from email.message import EmailMessage
init("""CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,event_type TEXT,email TEXT,product TEXT,download_url TEXT,status TEXT,attempts INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_error TEXT);""")
@app.get('/')
def home():return render_template('automation_home.html',title='Automation')
@app.post('/api/webhook')
def webhook():
 secret=os.getenv('WEBHOOK_SECRET')
 if not secret:abort(503)
 payload=request.get_data()
 signature=request.headers.get('X-Webhook-Signature','')
 expected=hmac.new(secret.encode(),payload,hashlib.sha256).hexdigest()
 if not hmac.compare_digest(signature,expected):abort(401)
 try:
  d=json.loads(payload);event_id=str(d['id'])[:120];email=str(d['email'])[:254];product=str(d['product'])[:200];url=str(d['download_url'])[:2000];event_type=str(d['type'])
  if event_type!='order.paid' or '@' not in email or not url.startswith('https://'):abort(400)
 except (KeyError,TypeError,ValueError):abort(400)
 with conn() as c:c.execute('INSERT OR IGNORE INTO events(id,event_type,email,product,download_url,status) VALUES(?,?,?,?,?,?)',(event_id,event_type,email,product,url,'pending'))
 return jsonify(accepted=True,id=event_id),202
@app.route('/dashboard',methods=['GET','POST'])
@admin_required
def dashboard():
 if request.method=='POST':
  eid=request.form.get('id','')
  with conn() as c:e=c.execute("SELECT * FROM events WHERE id=? AND status!='sent'",(eid,)).fetchone()
  if not e:abort(404)
  try:
   if not all(os.getenv(k) for k in ('SMTP_HOST','SMTP_FROM')):raise RuntimeError('SMTP not configured')
   msg=EmailMessage();msg['From']=os.getenv('SMTP_FROM');msg['To']=e['email'];msg['Subject']='Your digital product: '+e['product']
   msg.set_content(f'Thank you for your purchase!\n\nYour download: {e["download_url"]}\n')
   with smtplib.SMTP(os.getenv('SMTP_HOST'),int(os.getenv('SMTP_PORT','587')),timeout=15) as server:
    server.starttls(context=ssl.create_default_context())
    if os.getenv('SMTP_USER'):server.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD',''))
    server.send_message(msg)
   with conn() as c:c.execute("UPDATE events SET status='sent',attempts=attempts+1,last_error=NULL WHERE id=?",(eid,))
   flash('Email sent')
  except Exception as ex:
   with conn() as c:c.execute("UPDATE events SET status='failed',attempts=attempts+1,last_error=? WHERE id=?",(str(ex)[:200],eid))
   flash('Email failed. Check SMTP configuration.')
  return redirect('/dashboard')
 with conn() as c:events=c.execute('SELECT * FROM events ORDER BY created_at DESC LIMIT 100').fetchall()
 return render_template('automation_admin.html',title='Events',events=events)
if __name__=='__main__':app.run(port=int(os.getenv('PORT',5000)))
