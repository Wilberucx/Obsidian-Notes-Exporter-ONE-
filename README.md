# Obsidian Notes Exporter (ONE)

Una suite de exportación unificada y fácil de usar, diseñada para convertir tus notas de Obsidian en documentos profesionales (PDF, DOCX, EPUB) con un solo clic, directamente desde tu vault.



## Características Principales

-   ✅ **Instalación en 2 Minutos:** Olvídate de Python y dependencias. Descarga, ejecuta el setup y listo.
-   ✅ **Control Total desde YAML:** Define el título, autor, modo y formatos de salida en el `frontmatter` de tu nota.
-   ✅ **Integración Perfecta con Obsidian:** Lanza exportaciones con un clic derecho o un icono en la barra lateral.
-   ✅ **Exportación a PDF Profesional:** Generación de PDF de alta calidad, **completamente probada y funcional**, con maquetación de libro (título, índice y capítulos en páginas separadas).
-   🧪 **Soporte Experimental para DOCX y EPUB:** La exportación a `.docx` y `.epub` está implementada con plantillas básicas. La funcionalidad principal existe, pero estos formatos **no han sido probados exhaustivamente** y se consideran en desarrollo. ¡El feedback y los informes de bugs son bienvenidos!
-   ✅ **Dos Modos de Exportación:** Usa el **Modo Manual** para un control absoluto o el **Modo Automático** para exploraciones rápidas.
-   ✅ **Maquetación Profesional:** Genera automáticamente saltos de página para una estructura de libro limpia.

---

## Instalación

Instalar ONE es un proceso de 3 pasos que no te tomará más de dos minutos.

#### Paso 1: Descargar la Herramienta
-   Ve a la [**página de Releases**](https://github.com/Wilberucx/Obsidian-Notes-Exporter-ONE-/releases) de este repositorio.
-   Descarga el archivo `.zip` de la última versión.

#### Paso 2: Ejecutar la Configuración
-   Descomprime el archivo `.zip` en una ubicación **permanente** de tu ordenador (ej. `C:\Herramientas\ONE`).
-   Dentro de la carpeta, haz doble clic en **`ONE_Setup.exe`**.
-   Usa la herramienta gráfica para indicarle a ONE dónde están tus vaults de Obsidian y dónde quieres que se guarden las exportaciones.

#### Paso 3: Integrar con Obsidian
-   En Obsidian, instala y activa el plugin **`Shell Commands`** desde la tienda de plugins de la comunidad.
-   Ve a la configuración del plugin y crea un nuevo comando:
    -   **Shell command:**
        ```bash
        "C:\Ruta\Donde\Descomprimiste\ONE\ONE_Exporter.exe" "{{file_path:absolute}}"
        ```
        *(¡Asegúrate de poner la ruta correcta y usar las comillas!)*
    -   **Alias:** `Exportar Documento (ONE)`
    -   **Activa el icono de menú contextual (lista)** para un uso seguro.

---

## Guía de Uso

El corazón de ONE reside en la configuración de una **Nota Maestra (MOC)**. Aquí es donde defines todo sobre tu documento final.

### 1. Configura el Frontmatter YAML

Al principio de tu nota MOC, añade un bloque YAML para controlar la exportación.

```yaml
---
# --- Configuración de Exportación (ONE) ---

# Modo de exportación: 'manual' o 'automatic'
export_mode: manual

# Profundidad de rastreo (solo para modo 'automatic')
# Opciones: 0, 1, 2, ..., 'infinite'
export_depth: 1 

# Formatos de Salida: una lista con los formatos deseados.
# Opciones: pdf (probado), docx (experimental), epub (experimental), md.
# ('md' solo construye el paquete sin convertir)
export_formats: [pdf]

# --- Metadatos del Documento Final ---
export_title: "Mi Manuscrito Final"
export_author: "Tu Nombre"
export_date: '2025-12-31'
export_style: classic # Opciones para PDF: 'classic', 'modern'
cover-image: 'portada.jpg' # Para EPUB, la imagen debe estar en el vault

---
```

2. Elige tu Modo de Exportación

ONE te ofrece dos formas de construir tu documento:

Modo Manual (export_mode: manual) - Recomendado

Te da control absoluto sobre la estructura. El script interpreta el cuerpo de tu nota MOC como un plano exacto.

Para crear un capítulo: Usa una lista con un wikilink: - [[Mi Nota]]

Para darle un título personalizado: Pon un encabezado justo antes: ## Título Personalizado\n- [[Mi Nota]]

Para crear sub-secciones: Usa la sangría: - [[Mi Sub-Nota]]

Ejemplo de Estructura Manual:

``` markdown
- [[01 - Introducción]]

## Parte 1: Los Fundamentos
- [[02 - Conceptos Clave]]
  - [[02a - Sub-concepto A]]
- [[03 - Historia]]

- [[04 - Conclusión]]
```

Modo Automático (export_mode: automatic)

Construye el documento explorando los enlaces de tus notas automáticamente, basándose en la profundidad (export_depth) que definas. Es ideal para exploraciones rápidas de un tema.

<details>
<summary><strong>Haz clic aquí para ver una explicación detallada de los niveles de exportación automática.</strong></summary>


El nivel de exportación es la profundidad hasta donde el script sigue los enlaces salientes desde tu nota de inicio.
Estructura de Ejemplo:
![niveles de exportación](https://github.com/Wilberucx/Obsidian-Notes-Exporter-ONE-/blob/main/readme-images/Niveles%20de%20exportaci%C3%B3n%20de%20ONE.png)


export_depth: 0 (Solo Nota Inicial): Exporta exclusivamente la nota seleccionada. Ideal para notas autocontenidas como resúmenes o entradas de diario.

export_depth: 1 (Enlaces Directos): Incluye la nota inicial y todas las notas enlazadas directamente desde ella. Perfecto para un tema central con sus definiciones directas.

export_depth: 2 (Segundo Nivel): Recorre también las notas enlazadas desde las notas de Nivel 1. Útil para un capítulo de libro con subtemas.

export_depth: infinite (Toda la Red): El script recorre todos los enlaces disponibles sin límite. Útil para backups o exportaciones completas, pero úsalo con precaución, ya que podría exportar gran parte de tu vault.

El script genera una estructura jerárquica en el documento final basándose en el orden en que descubre las notas.

</details>

3. ¡Exporta!

Con tu nota MOC abierta, usa el método que configuraste en el Paso 3 de la instalación (menú contextual, icono de la cinta o paleta de comandos).

<details>
<summary><strong>Para Desarrolladores: Ejecutar desde el Código Fuente</strong></summary>


Si prefieres ejecutar el proyecto desde el código fuente de Python:

Clona el repositorio.

Crea un entorno virtual y actívalo: python -m venv .venv y .\.venv\Scripts\activate.

Instala las dependencias: pip install PyYAML.

Ejecuta la configuración: python config_tool.py.

Ejecuta el exportador: python ONE_Exporter.py.

</details>
