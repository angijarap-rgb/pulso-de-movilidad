# Evaluación del pronóstico

La unidad es un día calendario de Nueva York y una zona de recogida. El horizonte es un día. Los conteos representan viajes completados registrados por TLC y cubren seis zonas seleccionadas. Sirven como aproximación parcial a la demanda. Quedan fuera los viajes que nunca se realizaron o se hicieron con otros medios.

## Datos y disponibilidad

El pipeline verifica que al menos el 99 % de fechas del archivo corresponda al mes solicitado. Exige una observación para cada zona seleccionada en cada día y rechaza archivos sin esa cobertura. Las filas con fechas nulas o fuera del mes quedan fuera de la agregación. El reporte registra sus cantidades y la huella SHA-256 de cada archivo.

TLC indica que publica mensualmente, normalmente con unos dos meses de demora. Para la reproducción se aproxima la publicación como 60 días tras el cierre del mes. Los rezagos de 98, 105, 112 y 119 días conservan el día de semana y dejan margen para ese supuesto. Las fechas reales de publicación pueden variar.

| Etapa | Fechas efectivas del informe inicial |
|---|---|
| Entrenamiento | 28 oct a 31 dic 2023 |
| Validación y promoción | 1 abr a 31 may 2024 |
| Prueba reservada | 1 sep a 31 oct 2024 |

Se dejan tres meses completos entre los conjuntos de etiquetas para que entrenamiento y promoción respeten la disponibilidad estimada al inicio de la siguiente etapa. Los meses intermedios también aportan observaciones rezagadas cuando corresponde. La prueba queda fuera de la selección del modelo.

## Comparación y alertas

El baseline usa la mediana de los cuatro rezagos. El candidato es un modelo de árboles con pérdida Poisson que usa zona, calendario y rezagos. Para promoverlo debe reducir el MAE global de validación al menos 3 % y no empeorar ninguna zona por encima del mayor valor entre 10 % de su MAE base y 5 viajes. Cada ejecución compara con la regla estacional fija y permite regresar a un paquete anterior mediante `pulso.activate`.

El reporte incluye MAE y WAPE. MAE es el error absoluto medio en viajes por zona y día. WAPE es la suma de errores absolutos dividida por los viajes observados.

Cada ventana de prueba se evalúa por mes y zona frente a validación. La alerta de drift se activa cuando la diferencia absoluta de medias de la variable estacional alcanza un rango intercuartílico de referencia, con un piso de un viaje para el denominador. La alerta de desempeño requiere etiquetas y se activa cuando el MAE aumenta más que el mayor valor entre 25 % y 5 viajes. Son umbrales operativos del MVP. Los cambios normales de calendario pueden generar alertas y ameritan revisar el contexto.

## Resultado de la primera demo

El modelo estacional quedó activo. En validación, su MAE fue 801,3 viajes frente a 809,4 del candidato. En la prueba reservada obtuvo un MAE de 576,1 y un WAPE de 13,1 %. Estos resultados corresponden a seis zonas y a las ventanas indicadas. El archivo `site/report.json` permite verificar métricas por zona y las predicciones de cada día.

Los informes históricos se interpretan como una reproducción. La automatización de GitHub puede reevaluar otra ventana manualmente. La demo pública muestra el informe que se haya revisado y publicado.
