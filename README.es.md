<div align="center">

[🇬🇧 English](README.md) · [🇪🇸 Español](README.es.md)

</div>

# Prueba técnica de Ringr · Agentes conversacionales

## Tabla de contenidos

- [Descripción](#descripción)
- [Instalación](#instalación)
  - [Requisitos](#requisitos)
  - [Preparación](#preparación)
- [Uso](#uso)
  - [Ejecutar los tests](#ejecutar-los-tests)
  - [Ejecutar la simulación guionizada](#ejecutar-la-simulación-guionizada)
  - [Organización de los tests y las simulaciones](#organización-de-los-tests-y-las-simulaciones)
  - [Usar un agente desde código](#usar-un-agente-desde-código)
- [Funcionalidades](#funcionalidades)
- [Decisiones de diseño](#decisiones-de-diseño)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Documentación](#documentación)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Proceso de desarrollo](#proceso-de-desarrollo)
- [Recursos](#recursos)
- [Uso de IA](#uso-de-ia)
- [Créditos](#créditos)

## Descripción

Solución a la prueba técnica de Delivery Engineer de Ringr: un pequeño proyecto de Python orientado a objetos con dos agentes conversacionales que procesan información de una conversación y ejecutan acciones mediante una integración HTTP simulada.

En cada turno, un agente obtiene la respuesta de la persona a través de un modelo de conversación, extrae datos estructurados con un modelo parser, los valida y normaliza, y decide si debe ejecutar una acción externa:

- **`DebtAgent`** registra compromisos de pago. Cuando tiene una fecha y un importe válidos, envía un POST a `https://api.ringr.debt/v1/commitment`.
- **`AssistanceAgent`** registra solicitudes de clientes para agentes humanos. Cuando hay una solicitud, envía un POST a `https://api.ringr.assistance/v1/request`.

No se hacen llamadas HTTP reales ni a modelos de lenguaje. El objetivo es un diseño fácil de ampliar con nuevos agentes, acciones e integraciones, manteniendo un código limpio, robusto y testeable.

## Instalación

### Requisitos

- Python 3.10 o superior. Probado con Python 3.13 en macOS. Python 3.9 no funciona, porque el código usa anotaciones de tipo `X | None`
- Sin dependencias externas: el proyecto solo usa la biblioteca estándar de Python

Comprueba tu versión de Python:

    python3 --version

### Preparación

    git clone https://github.com/telufulu/ringr_technical_test.git
    cd ringr_technical_test

No hay nada que compilar ni instalar.

## Uso

El proyecto no tiene un programa principal: los agentes están pensados para recibir modelos de conversación y de parser reales. Para verlos funcionar, ejecuta los tests o la simulación guionizada. No hace falta un Makefile: cada uno es un único comando.

### Ejecutar los tests

    python3 tests/run_tests.py

La salida se agrupa por componente (`Agent`, `AssistanceAgent`, `DebtAgent`, `HttpClient`), con una línea por test. La última línea debería ser:

    ✓ 35 tests, 0 failures, 0 errors

El script devuelve el código de salida 1 si falla algún test. Los tests también se pueden ejecutar con la salida estándar de `unittest`, desde la raíz del repositorio:

    python3 -m unittest discover -s tests -v

### Ejecutar la simulación guionizada

    python3 tests/run_simulation.py               # las diez conversaciones
    python3 tests/run_simulation.py debt          # solo las de DebtAgent
    python3 tests/run_simulation.py assistance 3  # solo la conversación 3 de AssistanceAgent

Cada turno muestra la pregunta del agente, la respuesta de la persona, el texto procesado, la salida del parser y lo que ha hecho el agente. Por ejemplo:

    Turn 2
      Agent:  ¿Qué importe quieres pagar?
      Person: 150 euros
      Processed text: 'Importe comprometido: 150 euros'
      Parser: {'commitment_date': None, 'committed_amount': 150.0}
      → POST https://api.ringr.debt/v1/commitment
        body: {'commitment_date': '2090-05-20', 'committed_amount': 150.0}
      Pending data: {'commitment_date': None, 'committed_amount': None}
      Registered keys: [('2090-05-20', 150.0)]

Cada conversación, y lo que muestra, se describe en [docs/scripted_conversations.es.md](docs/scripted_conversations.es.md).

Los dos scripts funcionan desde cualquier directorio. Los colores se desactivan si la salida no es un terminal o si existe la variable de entorno `NO_COLOR`.

### Organización de los tests y las simulaciones

| Ruta | Contenido |
| --- | --- |
| `tests/test_agent.py` | Flujo común de cada turno, probado con un agente mínimo que no usa HTTP |
| `tests/test_debt_agent.py` | `DebtAgent`: escenarios de conversación, petición HTTP y validación |
| `tests/test_assistance_agent.py` | `AssistanceAgent`: escenarios de conversación, petición HTTP y validación |
| `tests/test_http.py` | Cliente HTTP simulado |
| `tests/mocked_models/` | Modelos de conversación y parser guionizados, y un cliente HTTP que responde `500` |
| `tests/simulations/scripted_conversation.py` | Las diez conversaciones guionizadas |
| `tests/run_tests.py` | Ejecuta todos los tests con una salida agrupada y con colores |
| `tests/run_simulation.py` | Ejecuta la simulación completa, la de un agente o una sola conversación |

Los tests comprueban los resultados automáticamente. La simulación solo muestra lo que ocurre en cada turno.

### Usar un agente desde código

Un agente acepta cualquier objeto con los métodos `answer_user()` y `parse_data()`. No necesitan heredar de ninguna clase:

```python
from agents.debt_agent import DebtAgent


class MyConversationModel:
    def answer_user(self) -> str:
        return "Commitment of 150 euros for 20 May 2090"


class MyParserModel:
    def parse_data(self, conversation_text: str) -> dict:
        return {"commitment_date": "2090-05-20", "committed_amount": 150.0}


agent = DebtAgent(MyConversationModel(), MyParserModel())
can_continue = agent.handle_turn()       # True
agent.http_client.last_request().body    # {'commitment_date': '2090-05-20', 'committed_amount': 150.0}
```

Ejecútalo desde la raíz del repositorio, para que se puedan importar los módulos `agents`, `models`, `integrations` y `config`.

## Funcionalidades

- Clase abstracta `Agent` con el flujo común de cada turno en `handle_turn`: obtener la respuesta, parsearla, normalizarla, comprobar duplicados y ejecutar la acción
- `DebtAgent`, que reúne la fecha y el importe en uno o varios turnos y registra el compromiso cuando ambos son válidos
- `AssistanceAgent`, que normaliza las solicitudes con `lower()` y `strip()` y las registra
- Cliente HTTP simulado que construye la petición (método, URL, cabeceras y cuerpo), la guarda para poder inspeccionarla y devuelve `200`
- Autenticación con Bearer token, más una cabecera adicional por cada campo parseado, con el mismo nombre
- Sin acciones duplicadas dentro de una conversación
- Gestión de fallos: ante una respuesta distinta de `200`, el agente muestra un error, conserva sus datos y detiene la conversación sin reintentar
- 35 tests unitarios y diez conversaciones guionizadas

## Decisiones de diseño

- **Template method.** `Agent.handle_turn` define el flujo una sola vez. Cada agente solo implementa `normalize_data`, `exec_action` y `clear_temp_data`, así que un agente nuevo no modifica los existentes.
- **El flujo común no supone HTTP.** Una acción tiene éxito si `exec_action` termina y falla si lanza `ActionFailedError`. Solo los agentes que necesitan HTTP reciben un cliente HTTP.
- **Contratos de los modelos como `Protocol`.** `ConversationModel` y `ParserModel` describen los métodos que necesitan los agentes. Sirve cualquier objeto con esos métodos, sin herencia. El enunciado indica que no hacen falta subclases de estos modelos.
- **`answer_user` cubre todo el intercambio.** El modelo de conversación habla con la persona y devuelve una versión procesada y concisa de su respuesta, que el agente pasa al parser. Por eso `handle_turn` solo devuelve si la conversación puede continuar.
- **Datos entre turnos.** Un `None` del parser significa «no aportado en este turno», así que se conserva el valor guardado. Un valor nuevo inválido anula el guardado.
- **Duplicados.** Cada agente guarda un `set` con las claves de las acciones ya registradas: `(fecha, importe)` en cobros y la solicitud normalizada en asistencia. Una clave solo se añade tras una respuesta `200`.
- **Reglas de negocio adicionales.** El importe debe ser mayor que cero y la fecha debe ser una fecha real en formato `yyyy-mm-dd` y estrictamente posterior a hoy. El enunciado no las exige: son supuestos de esta solución.
- **Configuración.** El token y los endpoints son constantes en `config.py`. El token es el valor de prueba del enunciado.

## Estructura del proyecto

    ringr_technical_test/
    ├── agents/
    │   ├── agent.py                  # Agent abstracto con el flujo común
    │   ├── assistance_agent.py       # AssistanceAgent
    │   └── debt_agent.py             # DebtAgent
    ├── docs/
    │   ├── adding_an_agent.md        # Guía para añadir un agente (+ .es.md)
    │   ├── ai_usage.md               # Cómo se usó la IA en el proyecto (+ .es.md)
    │   └── scripted_conversations.md # Las diez conversaciones guionizadas (+ .es.md)
    ├── integrations/
    │   └── http.py                   # Cliente HTTP simulado
    ├── models/
    │   ├── conversation_model.py     # Protocolo ConversationModel
    │   └── parser_model.py           # Protocolo ParserModel
    ├── tests/
    │   ├── mocked_models/            # Modelos guionizados y cliente HTTP que falla
    │   ├── simulations/
    │   │   └── scripted_conversation.py
    │   ├── run_simulation.py
    │   ├── run_tests.py
    │   ├── test_agent.py
    │   ├── test_assistance_agent.py
    │   ├── test_debt_agent.py
    │   └── test_http.py
    ├── config.py                     # Token y endpoints
    ├── README.md
    └── README.es.md

## Documentación

- [Añadir un agente nuevo](docs/adding_an_agent.es.md): qué archivos hay que modificar y qué tener en cuenta, con un ejemplo completo
- [Conversaciones guionizadas](docs/scripted_conversations.es.md): cada conversación de la simulación y lo que muestra
- [Uso de IA](docs/ai_usage.es.md): cómo se usó la IA en cada área del proyecto y quién tomó cada decisión

Todos los documentos están disponibles en inglés y en español.

## Limitaciones conocidas

- Los modelos de conversación y de parser no están implementados: son contratos, y los tests y la simulación usan mocks guionizados
- No hay una simulación de chat interactivo, solo la guionizada
- El conjunto de claves registradas vive en memoria, por instancia del agente. Se pierde al terminar el proceso y no se comparte entre conversaciones
- Un compromiso se identifica por su fecha y su importe, así que dos compromisos reales con la misma fecha y el mismo importe se tratan como uno solo
- Si una persona corrige el importe después de registrar un compromiso, se registra un segundo compromiso: el primero no se anula
- «Hoy» es la fecha local de la máquina que ejecuta el código
- Los importes son `float`, sin límite superior ni redondeo, así que están sujetos a la precisión de los números en coma flotante
- Los valores de las cabeceras no se codifican ni se comprueban: se asume que el parser devuelve texto válido para una cabecera HTTP
- No hay reintentos automáticos ni una gestión de errores detallada: una acción fallida detiene la conversación
- El token está en `config.py`. En un sistema real se guardaría fuera del código, por ejemplo en variables de entorno

## Proceso de desarrollo

Además de la solución final en `main`, el repositorio conserva las ramas usadas durante el desarrollo, para que también pueda consultarse el proceso de aprendizaje y desarrollo. Muestran las alternativas probadas y la evolución de las decisiones técnicas a lo largo del proyecto.

La rama de pruebas es [`draft`](https://github.com/telufulu/ringr_technical_test/tree/draft).

## Recursos

### Documentación de Python

- `abc`: Abstract Base Classes — https://docs.python.org/3/library/abc.html
- `typing.Protocol` — https://docs.python.org/3/library/typing.html#typing.Protocol
- `unittest`: Unit testing framework — https://docs.python.org/3/library/unittest.html
- `argparse`: Command-line parsing — https://docs.python.org/3/library/argparse.html
- `datetime.date.fromisoformat` — https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
- `re`: Regular expressions — https://docs.python.org/3/library/re.html
- PEP 8: Style Guide for Python Code — https://peps.python.org/pep-0008/

### Guías para escribir un README

- How to Write a Good README – freeCodeCamp — https://www.freecodecamp.org/news/how-to-write-a-good-readme-file/
- Make a README — https://www.makeareadme.com/

## Uso de IA

Durante el proyecto se han usado asistentes de IA (entre ellos, Claude Code y Notion AI):

- Las decisiones de arquitectura y diseño son de la autora. Se definieron y documentaron antes y durante la implementación, y la IA siempre se ha guiado por ellas
- La implementación base (`agents/`, `models/`, `integrations/` y `config.py`) la escribió la autora, con ayuda de la IA para explicar conceptos, implementaciones de referencia y revisión de código
- Los tests, los mocks de los tests, la simulación guionizada, los scripts para ejecutar los tests y la simulación, y la documentación de `docs/` se generaron con IA. La IA ha estado siempre supervisada y guiada por las decisiones de arquitectura del proyecto, y la autora ha revisado el resultado

En [docs/ai_usage.es.md](docs/ai_usage.es.md) se describe cómo se usó la IA en cada área, con ejemplos.

## Créditos

- Redes de telufulu
  - [GitHub](https://github.com/telufulu)
  - [LinkedIn](https://www.linkedin.com/in/teresa-b-lufuluabo-pastor-659702204/)
