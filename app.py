"""
Flask web interface for CV Parser pipeline.
Supports single upload and batch upload with live progress.
"""
import json
import os
import time
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread

from flask import (
    Flask, render_template_string, request, jsonify,
    send_file, session,
)

from main import parse_single_cv
from json_assembler import to_json_string

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".pdf", ".docx", ".doc"}

# In-memory store for batch job progress
_jobs: dict[str, dict] = {}


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXT


# ── HTML Template ─────────────────────────────────────────────────────────

HTML = r"""
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CV Parser</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;color:#1a1a2e;min-height:100vh}
.top-bar{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:20px 0;text-align:center;color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.2)}
.top-bar h1{font-size:24px;font-weight:600;letter-spacing:-.5px}
.top-bar p{font-size:13px;opacity:.7;margin-top:4px}
.container{max-width:960px;margin:30px auto;padding:0 20px}

/* Tabs */
.tabs{display:flex;gap:0;margin-bottom:0}
.tab{padding:12px 28px;background:#dfe6ed;border:none;cursor:pointer;font-size:14px;font-weight:500;color:#555;border-radius:10px 10px 0 0;transition:all .2s}
.tab:hover{background:#cdd5de}
.tab.active{background:#fff;color:#1a1a2e;font-weight:600;box-shadow:0 -2px 8px rgba(0,0,0,.06)}

/* Panels */
.panel{display:none;background:#fff;border-radius:0 10px 10px 10px;padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.panel.active{display:block}

/* Upload area */
.drop-zone{border:2px dashed #b0bec5;border-radius:12px;padding:48px 20px;text-align:center;cursor:pointer;transition:all .2s;background:#fafbfc}
.drop-zone:hover,.drop-zone.drag-over{border-color:#4361ee;background:#eef1ff}
.drop-zone svg{width:48px;height:48px;color:#90a4ae;margin-bottom:12px}
.drop-zone p{color:#78909c;font-size:14px}
.drop-zone .hint{font-size:12px;color:#b0bec5;margin-top:6px}
.file-input{display:none}

/* File list */
.file-list{margin-top:16px;max-height:220px;overflow-y:auto}
.file-item{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:#f8f9fa;border-radius:8px;margin-bottom:6px;font-size:13px}
.file-item .name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.file-item .size{color:#999;margin-left:12px;flex-shrink:0}
.file-item .remove{color:#e74c3c;cursor:pointer;margin-left:12px;font-weight:bold;flex-shrink:0}

/* Buttons */
.btn{display:inline-flex;align-items:center;gap:6px;padding:10px 24px;border:none;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;transition:all .15s}
.btn-primary{background:#4361ee;color:#fff}
.btn-primary:hover{background:#3a56d4}
.btn-primary:disabled{background:#a0aec0;cursor:not-allowed}
.btn-secondary{background:#e2e8f0;color:#475569}
.btn-secondary:hover{background:#cbd5e1}
.actions{margin-top:20px;display:flex;gap:10px;align-items:center}

/* Progress */
.progress-area{margin-top:20px}
.progress-bar-bg{height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden}
.progress-bar-fill{height:100%;background:linear-gradient(90deg,#4361ee,#7c3aed);border-radius:4px;transition:width .3s;width:0%}
.progress-text{font-size:13px;color:#64748b;margin-top:8px}

/* Results */
.results{margin-top:20px}
.result-card{border:1px solid #e2e8f0;border-radius:10px;margin-bottom:10px;overflow:hidden}
.result-header{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;cursor:pointer;transition:background .15s}
.result-header:hover{background:#f8fafc}
.result-header .status{width:8px;height:8px;border-radius:50%;margin-right:10px;flex-shrink:0}
.result-header .status.ok{background:#22c55e}
.result-header .status.err{background:#ef4444}
.result-header .fname{font-size:13px;font-weight:500;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.result-header .meta{font-size:12px;color:#94a3b8;margin-left:12px;flex-shrink:0}
.result-body{display:none;border-top:1px solid #e2e8f0}
.result-body.open{display:block}
.result-body pre{padding:16px;font-size:12px;background:#f8fafc;overflow-x:auto;max-height:400px;margin:0;white-space:pre-wrap;word-break:break-all}
.result-warnings{padding:10px 16px;background:#fef9e7;font-size:12px;color:#92400e}

/* Stats */
.stats-row{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap}
.stat-card{flex:1;min-width:120px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;text-align:center}
.stat-card .num{font-size:28px;font-weight:700;color:#1a1a2e}
.stat-card .label{font-size:11px;color:#94a3b8;text-transform:uppercase;margin-top:4px}
</style>
</head>
<body>

<div class="top-bar">
  <h1>CV Parser Pipeline</h1>
  <p>Upload PDF / DOCX &rarr; Structured JSON</p>
</div>

<div class="container">
  <div class="tabs">
    <button class="tab active" onclick="switchTab('single')">Single Upload</button>
    <button class="tab" onclick="switchTab('batch')">Batch Upload</button>
  </div>

  <!-- ───── Single ───── -->
  <div id="tab-single" class="panel active">
    <div class="drop-zone" id="dz-single" onclick="document.getElementById('file-single').click()">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16"/></svg>
      <p>Click or drag a CV file here</p>
      <div class="hint">PDF, DOCX</div>
    </div>
    <input type="file" id="file-single" class="file-input" accept=".pdf,.docx,.doc">
    <div class="file-list" id="fl-single"></div>
    <div class="actions">
      <button class="btn btn-primary" id="btn-parse" disabled onclick="parseSingle()">Parse CV</button>
      <span id="single-status" style="font-size:13px;color:#64748b"></span>
    </div>
    <div class="results" id="res-single"></div>
  </div>

  <!-- ───── Batch ───── -->
  <div id="tab-batch" class="panel">
    <div class="drop-zone" id="dz-batch" onclick="document.getElementById('file-batch').click()">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16"/></svg>
      <p>Click or drag multiple CV files here</p>
      <div class="hint">PDF, DOCX &mdash; up to 200 files</div>
    </div>
    <input type="file" id="file-batch" class="file-input" accept=".pdf,.docx,.doc" multiple>
    <div class="file-list" id="fl-batch"></div>
    <div class="actions">
      <button class="btn btn-primary" id="btn-batch" disabled onclick="startBatch()">Parse All</button>
      <button class="btn btn-secondary" id="btn-download" style="display:none" onclick="downloadAll()">Download ZIP</button>
      <span id="batch-status" style="font-size:13px;color:#64748b"></span>
    </div>
    <div class="progress-area" id="progress-area" style="display:none">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="pbar"></div></div>
      <div class="progress-text" id="ptxt"></div>
    </div>
    <div class="stats-row" id="stats-row" style="display:none">
      <div class="stat-card"><div class="num" id="st-total">0</div><div class="label">Total</div></div>
      <div class="stat-card"><div class="num" id="st-ok">0</div><div class="label">Success</div></div>
      <div class="stat-card"><div class="num" id="st-err">0</div><div class="label">Errors</div></div>
      <div class="stat-card"><div class="num" id="st-fields">0</div><div class="label">Avg Fields</div></div>
    </div>
    <div class="results" id="res-batch"></div>
  </div>
</div>

<script>
/* ── Tab switch ── */
function switchTab(name){
  document.querySelectorAll('.tab').forEach((t,i)=>{t.classList.toggle('active',i===(name==='single'?0:1))});
  document.getElementById('tab-single').classList.toggle('active',name==='single');
  document.getElementById('tab-batch').classList.toggle('active',name==='batch');
}

/* ── Drag & drop ── */
function setupDrop(dzId,inputId){
  const dz=document.getElementById(dzId),inp=document.getElementById(inputId);
  dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag-over')});
  dz.addEventListener('dragleave',()=>dz.classList.remove('drag-over'));
  dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('drag-over');inp.files=e.dataTransfer.files;inp.dispatchEvent(new Event('change'))});
}
setupDrop('dz-single','file-single');
setupDrop('dz-batch','file-batch');

/* ── File list rendering ── */
let singleFiles=[], batchFiles=[];

function renderFileList(files,containerId,btnId){
  const c=document.getElementById(containerId);
  c.innerHTML='';
  files.forEach((f,i)=>{
    const d=document.createElement('div');d.className='file-item';
    d.innerHTML=`<span class="name">${f.name}</span><span class="size">${(f.size/1024).toFixed(0)} KB</span><span class="remove" data-i="${i}">&times;</span>`;
    c.appendChild(d);
  });
  document.getElementById(btnId).disabled=files.length===0;
  c.querySelectorAll('.remove').forEach(r=>r.addEventListener('click',e=>{
    const idx=+e.target.dataset.i;
    if(containerId==='fl-single'){singleFiles.splice(idx,1);renderFileList(singleFiles,'fl-single','btn-parse')}
    else{batchFiles.splice(idx,1);renderFileList(batchFiles,'fl-batch','btn-batch')}
  }));
}

document.getElementById('file-single').addEventListener('change',e=>{
  singleFiles=[...e.target.files].filter(f=>f.name.match(/\.(pdf|docx|doc)$/i)).slice(0,1);
  renderFileList(singleFiles,'fl-single','btn-parse');
});
document.getElementById('file-batch').addEventListener('change',e=>{
  const added=[...e.target.files].filter(f=>f.name.match(/\.(pdf|docx|doc)$/i));
  batchFiles=[...batchFiles,...added].slice(0,200);
  renderFileList(batchFiles,'fl-batch','btn-batch');
});

/* ── Single parse ── */
async function parseSingle(){
  if(!singleFiles.length)return;
  const btn=document.getElementById('btn-parse'),st=document.getElementById('single-status'),res=document.getElementById('res-single');
  btn.disabled=true; st.textContent='Parsing...'; res.innerHTML='';
  const fd=new FormData(); fd.append('file',singleFiles[0]);
  try{
    const r=await fetch('/api/parse',{method:'POST',body:fd});
    const d=await r.json();
    st.textContent=`Done — ${d.fields_extracted} fields, ${d.elapsed_ms}ms`;
    res.innerHTML=buildResultCard(d);
  }catch(e){st.textContent='Error: '+e.message}
  btn.disabled=false;
}

/* ── Batch ── */
let currentJobId=null;
async function startBatch(){
  if(!batchFiles.length)return;
  const btn=document.getElementById('btn-batch'),st=document.getElementById('batch-status');
  btn.disabled=true; st.textContent='Uploading...';
  document.getElementById('progress-area').style.display='block';
  document.getElementById('stats-row').style.display='none';
  document.getElementById('res-batch').innerHTML='';
  document.getElementById('btn-download').style.display='none';

  const fd=new FormData();
  batchFiles.forEach(f=>fd.append('files',f));
  try{
    const r=await fetch('/api/batch/start',{method:'POST',body:fd});
    const d=await r.json();
    currentJobId=d.job_id;
    st.textContent='Processing...';
    pollProgress();
  }catch(e){st.textContent='Upload error: '+e.message;btn.disabled=false}
}

async function pollProgress(){
  if(!currentJobId)return;
  try{
    const r=await fetch('/api/batch/status/'+currentJobId);
    const d=await r.json();
    const pct=d.total?Math.round(d.done/d.total*100):0;
    document.getElementById('pbar').style.width=pct+'%';
    document.getElementById('ptxt').textContent=`${d.done} / ${d.total} files (${pct}%)`;

    if(d.status==='done'){
      document.getElementById('batch-status').textContent='Complete!';
      document.getElementById('btn-batch').disabled=false;
      document.getElementById('btn-download').style.display='inline-flex';
      showBatchResults(d);
      return;
    }
  }catch(e){}
  setTimeout(pollProgress,500);
}

function showBatchResults(d){
  const stats=document.getElementById('stats-row');stats.style.display='flex';
  document.getElementById('st-total').textContent=d.total;
  document.getElementById('st-ok').textContent=d.success;
  document.getElementById('st-err').textContent=d.errors;
  document.getElementById('st-fields').textContent=d.avg_fields||0;

  const c=document.getElementById('res-batch');c.innerHTML='';
  (d.results||[]).forEach(r=>{c.innerHTML+=buildResultCard(r)});
}

function downloadAll(){
  if(currentJobId) window.location='/api/batch/download/'+currentJobId;
}

/* ── Result card builder ── */
function buildResultCard(r){
  const ok=r.status==='success';
  const warns=r.warnings&&r.warnings.length?`<div class="result-warnings">${r.warnings.join('<br>')}</div>`:'';
  const jsonStr=r.data?JSON.stringify(r.data,null,2):'No data';
  const cvType=r.cv_type||'unknown';
  const typeBadge=cvType==='structured_form'?'<span style="background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px">FORM</span>':'<span style="background:#f0fdf4;color:#15803d;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px">FREE-FORM</span>';
  return `<div class="result-card">
    <div class="result-header" onclick="this.nextElementSibling.classList.toggle('open')">
      <span class="status ${ok?'ok':'err'}"></span>
      <span class="fname">${r.file||'result'}${typeBadge}</span>
      <span class="meta">${r.fields_extracted||0} fields &middot; ${r.elapsed_ms||0}ms</span>
    </div>
    <div class="result-body">${warns}<pre>${escHtml(jsonStr)}</pre></div>
  </div>`;
}

function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
</script>
</body>
</html>
"""


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/parse", methods=["POST"])
def api_parse():
    f = request.files.get("file")
    if not f or not _allowed(f.filename):
        return jsonify({"status": "error", "warnings": ["No valid file"]}), 400

    filepath = UPLOAD_DIR / f"{uuid.uuid4().hex}_{f.filename}"
    f.save(filepath)

    try:
        result = parse_single_cv(str(filepath))
        result["file"] = f.filename
    finally:
        filepath.unlink(missing_ok=True)

    return jsonify(result)


