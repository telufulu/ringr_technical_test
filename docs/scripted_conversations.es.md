🇬🇧 [Read in English](scripted_conversations.md)

# Conversaciones guionizadas

La simulación guionizada ejecuta diez conversaciones de ejemplo, cinco con `DebtAgent` y cinco con `AssistanceAgent`, y muestra en el terminal qué ocurre en cada turno.

Es una simplificación para trabajar sin un modelo de lenguaje real. Las preguntas del agente, las respuestas de la persona, el texto procesado y la salida del parser están escritos de antemano. La integración HTTP es la simulada, así que no se hace ninguna llamada por la red.

La simulación sirve para **ver** el comportamiento de los agentes, no para comprobarlo. Las mismas conversaciones están cubiertas por pruebas automáticas en `tests/test_debt_agent.py` y `tests/test_assistance_agent.py`, que sí verifican cada resultado.

## Ejecución

Desde cualquier directorio:

```bash
python3 tests/run_simulation.py               # las diez conversaciones
python3 tests/run_simulation.py debt          # solo las de DebtAgent
python3 tests/run_simulation.py assistance 3  # solo la conversación 3 de AssistanceAgent
```

`python3 tests/simulations/scripted_conversation.py` también ejecuta las diez conversaciones.

Requiere Python 3.10 o superior y no necesita dependencias externas.

## Qué muestra cada turno

| Línea | Significado |
| --- | --- |
| `Agent` | Pregunta que el modelo de conversación hace a la persona |
| `Person` | Lo que responde la persona |
| `Processed text` | Versión procesada de la respuesta que `answer_user` devuelve al agente |
| `Parser` | Diccionario que devuelve `parse_data` en ese turno. El parser lee la conversación desde su propio estado: el agente no le pasa el texto procesado |
| `→ POST ...` / `→ No request sent` | Si el agente ha enviado una petición simulada, con su URL y su cuerpo |
| `Pending data` | Datos temporales que el agente conserva para los turnos siguientes |
| `Registered keys` | Claves de las acciones ya registradas con éxito en la conversación |

Cada conversación empieza con una instancia nueva del agente y con el conjunto de claves vacío. Dentro de una conversación se usa siempre la misma instancia, como en una conversación real.

En los escenarios de cobros se usan fechas de 2090 para que siempre sean posteriores al día de ejecución.

## DebtAgent

El agente de cobros registra compromisos de pago. Necesita una fecha (`commitment_date`) y un importe (`committed_amount`) válidos, que pueden llegar en el mismo turno o en turnos distintos. Envía un POST a `https://api.ringr.debt/v1/commitment` cuando tiene los dos.

### 1. Datos completos en un turno

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «Pagaré 150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |

**Qué se comprueba**

- Con fecha e importe válidos en el mismo turno, el agente envía un único POST con los dos campos en el cuerpo
- Tras la respuesta `200`, la clave `("2090-05-20", 150.0)` se registra
- Los datos temporales vuelven a `None` y el agente queda listo para otro compromiso

### 2. Datos recibidos en turnos distintos

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «El 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": None}` |
| 2 | «150 euros» | `{"commitment_date": None, "committed_amount": 150.0}` |

**Qué se comprueba**

- En el turno 1 falta el importe: el agente guarda la fecha y no envía nada
- En el turno 2, `None` en la fecha significa «no aportada en este turno», así que se conserva la fecha anterior
- Con los dos datos completos, se envía un POST con la fecha del turno 1 y el importe del turno 2

### 3. Un dato nuevo inválido sustituye al anterior

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «El 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": None}` |
| 2 | «Sí, al 30 de febrero de 2090» | `{"commitment_date": "2090-02-30", "committed_amount": None}` |
| 3 | «El 21 de mayo de 2090 y 150 euros» | `{"commitment_date": "2090-05-21", "committed_amount": 150.0}` |

**Qué se comprueba**

- El 30 de febrero tiene el formato correcto, pero no es una fecha real, así que se rechaza
- Una fecha nueva inválida anula la fecha válida guardada antes: el campo pasa a `None`
- El agente no reutiliza la fecha anterior y solo envía un POST con la fecha nueva del turno 3

### 4. Duplicado y compromiso distinto en la misma fecha

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |
| 2 | «Sí, 150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |
| 3 | «Sí, 200 euros para esa misma fecha» | `{"commitment_date": "2090-05-20", "committed_amount": 200.0}` |

