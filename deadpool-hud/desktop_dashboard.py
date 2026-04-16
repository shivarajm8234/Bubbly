#!/usr/bin/env python3
"""
HUD
───
A glowing HUD bubble with a sleek tech-themed dashboard.
Includes file sharing between mobile & laptop via local network + QR code.
"""

import tkinter as tk
from tkinter import messagebox
import time, os, sys, subprocess, random, tempfile, threading, socket, json, base64, shutil
import http.server, urllib.parse, requests
from pathlib import Path
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
from functools import partial

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

# ══════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))

# Use explicit Desktop paths as requested by user
PHOTO_DIR = os.path.expanduser("~/Desktop/she❤️")
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR, exist_ok=True)

print(f"[*] Deadpool HUD Photo Directory: {PHOTO_DIR}")

CONFIG_FILE = Path.home() / ".bubble_hud_rc"
SHARE_DIR   = Path(os.path.expanduser("~/Desktop/Hub Server"))
if not SHARE_DIR.exists():
    SHARE_DIR.mkdir(parents=True, exist_ok=True)

print(f"[*] Deadpool HUD Share Directory: {SHARE_DIR}")
SHARE_PORT  = 8844
SLIDE_SECS  = 6
STATS_MS    = 2000
NET_PTS     = 40
PANEL_W     = 370
PANEL_H     = 640
BUBBLE_SIZE = 54
ALPHA       = 0.95
LOGO_PATH   = os.path.join(SCRIPT_DIR, "deadpool_logo.png")
QR_PATH     = os.path.join(SCRIPT_DIR, "share_qr.png")

# Default position
BUBBLE_X    = 6           
BUBBLE_Y    = 180         

def load_pos():
    global BUBBLE_X, BUBBLE_Y
    if CONFIG_FILE.exists():
        try:
            line = CONFIG_FILE.read_text().strip()
            x, y = map(int, line.split(","))
            BUBBLE_X, BUBBLE_Y = x, y
        except: pass

def save_pos(x, y):
    try: CONFIG_FILE.write_text(f"{x},{y}")
    except: pass

load_pos()

BG     = "#050505"
BG2    = "#121212"
ACCENT = "#e62117"
RED    = "#b31b14"
GREEN  = "#ffffff"
TEXT   = "#f0f0f0"
DIM    = "#666666"
FONT   = "Courier"
TRANS_COLOR = "#000001"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_gpu_util():
    try:
        res = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], stderr=subprocess.DEVNULL, encoding="utf-8")
        return int(res.strip())
    except:
        return 0

LOCAL_IP = get_local_ip()
SHARE_PORT  = 8844
SHARE_URL = f"http://{LOCAL_IP}:{SHARE_PORT}"
PAIR_CODE = f"{random.randint(100000, 999999)}"
AUTHORIZED_IPS = set()  # IP addresses that have passed authentication

def generate_qr():
    """Generate QR code image for the share URL."""
    if not HAS_QR:
        return
    try:
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        auth_url = f"http://hud:{PAIR_CODE}@{LOCAL_IP}:{SHARE_PORT}"
        qr.add_data(auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#e62117", back_color="#121212")
        img.save(QR_PATH)
    except:
        pass

generate_qr()

# ══════════════════════════════════════════════════════════

def human(b):
    for u in ("B/s","KB/s","MB/s","GB/s"):
        if b < 1024: return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}GB/s"

def human_size(b):
    for u in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} GB"

def get_photos():
    p = Path(PHOTO_DIR)
    if not p.exists(): return []
    exts = {".png",".jpg",".jpeg",".ppm",".pgm",".gif"}
    files = [f for f in p.iterdir() if f.suffix.lower() in exts]
    random.shuffle(files)
    return files

