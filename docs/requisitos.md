# Requisitos — Py-PDF-Compare

> **Versión 5** · **Generado:** 2026-08-24 08:39 CEST
> Documento de Fase 1 (AIDD · paso 1.1). Generado por `aidd requirements`.
> Entrada: no existe `docs/cliente-requisitos.md` — requisitos derivados por ingeniería inversa del código, el `README.md` y el workflow de CI. Salida hacia: `docs/mapa-historias-usuario.md`.
> Alcance: **estado actual (as-is)**. Este catálogo formaliza lo que el producto ya hace; toda evolución posterior entra como *change* de AISDD.
> Pendiente de aprobación humana.

## 1. Descripción del sistema y objetivos

**Py-PDF-Compare** es una herramienta de escritorio y línea de comandos que compara dos ficheros PDF y genera un informe PDF de diferencias, con las dos versiones enfrentadas lado a lado y las diferencias de texto resaltadas por color.

Problema que resuelve: revisar qué ha cambiado entre dos versiones de un documento PDF sin depender de herramientas comerciales, sin subir el documento a ningún servicio externo y sin perder la calidad del original.

Objetivos medibles (derivados del comportamiento actual):

- **O-1** — El informe conserva el contenido vectorial de los originales: el texto del informe sigue siendo seleccionable y buscable.
- **O-2** — El informe evita la rasterización: el tamaño de fichero resultante es entre 20 y 70 veces menor que el del enfoque basado en imágenes que sustituyó (`pdf_compare/config.py`).
- **O-3** — La instalación no requiere dependencias nativas externas al ecosistema Python (sin Poppler ni binarios de sistema).
- **O-4** — El producto es consumible por tres vías con el mismo núcleo: aplicación de escritorio, CLI y librería Python.

## 2. Usuarios y roles

El sistema **no tiene autenticación ni control de acceso**: es una herramienta local monousuario. Los "roles" son perfiles de uso, no permisos.

| Rol | Descripción | Interfaz | Permisos / responsabilidades |
|---|---|---|---|
| **Usuario de escritorio** | Persona que compara dos documentos de forma puntual y visual | GUI (`pdf-compare-gui`) | Selecciona ficheros, lanza la comparación, previsualiza, descarga o abre el informe |
| **Usuario de CLI / automatización** | Persona o script que integra la comparación en un flujo por lotes o en CI | CLI (`pdf-compare`) | Pasa rutas de entrada y salida, interpreta el código de salida del proceso |
| **Desarrollador integrador** | Programador que embebe la comparación en otra aplicación | API Python (`PDFComparator`) o submódulo git | Instancia el comparador, consume los bytes del informe y decide su persistencia |
| **Mantenedor** | Responsable del repositorio y de las publicaciones | GitHub Actions, PyPI | Versiona en `pyproject.toml`, dispara release de binarios y publicación en PyPI |

## 3. Requisitos funcionales

Prioridad orientativa: **A** (nuclear, define el producto), **M** (relevante), **B** (accesorio).

### 3.1 Núcleo de comparación

