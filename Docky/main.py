import sys
import os
import subprocess
import psutil
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                             QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QScrollArea, QMenu, QFileDialog, QInputDialog)
from PyQt6.QtCore import Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt6.QtGui import QColor, QFont, QPixmap, QIcon, QPainter, QLinearGradient, QBrush, QPen, QAction

# ══════════════════════════════════════════════════════════
#  CONFIG & CONSTANTS
# ══════════════════════════════════════════════════════════
BUBBLY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKY_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(DOCKY_DIR, "logo.png")
CONFIG_PATH = os.path.join(DOCKY_DIR, "config.json")

DEFAULT_CONFIG = {
    "Locky": {
        "entry": "main.py", # Direct entry is better for tracking
        "icon": os.path.join(BUBBLY_DIR, "Locky", "spiderlogo.png"),
        "name": "Locky Focus"
    },
    "deadpool-hud": {
        "entry": "desktop_dashboard.py",
        "icon": os.path.join(BUBBLY_DIR, "deadpool-hud", "deadpool_logo.png"),
        "name": "Deadpool HUD"
    }
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except: pass
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

# ══════════════════════════════════════════════════════════
#  UI UTILS
# ══════════════════════════════════════════════════════════

class AppButton(QFrame):
    def __init__(self, app_id, config, controller, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self.config = config
        self.running = False
        
        self.setFixedSize(64, 64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(config.get("name", app_id))
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_path = config.get("icon")
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            txt = config.get("name", app_id)[0].upper()
            self.icon_label.setText(txt)
            self.icon_label.setStyleSheet("color: #E62429; font-size: 20px; font-weight: bold;")
            
        self.layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.status_indicator = QFrame(self)
        self.status_indicator.setFixedSize(10, 10)
        self.status_indicator.move(48, 4)
        self.update_status(False)
        
        self.setStyleSheet("""
            QFrame { background: rgba(255, 255, 255, 0.05); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); }
        """)

    def update_status(self, running):
        self.running = running
        color = "#00ff7f" if running else "#ff3c41"
        self.status_indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: 1.5px solid rgba(0,0,0,0.7);")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10 if running else 4); shadow.setColor(QColor(color)); shadow.setOffset(0, 0)
        self.status_indicator.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        self.setStyleSheet("QFrame { background: rgba(255, 255, 255, 0.12); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.3); }")
        
    def leaveEvent(self, event):
        self.setStyleSheet("QFrame { background: rgba(255, 255, 255, 0.05); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); }")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Immediate toggle on single click
            self.window().toggle_app(self.app_id)
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def show_context_menu(self, pos):
        main_window = self.window()
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #111; color: white; border: 1px solid #333; border-radius: 10px; padding: 5px; }"
                           "QMenu::item { padding: 8px 25px; border-radius: 5px; }"
                           "QMenu::item:selected { background-color: #E62429; }")
        
        restart_action = QAction("🔄 Restart", self)
        restart_action.triggered.connect(lambda: main_window.restart_app(self.app_id))
        
        stop_action = QAction("🛑 Stop", self)
        stop_action.triggered.connect(lambda: main_window.stop_app(self.app_id))
        
        menu.addAction(restart_action)
        menu.addAction(stop_action)
        menu.exec(pos)

# ══════════════════════════════════════════════════════════
#  MAIN DOCK WINDOW
# ══════════════════════════════════════════════════════════

class Docky(QWidget):
    def __init__(self):
        super().__init__()
        self.app_configs = load_config()
        self.app_widgets = {}
        self.init_ui()
        self.init_monitor()
        
    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.container = QFrame()
        self.container.setObjectName("dockContainer")
        self.container.setStyleSheet("#dockContainer { background: rgba(10, 10, 10, 0.95); border-radius: 25px; border: 1.5px solid rgba(230, 36, 41, 0.6); }")
        
        self.inner_layout = QHBoxLayout(self.container)
        self.inner_layout.setContentsMargins(12, 8, 12, 8)
        self.inner_layout.setSpacing(10)
        
        self.apps_container = QWidget()
        self.apps_layout = QHBoxLayout(self.apps_container)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(8)
        self.inner_layout.addWidget(self.apps_container)
        
        self.refresh_app_buttons()
        
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(36, 36)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet("QPushButton { background: rgba(230, 36, 41, 0.1); color: #E62429; border-radius: 18px; font-size: 20px; font-weight: bold; border: 1px solid rgba(230, 36, 41, 0.3); }"
                                   "QPushButton:hover { background: #E62429; color: white; }")
        self.add_btn.clicked.connect(self.add_custom_app)
        self.inner_layout.addWidget(self.add_btn)
        
        self.main_layout.addWidget(self.container)
        self.update_geometry()

    def update_geometry(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = 40 + (len(self.app_configs) * 72) + 60
        self.setFixedWidth(width)
        self.setFixedHeight(85)
        self.move((screen.width() - self.width()) // 2, screen.height() - 105)

    def refresh_app_buttons(self):
        for widget in self.app_widgets.values(): widget.setParent(None); widget.deleteLater()
        self.app_widgets.clear()
        for app_id, config in self.app_configs.items():
            btn = AppButton(app_id, config, self)
            self.app_widgets[app_id] = btn
            self.apps_layout.addWidget(btn)
        self.update_geometry()

    def init_monitor(self):
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_app_status)
        self.monitor_timer.start(800)

    def update_app_status(self):
        for app_id, config in self.app_configs.items():
            path = config.get("path", os.path.join(BUBBLY_DIR, app_id))
            is_running = False
            for proc in psutil.process_iter(['cwd', 'cmdline']):
                try:
                    cmd = proc.info.get('cmdline')
                    cwd = proc.info.get('cwd')
                    
                    if cmd:
                        cmd_str = " ".join(cmd)
                        # Avoid matching Docky's own processes checking other apps
                        if "Docky" in cmd_str and app_id != "Docky":
                            continue
                            
                        # If the process's working directory is the app's path, or the command contains the app's path
                        if (cwd and cwd == path) or (path in cmd_str) or (app_id in cmd_str):
                            is_running = True
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
            
            if app_id in self.app_widgets:
                self.app_widgets[app_id].update_status(is_running)

    def toggle_app(self, app_id):
        # Debounce to prevent rapid start/stop (500ms cooldown)
        if hasattr(self, "_last_toggle") and (psutil.time.time() - self._last_toggle) < 0.5: return
        self._last_toggle = psutil.time.time()

        if self.app_widgets[app_id].running:
            self.stop_app(app_id)
        else:
            self.start_app(app_id)

    def start_app(self, app_id):
        config = self.app_configs[app_id]
        path = config.get("path", os.path.join(BUBBLY_DIR, app_id))
        # Use start.sh if it exists for Locky/etc, but track by main.py
        entry = config.get("entry")
        
        exec_file = os.path.join(path, "start.sh") if os.path.exists(os.path.join(path, "start.sh")) else os.path.join(path, entry)
        
        try:
            env = os.environ.copy()
            env["QT_QPA_PLATFORM"] = "xcb"
            if os.path.exists(os.path.join(path, "libs")): env["PYTHONPATH"] = os.path.join(path, "libs")
            
            if exec_file.endswith(".sh"):
                subprocess.Popen(["bash", exec_file], cwd=path, env=env, start_new_session=True)
            else:
                py = os.path.join(path, "venv", "bin", "python3") if os.path.exists(os.path.join(path, "venv", "bin", "python3")) else "python3"
                subprocess.Popen([py, exec_file], cwd=path, env=env, start_new_session=True)
        except Exception as e: print(f"[!] Error: {e}")

    def stop_app(self, app_id):
        config = self.app_configs[app_id]
        path = config.get("path", os.path.join(BUBBLY_DIR, app_id))
        for proc in psutil.process_iter(['cwd', 'cmdline']):
            try:
                cmd = proc.info.get('cmdline')
                cwd = proc.info.get('cwd')
                if cmd:
                    cmd_str = " ".join(cmd)
                    if "Docky" in cmd_str and app_id != "Docky":
                        continue
                    if (cwd and cwd == path) or (path in cmd_str) or (app_id in cmd_str):
                        proc.terminate()
            except: continue

    def restart_app(self, app_id):
        self.stop_app(app_id); QTimer.singleShot(1000, lambda: self.start_app(app_id))

    def add_custom_app(self):
        folder = QFileDialog.getExistingDirectory(self, "Select App", BUBBLY_DIR)
        if not folder: return
        app_name = os.path.basename(folder)
        entry = next((e for e in ["main.py", "desktop_dashboard.py", "run.sh"] if os.path.exists(os.path.join(folder, e))), "main.py")
        self.app_configs[app_name] = {"entry": entry, "path": folder, "icon": "", "name": app_name}
        save_config(self.app_configs); self.refresh_app_buttons()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_offset'): self.move(event.globalPosition().toPoint() - self._drag_offset)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dock = Docky(); dock.show()
    sys.exit(app.exec())