def load_photo(path, w, h):
    suf = Path(path).suffix.lower()
    if suf in (".png",".ppm",".pgm",".gif"):
        try:
            img = tk.PhotoImage(file=str(path))
            fx = max(1, img.width()  // w)
            fy = max(1, img.height() // h)
            f  = max(fx, fy)
            return img.subsample(f, f) if f > 1 else img
        except: return None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        subprocess.run(
            ["convert", "-resize", f"{w}x{h}^",
             "-gravity","center","-extent",f"{w}x{h}",
             str(path), tmp.name],
            check=True, capture_output=True, timeout=5)
        img = tk.PhotoImage(file=tmp.name)
        os.unlink(tmp.name)
        return img
    except: return None


# ══════════════════════════════════════════════════════════
#  FILE SHARING HTTP SERVER
# ══════════════════════════════════════════════════════════
SHARE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>HUD Share</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: #050505;
    color: #f0f0f0;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    min-height: 100vh;
    -webkit-tap-highlight-color: transparent;
  }
  .header {
    background: linear-gradient(135deg, #1a0000 0%%, #0a0a0a 50%%, #1a0000 100%%);
    border-bottom: 2px solid #e62117;
    padding: 24px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle at 50%% 100%%, rgba(230,33,23,0.15) 0%%, transparent 70%%);
  }
  .header h1 {
    color: #e62117;
    font-size: 24px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 3px;
    text-shadow: 0 0 20px rgba(230,33,23,0.5);
    position: relative;
  }
  .header p {
    color: #666;
    font-size: 11px;
    margin-top: 5px;
    position: relative;
  }
  .container { max-width: 600px; margin: 0 auto; padding: 16px; }

  .upload-zone {
    border: 2px dashed #e62117;
    border-radius: 16px;
    padding: 35px 20px;
    text-align: center;
    margin: 16px 0;
    background: rgba(230,33,23,0.03);
    transition: all 0.3s;
    cursor: pointer;
    position: relative;
  }
  .upload-zone:hover, .upload-zone.dragover {
    background: rgba(230,33,23,0.1);
    border-color: #ff4444;
    box-shadow: 0 0 30px rgba(230,33,23,0.2);
  }
  .upload-zone .icon { font-size: 42px; margin-bottom: 8px; }
  .upload-zone .text { color: #999; font-size: 13px; }
  .upload-zone .text b { color: #e62117; }
  .upload-zone input[type=file] {
    display: none;
  }

  .progress-bar {
    width: 100%%; height: 6px; background: #1a1a1a;
    border-radius: 3px; margin: 12px 0; display: none;
    overflow: hidden;
  }
  .progress-bar .fill {
    height: 100%%; background: linear-gradient(90deg, #e62117, #ff4444);
    border-radius: 3px; width: 0%%; transition: width 0.3s;
    box-shadow: 0 0 10px rgba(230,33,23,0.5);
  }

  .status {
    text-align: center; padding: 8px; color: #666;
    font-size: 12px; display: none;
  }
  .status.success { color: #4caf50; }
  .status.error { color: #e62117; }

  .section-title {
    color: #e62117;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin: 20px 0 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1a1a1a;
  }
  .file-list { list-style: none; }
  .file-item {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    background: #0d0d0d;
    border-radius: 10px;
    margin-bottom: 6px;
    border: 1px solid #1a1a1a;
    transition: all 0.2s;
  }
  .file-item:hover {
    border-color: #e62117;
    box-shadow: 0 0 15px rgba(230,33,23,0.1);
  }
  .file-icon { font-size: 22px; margin-right: 10px; flex-shrink: 0; }
  .file-info { flex: 1; min-width: 0; }
  .file-name {
    color: #f0f0f0;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .file-size { color: #666; font-size: 10px; margin-top: 2px; }
  .file-actions { display: flex; gap: 6px; }
  .file-actions a, .file-actions button {
    display: inline-block;
    padding: 5px 12px;
    background: #e62117;
    color: white;
    text-decoration: none;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    transition: all 0.2s;
    border: none;
    cursor: pointer;
  }
  .file-actions a:hover, .file-actions button:hover {
    background: #ff4444;
    box-shadow: 0 0 15px rgba(230,33,23,0.4);
  }
  .file-actions .del-btn { background: #333; }
  .file-actions .del-btn:hover { background: #b31b14; }
  .empty {
    text-align: center;
    padding: 25px;
    color: #444;
    font-size: 13px;
  }
  .tab-bar {
    display: flex;
    gap: 0;
    margin-bottom: 5px;
    background: #0d0d0d;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #1a1a1a;
  }
  .tab {
    flex: 1;
    padding: 11px;
    text-align: center;
    cursor: pointer;
    color: #666;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.2s;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .tab.active {
    background: #e62117;
    color: white;
  }
  .tab-content { display: none; }
  .tab-content.active { display: block; }

  .clip-area {
    width: 100%%;
    min-height: 100px;
    background: #0d0d0d;
    border: 1px solid #1a1a1a;
    border-radius: 10px;
    color: #f0f0f0;
    padding: 12px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    resize: vertical;
    outline: none;
    margin: 8px 0;
    transition: border-color 0.2s;
  }
  .clip-area:focus { border-color: #e62117; }
  .btn {
    display: inline-block;
    padding: 9px 18px;
    background: #e62117;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 3px;
  }
  .btn:hover { background: #ff4444; box-shadow: 0 0 20px rgba(230,33,23,0.3); }
  .btn-outline {
    background: transparent;
    border: 1px solid #e62117;
    color: #e62117;
  }
  .btn-outline:hover { background: rgba(230,33,23,0.1); }
  .btn-row { text-align: center; margin: 8px 0; }
  .device-info {
    background: #0d0d0d;
    border: 1px solid #1a1a1a;
    border-radius: 10px;
    padding: 12px;
    margin: 10px 0;
    text-align: center;
    font-size: 11px;
    color: #666;
  }
  .device-info .ip { color: #e62117; font-weight: bold; font-size: 14px; }
</style>
</head>
<body>
  <div class="header">
    <h1>⚔ HUD Share</h1>
    <p>Maximum Effort File Transfer • SHARE_URL_PLACEHOLDER</p>
  </div>
  <div class="container">
    <div class="tab-bar">
      <div class="tab active" onclick="switchTab('files')">📁 Files</div>
      <div class="tab" onclick="switchTab('clipboard')">📋 Clipboard</div>
    </div>

    <!-- FILES TAB -->
    <div id="tab-files" class="tab-content active">
      <div class="upload-zone" id="dropzone" onclick="document.getElementById('fileInput').click()">
        <div class="icon">📤</div>
        <div class="text">Tap to select files or <b>drag & drop</b></div>
        <input type="file" id="fileInput" multiple onchange="uploadFiles(this.files)">
      </div>
      <div class="progress-bar" id="progress"><div class="fill" id="progressFill"></div></div>
      <div class="status" id="status"></div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:20px;">
        <div class="section-title" style="margin:0;">Shared Files</div>
        <button class="btn btn-outline" style="padding:4px 10px; font-size:10px; text-transform:none;" onclick="loadFiles()">🔄 Refresh</button>
      </div>
      <ul class="file-list" id="fileList"></ul>
    </div>

    <!-- CLIPBOARD TAB -->
    <div id="tab-clipboard" class="tab-content">
      <div class="section-title">Shared Clipboard</div>
      <textarea class="clip-area" id="clipText" placeholder="Type or paste text here to share between devices..."></textarea>
      <div class="btn-row">
        <button class="btn" onclick="sendClip()">Send</button>
        <button class="btn btn-outline" onclick="loadClip()">Refresh</button>
        <button class="btn btn-outline" onclick="copyClip()">Copy</button>
      </div>
      <div class="status" id="clipStatus"></div>
    </div>

    <div class="device-info">
      Connected from: <span id="clientIP"></span><br>
      Files stored in: <b>~/Desktop/Sys-Mob</b><br>
      <button class="btn btn-outline" style="margin-top:10px; padding:5px 12px; font-size:10px;" onclick="disconnectBrowser()">🚫 Disconnect Device</button>
    </div>

    <!-- APT LOCK ALERT WEB -->
    <div id="aptLockAlert" style="display:none; margin-top:15px; background:rgba(230,33,23,0.1); border:1px solid #e62117; border-radius:12px; padding:15px; text-align:center;">
      <div style="color:#e62117; font-weight:bold; margin-bottom:10px;">⚠️ SYSTEM LOCK DETECTED</div>
      <p style="color:#999; font-size:12px; margin-bottom:15px;">APT or DPKG is currently locked by another process.</p>
      <button class="btn" style="width:100%;" onclick="fixAptLock()">Repair System Lock</button>
    </div>
  </div>

  <!-- AUTH MODAL -->
  <div id="authOverlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:1000; justify-content:center; align-items:center;">
    <div style="background:#0d0d0d; padding:30px; border-radius:16px; border:2px solid #e62117; text-align:center; max-width:90%;">
      <h2 style="color:#e62117; margin-bottom:10px;">⚔ SECURITY PAIRING</h2>
      <p style="color:#666; font-size:13px; margin-bottom:20px;">Enter the 6-digit code shown on your Laptop HUD</p>
      <input type="text" id="pinInput" maxlength="6" style="background:#000; border:1px solid #333; color:white; font-size:32px; text-align:center; width:200px; padding:10px; border-radius:8px; display:block; margin:0 auto 20px;">
      <button class="btn" onclick="pairBrowser()">Connect</button>
    </div>
  </div>

  <script>
    document.getElementById('clientIP').textContent = location.host;
    let pairingCode = localStorage.getItem('hud_pairing_code') || '';
    let isAuthorized = false;

    function checkAuth(r) {
      if (r.status === 401) {
        document.getElementById('authOverlay').style.display = 'flex';
        isAuthorized = false;
        pairingCode = '';
        localStorage.removeItem('hud_pairing_code');
        return false;
      }
      return true;
    }

    function pairBrowser(pCode) {
      const pin = pCode || document.getElementById('pinInput').value;
      if (!pin) {
        document.getElementById('authOverlay').style.display = 'flex';
        return;
      }
      
      fetch('/api/auth/' + pin).then(r => {
        if (r.ok) {
          localStorage.setItem('hud_pairing_code', pin);
          pairingCode = pin;
          document.getElementById('authOverlay').style.display = 'none';
          isAuthorized = true;
          loadFiles();
        } else {
          if (!pCode) alert('❌ Invalid code');
          document.getElementById('authOverlay').style.display = 'flex';
          isAuthorized = false;
          localStorage.removeItem('hud_pairing_code');
        }
      });
    }

    function getHeaders() {
      return pairingCode ? { 'Authorization': 'Bearer ' + pairingCode } : {};
    }

    function disconnectBrowser() {
      if(!confirm('Disconnect this device?')) return;
      localStorage.removeItem('hud_pairing_code');
      location.reload();
    }

    function switchTab(name) {
      document.querySelectorAll('.tab').forEach((t,i) => {
        t.classList.toggle('active', (name==='files' && i===0) || (name==='clipboard' && i===1));
      });
      document.getElementById('tab-files').classList.toggle('active', name==='files');
      document.getElementById('tab-clipboard').classList.toggle('active', name==='clipboard');
      if(name==='clipboard') loadClip();
    }

    const dz = document.getElementById('dropzone');
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
    dz.addEventListener('drop', e => {
      e.preventDefault(); dz.classList.remove('dragover');
      uploadFiles(e.dataTransfer.files);
    });

    function showStatus(msg, type) {
      const s = document.getElementById('status');
      if(!s) return;
      s.textContent = msg; s.className = 'status ' + type; s.style.display = 'block';
      setTimeout(() => s.style.display = 'none', 4000);
    }

    function uploadFiles(files) {
      const bar = document.getElementById('progress');
      const fill = document.getElementById('progressFill');
      bar.style.display = 'block'; fill.style.width = '0%';

      const fd = new FormData();
      for (let f of files) fd.append('file', f);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/upload');
      if (pairingCode) {
        xhr.setRequestHeader('Authorization', 'Bearer ' + pairingCode);
      }
      xhr.onload = () => {
        bar.style.display = 'none';
        if (xhr.status === 200) {
          showStatus('✅ Upload complete!', 'success');
          loadFiles();
        } else {
          checkAuth(xhr);
          if (xhr.status !== 401) showStatus('❌ Upload failed', 'error');
        }
      };
      xhr.onerror = () => { bar.style.display='none'; showStatus('❌ Network error','error'); };
      xhr.send(fd);
    }

    function loadFiles() {
      fetch('/api/files', { headers: getHeaders() }).then(r => {
        if (!checkAuth(r)) return [];
        return r.json();
      }).then(files => {
        if (!files) return;
        const list = document.getElementById('fileList');
        if (!files.length) {
          list.innerHTML = `<div class="empty">No files shared yet.<br>Upload from here or drop files in ~/Desktop/Sys-Mob</div>`;
          return;
        }
        list.innerHTML = files.map(f => `
          <li class="file-item">
            <span class="file-icon">${getIcon(f.name)}</span>
            <div class="file-info">
              <div class="file-name">${f.name}</div>
              <div class="file-size">${f.size}</div>
            </div>
            <div class="file-actions">
              <a href="/download/${encodeURIComponent(f.name)}?code=${pairingCode}">↓</a>
              <button class="del-btn" onclick="delFile('${f.name.replace(/'/g,"\\'")}')">✕</button>
            </div>
          </li>
        `).join('');
      });
    }

    function delFile(name) {
      if(!confirm('Delete ' + name + '?')) return;
      fetch('/api/delete/' + encodeURIComponent(name), {
        method:'DELETE',
        headers: getHeaders()
      }).then(r => { if(checkAuth(r)) loadFiles(); });
    }

    function getIcon(name) {
      const ext = name.split('.').pop().toLowerCase();
      const icons = {
        pdf:'📄',doc:'📝',docx:'📝',txt:'📝',
        jpg:'🖼️',jpeg:'🖼️',png:'🖼️',gif:'🖼️',webp:'🖼️',svg:'🖼️',
        mp4:'🎬',mkv:'🎬',avi:'🎬',mov:'🎬',
        mp3:'🎵',wav:'🎵',flac:'🎵',aac:'🎵',
        zip:'📦',rar:'📦',tar:'📦',gz:'📦',
        apk:'📱',exe:'💻',deb:'💻',
        py:'🐍',js:'⚡',html:'🌐',css:'🎨',json:'📋',
      };
      return icons[ext] || '📄';
    }

    function sendClip() {
      const text = document.getElementById('clipText').value;
      fetch('/api/clipboard', {
        method: 'POST',
        headers: {'Content-Type':'application/json', ...getHeaders()},
        body: JSON.stringify({text})
      }).then(r => {
        if (!checkAuth(r)) return;
        const s = document.getElementById('clipStatus');
        s.textContent = '✅ Text shared!'; s.className='status success'; s.style.display='block';
        setTimeout(()=>s.style.display='none',3000);
      });
    }

    function loadClip() {
      fetch('/api/clipboard', { headers: getHeaders() }).then(r => {
        if (!checkAuth(r)) return {};
        return r.json();
      }).then(d => {
        if (d.text !== undefined) document.getElementById('clipText').value = d.text;
      });
    }

    function copyClip() {
      const ta = document.getElementById('clipText');
      ta.select();
      navigator.clipboard.writeText(ta.value).then(() => {
        const s = document.getElementById('clipStatus');
        s.textContent = '📋 Copied!'; s.className='status success'; s.style.display='block';
        setTimeout(()=>s.style.display='none',2000);
      });
    }

    // Initial Auth
    if (pairingCode) {
      pairBrowser(pairingCode);
    } else {
      document.getElementById('authOverlay').style.display = 'flex';
    }

    function fixAptLock() {
      if(!confirm('This will attempt to kill stuck apt processes and remove lock files. Proceed?')) return;
      fetch('/api/fix_apt_lock', { method: 'POST', headers: getHeaders() })
        .then(r => r.ok ? alert('✅ Fix command sent to laptop') : alert('❌ Failed to send fix command'));
    }

    setInterval(() => {
      if(isAuthorized) {
        loadFiles();
        // Update sys stats for lock check
        fetch('/api/stats', { headers: getHeaders() })
          .then(r => r.json())
          .then(data => {
            const alertBox = document.getElementById('aptLockAlert');
            if (data.apt_lock) {
              alertBox.style.display = 'block';
              const listStr = data.apt_blockers ? data.apt_blockers.join(', ') : 'Unknown process';
              alertBox.querySelector('p').innerHTML = `Locked by: <b>${listStr}</b>`;
            } else {
              alertBox.style.display = 'none';
            }
          }).catch(e => {});
      }
    }, 8000);
  </script>
</body>
</html>
"""

class ShareHandler(BaseHTTPRequestHandler):
    def __init__(self, share_dir, *args, **kw):
        self.share_dir = share_dir
        super().__init__(*args, **kw)

    # def log_message(self, fmt, *args): pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, *")
        super().end_headers()

    def _send_cors(self):
        # Redundant now as end_headers handles it, but kept for compatibility if called elsewhere
        pass

    def _is_authorized(self):
        client_ip = self.client_address[0]
        # Auto-authorize ONLY local loopback requests
        if client_ip in ("127.0.0.1", "::1"):
            return True
            
        # Check query parameters for 'code' (for direct links like downloads)
        if "?code=" in self.path:
            try:
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if 'code' in params and params['code'][0] == PAIR_CODE:
                    if client_ip not in AUTHORIZED_IPS:
                        print(f"[*] IP {client_ip} authorized via query code")
                        AUTHORIZED_IPS.add(client_ip)
                    return True
            except:
                pass

        # Check Authorization header for Basic Auth or a custom pairing token
        auth_header = self.headers.get('Authorization')
        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                if token == PAIR_CODE:
                    if client_ip not in AUTHORIZED_IPS:
                        print(f"[*] IP {client_ip} authorized via Bearer token")
                        AUTHORIZED_IPS.add(client_ip)
                    return True
            elif auth_header.startswith('Basic '):
                try:
                    import base64
                    encoded = auth_header.split(' ')[1]
                    decoded = base64.b64decode(encoded).decode()
                    if ":" in decoded:
                        user, pw = decoded.split(":", 1)
                        if pw == PAIR_CODE:
                            if client_ip not in AUTHORIZED_IPS:
                                print(f"[*] IP {client_ip} authorized via Basic auth")
                                AUTHORIZED_IPS.add(client_ip)
                            return True
                except:
                    pass
        
        is_auth = client_ip in AUTHORIZED_IPS
        if not is_auth:
            print(f"[!] Auth failed for {client_ip} (Path: {self.path})")
        return is_auth

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def _is_offline(self):
        return hasattr(self.server, "app_ref") and self.server.app_ref and self.server.app_ref._is_mini_mode

    def do_GET(self):
        try:
            if self.path == "/api/status":
                self._api_status("offline" if self._is_offline() else "online")
                return
            elif self.path == "/api/stats":
                self._api_sys_stats()
                return
                
            if self.path.startswith("/api/auth/"):
                code = self.path.split("/")[-1]
                if code == PAIR_CODE:
                    print(f"[*] New authorized IP: {self.client_address[0]}")
                    AUTHORIZED_IPS.add(self.client_address[0])
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"ok":true}')
                else:
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"ok":false}')
                return

            # Restricted access check
            if not self._is_authorized() and self.path != "/":
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"unauthorized"}')
                return

            if self.path == "/" or self.path == "/index.html":
                self._serve_html()
            elif self.path == "/api/files":
                self._api_files()
            elif self.path == "/api/clipboard":
                self._api_get_clipboard()
            elif self.path.startswith("/download/"):
                self._download_file()
            else:
                # Fallback: check if the path (minus query) matches a file in share_dir
                path_only = urllib.parse.urlparse(self.path).path
                filename = urllib.parse.unquote(path_only.lstrip("/"))
                if filename:
                    fpath = self.share_dir / filename
                    if fpath.exists() and fpath.is_file():
                        self._download_file()
                        return
                self.send_error(404)
        except Exception as e:
            print(f"[!] GET Error: {e}")
            self.send_error(500, str(e))

    def do_POST(self):
        try:
            if not self._is_authorized():
                print(f"[!] Unauthorized POST from {self.client_address[0]}")
                self.send_response(401)
                self.end_headers()
                return

            if self.path == "/upload":
                self._handle_upload()
            elif self.path == "/api/fix_apt_lock":
                if hasattr(self.server, "app_ref") and self.server.app_ref:
                    self.server.app_ref._fix_apt_lock()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
            else:
                self.send_error(404)
        except Exception as e:
            print(f"[!] POST Error: {e}")
            self.send_error(500, str(e))

    def do_DELETE(self):
        if not self._is_authorized():
            self.send_response(401)
            self._send_cors()
            self.end_headers()
            return

        if self.path.startswith("/api/delete/"):
            self._delete_file()
        else:
            self.send_error(404)

    def _api_status(self, status="online"):
        import json
        data = {"status": status, "name": "HUD"}
        body = json.dumps(data).encode()
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        html = SHARE_HTML.replace("SHARE_URL_PLACEHOLDER", SHARE_URL)
        content = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def _api_files(self):
        files = []
        if self.share_dir.exists():
            for f in sorted(self.share_dir.iterdir()):
                if f.is_file() and not f.name.startswith("."):
                    files.append({"name": f.name, "size": human_size(f.stat().st_size)})
        body = json.dumps(files).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _api_sys_stats(self):
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        blockers = self.server.app_ref._is_apt_locked() if hasattr(self.server, "app_ref") else []
        data = {
            "gpu": get_gpu_util(),
            "cpu": cpu,
            "ram": ram.percent,
            "ram_total": human_size(ram.total),
            "ram_used": human_size(ram.used),
            "disk": disk.percent,
            "up": "0 KB/s", # Placeholder or implement network calc
            "down": "0 KB/s",
            "apt_lock": len(blockers) > 0,
            "apt_blockers": blockers
        }
        
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _api_get_clipboard(self):
        text = ""
        try:
            # Accessing Tk clipboard from thread can be tricky, but we try
            text = self.server.app_ref.clipboard_get()
        except:
            # Fallback to file if clipboard empty or error
            clip_file = self.share_dir / ".clipboard.txt"
            text = clip_file.read_text() if clip_file.exists() else ""
            
        body = json.dumps({"text": text}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _api_set_clipboard(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        text = data.get("text", "")
        
        # Save to file backup
        clip_file = self.share_dir / ".clipboard.txt"
        clip_file.write_text(text)
        
        # Try to set system clipboard
        try:
            self.server.app_ref.clipboard_clear()
            self.server.app_ref.clipboard_append(text)
        except:
            pass

        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _handle_upload(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            print(f"[!] Invalid Content-Type for upload: {content_type}")
            self.send_error(400, "Expected multipart/form-data")
            return
        
        # More robust boundary extraction
        try:
            boundary = content_type.split("boundary=")[1].split(";")[0]
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            boundary = boundary.encode()
        except Exception as e:
            print(f"[!] Failed to parse boundary: {e}")
            self.send_error(400, "Invalid boundary")
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            print("[!] Empty upload body")
            self.send_error(400, "Empty body")
            return

        print(f"[*] Receiving upload ({length} bytes)...")
        body = self.rfile.read(length)
        parts = body.split(b"--" + boundary)
        saved = 0
        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            
            header_end = part.find(b"\r\n\r\n")
            if header_end < 0: continue
            header = part[:header_end].decode(errors="replace")
            
            filename = None
            if 'filename="' in header:
                fn_start = header.find('filename="') + 10
                fn_end = header.find('"', fn_start)
                filename = header[fn_start:fn_end]
            elif 'name="' in header:
                # Fallback to name if filename missing
                fn_start = header.find('name="') + 6
                fn_end = header.find('"', fn_start)
                filename = f"upload_{int(time.time())}.dat"

            if not filename: continue
            
            filename = os.path.basename(filename)
            file_data = part[header_end+4:]
            if file_data.endswith(b"\r\n"):
                file_data = file_data[:-2]
            
            dest = self.share_dir / filename
            dest.write_bytes(file_data)
            print(f"[*] Saved file: {filename}")
            saved += 1

        body_resp = json.dumps({"saved": saved, "ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body_resp))
        self.end_headers()
        self.wfile.write(body_resp)

    def _download_file(self):
        # Extract filename from path, handling both /download/prefix and direct access
        path_only = urllib.parse.urlparse(self.path).path
        if path_only.startswith("/download/"):
            name = urllib.parse.unquote(path_only[len("/download/"):])
        else:
            name = urllib.parse.unquote(path_only.lstrip("/"))
            
        fpath = self.share_dir / name
        if not fpath.exists() or not fpath.is_file():
            print(f"[!] File not found: {fpath}")
            self.send_error(404)
            return
            
        try:
            data = fpath.read_bytes()
            self.send_response(200)
            # Map extension to mime type for better browser handling
            ext = fpath.suffix.lower()
            mime = "application/octet-stream"
            if ext in (".jpg", ".jpeg"): mime = "image/jpeg"
            elif ext == ".png": mime = "image/png"
            elif ext == ".gif": mime = "image/gif"
            elif ext == ".pdf": mime = "application/pdf"
            elif ext == ".txt": mime = "text/plain"
            
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            print(f"[!] Download error for {name}: {e}")
            self.send_error(500, str(e))

    def _delete_file(self):
        path_only = urllib.parse.urlparse(self.path).path
        name = urllib.parse.unquote(path_only[len("/api/delete/"):])
        fpath = self.share_dir / name
        if fpath.exists() and fpath.is_file():
            fpath.unlink()
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def start_share_server(share_dir, app_ref=None):
    """Start the file sharing server in a background thread."""
    share_dir.mkdir(parents=True, exist_ok=True)
    handler = partial(ShareHandler, share_dir)
    server = HTTPServer(("0.0.0.0", SHARE_PORT), handler)
    server.app_ref = app_ref
    server.daemon_threads = True
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ── Arc Gauge ───────────────────────────────────────────────
class ArcGauge(tk.Canvas):
    def __init__(self, parent, label, color, size=85, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=BG2, highlightthickness=0, **kw)
        self.label=label; self.color=color; self.size=size
        self._draw(0)
    def _draw(self, pct):
        s=self.size; self.delete("all"); p=12
        self.create_arc(p,p,s-p,s-p, start=220, extent=-260,
                        outline="#222222", style="arc", width=6)
        if pct>0:
            self.create_arc(p,p,s-p,s-p, start=220,
                            extent=-int(260*pct/100),
                            outline="#550000", style="arc", width=10)
            self.create_arc(p,p,s-p,s-p, start=220,
                            extent=-int(260*pct/100),
                            outline=self.color, style="arc", width=5)
        cx=cy=s//2
        self.create_text(cx,cy-6, text=f"{pct:.0f}%",
                         fill=TEXT, font=(FONT,11,"bold"))
        self.create_text(cx,cy+8, text=self.label,
                         fill=DIM, font=(FONT,7))
    def set(self, v): self._draw(v)


# ── Sparkline ────────────────────────────────────────────────
class Sparkline(tk.Canvas):
    def __init__(self, parent, label, color, **kw):
        super().__init__(parent, bg=BG2, highlightthickness=0, **kw)
        self.label=label; self.color=color
        self.data=deque([0]*NET_PTS, maxlen=NET_PTS); self._cur=""
        self.bind("<Configure>", lambda e: self._draw())
    def push(self, v, txt=""):
        self.data.append(v); self._cur=txt; self._draw()
    def _draw(self):
        self.delete("all")
        w=self.winfo_width()  or int(self["width"]  or 160)
        h=self.winfo_height() or int(self["height"] or 48)
        vals=list(self.data); mx=max(vals) or 1
        step=w/max(len(vals)-1,1); pts=[]
        for i,v in enumerate(vals):
            pts+=[i*step, h-3-(v/mx)*(h-12)]
        if len(pts)>=4:
            self.create_line(*pts, fill="#440000", width=4, smooth=True)
            self.create_line(*pts, fill=self.color, width=2, smooth=True)
        self.create_text(4,4, anchor="nw", text=self.label,
                         fill=DIM, font=(FONT,7))
        self.create_text(w-3,4, anchor="ne", text=self._cur,
                         fill=self.color, font=(FONT,8,"bold"))


# ══════════════════════════════════════════════════════════
#  Main App
# ══════════════════════════════════════════════════════════
class BubbleHUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", ALPHA)
        self.configure(bg=TRANS_COLOR)
        try:
            self.attributes("-transparentcolor", TRANS_COLOR)
        except Exception:
            pass
        self.resizable(False, False)

        self._expanded = False
        self._chat_active = False
        self._net_prev = None
        self._photos = get_photos()
        self._photo_idx = 0
        self._tk_img = None
        self._bubble_img = None
        self._qr_img = None
        self._blink_on = True
        self._share_server = None
        self._share_running = False

        self._dx = self._dy = 0
        self._start_x = self._start_y = 0
        self._bx = BUBBLE_X
        self._by = BUBBLE_Y
        self._drag_moved = False

        # Start share server immediately (requests blocked while mini mode)
        try:
            self._share_server = start_share_server(SHARE_DIR, self)
            self._share_running = True
        except:
            self._share_running = False

        self._is_mini_mode = True
        self._build_mini_mode()
        
        # Apply stealth mode hints
        self._set_stealth_mode()
        
    def _set_stealth_mode(self):
        """Apply multiple X11 window hints to hide from screen sharing/recording."""
        try:
            # 0. Robust way to get X11 window ID
            wid = self.winfo_id()
            try:
                wid_hex = self.frame()
                if wid_hex.startswith('0x'):
                    wid = int(wid_hex, 16)
            except: pass

            # 1. Hide from GNOME's native recorder (Mutter hint)
            subprocess.run(["xprop", "-id", str(wid), "-f", "_GTK_HIDE_FROM_SCREENCAST", "32c", "-set", "_GTK_HIDE_FROM_SCREENCAST", "1"], stderr=subprocess.DEVNULL)
            # 2. KDE-specific hint
            subprocess.run(["xprop", "-id", str(wid), "-f", "_KDE_SCREEN_CAPTURE_INHIBITED", "32c", "-set", "_KDE_SCREEN_CAPTURE_INHIBITED", "1"], stderr=subprocess.DEVNULL)
            # 3. Bypass compositor hint
            subprocess.run(["xprop", "-id", str(wid), "-f", "_NET_WM_BYPASS_COMPOSITOR", "32c", "-set", "_NET_WM_BYPASS_COMPOSITOR", "1"], stderr=subprocess.DEVNULL)
            # 4. Standard Hints - many tools ignore windows with SKIP_TASKBAR/SKIP_PAGER, STICKY forces all workspaces
            subprocess.run(["xprop", "-id", str(wid), "-f", "_NET_WM_STATE", "32a", "-set", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,_NET_WM_STATE_STAY_ON_TOP,_NET_WM_STATE_STICKY"], stderr=subprocess.DEVNULL)
            # 5. Force window type to 'tooltip' via xprop (more robust than tkinter attributes)
            subprocess.run(["xprop", "-id", str(wid), "-f", "_NET_WM_WINDOW_TYPE", "32a", "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_TOOLTIP"], stderr=subprocess.DEVNULL)
            
            self.attributes("-topmost", True)
        except:
            pass
        # Repeat every 5 seconds to ensure it stays set
        self.after(5000, self._set_stealth_mode)

    def _build_mini_mode(self):
        # We start in Mini Mode (offline)
        S = BUBBLE_SIZE
        self.geometry(f"{S}x{S}+{self._bx}+{self._by}")
        self._mini_frame = tk.Frame(self, bg=TRANS_COLOR, bd=0)
        self._mini_frame.pack()
        
        self._mcv = tk.Canvas(self._mini_frame, width=S, height=S,
                              bg=TRANS_COLOR, highlightthickness=0)
        self._mcv.pack()

        cx = cy = S//2
        # Dim ring denoting offline
        self._mcv.create_oval(cx-(S//2-1), cy-(S//2-1), cx+(S//2-1), cy+(S//2-1),
                              outline="#440000", width=2)
                              
        if os.path.exists(LOGO_PATH):
            self._bubble_img = load_photo(LOGO_PATH, S-16, S-16)
            if self._bubble_img:
                img_item = self._mcv.create_image(S//2, S//2, image=self._bubble_img)
            else:
                img_item = self._mcv.create_text(S//2, S//2, text="⚔", font=("", 18), fill="#440000")
        else:
            img_item = self._mcv.create_text(S//2, S//2, text="⚔", font=("", 18), fill="#440000")

        # Mini mode can be dragged around
        self._mcv.bind("<Button-1>",  self._bubble_click)
        self._mcv.bind("<B1-Motion>", self._bubble_drag)
        self._mcv.bind("<ButtonRelease-1>", self._mini_release)

    def _mini_release(self, e):
        if not self._drag_moved:
            self._start_hud()
        else:
            save_pos(self._bx, self._by)

    def _go_mini_mode(self):
        """Turn off everything and drop back to just the icon"""
        self._is_mini_mode = True
        self._expanded = False
        self._blink_on = False
        
        try:
            self._bubble_frame.pack_forget()
            self._panel.pack_forget()
            if hasattr(self, "_chat_panel"):
                self._chat_panel.pack_forget()
        except:
            pass
            
        S = BUBBLE_SIZE
        self.geometry(f"{S}x{S}+{self._bx}+{self._by}")
        self._mini_frame.pack()

    def _start_hud(self):
        self._is_mini_mode = False
        self._mini_frame.pack_forget()
        
        # Build UI if it's the first time
        if not hasattr(self, "_panel"):
            self._build_bubble()
            self._build_panel()
            self._update_stats()
            self._tick_clock()
            self._update_network_status()

        self._blink_on = True
        self._show_bubble()
        
    # ── BUBBLE ─────────────────────────────────────────────
    def _build_bubble(self):
        S = BUBBLE_SIZE
        self._bubble_frame = tk.Frame(self, bg=TRANS_COLOR, bd=0)
        self._bcv = tk.Canvas(self._bubble_frame, width=S, height=S,
                              bg=TRANS_COLOR, highlightthickness=0)
        self._bcv.pack()

        # Deadpool Red glow rings
        for i, (r, a) in enumerate([(S//2-1,  "#330000"),
                                     (S//2-5,  "#660000"),
                                     (S//2-9,  ACCENT)]):
            cx = cy = S//2
            self._bcv.create_oval(cx-r, cy-r, cx+r, cy+r,
                                  outline=a, width=2 if i<2 else 3, tags="ring")

        # Logo
        if os.path.exists(LOGO_PATH):
            self._bubble_img = load_photo(LOGO_PATH, S-16, S-16)
            if self._bubble_img:
                self._bcv.create_image(S//2, S//2, image=self._bubble_img, tags="bubble")
            else:
                self._bcv.create_text(S//2, S//2, text="⚔", font=("", 18), fill=ACCENT, tags="bubble")
        else:
            self._bcv.create_text(S//2, S//2, text="⚔", font=("", 18), fill=ACCENT, tags="bubble")

        self._bcv.bind("<Button-1>",  self._bubble_click)
        self._bcv.bind("<B1-Motion>", self._bubble_drag)
        self._bcv.bind("<ButtonRelease-1>", self._bubble_release)
        self._bcv.bind("<Double-Button-1>", lambda e: self._toggle())

        self._drag_moved = False
        self._blink_bubble()

    def _blink_bubble(self):
        if self._is_mini_mode:
            return
        if not self._expanded:
            color = ACCENT if self._blink_on else "#440000"
            self._bcv.itemconfig("ring", outline=color)
            self._blink_on = not self._blink_on
            self.after(900, self._blink_bubble)

    def _bubble_click(self, e):
        self._drag_moved = False
        self._start_x, self._start_y = e.x_root, e.y_root
        self._offset_x = e.x_root - self.winfo_x()
        self._offset_y = e.y_root - self.winfo_y()

    def _bubble_drag(self, e):
        if abs(e.x_root - self._start_x) > 3 or abs(e.y_root - self._start_y) > 3:
            self._drag_moved = True
        if not self._drag_moved:
            return
        self._bx = e.x_root - self._offset_x
        self._by = e.y_root - self._offset_y
        self.geometry(f"+{self._bx}+{self._by}")

    def _bubble_release(self, e):
        if not self._drag_moved:
            self._toggle()
        else:
            save_pos(self._bx, self._by)

    # ── PANEL ──────────────────────────────────────────────
    def _build_panel(self):
        P = 8
        PW = PANEL_W

        self._panel = tk.Frame(self, bg=BG, width=PW)
        self._panel.bind("<Button-1>",  self._bubble_click)
        self._panel.bind("<B1-Motion>", self._bubble_drag)
        self._panel.bind("<ButtonRelease-1>", self._bubble_release)

        # ── Header
        top = tk.Frame(self._panel, bg=BG)
        top.pack(fill="x", padx=P, pady=(6,2))
        top.bind("<Button-1>",  self._bubble_click)
        top.bind("<B1-Motion>", self._bubble_drag)
        top.bind("<ButtonRelease-1>", self._bubble_release)
        tk.Label(top, text="◈ HUD", bg=BG, fg=ACCENT,
                 font=(FONT,9,"bold")).pack(side="left")
        self._clk_lbl = tk.Label(top, text="", bg=BG, fg=DIM, font=(FONT,8))
        self._clk_lbl.pack(side="right", padx=(0,4))
        close_btn = tk.Label(top, text="✕", bg=BG, fg=DIM,
                             font=(FONT,11,"bold"), cursor="hand2")
        close_btn.pack(side="right", padx=(4,0))
        close_btn.bind("<Button-1>", lambda e: self._toggle())

        power_btn = tk.Label(top, text="⏻ OFF", bg=RED, fg=TEXT,
                             font=(FONT,7,"bold"), cursor="hand2", padx=4, pady=1)
        power_btn.pack(side="right", padx=(10,4))
        power_btn.bind("<Button-1>", lambda e: self._go_mini_mode())

        exit_btn = tk.Label(top, text="EXIT APP", bg=BG, fg=DIM, cursor="hand2", font=(FONT,6))
        exit_btn.pack(side="bottom", anchor="se", pady=4)
        exit_btn.bind("<Button-1>", lambda e: self.destroy())

        tk.Frame(self._panel, bg=ACCENT, height=1).pack(fill="x", padx=P)

        # ── Photo slideshow
        self._photo_lbl = tk.Label(self._panel, bg=BG2, width=354, height=110)
        self._photo_lbl.pack(padx=P, pady=(4,2))

        # ── Gauges
        gf = tk.Frame(self._panel, bg=BG)
        gf.pack(fill="x", padx=P, pady=2)
        self._g_gpu  = ArcGauge(gf,"GPU",  "#ff9900")
        self._g_cpu  = ArcGauge(gf,"CPU",  ACCENT)
        self._g_ram  = ArcGauge(gf,"RAM",  RED)
        self._g_disk = ArcGauge(gf,"DISK", GREEN)
        for g in (self._g_gpu, self._g_cpu, self._g_ram, self._g_disk):
            g.pack(side="left", expand=True, fill="both", padx=2)

        inf = tk.Frame(self._panel, bg=BG)
        inf.pack(fill="x", padx=P)
        self._lbl_freq = tk.Label(inf, text="", bg=BG, fg=DIM, font=(FONT,7))
        self._lbl_freq.pack(side="left")
        self._lbl_ram  = tk.Label(inf, text="", bg=BG, fg=DIM, font=(FONT,7))
        self._lbl_ram.pack(side="right")

        tk.Frame(self._panel, bg="#1a1a1a", height=1).pack(fill="x", padx=P, pady=2)

        # ── Network sparklines
        tk.Label(self._panel, text="▲▼ NETWORK", bg=BG, fg=ACCENT,
                 font=(FONT,7,"bold"), anchor="w").pack(fill="x", padx=P)
        nf = tk.Frame(self._panel, bg=BG)
        nf.pack(fill="x", padx=P, pady=2)
        self._sp_up   = Sparkline(nf,"Upload",  RED,   width=162, height=38)
        self._sp_dn   = Sparkline(nf,"Download",GREEN, width=162, height=38)
        self._sp_up.pack(side="left",  padx=(0,2))
        self._sp_dn.pack(side="right", padx=(2,0))

        tk.Frame(self._panel, bg="#1a1a1a", height=1).pack(fill="x", padx=P, pady=2)

        # SHARE SECTION with QR Code
        # ═══════════════════════════════════════════════════
        tk.Label(self._panel, text="⚔ HUD SHARE", bg=BG, fg=ACCENT,
                 font=(FONT,7,"bold"), anchor="w").pack(fill="x", padx=P)

        self._share_box = tk.Frame(self._panel, bg=BG2)
        self._share_box.pack(fill="x", padx=P, pady=(2,0))

        # Top row: status + port
        sf_top = tk.Frame(self._share_box, bg=BG2)
        sf_top.pack(fill="x", padx=8, pady=(5,2))
        
        status_color = "#4caf50" if self._share_running else RED
        status_text = "● ONLINE" if self._share_running else "● OFFLINE"
        tk.Label(sf_top, text=status_text, bg=BG2, fg=status_color,
                 font=(FONT,7,"bold")).pack(side="left")

        tk.Label(sf_top, text=f"Port {SHARE_PORT}", bg=BG2, fg=DIM,
                 font=(FONT,7)).pack(side="right")

        # QR Code + URL side by side
        qr_row = tk.Frame(self._share_box, bg=BG2)
        qr_row.pack(fill="x", padx=8, pady=(2,2))

        # QR code image
        qr_frame = tk.Frame(qr_row, bg="#1a0000", padx=3, pady=3)
        qr_frame.pack(side="left", padx=(0,8))

        self._qr_label = tk.Label(qr_frame, bg="#121212")
        if os.path.exists(QR_PATH):
            self._qr_img = load_photo(QR_PATH, 100, 100)
            if self._qr_img:
                self._qr_label.config(image=self._qr_img)
            else:
                self._qr_label.config(text="QR", fg=DIM, font=(FONT,8))
        else:
            self._qr_label.config(text="QR", fg=DIM, font=(FONT,8))
        self._qr_label.pack()

        # URL and info on the right
        info_frame = tk.Frame(qr_row, bg=BG2)
        info_frame.pack(side="left", fill="both", expand=True)

        tk.Label(info_frame, text="Scan with phone", bg=BG2, fg=DIM,
                 font=(FONT,7), anchor="w").pack(fill="x")

        url_frame = tk.Frame(info_frame, bg="#1a0000")
        url_frame.pack(fill="x", pady=(3,3))
        url_lbl = tk.Label(url_frame, text=SHARE_URL, bg="#1a0000",
                           fg=ACCENT, font=(FONT,7,"bold"),
                           cursor="hand2", pady=3, padx=4)
        url_lbl.pack(fill="x")
        self._url_lbl = url_lbl
        url_lbl.bind("<Button-1>", lambda e: self._open_url(SHARE_URL))

        tk.Label(info_frame, text="📱 Same WiFi network", bg=BG2, fg=DIM,
                 font=(FONT,6), anchor="w").pack(fill="x")
        
        pair_frame = tk.Frame(info_frame, bg=BG2)
        pair_frame.pack(fill="x", pady=(2,0))
        tk.Label(pair_frame, text="🔑 Code: ", bg=BG2, fg=DIM, font=(FONT,7)).pack(side="left")
        self._code_lbl = tk.Label(pair_frame, text=PAIR_CODE, bg=BG2, fg=ACCENT, font=(FONT,8,"bold"))
        self._code_lbl.pack(side="left")

        tk.Label(info_frame, text="📂 ~/Desktop/Sys-Mob", bg=BG2, fg=DIM,
                 font=(FONT,6), anchor="w").pack(fill="x")

        # Buttons
        btn_frame = tk.Frame(self._share_box, bg=BG2)
        btn_frame.pack(fill="x", padx=8, pady=(2,5))

        for txt, cmd in [("📂 Folder", self._open_share_folder),
                         ("🌐 Browser", lambda: self._open_url(SHARE_URL)),
                         ("🚫 Disconnect", self._reset_auth)]:
            b = tk.Label(btn_frame, text=txt, bg="#1a0000" if "Folder" in txt or "Browser" in txt else "#300", 
                         fg=ACCENT,
                         font=(FONT,7,"bold"), cursor="hand2", padx=8, pady=2)
            b.pack(side="left", padx=(0,4))
            b.bind("<Button-1>", lambda e, c=cmd: c())

        self._share_count_lbl = tk.Label(btn_frame, text="", bg=BG2, fg=DIM,
                                         font=(FONT,6))
        self._share_count_lbl.pack(side="right")
        self._update_share_count()

        # ── APT Lock Status (Always visible)
        self._apt_lock_frame = tk.Frame(self._panel, bg=BG2, bd=1, relief="flat")
        self._apt_lock_frame.pack(fill="x", padx=8, pady=(2,5), after=self._share_box)
        
        self._apt_warn_lbl = tk.Label(self._apt_lock_frame, text="✅ APT: OK", bg=BG2, fg=DIM,
                                      font=(FONT, 7, "bold"))
        self._apt_warn_lbl.pack(side="left", padx=10, pady=4)
        
        self._apt_fix_btn = tk.Label(self._apt_lock_frame, text="REPAIR NOW", bg=ACCENT, fg=TEXT,
                                     font=(FONT, 7, "bold"), cursor="hand2", padx=8, pady=2)
        # Don't pack yet


        # Footer
        tk.Frame(self._panel, bg=ACCENT, height=1).pack(fill="x", padx=P, pady=(4,0))
        tk.Label(self._panel, text="Maximum Effort Dashboard",
                 bg=BG, fg="#333333", font=(FONT,6)).pack(pady=2)

    def _reset_auth(self):
        global AUTHORIZED_IPS, PAIR_CODE
        AUTHORIZED_IPS.clear()
        PAIR_CODE = f"{random.randint(100000, 999999)}"
        self._code_lbl.config(text=PAIR_CODE)
        generate_qr()
        if hasattr(self, '_qr_label') and os.path.exists(QR_PATH):
            img = load_photo(QR_PATH, 100, 100)
            if img:
                self._qr_img = img
                self._qr_label.config(image=self._qr_img)
        # messagebox.showinfo("Security", "All sessions disconnected. New pairing code generated.", parent=self)

    def _open_url(self, url):
        try: subprocess.Popen(["xdg-open", url])
        except: pass

    def _open_share_folder(self):
        SHARE_DIR.mkdir(parents=True, exist_ok=True)
        try: subprocess.Popen(["xdg-open", str(SHARE_DIR)])
        except: pass

    def _update_share_count(self):
        if SHARE_DIR.exists():
            count = len([f for f in SHARE_DIR.iterdir()
                        if f.is_file() and not f.name.startswith(".")])
            self._share_count_lbl.config(text=f"{count} file{'s' if count!=1 else ''}")
        else:
            self._share_count_lbl.config(text="0 files")
        self.after(5000, self._update_share_count)

    # ── APT LOCK MONITOR ──────────────────────────────────
    def _is_apt_locked(self):
        """Check for APT/DPKG lock files and processes and return list of process names/PIDs."""
        lock_files = [
            "/var/lib/dpkg/lock-frontend",
            "/var/lib/dpkg/lock",
            "/var/cache/apt/archives/lock"
        ]
        blockers = []
        try:
            for f in lock_files:
                if os.path.exists(f):
                    res = subprocess.run(["fuser", f], capture_output=True, text=True)
                    pids = res.stdout.strip().split()
                    for pid in pids:
                        try:
                            p = psutil.Process(int(pid))
                            blockers.append(f"{p.name()} ({pid})")
                        except:
                            blockers.append(f"PID {pid}")
        except: pass

        if not blockers and HAS_PSUTIL:
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info['name'] in ('apt', 'apt-get', 'dpkg'):
                        blockers.append(f"{proc.info['name']} ({proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
        return list(set(blockers))  # Unique list

    def _check_apt_lock(self):
        """Update UI based on APT lock status."""
        blockers = self._is_apt_locked()
        is_locked = len(blockers) > 0
        if hasattr(self, "_apt_warn_lbl"):
            if is_locked:
                self._apt_lock_frame.config(bg="#300")
                txt = "⚠️  LOCKED: " + ", ".join(blockers[:2])
                if len(blockers) > 2: txt += "..."
                self._apt_warn_lbl.config(text=txt, bg="#300", fg=ACCENT)
                if not self._apt_fix_btn.winfo_ismapped():
                    self._apt_fix_btn.pack(side="right", padx=10, pady=4)
                    self._apt_fix_btn.bind("<Button-1>", lambda e: self._fix_apt_lock())
            else:
                self._apt_lock_frame.config(bg=BG2)
                self._apt_warn_lbl.config(text="✅  APT: OK", bg=BG2, fg=DIM)
                if self._apt_fix_btn.winfo_ismapped():
                    self._apt_fix_btn.pack_forget()

    def _fix_apt_lock(self):
        """Run the fix commands provided by the user in a terminal."""
        cmd = (
            "echo '--- STARTING APT LOCK FIX ---'; "
            "echo '1. Killing apt processes...'; sudo killall apt apt-get 2>/dev/null; "
            "echo '2. Removing lock files...'; "
            "sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock; "
            "echo '3. Reconfiguring dpkg...'; sudo dpkg --configure -a; "
            "echo '4. Updating apt...'; sudo apt update; "
            "echo '--- DONE! Press Enter to close ---'; read"
        )
        try:
            # Try to find a terminal to run the fix
            terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm", "mate-terminal"]
            found = False
            for t in terminals:
                if shutil.which(t):
                    if t in ("gnome-terminal", "x-terminal-emulator"):
                        # Use -- to separate terminal args from command args
                        subprocess.Popen([t, "--", "bash", "-c", cmd])
                    else:
                        subprocess.Popen([t, "-e", f"bash -c \"{cmd}\""])
                    found = True
                    break
            if not found:
                # Last resort fallback (unlikely if found is false but worth a try)
                subprocess.Popen(["/usr/bin/x-terminal-emulator", "--", "bash", "-c", cmd])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch terminal: {e}", parent=self)


    # ── SHOW / HIDE ────────────────────────────────────────
    def _show_bubble(self):
        self._panel.pack_forget()
        self._bubble_frame.pack(padx=0, pady=0)
        S = BUBBLE_SIZE
        self.geometry(f"{S}x{S}+{self._bx}+{self._by}")
        self._blink_on = True
        self._blink_bubble()

    def _show_panel(self):
        self._bubble_frame.pack_forget()
        self._panel.pack(fill="both", expand=True)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        if self._bx > sw // 2:
            px = self._bx - PANEL_W - 4
        else:
            px = self._bx + BUBBLE_SIZE + 4
        py = max(4, min(self._by, sh - PANEL_H - 4))
        self.geometry(f"{PANEL_W}x{PANEL_H}+{px}+{py}")
        self._next_photo()

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._show_panel()
        else:
            self._show_bubble()

    def _update_network_status(self):
        global LOCAL_IP, SHARE_URL
        new_ip = get_local_ip()
        if new_ip != LOCAL_IP:
            LOCAL_IP = new_ip
            SHARE_URL = f"http://{LOCAL_IP}:{SHARE_PORT}"
            generate_qr()
            if hasattr(self, '_url_lbl'):
                self._url_lbl.config(text=SHARE_URL)
            if hasattr(self, '_qr_label') and os.path.exists(QR_PATH):
                img = load_photo(QR_PATH, 100, 100)
                if img:
                    self._qr_img = img
                    self._qr_label.config(image=self._qr_img)
        self.after(5000, self._update_network_status)

    # ── CLOCK ──────────────────────────────────────────────
    def _tick_clock(self):
        self._clk_lbl.config(text=time.strftime("%H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ── PHOTOS ─────────────────────────────────────────────
    def _next_photo(self):
        if not self._expanded:
            return
        if self._photos:
            path = self._photos[self._photo_idx % len(self._photos)]
            self._photo_idx += 1
            img = load_photo(path, PANEL_W - 16, 110)
            if img:
                self._tk_img = img
                self._photo_lbl.config(image=img, text="")
            else:
                self._photo_lbl.config(image="",
                    text="[install imagemagick for JPG support]",
                    fg=DIM, font=(FONT,7))
        else:
            self._photo_lbl.config(image="",
                text="📷  Add photos to ~/Pictures",
                fg=DIM, font=(FONT,8))
        self.after(SLIDE_SECS * 1000, self._next_photo)

    # ── STATS ──────────────────────────────────────────────
    def _update_stats(self):
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent()
            vm  = psutil.virtual_memory()
            if self._expanded:
                gpu = get_gpu_util()
                self._g_gpu.set(gpu)
                self._g_cpu.set(cpu)
                self._g_ram.set(vm.percent)
                self._lbl_ram.config(
                    text=f"{vm.used/1024**3:.1f}/{vm.total/1024**3:.1f} GB")
                try:
                    freq = psutil.cpu_freq()
                    self._lbl_freq.config(
                        text=f"{freq.current/1000:.2f} GHz")
                except: pass
                try:
                    self._g_disk.set(psutil.disk_usage("/").percent)
                except: pass
            net = psutil.net_io_counters()
            now = time.time()
            if self._net_prev:
                dt = now - self._net_prev[2]
                up = (net.bytes_sent - self._net_prev[0]) / dt
                dn = (net.bytes_recv - self._net_prev[1]) / dt
                if self._expanded:
                    self._sp_up.push(up, human(up))
                    self._sp_dn.push(dn, human(dn))
            self._net_prev = (net.bytes_sent, net.bytes_recv, now)
        
        # Also check APT lock
        if self._expanded:
            self._check_apt_lock()

        self.after(STATS_MS, self._update_stats)


# ══════════════════════════════════════════════════════════
#  Auto-start setup
# ══════════════════════════════════════════════════════════
def setup():
    script = os.path.abspath(__file__)
    d = Path.home() / ".config" / "autostart"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "bubble-hud.desktop"
    f.write_text(f"""[Desktop Entry]
Type=Application
Name=HUD
Exec=python3 {script}
Hidden=false
X-GNOME-Autostart-enabled=true
""")
    print(f"✅  Autostart created: {f}")
    print()
    print("📦  Install (once):")
    print("    pip3 install psutil qrcode[pil] --break-system-packages")
    print("    sudo apt install python3-tk imagemagick")
    print()
    print(f"📷  Photos: {PHOTO_DIR}")
    print(f"📂  Share:  {SHARE_DIR}")
    print(f"🌐  URL:    {SHARE_URL}")
    print(f"▶   Run:    python3 {script}")

if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup()
    else:
        if not HAS_PSUTIL:
            print("Missing psutil:")
            print("  pip3 install psutil --break-system-packages")
            sys.exit(1)
        BubbleHUD().mainloop()
