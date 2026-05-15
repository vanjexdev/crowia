'use strict';
import { AudioRecorder, AudioPlayer } from './audio.js';

class GiseloApp {
  constructor() {
    this._ws = null;
    this._recorder = new AudioRecorder();
    this._player = new AudioPlayer();
    this._currentView = 'chat';
    this._assistantBubble = null;
    this._ttsEnabled = true;
    this._backend = 'claude';
    this._reconnectDelay = 1000;
    this._snackTimer = null;
  }

  // ── Init ────────────────────────────────────────────────────────────────
  async init() {
    this._bindNav();
    this._bindChat();
    this._bindSettings();
    this._connect();
    this._registerSW();
    await this._loadStatus();
  }

  async _loadStatus() {
    try {
      const r = await fetch('/api/status');
      const d = await r.json();
      this._backend = d.backend;
      this._ttsEnabled = d.tts;
      this._updateBackendChip(d.backend);
      this._syncSettingsUI();
    } catch (_) {}
  }

  // ── WebSocket ───────────────────────────────────────────────────────────
  _connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    this._ws = new WebSocket(`${proto}//${location.host}/ws`);
    this._ws.binaryType = 'arraybuffer';

    this._ws.onopen = () => {
      this._reconnectDelay = 1000;
      this._setStatus('idle', 'Conectado');
    };

    this._ws.onmessage = e => this._onMessage(e);

