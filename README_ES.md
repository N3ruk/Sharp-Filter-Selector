# Sharp Filter Selector — Selector FSR / NIS para Decky Loader y Gamescope

**Sharp Filter Selector** es un plugin para **Decky Loader y Gamescope** que permite cambiar el filtro de escalado activo entre **AMD FidelityFX Super Resolution (FSR)** y **NVIDIA Image Scaling (NIS)** directamente desde el menú de acceso rápido.

Está diseñado para **Steam Deck / SteamOS** y sesiones de juego Linux compatibles que utilicen **Decky Loader + Gamescope**. También incorpora un control sencillo de **nitidez NIS de 0 a 5**, sin necesidad de modificar las opciones de lanzamiento de cada juego.

> English documentation: **[README.md](README.md)**

## Características

- Cambiar el escalado de Gamescope entre **FSR** y **NIS** desde Decky Loader.
- Ajustar la **nitidez de NIS** entre **0 (mínima)** y **5 (máxima)**.
- Aplicar el filtro a sesiones Gamescope/Xwayland activas.
- Recordar el filtro y nivel de nitidez seleccionados.
- No requiere modificar las opciones de lanzamiento de cada juego.
- **No sustituye, parchea ni instala Gamescope**.

## Requisitos

- **Decky Loader**.
- Una sesión de juego Linux ejecutando **Gamescope**.
- `xprop` disponible en el sistema.
- Una configuración en la que Gamescope esté realizando realmente un escalado de resolución.

> Si el juego ya se renderiza a la resolución final de la pantalla, cambiar entre FSR y NIS puede producir poca o ninguna diferencia visible. El plugin selecciona el filtro de escalado; no obliga al juego a renderizar a una resolución inferior.

## Instalación

### Desde GitHub Releases

1. Abre la sección **Releases** del repositorio.
2. Descarga el último `sharp-filter-selector-vX.Y.Z.zip`.
3. Instálalo mediante el sistema de instalación/desarrollo de plugins de Decky Loader, o extrae la carpeta `sharp-filter-selector` en el directorio de plugins de Decky.
4. Recarga Decky Loader o reinicia Gaming Mode/Steam.

Directorio habitual:

```text
~/homebrew/plugins/sharp-filter-selector/
```

### Desde el código fuente

```bash
git clone https://github.com/N3ruk/Sharp-Filter-Selector.git
cd Sharp-Filter-Selector
./install.sh
```

Para desinstalar:

```bash
./uninstall.sh
```

## Uso

1. Inicia un juego dentro de una sesión Gamescope.
2. Abre el **Quick Access Menu**.
3. Entra en **Decky Loader → Sharp Filter Selector**.
4. Activa **Use NIS** para cambiar de FSR a NVIDIA Image Scaling.
5. Ajusta **NIS sharpness** entre `0` y `5`.
6. Desactiva **Use NIS** para volver a FSR.

La línea de estado muestra el filtro seleccionado y los displays de Gamescope que se han actualizado.

## FSR frente a NIS en Gamescope

Sharp Filter Selector no implementa un escalador propio. Controla el estado de los filtros de escalado expuestos por Gamescope.

- **FSR** = AMD FidelityFX Super Resolution.
- **NIS** = NVIDIA Image Scaling.
- El slider de nitidez controla el valor de sharpening utilizado por Gamescope.
- Los propios controles de escalado de Steam/Gamescope pueden modificar el mismo estado.

Esto permite comparar rápidamente **FSR y NIS en Gamescope** sin mantener diferentes cadenas de opciones de lanzamiento para cada juego.

## Cómo funciona

El backend actualiza las propiedades X11 de las sesiones Gamescope/Xwayland activas y aplica los valores correspondientes del filtro de escalado y nitidez.

El plugin no inyecta librerías gráficas, no modifica los archivos de los juegos y no sustituye Gamescope. Por ello, desinstalarlo no requiere restaurar una instalación modificada de Gamescope.

## Compatibilidad

El plugin está pensado para:

- Entornos con **Decky Loader**.
- **Steam Deck / SteamOS**.
- Sistemas Linux gaming que ejecuten **Gamescope** con sesiones Xwayland compatibles.

El soporte real depende de que la sesión Gamescope exponga las propiedades de escalado esperadas y de que `xprop` esté disponible.

## Solución de problemas

**El plugin indica que no encuentra una sesión Gamescope.**  
Comprueba que estás utilizándolo desde una sesión de juego Gamescope y que existe un display Gamescope/Xwayland activo.

**El filtro cambia pero la imagen parece igual.**  
Gamescope debe estar escalando la imagen para que FSR/NIS tenga un efecto visible. Prueba a renderizar el juego por debajo de la resolución de salida.

**El plugin indica que falta `xprop`.**  
Instala el paquete que proporciona `xprop` en tu distribución y vuelve a cargar Decky Loader.

**El filtro cambia después de utilizar los controles de escalado de Steam.**  
Steam/Gamescope puede escribir sobre el mismo estado. Abre de nuevo Sharp Filter Selector y vuelve a aplicar el filtro deseado.

## Desarrollo

Construir el frontend:

```bash
npm run build
```

Crear el ZIP para una Release:

```bash
npm run package
```

El resultado se guarda como:

```text
release/sharp-filter-selector-vX.Y.Z.zip
```

## Licencia

BSD 3-Clause. Consulta **[LICENSE](LICENSE)**.

## Agradecimientos

Desarrollado para [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) y [Gamescope](https://github.com/ValveSoftware/gamescope).

FSR es una tecnología de AMD y NIS una tecnología de NVIDIA. Este proyecto es un plugin independiente de la comunidad y no está afiliado ni respaldado por Valve, AMD o NVIDIA.
