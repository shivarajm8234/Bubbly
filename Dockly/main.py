import sys
import os
import subprocess
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QRect, QPropertyAnimation
from PyQt6.QtGui import QColor, QFont, QCursor, QPixmap

_DIR = os.path.dirname(os.path.abspath(__file__))
# Check for a local dockly_logo.png
LOGO_PATH = os.path.join(_DIR, "dockly_logo.png")

class ContainerItem(QFrame):
    def __init__(self, cid, image_name, name, state, status, parent=None):
        super().__init__(parent)
        self.cid = cid
        self.image_name = image_name
        self.name = name
        self.state = state  # 'running', 'exited', etc.
        self.parent_ui = parent

        self.setFixedHeight(70)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QFrame:hover { background-color: rgba(255, 255, 255, 0.08); }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Info side
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel(self.image_name)
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: none;")
        
        sub = QLabel(f"{self.name} | {status}")
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; border: none;")
        
        info_layout.addWidget(title)
        info_layout.addWidget(sub)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Action button
        self.toggle_btn = QPushButton("ON" if self.state == "running" else "OFF")
        self.toggle_btn.setFixedSize(60, 30)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn_style()
        self.toggle_btn.clicked.connect(self.toggle_container)
        
        layout.addWidget(self.toggle_btn)

    def update_btn_style(self):
        if self.state == "running":
            self.toggle_btn.setText("STOP")
            self.toggle_btn.setStyleSheet("""
                QPushButton { background-color: #E62429; color: white; border-radius: 15px; font-weight: bold; border: none; }
                QPushButton:hover { background-color: #ff3c41; }
            """)
        else:
            self.toggle_btn.setText("START")
            self.toggle_btn.setStyleSheet("""
                QPushButton { background-color: #222; color: #00ff7f; border-radius: 15px; font-weight: bold; border: 1px solid #00ff7f; }
                QPushButton:hover { background-color: #333; }
            """)

    def toggle_container(self):
        self.toggle_btn.setText("...")
        QApplication.processEvents()
        if self.state == "running":
            subprocess.run(["docker", "stop", self.cid], capture_output=True)
        else:
            subprocess.run(["docker", "start", self.cid], capture_output=True)
        # Notify parent to refresh
        if self.parent_ui and hasattr(self.parent_ui, 'load_containers'):
            QTimer.singleShot(500, self.parent_ui.load_containers)

class DocklyDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_containers()
        
        # Auto refresh check
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_containers)
        self.refresh_timer.start(5000)

    def init_ui(self):
        self.setFixedSize(400, 600)
        # Window stickiness across workspaces
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a1a, stop:1 #0a0a0a);
                border-radius: 30px;
                border: 2px solid #00bbff;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 187, 255, 100))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(LOGO_PATH):
            pixmap = QPixmap(LOGO_PATH).scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo.setPixmap(pixmap)
        else:
            self.logo.setText("🐳")
            self.logo.setStyleSheet("color: #00bbff; font-size: 36px; border: none; background: transparent;")
        
        header.addWidget(self.logo)
        
        title_box = QVBoxLayout()
        title = QLabel("DOCKLY")
        title.setStyleSheet("color: #00bbff; font-size: 20px; font-weight: 1000; letter-spacing: 2px; border: none; background: transparent;")
        sub = QLabel("CONTAINER MANAGER")
        sub.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 10px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.addLayout(title_box)
        
        header.addStretch()
        
        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.5); font-size: 24px; font-weight: bold; border: none; border-radius: 15px;}
            QPushButton:hover { background: rgba(255,255,255,0.1); color: white; }
        """)
        self.close_btn.clicked.connect(self.close)
        header.addWidget(self.close_btn)
        
        layout.addLayout(header)
        
        # Separator
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet("background: rgba(0, 187, 255, 0.3); border: none;")
        layout.addWidget(sep)
        
        # Scroll Area for containers
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: rgba(0,0,0,0.2); width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: rgba(0,187,255,0.5); border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
        """)
        
        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 5, 0, 5)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll)
        
        # Bottom controls
        refresh_btn = QPushButton("↻ REFRESH LIST")
        refresh_btn.setFixedHeight(40)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton { background: rgba(0, 187, 255, 0.1); color: #00bbff; border: 1px solid rgba(0,187,255,0.3); border-radius: 20px; font-weight: bold; }
            QPushButton:hover { background: rgba(0, 187, 255, 0.3); }
        """)
        refresh_btn.clicked.connect(self.load_containers)
        layout.addWidget(refresh_btn)
        
        self.main_layout.addWidget(self.container)
        
        # Center on screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def load_containers(self):
        # Clear existing
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        try:
            result = subprocess.run(["docker", "ps", "-a", "--format", "{{.ID}}|{{.Image}}|{{.Names}}|{{.State}}|{{.Status}}"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if not lines or lines[0] == '':
                    empty = QLabel("No Docker containers found.\nUse 'docker run' to create some!")
                    empty.setStyleSheet("color: rgba(255,255,255,0.5); font-style: italic; border: none; background: transparent;")
                    empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.list_layout.addWidget(empty)
                else:
                    for line in lines:
                        parts = line.split('|')
                        if len(parts) >= 5:
                            cid, image, name, state, status = parts[:5]
                            item = ContainerItem(cid, image, name, state, status, self)
                            self.list_layout.addWidget(item)
            else:
                QLabel("Docker error or not running", self.list_widget)
        except Exception as e:
            err = QLabel(f"Error fetching docker: {e}")
            err.setStyleSheet("color: red; border: none;")
            self.list_layout.addWidget(err)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and self._drag_pos is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

if __name__ == "__main__":
    if not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = DocklyDashboard()
    window.show()
    sys.exit(app.exec())
