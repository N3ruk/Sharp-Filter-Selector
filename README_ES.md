# Sharp Filter Selector — SGSR / FSR / NIS para Decky Loader

**Sharp Filter Selector** es un plugin de Decky Loader que controla el filtro
Sharp de Gamescope desde el menú de acceso rápido. En versiones recientes de
Gamescope conserva **SGSR** como ruta Sharp nativa y ofrece overrides explícitos
para **AMD FSR** y **NVIDIA NIS**.

[English documentation](README.md)

## Características

- Detecta soporte SGSR en el proceso Gamescope propietario de la sesión
  Xwayland activa.
- Conserva el comportamiento Sharp nativo: SGSR para entrada SDR y fallback FSR
  de Gamescope para entrada HDR.
- Ofrece overrides explícitos **Use NIS** y **Use FSR** cuando están soportados.
- Control compartido de nitidez 0–5 para FSR/NIS explícitos.
- Sincroniza las distintas raíces Xwayland de Gamescope.
- Deja el modo de reescalado QAM (`Automático`, `Ajustar`, `Entero`, `Estirar`)
  bajo control del QAM; en Ubuntu elegir filtro nunca cambia el scaler.
- Recuerda las selecciones explícitas sin escrituras pasivas al cargar el
  frontend.
- No parchea, sustituye ni instala Gamescope.

## Requisitos

- Decky Loader.
- Una sesión gaming Gamescope/Xwayland activa.
- `xprop` disponible en el sistema.
- Renderizar el juego por debajo de la resolución de salida para apreciar el
  filtro de escalado.

El soporte SGSR depende del Gamescope que esté ejecutándose. Si no está
disponible, el plugin conserva el comportamiento compatible FSR/NIS.

## Instalación

### ZIP de GitHub Releases

1. Descarga el ZIP de la versión deseada (por ejemplo,
   `sharp-filter-selector-v1.1.0.zip`).
2. Extráelo; contiene una única carpeta `sharp-filter-selector`.
3. Ejecuta el instalador incluido:

```bash
cd sharp-filter-selector
./install.sh
```

Destino predeterminado:

```text
~/homebrew/plugins/sharp-filter-selector/
```

Recarga Decky Loader o reinicia Steam/Gaming Mode. Para una ubicación de prueba:

```bash
DECKY_PLUGIN_DIR=/ruta/a/plugins/sharp-filter-selector ./install.sh
```

Para desinstalar:

```bash
./uninstall.sh
```

### Desde el código fuente

```bash
git clone https://github.com/N3ruk/Sharp-Filter-Selector.git
cd Sharp-Filter-Selector
./install.sh
```

## Uso

1. Inicia un juego dentro de Gamescope.
2. Abre QAM → Decky Loader → Sharp Filter Selector.
3. Deja ambos overrides apagados para usar Sharp nativo.
4. Activa **Use NIS** para NVIDIA Image Scaling.
5. En Gamescope compatible con SGSR, activa **Use FSR** para forzar AMD FSR.
6. Ajusta **Sharpness** entre 0 y 5 con FSR o NIS explícitos.

Solo puede existir un override explícito activo. La línea de estado muestra el
motor efectivo y los objetivos Gamescope modificados.

## Cómo funciona

### Ubuntu / Linux genérico

El backend descubre los displays Gamescope/Xwayland mediante la ascendencia y
el entorno de procesos. El servidor Xwayland 0 es la autoridad del QAM. Sus
valores válidos de scaler y filtro se reflejan en las demás raíces sin cambiar
el scaler elegido por QAM.

En Gamescope 3.16.29+, el valor Sharp histórico `2` del QAM se traduce al
selector SGSR nativo `5` cuando el proceso Gamescope activo anuncia SGSR. Los
overrides mantienen NIS `3` o FSR `2`.

### SteamOS

Se conserva la detección multi-Xwayland y la transición explícita LINEAR → NIS
ya validadas, añadiendo SGSR nativo y FSR explícito cuando Gamescope lo permite.

### HDR

La restricción afecta a la entrada **HDR**, no simplemente a que la salida HDR
esté activa. Si la aplicación entrega HDR, Gamescope usa su fallback FSR para
Sharp nativo. Una salida HDR con contenido SDR puede seguir usando SGSR.

Desde 1.1.0, solo `GAMESCOPE_COLOR_APP_WANTS_HDR_FEEDBACK` condiciona la
ocultación por HDR. Si falta, es inválido o contradictorio, se considera
desconocido: FSR y NIS siguen disponibles si Gamescope admite SGSR,
independientemente del HDR de la pantalla. Abrir QAM no activa por sí mismo
esta condición; se consulta la señal actual sin conservar HDR de otro juego.

## Compatibilidad y validación

La versión 1.1.0 se validó en Ubuntu 26.04 Gaming Mode con Gamescope 3.16.30,
NVIDIA RTX 2060, varias raíces Xwayland, salida 4K y VRR. Una prueba física con
juego y QAM confirmó que un juego SDR sobre una salida HDR conserva FSR y NIS,
y que la transición de visibilidad de FSR depende de la señal HDR de la
aplicación, no del interruptor HDR de pantalla. SGSR nativo, FSR/NIS explícitos,
el ajuste de nitidez 0–5 y todos los modos de reescalado QAM siguen operativos.

La batería automatizada cubre además señal SDR, HDR, ausente, inválida y
contradictoria, fallos de refresco del frontend y el mapeo completo de nitidez
FSR/NIS. No simula Gamescope ni sustituye la validación física anterior.

Otros sistemas necesitan propiedades compatibles de Gamescope y `xprop`. Se
conserva soporte SteamOS, que debe validarse con sus versiones instaladas de
Gamescope y Decky.

## Solución de problemas

**No se encontraron objetivos Gamescope**

Utiliza el plugin dentro de una sesión Gamescope activa y comprueba `xprop`.

**El filtro cambia pero la imagen parece igual**

Gamescope debe estar reescalando. Renderiza el juego por debajo de la resolución
final.

**Sharp nativo muestra FSR en vez de SGSR**

Es normal con entrada HDR o cuando el Gamescope activo no anuncia SGSR.

**El modo de reescalado QAM no modifica la imagen**

El plugin no controla ese modo. Revisa Gamescope y la integración QAM; elegir un
filtro deliberadamente no sobrescribe el scaler.

## Desarrollo y empaquetado

```bash
npm install
npm run build
npm run package
```

Se generan:

```text
release/sharp-filter-selector-vX.Y.Z.zip
release/sharp-filter-selector-vX.Y.Z.zip.sha256
```

El ZIP incluye runtime compilado, fuente del frontend, instalador y
desinstalador portables, README, changelog y licencia.

Las releases usan el `dist/index.js` validado y guardado en el repositorio. Como
las dependencias de Decky pueden cambiar el wrapper generado, revisa y prueba un
nuevo `npm run build` antes de sustituir ese bundle validado.

## Licencia y divulgación

BSD 3-Clause. Consulta [LICENSE](LICENSE).

Desarrollado para [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)
y [Gamescope](https://github.com/ValveSoftware/gamescope). FSR, NIS y SGSR son
tecnologías de sus respectivos propietarios. Este plugin comunitario es
independiente y no está afiliado ni respaldado por Valve, AMD o NVIDIA.

Consulta [AI_DISCLOSURE.md](AI_DISCLOSURE.md) para la procedencia de la
asistencia de IA empleada en el proyecto.
