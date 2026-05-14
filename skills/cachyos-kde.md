# Skill: CachyOS + KDE Plasma 6

El usuario usa CachyOS (Arch Linux derivado) con KDE Plasma 6 en Wayland. Teclado: Epomaker F75.

## Gestión de paquetes

- **Instalar**: `paru -S paquete` (AUR+repos) o `sudo pacman -S paquete` (solo repos oficiales)
- **Actualizar sistema**: `paru -Syu` o `sudo pacman -Syu`
- **Buscar**: `paru -Ss término` o `pacman -Ss término`
- **Eliminar**: `sudo pacman -Rns paquete` (elimina con dependencias huérfanas)
- **Info de paquete**: `pacman -Qi paquete` (instalado) / `pacman -Si paquete` (repos)
- **Archivos de paquete**: `pacman -Ql paquete`
- **Qué paquete tiene un archivo**: `pacman -Qo /ruta/al/archivo`
- **Paquetes instalados manualmente**: `pacman -Qe`
- **AUR helper**: `paru` (preferido sobre `yay`)
- **Config pacman**: `/etc/pacman.conf`
- **Repos CachyOS**: cachyos, cachyos-v3, cachyos-extra-v3 (paquetes optimizados x86-64-v3)

## Kernel y sistema

- **Kernel activo**: `uname -r` — normalmente `linux-cachyos` (BORE scheduler)
- **Kernels instalados**: `pacman -Qs linux`
- **Ver logs del sistema**: `journalctl -xe` / `journalctl -u servicio -f` (follow)
- **Logs de arranque**: `journalctl -b` (actual) / `journalctl -b -1` (anterior)
- **Servicios**: `systemctl status servicio` / `systemctl start|stop|restart|enable|disable servicio`
- **Servicios usuario**: `systemctl --user status servicio`
- **Hardware**: `lscpu`, `lsmem`, `lsblk`, `lsusb`, `lspci`
- **GPU**: `glxinfo | grep renderer` o `vulkaninfo | grep deviceName`
- **Temperatura/sensores**: `sensors` (paquete `lm_sensors`)
- **Uso de recursos**: `btop` o `htop`
- **Espacio en disco**: `df -h` / `du -sh directorio`

## KDE Plasma 6

- **Reiniciar Plasma**: `kquitapp6 plasmashell && kstart plasmashell`
- **Reiniciar KWin**: `kwin_wayland --replace &`
- **Configuración KDE**: `systemsettings6`
- **KRunner (lanzador)**: Alt+F2 o Alt+Space
- **Config de pantalla**: `kscreen-doctor -o` (listar) / System Settings → Display
- **Widgets**: clic derecho en escritorio → Editar modo
- **Temas**: `lookandfeeltool -l` (listar) / `lookandfeeltool -a tema`
- **Archivos de config KDE**: `~/.config/` (kwinrc, plasma-org.kde.plasma.desktop-appletsrc, etc.)
- **Compositor**: KWin con Wayland, efectos en System Settings → Display & Monitor → Compositor
- **Virtual desktops**: configurables en System Settings → Window Management

## Wayland

- **Display**: `WAYLAND_DISPLAY=wayland-0` (variable de entorno)
- **Socket**: `/run/user/UID/wayland-0`
- **XDG portals**: `xdg-desktop-portal-kde` (capturas, file picker, etc.)
- **Forzar Wayland en apps Qt**: `QT_QPA_PLATFORM=wayland`
- **Forzar Wayland en Firefox**: `MOZ_ENABLE_WAYLAND=1`
- **Apps que no soportan Wayland**: correr con `DISPLAY=:0 app` (XWayland)
- **Info sesión Wayland**: `loginctl show-session`
- **Clipboard en Wayland**: `wl-copy` / `wl-paste` (paquete `wl-clipboard`)

## Audio

- **Sistema**: PipeWire + WirePlumber
- **Mixer**: `pavucontrol` o System Settings → Audio
- **CLI audio**: `pactl` (cambiar volumen, fuentes, sumideros)
- **Ver dispositivos**: `pactl list sinks` / `pactl list sources`
- **Ver estado PipeWire**: `wpctl status`
- **Reiniciar audio**: `systemctl --user restart pipewire pipewire-pulse wireplumber`
- **Volumen**: `pactl set-sink-volume @DEFAULT_SINK@ 50%` / `+5%` / `-5%`
- **Mute**: `pactl set-sink-mute @DEFAULT_SINK@ toggle`

## Red

- **Gestor**: NetworkManager
- **CLI**: `nmcli device status` / `nmcli connection show` / `nmcli connection up NOMBRE`
- **WiFi**: `nmcli device wifi list` / `nmcli device wifi connect SSID password PASS`
- **IP**: `ip addr` / `ip route`
- **DNS**: `resolvectl status`
- **Firewall**: `ufw status` o `firewall-cmd --state`

## Aplicaciones comunes

| Propósito | App | Comando |
|-----------|-----|---------|
| Terminal | Alacritty | `alacritty` |
| Editor código | Zed | `zeditor` |
| Navegador | Firefox | `firefox` |
| Archivos | Dolphin | `dolphin` |
| Captura pantalla | Spectacle | `spectacle` |
| Texto | Kate / KWrite | `kate` / `kwrite` |
| Imagen | Gwenview | `gwenview` |
| Monitor sistema | KSysGuard | `ksysguard` |
| Ofimática | LibreOffice | `libreoffice` |
| Docker | Docker / Podman | `docker` / `podman` |

## Rutas importantes

- **Config usuario**: `~/.config/`
- **Apps locales**: `~/.local/share/applications/`
- **Binarios locales**: `~/.local/bin/`
- **Autostart**: `~/.config/autostart/`
- **Config sistema**: `/etc/`
- **Logs sistema**: `/var/log/`
- **Paquetes caché**: `/var/cache/pacman/pkg/`
- **AUR builds**: `~/.cache/paru/`

## Tips CachyOS-específicos

- CachyOS usa paquetes compilados para x86-64-v3 (AVX2) — más rápidos que Arch vanilla
- `cachyos-hello` — app de bienvenida/herramientas del sistema
- `cachyos-rate-mirrors` — seleccionar mirrors más rápidos
- Para problemas de paquetes: `sudo pacman -Syuu` (downgrade si hay conflictos)
- CachyOS-Settings: herramientas adicionales del sistema
- El kernel `linux-cachyos` usa BORE scheduler (mejor para desktop/gaming)