**Qué se comprueba**

- En el turno 2, la clave ya está registrada: no se envía otro POST, los datos temporales se limpian y el registro de claves no cambia
- En el turno 3 coincide la fecha, pero no el importe. Es un compromiso distinto y sí se envía
- En total se envían dos POST, no tres, y quedan registradas las dos claves

Un compromiso se identifica por la pareja fecha e importe. Es una simplificación de la prueba: dos compromisos reales con la misma fecha y el mismo importe se tratarían como uno solo.

### 5. Respuesta HTTP no exitosa

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |

En esta conversación, la integración HTTP se sustituye por `FailingHttpClient`, que devuelve `500` en lugar de `200`.

**Qué se comprueba**

- El agente intenta enviar la petición, recibe el error y muestra en rojo «Sorry, something went wrong. Please try again later»
- La clave no se registra y los datos temporales se conservan
- `handle_turn` devuelve `False`, la conversación se detiene y no hay reintento automático

## AssistanceAgent

El agente de atención al cliente registra solicitudes para agentes humanos. Acepta cualquier texto en `request`, incluida la cadena vacía, y lo normaliza con `lower()` y `strip()`. Envía un POST a `https://api.ringr.assistance/v1/request` con el texto normalizado.

### 1. Solicitud válida

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «Necesito una copia de mi contrato» | `{"request": "Necesito una copia de mi contrato"}` |

**Qué se comprueba**

- La solicitud se normaliza a `"necesito una copia de mi contrato"`
- Se envía un POST con el texto normalizado en el cuerpo y en la cabecera `request`
- Tras la respuesta `200`, la clave se registra y la solicitud temporal vuelve a `None`

### 2. No hay solicitud

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «Solo quería saber el horario» | `{"request": None}` |

**Qué se comprueba**

- `None` significa que no hay nada que registrar
- No se envía ningún POST y el registro de claves sigue vacío

### 3. Duplicado tras normalizar

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «Necesito una copia de mi contrato» | `{"request": "Necesito una copia de mi contrato"}` |
| 2 | «Sí, necesito una copia de mi contrato» | `{"request": "  NECESITO UNA COPIA DE MI CONTRATO  "}` |

**Qué se comprueba**

- El turno 1 registra la clave normalizada
- En el turno 2, el parser devuelve la misma solicitud en mayúsculas y con espacios en los extremos. Tras normalizar, la clave coincide, así que es un duplicado
- No se envía otro POST. En total se envía uno

El texto procesado es el mismo en los dos turnos, pero el parser devuelve resultados distintos. El parser no depende del texto procesado: el parser simulado devuelve sus resultados por orden de turno.

### 4. Cadena vacía y otra solicitud

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | (introduce una cadena de espacios) | `{"request": "   "}` |
| 2 | «Una copia de mi contrato» | `{"request": "Una copia de mi contrato"}` |

**Qué se comprueba**

- Al eliminar los espacios, la solicitud queda como `""`. La cadena vacía es una solicitud válida, distinta de `None`, y se envía
- La solicitud del turno 2 es una clave distinta de la vacía y también se envía
- En total se envían dos POST y quedan registradas las dos claves

### 5. Respuesta HTTP no exitosa

| Turno | Persona | Parser |
| --- | --- | --- |
| 1 | «Necesito una copia de mi contrato» | `{"request": "Necesito una copia de mi contrato"}` |

Como en la conversación 5 de cobros, la integración HTTP devuelve `500`.

**Qué se comprueba**

- El agente muestra el mensaje de error en rojo
- La solicitud normalizada y su clave se conservan, y no se registra nada
- `handle_turn` devuelve `False`, la conversación se detiene y no hay reintento automático

## Cómo añadir una conversación

Las conversaciones están definidas en la lista `SCENARIOS` de `tests/simulations/scripted_conversation.py`. Para añadir una nueva:

1. Crea una entrada con `debt_scenario(...)` o `assistance_scenario(...)`, indicando un número que no esté en uso, un título, el resultado esperado y la lista de turnos
2. En cada turno, indica `agent`, `person`, `processed` y `parsed`
3. Para simular un fallo HTTP, pasa `http_client=failing_http_client`

La nueva conversación estará disponible directamente en `tests/run_simulation.py`.