| ID | Requisito | Actor | Prio |
|---|---|---|---|
| RF-01 | El sistema debe comparar dos ficheros PDF (original y modificado) y producir un informe PDF con ambos enfrentados lado a lado, página a página | Todos | A |
| RF-02 | El sistema debe alinear las páginas por **similitud de contenido textual**, no por número de página, de modo que un desplazamiento de páginas no se interprete como cambio masivo | Todos | A |
| RF-03 | El alineado debe clasificar cada pareja de páginas como equivalente, sustituida, insertada o eliminada, explorando páginas siguientes para encontrar la correspondencia real | Todos | A |
| RF-04 | Una página presente solo en el original debe aparecer en el panel izquierdo etiquetada como ausente, con el panel derecho en blanco | Todos | A |
| RF-05 | Una página presente solo en el modificado debe aparecer en el panel derecho etiquetada como añadida, con el panel izquierdo en blanco | Todos | A |
| RF-06 | El sistema debe resaltar las diferencias **a nivel de palabra**, localizándolas por su caja delimitadora en la página: rojo para lo eliminado sobre el original, verde para lo añadido sobre el modificado | Todos | A |
| RF-07 | Cuando la página del original y la del modificado no ocupan la misma posición, el informe debe señalarlo visualmente como página desplazada | Todos | M |
| RF-08 | Cada panel debe llevar una etiqueta con su origen (original / modificado) y el número de página correspondiente en su documento | Todos | M |
| RF-09 | El informe debe construirse insertando el contenido vectorial de las páginas originales, sin convertirlas a imagen | Todos | A |
| RF-10 | El sistema debe detectar que no existen diferencias entre ambos documentos e informar de ello al usuario en lugar de entregar un informe sin valor | Todos | M |
| ~~RF-11~~ | ~~Comparación textual en formato *unified diff* en la API~~ — **retirado el 2026-08-24**: `compare_text()` ignoraba el alineado de páginas, no lo exponía ninguna interfaz y quedaba superado por RF-31. ID no reutilizable | — | — |
| RF-31 | El sistema debe poder ejecutar la comparación y devolver el resultado como datos (nombres, rutas y número de páginas de ambos documentos; si son idénticos; si falta capa de texto; y recuentos de páginas añadidas, eliminadas y modificadas y de palabras añadidas y eliminadas), sin componer el informe PDF | Usuario de CLI, Desarrollador integrador | A |
| RF-32 | El resultado en datos debe proceder del **mismo** alineado de páginas y del **mismo** diff por palabra que el informe PDF, de modo que ambos no puedan discrepar | Todos | A |

### 3.2 Interfaz de línea de comandos

| ID | Requisito | Actor | Prio |
|---|---|---|---|
| RF-12 | La CLI debe aceptar la ruta del PDF original y del modificado como argumentos posicionales obligatorios | Usuario de CLI | A |
| RF-13 | La CLI debe permitir indicar la ruta del informe de salida mediante una opción, con un valor por defecto cuando se omite | Usuario de CLI | A |
| RF-14 | La CLI debe validar que ambos ficheros de entrada existen antes de procesar y terminar con error y mensaje explícito si alguno falta | Usuario de CLI | A |
| RF-15 | La CLI debe informar del progreso y, al terminar, del tamaño del informe generado | Usuario de CLI | B |
| RF-16 | Ante un fallo durante la comparación, la CLI debe informar del error y terminar con código de salida distinto de cero, para poder encadenarse en scripts | Usuario de CLI | M |

### 3.3 Aplicación de escritorio

| ID | Requisito | Actor | Prio |
|---|---|---|---|
| RF-17 | La aplicación debe permitir seleccionar cada documento mediante un diálogo del sistema filtrado a ficheros PDF | Usuario de escritorio | A |
| RF-18 | La aplicación debe impedir lanzar la comparación si falta alguno de los dos documentos, avisando al usuario | Usuario de escritorio | M |
| RF-19 | La comparación debe ejecutarse sin bloquear la interfaz, mostrando un indicador de progreso mientras dura | Usuario de escritorio | A |
| RF-20 | La aplicación debe previsualizar el informe generado dentro de la propia ventana, página a página y con desplazamiento vertical | Usuario de escritorio | A |
| RF-21 | La aplicación debe permitir descargar el informe a la carpeta de descargas del usuario, resolviendo su ubicación real en cada sistema operativo y sin sobrescribir ficheros previos | Usuario de escritorio | M |
| RF-22 | La aplicación debe permitir abrir el informe con el visor de PDF por defecto del sistema operativo | Usuario de escritorio | M |
| RF-23 | La aplicación debe permitir guardar el informe en una ubicación elegida por el usuario mediante diálogo | Usuario de escritorio | M |
| RF-24 | La aplicación debe comunicar los errores tanto en el área de estado como en un diálogo modal, y volver a dejar la interfaz operativa | Usuario de escritorio | M |
| RF-25 | Las acciones sobre el informe deben permanecer deshabilitadas mientras no exista un informe generado | Usuario de escritorio | B |

