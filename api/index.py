from __future__ import annotations
import base64,binascii,json,os,tempfile
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from flask import Flask,jsonify,render_template,request,session,redirect
from PIL import Image,UnidentifiedImageError
from werkzeug.security import generate_password_hash,check_password_hash
import psycopg
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation
import re,hashlib,secrets
from KODIGO import payloads,qr_engine
from KODIGO.qr_engine import QRStyle
ROOT=Path(__file__).resolve().parents[1]
app=Flask(__name__,template_folder=str(ROOT/"templates"),static_folder=None)
app.config["MAX_CONTENT_LENGTH"]=4*1024*1024
app.secret_key=os.environ.get("FLASK_SECRET_KEY")
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax",SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),PERMANENT_SESSION_LIFETIME=60*60*24*30)
_schema_ready=False
def db_connection():
 url=os.environ.get("DATABASE_URL")
 if not url: raise RuntimeError("Database is not configured.")
 return psycopg.connect(url,connect_timeout=8,row_factory=dict_row)
def ensure_schema():
 global _schema_ready
 if _schema_ready: return
 with db_connection() as conn:
  conn.execute("""CREATE TABLE IF NOT EXISTS kod_users (id BIGSERIAL PRIMARY KEY,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,email_verified BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
  conn.execute("ALTER TABLE kod_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE")
  conn.execute("""CREATE TABLE IF NOT EXISTS kod_email_verifications (id BIGSERIAL PRIMARY KEY,user_id BIGINT NOT NULL REFERENCES kod_users(id) ON DELETE CASCADE,token_hash TEXT NOT NULL UNIQUE,expires_at TIMESTAMPTZ NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
  conn.execute("CREATE INDEX IF NOT EXISTS kod_email_verifications_user_idx ON kod_email_verifications(user_id)")
  conn.execute("""CREATE TABLE IF NOT EXISTS kod_qr_codes (id BIGSERIAL PRIMARY KEY,user_id BIGINT NOT NULL REFERENCES kod_users(id) ON DELETE CASCADE,title TEXT NOT NULL,kind TEXT NOT NULL,image TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
  conn.execute("CREATE INDEX IF NOT EXISTS kod_qr_codes_user_created_idx ON kod_qr_codes(user_id,created_at DESC)")
 _schema_ready=True

def send_verification_email(email,token):
 api_key=os.environ.get("RESEND_API_KEY"); sender=os.environ.get("EMAIL_FROM")
 if not api_key or not sender: raise RuntimeError("Email delivery is not configured.")
 base=os.environ.get("APP_BASE_URL",request.url_root.rstrip("/")).rstrip("/")
 link=base+"/api/verify?token="+token
 body={"from":sender,"to":[email],"subject":"Verify your KODIGO account","html":f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:32px;color:#17182b"><h1 style="margin-bottom:8px">Welcome to KODIGO</h1><p>Confirm your email address to activate your account.</p><p style="margin:28px 0"><a href="{link}" style="background:#5146d8;color:#fff;padding:14px 22px;border-radius:10px;text-decoration:none;font-weight:bold">Verify email address</a></p><p>This link expires in 30 minutes. If you did not create a KODIGO account, you can ignore this email.</p><p style="color:#777;font-size:12px">KODIGO · Create. Customize. Connect.</p></div>"""}
 req=Request("https://api.resend.com/emails",data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},method="POST")
 with urlopen(req,timeout=15) as response: response.read()
def create_verification(user_id,email):
 token=secrets.token_urlsafe(32); digest=hashlib.sha256(token.encode()).hexdigest()
 with db_connection() as conn:
  conn.execute("DELETE FROM kod_email_verifications WHERE user_id=%s",(user_id,))
  conn.execute("INSERT INTO kod_email_verifications(user_id,token_hash,expires_at) VALUES(%s,%s,NOW()+INTERVAL '30 minutes')",(user_id,digest))
 send_verification_email(email,token)

def current_user():
 ensure_schema()
 uid=session.get("user_id")
 if not uid: return None
 with db_connection() as conn:
  user=conn.execute("SELECT id,email,email_verified FROM kod_users WHERE id=%s",(uid,)).fetchone()
 if user and not user["email_verified"]:
  session.clear(); return None
 return user
@app.after_request
def security_headers(response):
 response.headers.setdefault("X-Content-Type-Options","nosniff")
 response.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
 response.headers.setdefault("X-Frame-Options","DENY")
 return response
KINDS={"url","text","contact","wifi"}
@app.get("/api/account")
def account():
 try:
  user=current_user()
  return jsonify(user={"id":user["id"],"email":user["email"]} if user else None)
 except Exception:
  app.logger.exception("Account lookup failed"); return jsonify(error="Account service is temporarily unavailable."),503

@app.post("/api/signup")
def signup():
 if not app.secret_key: return jsonify(error="Session security is not configured."),503
 data=request.get_json(silent=True) or {}; email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
 if not re.fullmatch(r"[^\\s@]+@[^\\s@]+\\.[^\\s@]+",email) or len(email)>254: return jsonify(error="Enter a valid email address."),400
 if len(password)<10 or len(password)>128: return jsonify(error="Use a password between 10 and 128 characters."),400
 try:
  ensure_schema()
  with db_connection() as conn:
   row=conn.execute("INSERT INTO kod_users(email,password_hash) VALUES(%s,%s) RETURNING id,email",(email,generate_password_hash(password))).fetchone()
  sent=True
  try: create_verification(row["id"],row["email"])
  except Exception:
   sent=False; app.logger.exception("Verification email could not be sent")
  return jsonify(verificationRequired=True,emailSent=sent,email=row["email"],message="Check your inbox for a verification link." if sent else "Your account was created, but email delivery is not configured yet."),201
 except UniqueViolation: return jsonify(error="An account with that email already exists. Please log in or request a new verification email."),409
 except Exception:
  app.logger.exception("Signup failed"); return jsonify(error="Couldn't create your account. Please try again."),503

@app.post("/api/resend-verification")
def resend_verification():
 data=request.get_json(silent=True) or {}; email=str(data.get("email","")).strip().lower()
 try:
  ensure_schema()
  with db_connection() as conn: user=conn.execute("SELECT id,email,email_verified FROM kod_users WHERE email=%s",(email,)).fetchone()
  if user and not user["email_verified"]:
   create_verification(user["id"],user["email"])
  return jsonify(ok=True,message="If that account needs verification, a new email has been sent.")
 except Exception:
  app.logger.exception("Resending verification email failed")
  return jsonify(error="Couldn't send the verification email. Please try again later."),503

@app.get("/api/verify")
def verify_email():
 token=request.args.get("token","")
 if not token or len(token)>200: return redirect("/?verified=0")
 digest=hashlib.sha256(token.encode()).hexdigest()
 try:
  ensure_schema()
  with db_connection() as conn:
   row=conn.execute("SELECT user_id FROM kod_email_verifications WHERE token_hash=%s AND expires_at>NOW()",(digest,)).fetchone()
   if not row: return redirect("/?verified=0")
   conn.execute("UPDATE kod_users SET email_verified=TRUE WHERE id=%s",(row["user_id"],))
   conn.execute("DELETE FROM kod_email_verifications WHERE user_id=%s",(row["user_id"],))
  return redirect("/?verified=1")
 except Exception:
  app.logger.exception("Email verification failed"); return redirect("/?verified=0")

@app.post("/api/login")
def login():
 if not app.secret_key: return jsonify(error="Session security is not configured."),503
 data=request.get_json(silent=True) or {}; email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
 try:
  ensure_schema()
  with db_connection() as conn: row=conn.execute("SELECT id,email,password_hash,email_verified FROM kod_users WHERE email=%s",(email,)).fetchone()
  if not row or not check_password_hash(row["password_hash"],password): return jsonify(error="Email or password is incorrect."),401
  if not row["email_verified"]: return jsonify(error="Please verify your email first. Check your inbox or request a new verification email.",verificationRequired=True),403
  session.clear(); session["user_id"]=row["id"]; session.permanent=True
  return jsonify(user={"id":row["id"],"email":row["email"]})
 except Exception:
  app.logger.exception("Login failed"); return jsonify(error="Login is temporarily unavailable."),503

@app.post("/api/logout")
def logout():
 session.clear(); return jsonify(ok=True)

@app.route("/api/history",methods=["GET","POST","DELETE"])
def history_api():
 user=current_user()
 if not user: return jsonify(error="Log in to access your saved QR codes."),401
 try:
  ensure_schema()
  with db_connection() as conn:
   if request.method=="GET":
    rows=conn.execute("SELECT id,title,kind,image,created_at FROM kod_qr_codes WHERE user_id=%s ORDER BY created_at DESC LIMIT 100",(user["id"],)).fetchall()
    return jsonify(items=[{"id":str(x["id"]),"title":x["title"],"kind":x["kind"],"image":x["image"],"date":x["created_at"].isoformat()} for x in rows])
   if request.method=="POST":
    data=request.get_json(silent=True) or {}; title=str(data.get("title","QR code"))[:200]; kind=str(data.get("kind","url")); image=data.get("image","")
    if kind not in KINDS or not isinstance(image,str) or not image.startswith("data:image/png;base64,") or len(image)>2500000: return jsonify(error="Invalid QR history item."),400
    row=conn.execute("INSERT INTO kod_qr_codes(user_id,title,kind,image) VALUES(%s,%s,%s,%s) RETURNING id",(user["id"],title,kind,image)).fetchone()
    return jsonify(id=str(row["id"])),201
   item_id=request.args.get("id")
   if item_id: conn.execute("DELETE FROM kod_qr_codes WHERE id=%s AND user_id=%s",(item_id,user["id"]))
   else: conn.execute("DELETE FROM kod_qr_codes WHERE user_id=%s",(user["id"],))
   return jsonify(ok=True)
 except Exception:
  app.logger.exception("QR history operation failed"); return jsonify(error="Couldn't access saved QR history."),503

@app.get("/")
def home(): return render_template("index.html")
@app.get("/api/health")
def health(): return jsonify(ok=True,aiConfigured=bool(os.environ.get("GEMINI_API_KEY")))
@app.post("/api/generate")
def generate():
 data=request.get_json(silent=True) or {}; kind=str(data.get("kind","url")); fields=data.get("fields") if isinstance(data.get("fields"),dict) else {}
 if kind not in KINDS: return jsonify(error="Choose a supported QR type."),400
 payload=payloads.build(kind,fields)
 if not payload: return jsonify(error="Add content to create your QR code."),400
 temp_path=None
 try:
  raw=data.get("style") if isinstance(data.get("style"),dict) else {}; base=QRStyle()
  fg=str(raw.get("fg",base.fg)); bg=str(raw.get("bg",base.bg)); qr_engine.hex_to_rgb(fg); qr_engine.hex_to_rgb(bg)
  shape=raw.get("module_style",base.module_style); quality=raw.get("quality",base.quality)
  if shape not in qr_engine.MODULE_STYLES or quality not in qr_engine.QUALITY_BOX_SIZE: raise ValueError("Choose a valid QR style and quality.")
  style=QRStyle(fg=fg,bg=bg,module_style=shape,quality=quality,border=max(1,min(8,int(raw.get("border",4)))),logo_scale=max(.1,min(.3,float(raw.get("logo_scale",.22)))))
  logo=data.get("logo")
  if logo:
   if not isinstance(logo,str) or "," not in logo: raise ValueError("The logo image could not be read.")
   raw_logo=base64.b64decode(logo.split(",",1)[1],validate=True)
   if len(raw_logo)>2*1024*1024: raise ValueError("Logo images must be 2 MB or smaller.")
   try:
    with Image.open(BytesIO(raw_logo)) as im: im.verify()
   except (UnidentifiedImageError,OSError): raise ValueError("Choose a valid PNG, JPG, or WebP image.")
   handle=tempfile.NamedTemporaryFile(delete=False,suffix=".png"); handle.write(raw_logo); handle.close(); temp_path=handle.name; style.logo_path=temp_path
  result=qr_engine.render(payload,style,preview_px=None if data.get('export') else 640); output=BytesIO(); result.image.save(output,format="PNG",dpi=(300,300),optimize=True)
  return jsonify(image="data:image/png;base64,"+base64.b64encode(output.getvalue()).decode("ascii"),title=payloads.title_for(kind,fields),modules=result.modules,errorCorrection=result.ec_label,contrast=round(qr_engine.contrast_ratio(style.fg,style.bg),2),warnings=result.warnings)
 except qr_engine.QRDataTooLarge as exc: return jsonify(error=str(exc)),422
 except (ValueError,TypeError,binascii.Error) as exc: return jsonify(error=str(exc)),400
 except Exception:
  app.logger.exception("QR generation failed"); return jsonify(error="KODIGO couldn't generate this QR code. Check your settings and try again."),500
 finally:
  if temp_path:
   try: os.unlink(temp_path)
   except OSError: pass
@app.post("/api/assistant")
def assistant():
 key=os.environ.get("GEMINI_API_KEY")
 if not key: return jsonify(error="AI is not configured. Add GEMINI_API_KEY in Vercel Project Settings."),503
 data=request.get_json(silent=True) or {}; message=str(data.get("message","")).strip()
 if not message: return jsonify(error="Type a message first."),400
 if len(message)>1500: return jsonify(error="Keep messages under 1,500 characters."),400
 history=data.get("history",[]); contents=[]
 if isinstance(history,list):
  for item in history[-8:]:
   if isinstance(item,dict):
    text=str(item.get("text","")).strip()[:1500]; role="model" if item.get("role")=="assistant" else "user"
    if text: contents.append({"role":role,"parts":[{"text":text}]})
 contents.append({"role":"user","parts":[{"text":message}]})
 body={"systemInstruction":{"parts":[{"text":"You are KODIGO AI, a concise and friendly QR Code Studio assistant. Help with links, text, vCard contacts, Wi-Fi QR codes, color contrast, square/rounded/dot modules, center logos, quiet zones and PNG export. Give practical steps. Wi-Fi QR codes contain network credentials; warn users to share carefully. Do not ask for passwords or private credentials. Do not claim to see a QR image unless provided."}]},"contents":contents,"generationConfig":{"temperature":.55,"maxOutputTokens":500}}
 req=Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",data=json.dumps(body).encode(),headers={"Content-Type":"application/json","x-goog-api-key":key},method="POST")
 try:
  with urlopen(req,timeout=25) as response: result=json.loads(response.read().decode())
  answer="".join(p.get("text","") for p in result.get("candidates",[{}])[0].get("content",{}).get("parts",[]) if isinstance(p,dict)).strip()
  return (jsonify(reply=answer),200) if answer else (jsonify(error="The assistant returned an empty reply. Try again."),502)
 except HTTPError as exc:
  if exc.code==429: return jsonify(error="The free AI limit is temporarily reached. Try again later."),429
  app.logger.warning("Gemini request failed: HTTP %s",exc.code)
  return jsonify(error="The AI service rejected the request. Check the API key and try again."),502
 except (URLError,TimeoutError,json.JSONDecodeError):
  return jsonify(error="Couldn't reach the AI service. Check your connection and try again."),502
@app.errorhandler(413)
def too_large(_): return jsonify(error="Request too large. Use a logo smaller than 2 MB."),413
if __name__=="__main__": app.run(debug=True)
