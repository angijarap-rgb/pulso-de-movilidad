# Metodología — Metro de Lima

## Origen y preparación

- [Publicación de estadísticas ferroviarias del MTC](https://www.gob.pe/institucion/mtc/informes-publicaciones/345063-estadistica-servicios-de-transporte-terrestre-por-ferrovia-servicio-de-pasajeros)
- [Excel oficial de tráfico mensual por estación](https://cdn.www.gob.pe/uploads/document/file/404675/345063-trafico-mensual-de-pasajeros-en-el-metro-de-lima-segun-estacion-2012-2025.xlsx?v=1785793887)
- SHA-256 del Excel descargado: `bdcdeaf76c5f87020664cad04909dc0f2296821b3542e4370ad1793e3b17a58e`

El Excel identifica a la ATU como fuente y al MTC como responsable de la elaboración. La ficha indica junio de 2025 y la hoja 2025 del archivo descargado contiene los doce meses con conteos. Se usaron las hojas 2022–2025 y se verificó que la suma de las 26 estaciones coincide con el total oficial de cada uno de los 48 meses. Se excluyeron las filas de totales, las notas y los años anteriores al convertir a CSV. El pipeline valida formato, duplicados, valores faltantes, cobertura y conteos no negativos.

## Pronóstico y evaluación

Se predicen pasajeros por estación para el mes siguiente al momento de emisión. La referencia estacional toma el valor del mismo mes del año anterior. El candidato usa un modelo de árboles con pérdida Poisson, el calendario y conteos de 2, 3 y 12 meses atrás. El rezago mínimo de dos meses y las brechas entre ventanas son supuestos de esta reproducción histórica. La disponibilidad real de cada dato en su fecha original no se verificó.

| Ventana | Meses |
|---|---|
| Entrenamiento | Enero a noviembre de 2023 |
| Validación | Enero a noviembre de 2024 |
| Prueba reservada | Enero a diciembre de 2025 |

Los datos de 2022 sirven de historial para los primeros rezagos. Los meses excluidos de las ventanas pueden servir como observaciones rezagadas cuando corresponda. Para promover al candidato se exige reducir el MAE de validación al menos 3 % y no empeorar el MAE de una estación por encima del mayor valor entre 10 % y 5 pasajeros. La prueba de 2025 se usa para reportar resultados después de la selección.

El monitoreo se agrupa por estación y trimestre. Una alerta de drift compara la media de la entrada estacional con la de validación, normalizada por el rango intercuartílico. Una alerta de desempeño compara el MAE observado con el de validación y se activa cuando aumenta más que el mayor valor entre 25 % y 5 pasajeros. Las alertas sirven para investigar cambios y se interpretan con el contexto de cada estación.