### 3.4 API, empaquetado y distribución

| ID | Requisito | Actor | Prio |
|---|---|---|---|
| RF-26 | El paquete debe exponer una clase comparadora como API pública estable, construible a partir de las rutas de ambos documentos y capaz de devolver el informe en memoria | Desarrollador integrador | A |
| RF-27 | El proyecto debe publicarse como paquete instalable desde PyPI, declarando los dos puntos de entrada ejecutables (CLI y GUI) | Mantenedor | A |
| RF-28 | El proyecto debe poder integrarse en otro repositorio como submódulo git e importarse directamente | Desarrollador integrador | B |
| RF-29 | El proyecto debe generar ejecutables autónomos para Windows, Linux y macOS (Apple Silicon), sin requerir Python instalado en la máquina destino | Mantenedor | M |
| RF-30 | La publicación de binarios y del paquete debe dispararse automáticamente al integrar en la rama principal una versión nueva, y no repetirse para una versión ya publicada | Mantenedor | M |

## 4. Requisitos no funcionales

| ID | Requisito | Categoría | Verificación |
|---|---|---|---|
| NFR-01 | El informe debe preservar el texto como texto: seleccionable y buscable en cualquier visor | Calidad de salida | Buscar una cadena conocida en el informe generado |
| NFR-02 | El informe no debe rasterizar el contenido original; el tamaño resultante debe mantenerse en el orden de magnitud de los documentos de entrada | Rendimiento | Comparar tamaño del informe frente a la suma de las entradas |
| NFR-03 | La instalación no debe requerir dependencias nativas externas al ecosistema Python | Portabilidad | Instalación limpia en un sistema sin herramientas PDF |
| NFR-04 | El sistema debe funcionar sobre Python 3.12 o superior | Compatibilidad | Declarado en el empaquetado y ejercitado en CI |
| NFR-05 | El sistema debe funcionar en Windows, macOS y Linux, incluidas las rutas específicas de cada sistema para descargas y apertura de ficheros | Portabilidad | Ejecución en las tres plataformas |
| NFR-06 | La interfaz gráfica no debe congelarse durante la comparación: el trabajo pesado se ejecuta fuera del hilo de interfaz y la comunicación entre hilos es segura | Usabilidad / robustez | Comparar un documento extenso y verificar que la ventana responde |
| NFR-07 | La previsualización debe renderizarse a resolución reducida para acotar el consumo de memoria, sin afectar a la calidad del informe entregado | Rendimiento | Inspección del uso de memoria con documentos de muchas páginas |
| NFR-08 | Los documentos abiertos deben cerrarse siempre al terminar el proceso, sin dejar descriptores abiertos | Robustez | Comparaciones encadenadas en un proceso de larga vida |
| NFR-09 | Todo el procesamiento debe ser local: el sistema no envía los documentos ni su contenido a ningún servicio externo | Privacidad / RGPD | Ausencia de tráfico de red durante una comparación |
| NFR-10 | La publicación en PyPI debe realizarse sin credenciales de larga duración almacenadas en el repositorio | Seguridad | Revisión del workflow de publicación |
| NFR-11 | El proceso de publicación debe ser idempotente: una versión ya publicada no vuelve a publicarse aunque se repita la ejecución | Fiabilidad | Reejecución del workflow sobre una versión existente |
| NFR-12 | El código fuente debe permanecer en un único paquete Python sin dependencias circulares entre interfaz, CLI y núcleo de comparación | Mantenibilidad | Revisión de imports: el núcleo no importa CLI ni GUI |

## 5. Restricciones técnicas no negociables