@app.route("/api/batch/start", methods=["POST"])
def api_batch_start():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files"}), 400

    job_id = uuid.uuid4().hex
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir()

    saved = []
    for f in files:
        if f and _allowed(f.filename):
            dest = job_dir / f.filename
            # Handle duplicate filenames
            if dest.exists():
                dest = job_dir / f"{uuid.uuid4().hex[:6]}_{f.filename}"
            f.save(dest)
            saved.append(str(dest))

    _jobs[job_id] = {
        "status": "running",
        "total": len(saved),
        "done": 0,
        "success": 0,
        "errors": 0,
        "results": [],
        "avg_fields": 0,
        "dir": str(job_dir),
    }

    thread = Thread(target=_run_batch_job, args=(job_id, saved), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/batch/status/<job_id>")
def api_batch_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/batch/download/<job_id>")
def api_batch_download(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in job["results"]:
            if r.get("data"):
                fname = Path(r["file"]).stem + ".json"
                zf.writestr(fname, to_json_string(r["data"]))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name="cv_parsed.zip")


def _run_batch_job(job_id: str, filepaths: list[str]):
    job = _jobs[job_id]
    total_fields = 0

    with ThreadPoolExecutor(max_workers=min(2, len(filepaths))) as executor:
        futures = {executor.submit(parse_single_cv, fp): fp for fp in filepaths}

        for future in as_completed(futures):
            fp = futures[future]
            try:
                result = future.result()
                result["file"] = Path(fp).name
            except Exception as e:
                result = {
                    "file": Path(fp).name,
                    "status": "error",
                    "warnings": [str(e)],
                    "data": None,
                    "fields_extracted": 0,
                    "elapsed_ms": 0,
                }

            job["results"].append(result)
            job["done"] += 1
            if result["status"] == "success":
                job["success"] += 1
            else:
                job["errors"] += 1
            total_fields += result.get("fields_extracted", 0)
            job["avg_fields"] = round(total_fields / job["done"], 1)

    job["status"] = "done"

    # Cleanup uploaded files
    import shutil
    shutil.rmtree(job["dir"], ignore_errors=True)


if __name__ == "__main__":
    app.run(debug=True, port=5005)
