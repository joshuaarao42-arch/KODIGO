from __future__ import annotations
import base64,binascii,hashlib,json,os,tempfile,time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from flask import Flask,jsonify,render_template,request,session
from PIL import Image,UnidentifiedImageError
from werkzeug.security import generate_password_hash,check_password_hash
import psycopg
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation
import re
from KODIGO import payloads,qr_engine
from KODIGO.qr_engine import QRStyle
ROOT=Path(__file__).resolve().parents[1]
app=Flask(__name__,template_folder=str(ROOT/"templates"),static_folder=None)
app.config["MAX_CONTENT_LENGTH"]=4*1024*1024
app.secret_key=os.environ.get("FLASK_SECRET_KEY")
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax",SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),PERMANENT_SESSION_LIFETIME=60*60*24*30)
_schema_ready=False
Image.MAX_IMAGE_PIXELS=16_000_000
def db_connection():
 url=os.environ.get("DATABASE_URL")
 if not url: raise RuntimeError("Database is not configured.")
 return psycopg.connect(url,connect_timeout=8,row_factory=dict_row)
def ensure_schema():
 global _schema_ready
 if _schema_ready: return
 with db_connection() as conn:
  conn.execute("""CREATE TABLE IF NOT EXISTS kod_users (id BIGSERIAL PRIMARY KEY,email TEXT UNIQUE,password_hash TEXT NOT NULL,username TEXT UNIQUE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
  conn.execute("ALTER TABLE kod_users ADD COLUMN IF NOT EXISTS username TEXT")
  conn.execute("ALTER TABLE kod_users ALTER COLUMN email DROP NOT NULL")
  conn.execute("UPDATE kod_users SET username = LOWER(REGEXP_REPLACE(SPLIT_PART(email, '@', 1), '[^a-zA-Z0-9_]', '', 'g')) || id::text WHERE username IS NULL AND email IS NOT NULL")
  conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS kod_users_username_unique_idx ON kod_users(username)")
  conn.execute("ALTER TABLE kod_users ALTER COLUMN username SET NOT NULL")
  conn.execute("""CREATE TABLE IF NOT EXISTS kod_qr_codes (id BIGSERIAL PRIMARY KEY,user_id BIGINT NOT NULL REFERENCES kod_users(id) ON DELETE CASCADE,title TEXT NOT NULL,kind TEXT NOT NULL,image TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
  conn.execute("CREATE INDEX IF NOT EXISTS kod_qr_codes_user_created_idx ON kod_qr_codes(user_id,created_at DESC)")
  conn.execute("""CREATE TABLE IF NOT EXISTS kod_rate_limits (bucket TEXT NOT NULL,window_start BIGINT NOT NULL,hits INTEGER NOT NULL,PRIMARY KEY(bucket,window_start))""")
 _schema_ready=True

def client_ip():
 forwarded=request.headers.get("x-vercel-forwarded-for") or request.headers.get("x-forwarded-for","")
 return (forwarded.split(",")[-1].strip() if forwarded else request.remote_addr or "unknown")[:64]

def rate_limit(scope,limit,window_seconds,subject=""):
 ensure_schema()
 now=int(time.time()); window_start=(now//window_seconds)*window_seconds
 identity=hashlib.sha256(f"{scope}:{client_ip()}:{subject}".encode()).hexdigest()
 with db_connection() as conn:
  row=conn.execute("""INSERT INTO kod_rate_limits(bucket,window_start,hits) VALUES(%s,%s,1)
   ON CONFLICT(bucket,window_start) DO UPDATE SET hits=kod_rate_limits.hits+1 RETURNING hits""",(identity,window_start)).fetchone()
  if now%3600<5: conn.execute("DELETE FROM kod_rate_limits WHERE window_start < %s",(now-172800,))
 return row["hits"]<=limit

def csrf_guard():
 if request.method not in ("POST","PUT","PATCH","DELETE") or not request.path.startswith("/api/"): return None
 if request.headers.get("X-KODIGO-Request")!="1": return jsonify(error="Request could not be verified. Refresh the page and try again."),403
 origin=request.headers.get("Origin")
 if origin:
  parsed=urlsplit(origin)
  if parsed.netloc.lower()!=request.host.lower() or parsed.scheme not in ("http","https"):
   return jsonify(error="Cross-site request blocked."),403
 if request.headers.get("Sec-Fetch-Site")=="cross-site": return jsonify(error="Cross-site request blocked."),403
 return None

app.before_request(csrf_guard)

def current_user():
 ensure_schema()
 uid=session.get("user_id")
 if not uid: return None
 with db_connection() as conn:
  user=conn.execute("SELECT id,username FROM kod_users WHERE id=%s",(uid,)).fetchone()
 return user
@app.after_request
def security_headers(response):
 response.headers.setdefault("X-Content-Type-Options","nosniff")
 response.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
 response.headers.setdefault("X-Frame-Options","DENY")
 response.headers.setdefault("Content-Security-Policy","default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'")
 response.headers.setdefault("Permissions-Policy","camera=(), microphone=(), geolocation=()")
 response.headers.setdefault("Cross-Origin-Opener-Policy","same-origin")
 if request.is_secure or request.headers.get("x-forwarded-proto")=="https":
  response.headers.setdefault("Strict-Transport-Security","max-age=31536000; includeSubDomains")
 if request.path.startswith("/api/"): response.headers.setdefault("Cache-Control","no-store")
 return response
KINDS={"url","text","contact","wifi"}
@app.get("/api/account")
def account():
 try:
  user=current_user()
  return jsonify(user={"id":user["id"],"username":user["username"]} if user else None)
 except Exception:
  app.logger.exception("Account lookup failed"); return jsonify(error="Account service is temporarily unavailable."),503

@app.post("/api/signup")
def signup():
 if not app.secret_key: return jsonify(error="Session security is not configured."),503
 data=request.get_json(silent=True) or {}; username=str(data.get("username","")).strip().lower(); password=str(data.get("password",""))
 try:
  if not rate_limit("signup",5,3600): return jsonify(error="Too many signup attempts. Please try again later."),429
 except Exception:
  app.logger.exception("Signup rate limit unavailable"); return jsonify(error="Account service is temporarily unavailable."),503
 if not re.fullmatch(r"[a-z0-9_]{3,24}",username): return jsonify(error="Username must be 3–24 characters using letters, numbers, or underscores."),400
 if len(password)<10 or len(password)>128: return jsonify(error="Use a password between 10 and 128 characters."),400
 try:
  ensure_schema()
  with db_connection() as conn:
   row=conn.execute("INSERT INTO kod_users(username,email,password_hash) VALUES(%s,NULL,%s) RETURNING id,username",(username,generate_password_hash(password))).fetchone()
  session.clear(); session["user_id"]=row["id"]; session.permanent=True
  return jsonify(user={"id":row["id"],"username":row["username"]}),201
 except UniqueViolation: return jsonify(error="That username is already taken. Choose another one."),409
 except Exception:
  app.logger.exception("Signup failed"); return jsonify(error="Could not create your account. Please try again."),503

@app.post("/api/login")
def login():
 if not app.secret_key: return jsonify(error="Session security is not configured."),503
 data=request.get_json(silent=True) or {}; username=str(data.get("username","")).strip().lower(); password=str(data.get("password",""))
 try:
  if not rate_limit("login_ip",30,900): return jsonify(error="Too many login attempts. Please wait and try again."),429
  if not rate_limit("login_user",10,900,username): return jsonify(error="Too many login attempts for this username. Please wait and try again."),429
  ensure_schema()
  with db_connection() as conn: row=conn.execute("SELECT id,username,password_hash FROM kod_users WHERE username=%s",(username,)).fetchone()
  if not row or not check_password_hash(row["password_hash"],password): return jsonify(error="Username or password is incorrect."),401
  session.clear(); session["user_id"]=row["id"]; session.permanent=True
  return jsonify(user={"id":row["id"],"username":row["username"]})
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
    if not rate_limit("history_save",120,3600,str(user["id"])): return jsonify(error="Too many save requests. Try again later."),429
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
 try:
  if not rate_limit("qr_generate",90,60): return jsonify(error="You're creating QR codes too quickly. Please wait a moment."),429
 except Exception:
  app.logger.exception("QR rate limit unavailable"); return jsonify(error="QR service is temporarily unavailable."),503
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
   if not isinstance(logo,str) or not logo.startswith("data:image/") or "," not in logo or len(logo)>2_900_000: raise ValueError("The logo image could not be read.")
   raw_logo=base64.b64decode(logo.split(",",1)[1],validate=True)
   if len(raw_logo)>2*1024*1024: raise ValueError("Logo images must be 2 MB or smaller.")
   try:
    with Image.open(BytesIO(raw_logo)) as im:
     if im.format not in ("PNG","JPEG","WEBP"): raise ValueError("Choose a PNG, JPG, or WebP image.")
     if im.width>4096 or im.height>4096 or im.width*im.height>12_000_000: raise ValueError("Logo dimensions must be no larger than 4096 × 4096 pixels or 12 megapixels.")
     im.load()
     clean_logo=im.convert("RGBA")
     handle=tempfile.NamedTemporaryFile(delete=False,suffix=".png"); temp_path=handle.name; handle.close()
     clean_logo.save(temp_path,format="PNG",optimize=True)
   except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning): raise ValueError("Choose a valid, safely sized PNG, JPG, or WebP image.")
   style.logo_path=temp_path
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
 try:
  if not rate_limit("ai_assistant",30,3600): return jsonify(error="KODIGO AI has reached its request limit for now. Please try again later."),429
 except Exception:
  app.logger.exception("AI rate limit unavailable"); return jsonify(error="AI service is temporarily unavailable."),503
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
