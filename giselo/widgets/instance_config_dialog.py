import io
import pathlib

import yaml
from ruamel.yaml import YAML

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QDialogButtonBox)
from PyQt6.QtCore import Qt

_CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config.yaml"

_STYLE = """
QDialog {
    background: #0a1628;
    color: #cfd6e6;
}
QLabel {
    color: #cfd6e6;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
QLineEdit {
    background: #0f1e35;
    color: #cfd6e6;
    border: 1px solid rgba(93,107,133,0.4);
    border-radius: 4px;
    padding: 4px 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
QLineEdit:focus {
    border-color: #88c93a;
}
QPushButton {
    background: transparent;
    color: #cfd6e6;
    border: 1px solid rgba(93,107,133,0.4);
    border-radius: 4px;
    padding: 4px 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
QPushButton:hover {
    border-color: #88c93a;
    color: #88c93a;
}
QPushButton#accept-btn {
    border-color: #88c93a;
    color: #88c93a;
}
QPushButton#accept-btn:hover {
    background: rgba(136,201,58,0.12);
}
"""


class InstanceConfigDialog(QDialog):
    def __init__(self, instance_name: str, parent=None):
        super().__init__(parent)
        self._instance_name = instance_name
        self.setWindowTitle(f"Configurar: {instance_name}")
        self.setMinimumWidth(460)
        self.setStyleSheet(_STYLE)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Dialog)

        existing = self._load_existing()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"⚙  Instancia: {instance_name}")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #88c93a; margin-bottom: 4px;")
        layout.addWidget(title)

        # api_key row
        layout.addWidget(QLabel("API Key"))
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self._key_edit = QLineEdit(existing.get("api_key", ""))
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("dejar vacío = usar global")
        key_row.addWidget(self._key_edit)
        self._show_btn = QPushButton("Mostrar")
        self._show_btn.setFixedWidth(68)
        self._show_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._show_btn)
        layout.addLayout(key_row)

        # model
        layout.addWidget(QLabel("Modelo"))
        self._model_edit = QLineEdit(existing.get("model", ""))
        self._model_edit.setPlaceholderText("dejar vacío = usar global")
        layout.addWidget(self._model_edit)

        # base_url
        layout.addWidget(QLabel("Base URL"))
        self._url_edit = QLineEdit(existing.get("base_url", ""))
        self._url_edit.setPlaceholderText("ej: https://openrouter.ai/api/v1")
        layout.addWidget(self._url_edit)

        # notes
        layout.addWidget(QLabel("Notas"))
        self._notes_edit = QLineEdit(existing.get("notes", ""))
        self._notes_edit.setPlaceholderText("opcional")
        layout.addWidget(self._notes_edit)

        layout.addSpacing(8)

        # buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("accept-btn")
        save_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _toggle_key_visibility(self) -> None:
        if self._key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("Ocultar")
        else:
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("Mostrar")

    def _load_existing(self) -> dict:
        try:
            cfg = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
            return cfg.get("instances", {}).get("config", {}).get(self._instance_name, {}) or {}
        except Exception:
            return {}

    def _on_accept(self) -> None:
        data = {}
        api_key = self._key_edit.text().strip()
        model = self._model_edit.text().strip()
        base_url = self._url_edit.text().strip()
        notes = self._notes_edit.text().strip()
        if api_key:
            data["api_key"] = api_key
        if model:
            data["model"] = model
        if base_url:
            data["base_url"] = base_url
        if notes:
            data["notes"] = notes

        try:
            _yaml = YAML()
            _yaml.preserve_quotes = True
            cfg = _yaml.load(_CONFIG_PATH.read_text(encoding="utf-8"))
            instances = cfg.setdefault("instances", {})
            config_block = instances.setdefault("config", {})
            if data:
                config_block[self._instance_name] = data
            else:
                config_block.pop(self._instance_name, None)
            buf = io.StringIO()
            _yaml.dump(cfg, buf)
            _CONFIG_PATH.write_text(buf.getvalue(), encoding="utf-8")
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {exc}")
            return

        self.accept()
