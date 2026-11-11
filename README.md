# Pulso de Movilidad — Metro de Lima

Pronóstico mensual de pasajeros por estación de la Línea 1. La demo compara una referencia estacional y un modelo de árboles con las cifras observadas durante 2025.

Los datos provienen de un Excel oficial del Ministerio de Transportes y Comunicaciones (MTC), elaborado con información de la ATU. La copia normalizada incluida en `datasets/metro-lima.csv` tiene 1.248 observaciones de 26 estaciones entre enero de 2022 y diciembre de 2025. [Fuente oficial y metodología](docs/metodologia.md).

## Ver la demo

En PowerShell, desde la carpeta del repositorio:

```powershell
py -3.10 -m http.server 8080 --directory site --bind 127.0.0.1
```

Abre [http://127.0.0.1:8080](http://127.0.0.1:8080). Elige una estación para actualizar el gráfico, los valores mensuales y el monitoreo trimestral. Las métricas generales resumen las 26 estaciones. Puedes usar Python 3.12 en lugar de 3.10 para este comando si ya lo tienes.

## Entrenar y probar la API

El pipeline usa Python 3.12. Ejecuta estos comandos en otra terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pulso.pipeline --publish site/report.json
.\.venv\Scripts\python.exe -m uvicorn pulso.api:app --host 127.0.0.1 --port 8000
```

Abre [Swagger](http://127.0.0.1:8000/docs) para probar la API. Consulta `GET /v1/stations` para obtener los códigos. En `GET /v1/forecast`, envía un código de estación como `station` y el primer día del mes como `month`, por ejemplo `2025-03-01`.

## Revisar experimentos

```powershell
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri sqlite:///runs/mlflow.db --host 127.0.0.1 --port 5000
```

En [MLflow](http://127.0.0.1:5000), revisa el experimento `pulso-metro-lima` y el alias `champion`. Para reactivar un paquete anterior, ejecuta `python -m pulso.activate ID_DE_EJECUCION` con el Python del entorno virtual y reinicia la API.

## Contenedor opcional

Después de entrenar:

```powershell
docker build -t pulso-api .
docker run --rm -p 127.0.0.1:8000:8000 --mount "type=bind,source=$($PWD.Path)/runs,target=/app/runs,readonly" pulso-api
```

## Publicar

Consulta [docs/subir-a-github.md](docs/subir-a-github.md) para revisar los cambios en una rama y actualizar la demo en Pages.
