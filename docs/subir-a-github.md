# Subir Pulso de Movilidad por partes

Crea en GitHub un repositorio **público y vacío** llamado `pulso-de-movilidad`. No agregues README ni plantilla de licencia durante la creación. Extrae el ZIP y abre en VS Code la carpeta que contiene `README.md`. Ejecuta los comandos en PowerShell desde esa carpeta.

## 1. Base y lectura de datos

```powershell
git init -b main
git remote add origin https://github.com/TU_USUARIO/pulso-de-movilidad.git
git add .gitignore requirements.txt requirements-dev.txt pulso/__init__.py pulso/data.py
git diff --cached --stat
git commit -m "Preparar entorno y validar datos de viajes"
git push -u origin main
```

Reemplaza `TU_USUARIO` por tu usuario real. Este bloque sube la configuración y la ingestión.

## 2. Entrenamiento y evaluación

```powershell
git add pulso/features.py pulso/evaluation.py pulso/registry.py pulso/pipeline.py pulso/activate.py
git diff --cached --stat
git commit -m "Entrenar y evaluar modelos con ventanas temporales"
git push
```

Antes de pasar al siguiente bloque, puedes ejecutar el entrenamiento sintético indicado en el README y revisar la decisión en `runs`.

## 3. API, pruebas y contenedor

```powershell
git add pulso/api.py tests Dockerfile .dockerignore .github/workflows/ci.yml
git diff --cached --stat
git commit -m "Servir pronósticos y verificar el pipeline"
git push
```

En la pestaña **Actions** podrás ver la ejecución de **Pruebas**.

## 4. Demo pública y documentación

```powershell
git add site docs README.md .github/workflows/pages.yml .github/workflows/evaluate.yml
git diff --cached --stat
git commit -m "Publicar la demo histórica y documentar los resultados"
git push
```

1. Ve a **Settings → Pages** y selecciona **GitHub Actions** en **Source**.
2. Ve a **Actions → Publicar demo → Run workflow** y selecciona `main`.
3. Abre el enlace que devuelve el despliegue. Cambia de zona y comprueba que actualicen el gráfico y la tabla.
4. Usa **Reevaluar datos TLC** cuando quieras probar una ventana nueva. Revisa su informe antes de actualizar el reporte que sirve la demo.

Los archivos Parquet descargados, el entorno virtual y los modelos locales quedan excluidos por `.gitignore`. Usa `git status --short` al final para revisar el estado.