    this._ws.onclose = () => {
      this._setStatus('error', 'Reconectando…');
      setTimeout(() => {
        this._reconnectDelay = Math.min(this._reconnectDelay * 2, 10000);
        this._connect();
      }, this._reconnectDelay);
    };
  }

  _send(obj) {
    if (this._ws.readyState === WebSocket.OPEN) this._ws.send(JSON.stringify(obj));
  }

  _sendBinary(blob) {
    if (this._ws.readyState === WebSocket.OPEN) this._ws.send(blob);
  }

  _onMessage(e) {
    if (e.data instanceof ArrayBuffer) {
      if (this._ttsEnabled) this._player.playWav(e.data.slice(0));
      return;
    }
    const msg = JSON.parse(e.data);
    switch (msg.type) {
      case 'status':
        this._setStatus('processing', msg.message);
        break;
      case 'transcript':
        this._addBubble('user', msg.content);
        break;
      case 'chunk':
        this._appendAssistant(msg.content);
        break;
      case 'done':
        this._finalizeAssistant(msg.content);
        this._setStatus('idle', 'Listo');
        break;
      case 'audio_start':
        break;
      case 'audio_end':
        break;
      case 'error':
        this._setStatus('idle', msg.message);
        this._snack(msg.message);
        break;
      case 'backend':
        this._backend = msg.name;
        this._updateBackendChip(msg.name);
        break;
    }
  }

  // ── Navigation ──────────────────────────────────────────────────────────
  _bindNav() {
    document.querySelectorAll('[data-view]').forEach(btn => {
      btn.addEventListener('click', () => this._switchView(btn.dataset.view));
    });
  }

  _switchView(view) {
    this._currentView = view;
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${view}`)?.classList.add('active');
    document.querySelectorAll('[data-view]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === view);
    });
    if (view === 'history') this._renderHistory();
  }

  // ── Chat ────────────────────────────────────────────────────────────────
  _bindChat() {
    const input = document.getElementById('text-input');
    const sendBtn = document.getElementById('btn-send');
    const micBtn = document.getElementById('btn-mic');
    const micFab = document.getElementById('btn-mic-fab');
    const clearBtn = document.getElementById('btn-clear');

    const submit = () => {
      const text = input.value.trim();
      if (!text) return;
      this._player.unlock();
      this._addBubble('user', text);
      this._send({ type: 'text', content: text });
      this._setStatus('processing', `Preguntando a ${this._backend}…`);
      input.value = '';
      input.style.height = '';
    };

    sendBtn.addEventListener('click', submit);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    input.addEventListener('input', () => {
      input.style.height = '';
      input.style.height = Math.min(input.scrollHeight, 160) + 'px';
    });

    const toggleMic = () => this._toggleRecording();
    if (micBtn) micBtn.addEventListener('click', toggleMic);
    if (micFab) micFab.addEventListener('click', toggleMic);
    if (clearBtn) clearBtn.addEventListener('click', () => {
      this._send({ type: 'clear_history' });
      document.getElementById('messages').innerHTML = '';
      this._snack('Historial borrado');
    });
  }

  async _toggleRecording() {
    const micBtn = document.getElementById('btn-mic');
    const micFab = document.getElementById('btn-mic-fab');

    if (!this._recorder.active) {
      try {
        this._player.unlock();
        await this._recorder.start();
        this._send({ type: 'voice_start' });
        this._setStatus('recording', 'Grabando… (toca para detener)');
        [micBtn, micFab].forEach(b => b?.classList.add('recording'));
      } catch (e) {
        this._snack('No se pudo acceder al micrófono: ' + e.message);
      }
    } else {
      [micBtn, micFab].forEach(b => b?.classList.remove('recording'));
      const blob = await this._recorder.stop();
      this._setStatus('processing', 'Enviando audio…');
      if (blob) this._sendBinary(blob);
      this._send({ type: 'voice_end' });
    }
  }

  // ── Bubbles ─────────────────────────────────────────────────────────────
  _addBubble(role, text) {
    const messages = document.getElementById('messages');
    const row = document.createElement('div');
    row.className = `bubble-row ${role}`;

    if (role === 'assistant') {
      const avatar = document.createElement('div');
      avatar.className = 'bubble-avatar';
      avatar.textContent = 'G';
      row.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    row.appendChild(bubble);

    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;

    if (role === 'assistant') this._assistantBubble = bubble;
    return bubble;
  }

  _appendAssistant(chunk) {
    if (!this._assistantBubble) {
      this._addBubble('assistant', '');
      this._assistantBubble.classList.add('streaming');
    }
    this._assistantBubble.textContent += chunk;
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
  }

  _finalizeAssistant(full) {
    if (this._assistantBubble) {
      this._assistantBubble.textContent = full;
      this._assistantBubble.classList.remove('streaming');
      this._assistantBubble = null;
    } else {
      this._addBubble('assistant', full);
    }
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
  }

  // ── History view ────────────────────────────────────────────────────────
  async _renderHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    try {
      const r = await fetch('/api/history');
      const d = await r.json();
      if (!d.messages?.length) {
        list.innerHTML = '<div class="empty-state"><span class="material-symbols-rounded">history</span>Sin historial</div>';
        return;
      }
      d.messages.forEach(m => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
          <div class="history-role ${m.role}">${m.role === 'user' ? 'Tú' : 'Giselo'}</div>
          <div class="history-content">${this._esc(m.content)}</div>
        `;
        list.appendChild(item);
      });
    } catch (e) {
      list.innerHTML = '<div class="empty-state">Error cargando historial</div>';
    }
  }

  // ── Settings ────────────────────────────────────────────────────────────
  _bindSettings() {
    document.getElementById('toggle-tts')?.addEventListener('change', e => {
      this._ttsEnabled = e.target.checked;
    });

    document.querySelectorAll('.backend-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this._send({ type: 'switch_backend', backend: btn.dataset.backend });
        document.querySelectorAll('.backend-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  }

  _syncSettingsUI() {
    const toggle = document.getElementById('toggle-tts');
    if (toggle) toggle.checked = this._ttsEnabled;
    document.querySelectorAll('.backend-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.backend === this._backend);
    });
  }

  // ── Status bar ──────────────────────────────────────────────────────────
  _setStatus(state, msg) {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    const bar = document.getElementById('status-bar');
    if (!dot || !text) return;
    dot.className = `status-dot ${state}`;
    text.textContent = msg;
    bar.classList.toggle('hidden', state === 'idle');
  }

  _updateBackendChip(name) {
    const chip = document.getElementById('backend-name');
    if (chip) chip.textContent = name;
  }

  // ── Snackbar ────────────────────────────────────────────────────────────
  _snack(msg) {
    const sb = document.getElementById('snackbar');
    if (!sb) return;
    sb.textContent = msg;
    sb.classList.add('show');
    clearTimeout(this._snackTimer);
    this._snackTimer = setTimeout(() => sb.classList.remove('show'), 3000);
  }

  // ── Service Worker ──────────────────────────────────────────────────────
  async _registerSW() {
    if ('serviceWorker' in navigator) {
      try {
        await navigator.serviceWorker.register('/sw.js');
      } catch (_) {}
    }
  }

  // ── Util ────────────────────────────────────────────────────────────────
  _esc(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
}

const app = new GiseloApp();
app.init();
