# Sharp Filter Selector

Controles SGSR, FSR y NIS para **Decky Loader** en SteamOS y Ubuntu/UGM.
Utiliza el Gamescope activo; no lo instala ni lo sustituye.

**[English](README.md)** · [Descargar](https://github.com/N3ruk/Sharp-Filter-Selector/releases/latest) · [Historial](CHANGELOG.md)

## Requisitos

- Decky Loader y una sesión gaming real de Gamescope/Xwayland.
- El comando `xprop` del sistema.
- Un juego renderizado por debajo de la resolución de salida para apreciar el filtro.
- Gamescope **activo** compatible con SGSR para usar SGSR y el override FSR separado.

## Instalación

Descarga el ZIP y su `.sha256` desde [Releases](https://github.com/N3ruk/Sharp-Filter-Selector/releases/latest) y ejecuta:

```bash
sha256sum -c sharp-filter-selector-v1.2.0.zip.sha256
unzip sharp-filter-selector-v1.2.0.zip
cd sharp-filter-selector
./install.sh
```

El instalador actualiza `~/homebrew/plugins/sharp-filter-selector`.
Recarga el plugin desde Decky o reinicia Steam/Gaming para cargarlo.
Se conservan las selecciones guardadas. Para desinstalar: `./uninstall.sh`.

## Uso

Con un juego abierto, entra en **QAM → Decky → Sharp Filter Selector**.

| Selección | Resultado |
| --- | --- |
| Ambos overrides apagados | Nitidez del QAM usa SGSR si es compatible; si no, FSR nativo |
| **Use NIS** activado | NVIDIA Image Scaling |
| **Use FSR** activado | AMD FSR explícito en lugar de SGSR |
| **Sharpness** 0–5 | Nitidez compartida para NIS o FSR explícitos |

Solo un override puede estar activado. Para usar SGSR, apaga ambos y selecciona
**Nitidez** en el QAM de Steam. En SteamOS el puente actúa periódicamente
(~750 ms más la respuesta X11); no es una modificación atómica de Gamescope.
El QAM conserva su modo de escalado en Ubuntu y SteamOS moderno compatible con SGSR.

## Si falta alguna opción

- **Esperando Gamescope:** entra en una sesión Gaming real. Escritorio/Big Picture
  por sí solos no demuestran que Gamescope esté activo.
- **FSR oculto:** puede faltar soporte SGSR en el Gamescope activo, fallar la
  detección o existir entrada HDR del juego. Consulta el estado SGSR del plugin.
- **HDR:** con entrada HDR, Gamescope aplica su fallback FSR. Una pantalla en HDR
  con un juego SDR no oculta por sí sola el override FSR.
- **No cambia la imagen:** reduce la resolución del juego por debajo de la pantalla.

## Documentación

- [Compatibilidad, cambios 1.1.0 → 1.2.0 y validación](docs/COMPATIBILITY.md#español)
- [Estructura, compilación, pruebas y paquetes](docs/DEVELOPMENT.md#español)
- [Historial de versiones](CHANGELOG.md)

El ZIP de instalación contiene el plugin, instalador y documentación de uso.
Las fuentes completas del frontend, configuración de build y pruebas están en el repositorio.

## Licencia

[BSD-3-Clause](LICENSE). Proyecto independiente, sin afiliación con Valve, AMD ni NVIDIA.