| ID | Restricción | Motivo |
|---|---|---|
| RT-01 | La manipulación de PDF se realiza con **PyMuPDF**; es la dependencia estructural del núcleo y la que hace innecesarias las herramientas nativas | Sustituye al enfoque previo basado en Poppler e imágenes; cambiarla implica reescribir el núcleo |
| RT-02 | La interfaz gráfica se construye con **CustomTkinter** sobre Tcl/Tk, con hooks propios de runtime en el empaquetado para Linux y macOS | Ya resuelto en los scripts de build; cambiar de framework invalida el empaquetado actual |
| RT-03 | Los parámetros `--dpi` y `--quality` de la CLI, y las constantes `PDF_RENDER_DPI` y `JPEG_QUALITY` de `pdf_compare/config.py`, **se mantienen aunque no tengan efecto** en el render vectorial | Compatibilidad hacia atrás: la API y la CLI ya están publicadas en PyPI y retirarlas rompería a consumidores existentes |
| RT-04 | La versión del producto es la declarada en `pyproject.toml` y debe mantenerse sincronizada con `pdf_compare/__init__.py`; el CI la lee de `pyproject.toml` para etiquetar y publicar | El release automático depende de esa única fuente |
| RT-05 | El empaquetado usa `hatchling` como backend de construcción y `uv` como gestor de entorno en CI | Fijado en el workflow y en los scripts de build |
| RT-06 | El versionado sigue un esquema **calendario** (`AAAA.M.P`), no semántico | Versión actual `2026.2.3`; condiciona cómo se comunican los cambios incompatibles |
| RT-07 | La compatibilidad de licencias entre el código propio y PyMuPDF condiciona la distribución del producto | Ver **P-01** en la sección 8: hay una contradicción sin resolver |

## 6. Alcance

### Dentro de esta fase (as-is)

- Comparación de dos documentos PDF **con capa de texto**, con alineado de páginas y resaltado de diferencias por palabra.
- Las tres interfaces existentes: CLI, aplicación de escritorio y API Python.
- Empaquetado y distribución actuales: PyPI, binarios autónomos para las tres plataformas y uso como submódulo.

### Fuera de esta fase

- **PDF escaneados o sin capa de texto.** El alineado y el resaltado dependen íntegramente del texto extraíble; sobre un documento escaneado el sistema no detecta diferencias. Es una **limitación conocida y declarada**: la herramienta exige documentos con capa de texto y no se compromete a incorporar OCR. Desde el 2026-08-17 el sistema **sí detecta y avisa** de que falta la capa de texto en lugar de entregar en silencio un informe sin diferencias (ver D-08); sigue sin haber OCR.
- Comparación de más de dos documentos o de carpetas completas.
- Detección de diferencias **no textuales**: imágenes, gráficos vectoriales, cambios de color o de tipografía sin cambio de contenido.
- Comparación semántica o por lenguaje natural (resumen de cambios, clasificación de relevancia).
- Cualquier funcionalidad multiusuario, de servidor o de red: autenticación, historial, almacenamiento compartido.
- Internacionalización: la interfaz y las etiquetas del informe están en inglés y así permanecen.
- Configuración persistente de preferencias de usuario.

## 7. Variables de entorno y configuración requerida

El producto **no consume ninguna variable de entorno propia** en tiempo de ejecución. Toda su configuración es por argumentos de CLI o por parámetros del constructor de la API.

| Elemento | Ámbito | Uso |
|---|---|---|
| `pdf_compare/config.py` | Ejecución | Constantes heredadas del render por imagen, sin efecto actual (ver RT-03) |
| Carpeta temporal del sistema | Ejecución (GUI) | Ubicación del informe intermedio antes de descargarlo o guardarlo |
| Carpeta de descargas del usuario | Ejecución (GUI) | Destino de la acción de descarga; se resuelve por registro en Windows y por convención en macOS/Linux |
| Entorno `pypi-release` de GitHub | CI/CD | Entorno protegido desde el que se publica el paquete |
| OIDC de GitHub Actions | CI/CD | Publicación en PyPI sin token almacenado (*trusted publishing*) |
| `GITHUB_TOKEN` | CI/CD | Creación de tags y releases; lo provee la propia plataforma |

