# Pulso de Movilidad

Pronóstico diario de viajes completados en taxi amarillo para seis zonas de Nueva York. El proyecto compara una regla estacional con un modelo de árboles y conserva un historial de por qué se promovió o se rechazó cada candidato.

La demo incluida reproduce septiembre y octubre de 2024 con datos de NYC Taxi & Limousine Commission (TLC). El informe conserva la versión de la ejecución y los hashes de sus archivos de origen.

## Abrir la demo

En PowerShell, abre la carpeta que contiene este README. Con Python 3.12 instalado:

```powershell
py -3.12 -m http.server 8080 --directory site --bind 127.0.0.1
```

Entra en [http://localhost:8080](http://localhost:8080). Puedes cambiar la zona, comparar ambas predicciones con los viajes observados y revisar las alertas mensuales. El reporte ya viene en el ZIP.

## Entrenar y probar la API

Instala las dependencias en un entorno virtual. Los comandos funcionan sin activar el entorno en PowerShell.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Para recorrer el pipeline con una muestra sintética y sin descargar Parquet:

```powershell
.\.venv\Scripts\python.exe -m pulso.pipeline --synthetic
$env:PULSO_SOURCE = 'synthetic'
.\.venv\Scripts\python.exe -m uvicorn pulso.api:app --host 127.0.0.1 --port 8000
```

Abre [Swagger](http://127.0.0.1:8000/docs) o consulta [un pronóstico de ejemplo](http://127.0.0.1:8000/v1/forecast?day=2024-09-01&zone=48). `/health` informa qué ejecución cargó la API.

Para repetir la evaluación real, detén Uvicorn con Ctrl+C y usa:

```powershell
.\.venv\Scripts\python.exe -m pulso.pipeline --publish site/report.json
$env:PULSO_SOURCE = 'tlc'
.\.venv\Scripts\python.exe -m uvicorn pulso.api:app --host 127.0.0.1 --port 8000
```

La primera ejecución real descarga 16 archivos Parquet, cerca de 0,9 GB en total. En las siguientes se reutilizan los archivos de `data/raw`. Puedes pasar `--start AAAA-MM` para evaluar otra ventana de 16 meses ya publicados. La ruta con datos reales necesita internet al descargar. El entrenamiento y la API funcionan en CPU.

En macOS o Linux, crea el entorno con `python3.12 -m venv .venv`, usa `.venv/bin/python` y exporta `PULSO_SOURCE` desde tu shell si vas a servir el escenario sintético.

## Revisar experimentos y volver a una versión

```powershell
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri sqlite:///runs/mlflow.db --host 127.0.0.1 --port 5000
```

En [MLflow](http://127.0.0.1:5000) puedes revisar los experimentos `pulso-tlc` y `pulso-synthetic` según lo que hayas ejecutado. El registro conserva ambos modelos y apunta `champion` a la versión activa. Cada ejecución también guarda un reporte y un paquete local en `runs/versions`. Ejecuta un pipeline a la vez por carpeta de trabajo.

Para volver a una ejecución anterior, reemplaza `ID_DE_EJECUCION` por un ID mostrado en el reporte o en la salida del pipeline y reinicia la API.

```powershell
.\.venv\Scripts\python.exe -m pulso.activate ID_DE_EJECUCION
```

## Contenedor opcional

Después de entrenar con datos TLC, desde PowerShell:

```powershell
docker build -t pulso-api .
docker run --rm -p 127.0.0.1:8000:8000 --mount "type=bind,source=$($PWD.Path)/runs,target=/app/runs,readonly" pulso-api
```

Para servir la muestra sintética, agrega `-e PULSO_SOURCE=synthetic` antes de `pulso-api`. Usa los artefactos producidos por tu propia ejecución.

## Publicar en GitHub

En [docs/subir-a-github.md](docs/subir-a-github.md) están los commits por etapas y la configuración de Pages. GitHub Actions ejecuta las pruebas en cada cambio a `main` y en pull requests. El workflow manual **Reevaluar datos TLC** genera un informe descargable para otra ventana. La publicación de Pages también se dispara manualmente y sirve la carpeta `site`.

El sitio público explora predicciones precalculadas. FastAPI permite solicitar predicciones nuevas desde tu equipo.

## Metodología

[Evaluación, retraso de publicación y monitoreo](docs/metodologia.md) · [Fuente y diccionario de NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
