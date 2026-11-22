🇬🇧 [Read in English](ai_usage.md)

# Uso de IA

Este documento explica cómo se han usado los asistentes de IA en el proyecto, para qué y quién ha tomado cada decisión.

## Resumen

La IA se ha usado como herramienta de apoyo durante todo el proyecto: para entender el enunciado, explorar alternativas de diseño, documentar decisiones, revisar código y generar los tests, la simulación y parte de la documentación. La arquitectura y todas las decisiones de diseño son de la autora. La IA explicaba las opciones y sus inconvenientes, y registraba o aplicaba las decisiones una vez tomadas.

Herramientas usadas:

- **Notion AI**: planificación, explicaciones y documentación de las decisiones de diseño en las notas del proyecto
- **Claude Code**: revisión de código y explicaciones durante la implementación, y generación de los tests, los mocks, la simulación y la documentación

## Principios

- **Decide la autora.** La IA proponía alternativas y explicaba sus limitaciones. La opción elegida, y el motivo, siempre fueron de la autora
- **Primero las decisiones, después el código.** El diseño se acordó y se dejó por escrito antes de implementarlo, y la IA trabajó a partir de esas decisiones escritas
- **Supuestos explícitos.** Cuando el enunciado dejaba algo abierto, la IA lo señalaba y la interpretación elegida se registraba como supuesto, no como requisito
- **Todo se revisa.** La autora revisó el contenido generado, y el código se ejecutó y se probó antes de aceptarlo

## Uso por área

### 1. Comprensión del enunciado y planificación

La IA ayudó a leer el enunciado y a organizar el trabajo.

- Organizó el proyecto en cuatro fases (documentación y diseño, diseño de pruebas, implementación y revisión) y las convirtió en tareas con vistas filtradas para su seguimiento
- Explicó los conceptos del ejercicio: agentes conversacionales, su ciclo de vida y los turnos, los modelos simulados y las integraciones HTTP
- Separó lo que debía implementarse de lo que podía simularse, y buscó repositorios de referencia sobre patrones de agentes y simulación HTTP

### 2. Exploración de alternativas de diseño

Ante cada cuestión abierta, la IA explicaba las opciones y sus limitaciones para que la autora eligiera.

- **Responsabilidades:** qué corresponde a la clase base y qué a cada agente, y la diferencia entre una acción genérica y una integración HTTP. La autora decidió que la clase base define el flujo y que `exec_action` sea genérico
- **Duplicados:** si comprobarlos dentro de la normalización o en un paso aparte, y cómo un `set` puede guardar claves de distintos tipos. La autora eligió una comprobación separada, con una tupla como clave en cobros y el texto normalizado en asistencia
- **Casos límite:** la diferencia entre `None` y una cadena vacía, la precisión y los valores especiales de `float`, y por qué los saltos de línea son un problema en las cabeceras HTTP. Cada uno terminó en una decisión o un supuesto registrado

### 3. Documentación de las decisiones

La IA mantuvo al día las notas de diseño a medida que se tomaban las decisiones.

- Registró cada decisión con su justificación: el orden del turno (normalizar, comprobar duplicados, ejecutar la acción y registrar la clave tras un `200`), el tratamiento de los datos temporales entre turnos y detener la conversación mostrando un error en lugar de reintentar
- Convirtió las decisiones acordadas en firmas de métodos, sin implementarlas
- Revisó la coherencia de las notas, señaló las contradicciones sin modificarlas y mantuvo actualizada la lista de decisiones pendientes
- Preparó conversaciones de ejemplo con resultados esperados, que después se convirtieron en los tests y en la simulación guionizada

### 4. Apoyo a la implementación

La autora escribió la implementación base (`agents/`, `models/`, `integrations/`, `config.py`). La IA apoyó ese trabajo sin sustituirlo.

- Preparó implementaciones de referencia de la arquitectura base a partir de las decisiones acordadas, que la autora usó como guía
- Explicó conceptos de Python a medida que surgían, como las clases abstractas, `Protocol`, `super()`, los atributos de instancia y de clase, `@property` y las expresiones regulares
- Revisó cada archivo a medida que se escribía, lo ejecutó y señaló errores (imports que faltaban, atributos declarados con `:` en lugar de `=`, dos clases fusionadas en una) para que la autora los corrigiera

### 5. Tests y simulación

La autora definió qué había que probar: las conversaciones de ejemplo y las reglas del diseño. El código de los tests y de la simulación se generó con IA a partir de ellas, así que sus decisiones de implementación son de la IA.

- Generó los tests unitarios, un archivo por componente, convirtiendo cada conversación de ejemplo en un test y añadiendo casos límite de validación
- Generó los mocks de los tests: modelos de conversación y de parser guionizados, y un cliente HTTP que responde `500` para probar la rama de fallo
- Generó la simulación guionizada con las conversaciones de ejemplo, y los scripts que ejecutan los tests y la simulación con una salida legible

### 6. Documentación del proyecto

- Redactó el README en inglés y en español, siguiendo la plantilla de README de la autora adaptada a este proyecto
- Redactó las guías de `docs/`: cómo añadir un agente y qué muestra cada conversación guionizada

## Responsabilidades

| Área | IA | Autora |
| --- | --- | --- |
| Planificación | Propuso fases y tareas | Aprobó el plan |
| Diseño | Explicó opciones e inconvenientes | Tomó todas las decisiones |
| Notas de diseño | Registró las decisiones | Las revisó |
| Implementación base | Explicó conceptos y revisó el código | Escribió el código |
| Tests y simulación | Los generó a partir de las decisiones | Definió los casos y revisó el resultado |
| Documentación | Redactó los borradores | Definió el contenido y lo revisó |

## Qué no hizo la IA

- No tomó decisiones de diseño ni eligió entre alternativas
- No escribió la implementación base que está en el repositorio
- No cambió decisiones ni corrigió contradicciones en las notas sin la aprobación de la autora