Sin secretos propios que gestionar en local.

## 8. Preguntas abiertas y pendientes

- **P-01 · [BLOQUEANTE] Contradicción de licencia.** El fichero `LICENSE` del repositorio contiene la **GPL-3.0**, mientras que `pyproject.toml` y el `README.md` declaran **MIT**. Además, PyMuPDF (RT-01) se distribuye bajo AGPL-3.0 o licencia comercial, lo que condiciona bajo qué licencia puede distribuirse un producto que la enlaza. Hay que decidir cuál es la licencia real del proyecto y alinear los tres sitios. Afecta a RT-07 y a toda la distribución (RF-27, RF-29).
- ~~**P-02 · Discrepancia entre la documentación y el comportamiento de RF-10.**~~ **Resuelto el 2026-08-17.** `compare_visuals()` devuelve `None` cuando no hay ninguna diferencia, y la CLI y la GUI informan de ello; las ramas que antes eran inalcanzables ahora se ejecutan. Se define "sin diferencias" como: ninguna página añadida ni eliminada, y ningún cambio de texto a nivel de palabra en las páginas emparejadas.
- ~~**P-03 · RF-11 no está expuesto.**~~ **Resuelto el 2026-08-24**, retirándolo en vez de exponerlo: el diff plano no aprovechaba el alineado de páginas. Sustituido por RF-31 y RF-32. Es un cambio incompatible en la API pública ya publicada en PyPI, sin señalizar por el versionado calendario (RT-06).
- **P-08 · La composición del PDF no es el cuello de botella, al contrario de lo que se asumió.** Medido el 2026-08-24 sobre un par de 19 y 103 páginas: `analyze()` tarda 0,83 s y `compare_visuals()` 0,82 s. `show_pdf_page` referencia las páginas de origen como objetos vectoriales en lugar de rasterizarlas, así que componer cuesta casi nada; el coste está en la extracción de texto y el diff, que ambos caminos comparten. Queda pendiente decidir si merece la pena perfilar la extracción, que es lo que domina.
- **P-09 · Falta un `CHANGELOG`.** La retirada de `compare_text()` es incompatible y el versionado calendario (RT-06) no lo señaliza: hoy no hay ningún sitio donde un consumidor pueda enterarse.
- **P-04 · Umbrales de alineado.** El 2026-08-17 se corrigieron dos defectos que incumplían RF-02, RF-03 y RF-05: un *off-by-one* que hacía explorar 2 posiciones en lugar de las 3 declaradas, y el uso del umbral absoluto de "misma página" (0,6) también para decidir si una página está desplazada. Este segundo defecto impedía detectar una inserción cuando la página desplazada **además había sido editada**, con lo que la página añadida se emparejaba con la original y la verdadera equivalente se marcaba como añadida. La detección de desplazamiento es ahora **relativa** (el candidato debe encajar `SHIFT_MARGIN` veces mejor que el emparejamiento actual y superar un suelo de ruido), y las cuatro constantes están documentadas a nivel de módulo. **Queda abierto**: los valores concretos siguen elegidos por criterio y no por medida, y el alineado sigue siendo voraz y local, por lo que no recupera desplazamientos mayores que `LOOKAHEAD_WINDOW`. Decidir si se validan con un corpus de documentos reales o si se sustituye por un alineado global.
- **P-05 · No hay verificación automática.** El proyecto declara `pytest` como dependencia de desarrollo pero no contiene ni un test, y el CI solo construye y publica: ningún requisito de este catálogo está verificado de forma automatizada. Los documentos `sample-files/` cubren los cuatro escenarios de alineado y son la base natural para esa suite. **Sigue abierto y es ahora más urgente**: las correcciones del 2026-08-17 se validaron con comprobaciones manuales y desechables, que no protegen de regresiones futuras.
- **P-06 · Límites operativos sin definir.** No hay criterio establecido de número máximo de páginas, tamaño de fichero ni tiempo de respuesta aceptable. NFR-02 y NFR-07 se han redactado como cualitativos; convendría cuantificarlos con medidas reales antes de comprometerlos.
- **P-07 · Trazabilidad de errores.** El sistema informa por salida estándar y por diálogos, sin registro estructurado. Decidir si un producto de escritorio local necesita observabilidad o si basta lo actual.

