from __future__ import annotations
import base64,binascii,json,os,tempfile
from io import BytesIO
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from flask import Flask,jsonify,render_template,request
from PIL import Image,UnidentifiedImageError
from KODIGO import payloads,qr_engine
from KODIGO.qr_engine import QRStyle
app=Flask(__name__,template_folder="templates",static_folder="static")
app.config["MAX_CONTENT_LENGTH"]=4*1024*1024
KINDS={"url","text","contact","wifi"}
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
  result=qr_engine.render(payload,style,preview_px=640); output=BytesIO(); result.image.save(output,format="PNG",dpi=(300,300),optimize=True)
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
