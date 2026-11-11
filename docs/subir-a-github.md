# Actualizar la demo publicada

Aplica el ZIP sobre tu copia del repositorio en una rama como `feature/metro-lima`. Prueba la demo en local y revisa `git status --short` antes de preparar los cambios.

```powershell
git add datasets/metro-lima.csv pulso/data.py pulso/features.py pulso/evaluation.py pulso/pipeline.py pulso/registry.py pulso/api.py tests/test_pulso.py
git commit -m "Adaptar el pronóstico a las estaciones del Metro de Lima"
git add site README.md docs .github/workflows/evaluate.yml
git commit -m "Actualizar la demo con los resultados del Metro de Lima"
git push -u origin feature/metro-lima
```

Abre un pull request hacia `main`. Cuando pasen las pruebas y revises los cambios, fusiona el pull request. En **Actions → Publicar demo**, ejecuta el flujo con la rama `main`. El sitio se publica en la dirección de Pages del repositorio.
