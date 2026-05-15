# Bugs Pendientes — fix/second-round

## ✓ Ya Arreglados (commit 543f622)
- ✓ Deadlock pipeline_lock
- ✓ Race history lock
- ✓ TTS state sync
- ✓ Media false positives
- ✓ Persona identity

---

## ✗ Bugs Abiertos (3)

### 1. Hardcoded home path
**Ubicación**: `crowia/backends/claude_cli.py:76`
**Problema**: `--add-dir /home/jesusu` hardcodeado. Rompe en otros usuarios.
**Plan**:
```python
# Reemplazar línea 76:
"--add-dir", "/home/jesusu",
# Por:
"--add-dir", str(pathlib.Path.home()),
```
**Nota**: Línea 77 ya lo hace correctamente con `str(pathlib.Path.home())`

---

### 2. Exception silenciosa en file picker
**Ubicación**: `crowia/ui.py:187-188`
**Problema**: `except Exception: pass` sin log. Si falla giselo-pick, usuario no sabe.
**Plan**:
```python
# Reemplazar:
            except Exception:
                pass

# Por:
            except Exception as e:
                log.error("File picker error: %s", e)
```

---

### 3. Qt signal emit desde thread daemon
**Ubicación**: `crowia/ui.py:186`
**Problema**: `self._file_ready.emit()` corre en thread daemon (línea 189). En PyQt6+Wayland, emitir signals desde threads no-main causa undefined behavior o crashes.
**Plan**:
```python
# Reemplazar:
                    self._file_ready.emit(result.stdout.strip())

# Por:
                    # Queue a safe emit call to main thread
                    Qt.QMetaObject.invokeMethod(
                        self, "_on_file_ready", Qt.ConnectionType.QueuedConnection,
                        Qt.Q_ARG(str, result.stdout.strip())
                    )

# Agregar método:
    def _on_file_ready(self, path: str):
        self._file_ready.emit(path)
```

---

## Estado: always_on.py

**Validado**: `self._active` no tiene race. Solo tocado por `_processor()` thread. Comentario línea 48 es correcto.

---

## Prioridad de Arreglo

1. **Hardcoded path** — bloqueante en producción
2. **Exception silenciosa** — debugging imposible
3. **Qt emit desde thread** — race potencial en UI