## 9. Decisiones tomadas en el paso 1.1

| # | Pregunta | Opciones | Decisión | Origen | Justificación |
|---|---|---|---|---|---|
| D-01 | ¿El documento cubre solo el estado actual o también la evolución prevista? | as-is / as-is + to-be | **Solo el estado actual (as-is)** | usuario | El repositorio es *brownfield* sin backlog definido; la línea base trazable es lo que permite que cada evolución entre después como *change* de AISDD |
| D-02 | ¿Cómo se recoge la incapacidad de tratar PDF escaneados? | fuera de alcance / degradación controlada / OCR futuro | **Fuera de alcance, explícito** | usuario | Se declara como limitación conocida en la sección 6 sin comprometer OCR, que añadiría una dependencia pesada al producto |
| D-03 | ¿Qué comportamiento se formaliza cuando no hay diferencias? | informar / generar siempre el informe | **Informar de que no hay cambios** (RF-10) | usuario | Se toma como correcto lo documentado en el `README.md`; la implementación actual queda registrada como deuda en P-02 |
| D-04 | ¿Qué estatus tienen los parámetros heredados `--dpi`, `--quality` y `config.py`? | restricción de compatibilidad / deprecados a eliminar | **Restricción de compatibilidad** (RT-03) | usuario | La API y la CLI ya están publicadas en PyPI; retirarlas sería un cambio incompatible para consumidores existentes |
| D-05 | ¿Cómo se trata la ausencia de `docs/cliente-requisitos.md`? | bloquear / continuar por ingeniería inversa | **Continuar por ingeniería inversa** | default | El producto existe y es la fuente de verdad más fiable; se deja constancia de que no hubo brief formal de cliente |
| D-06 | ¿Se documentan roles con permisos? | sí / no aplica | **No aplica: perfiles de uso** | default | La herramienta es local y monousuario, sin autenticación ni control de acceso que modelar |
| D-07 | ¿Se resuelve la contradicción de licencia detectada? | resolver ahora / registrar como bloqueante | **Registrar como bloqueante** (P-01) | default | Es una decisión legal del propietario del proyecto, no derivable del código |
| D-08 | ¿Se avisa de la ausencia de capa de texto? | mantener D-02 estricto / avisar | **Avisar** | usuario | Corrige D-02. La revisión de código del 2026-08-17 (hallazgo F8) mostró que `ratio('','') == 1.0` hace que un escaneado produzca un informe que afirma que no hay cambios: un fallo silencioso. El usuario aprobó aplicar los hallazgos de la revisión, lo que introduce la degradación controlada que D-02 había descartado. Sigue sin haber OCR, así que el alcance de la sección 6 no cambia |
| D-09 | ¿El informe en datos expresa el grado de diferencia como porcentaje de similitud o como recuentos? | porcentaje / recuentos / solo booleano | **Recuentos, más un booleano `identical`** | usuario | Un porcentaje exige fijar un denominador que nadie puede acordar (¿palabras del original, de ambos, cuánto vale una página entera añadida?) y produce un número indefendible; los recuentos son hechos y el consumidor deriva el ratio que necesite. Un booleano solo no distinguiría una coma de un documento reescrito |
| D-10 | ¿`--json` genera también el PDF? | ambos / solo JSON | **Solo JSON** | usuario | El caso de uso no necesita el documento. Nota: el ahorro de tiempo esperado **no se materializó** (ver P-08); el motivo real es el formato y no escribir un fichero grande innecesario |
