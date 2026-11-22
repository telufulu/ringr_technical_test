🇬🇧 [Read in English](adding_an_agent.md)

# Añadir un agente nuevo

Esta guía explica qué archivos hay que modificar para añadir un agente nuevo. Usa como ejemplo un `CallbackAgent` ficticio, que registra el teléfono en el que una persona quiere que la llamen.

El flujo común de cada turno está en `Agent.handle_turn` (`agents/agent.py`) y no hay que cambiarlo. Un agente nuevo solo define sus datos, su validación y su acción.

## 1. Añadir la configuración

Si el agente llama a un endpoint nuevo, añádelo a `config.py` junto a los existentes:

```python
CALLBACK_REQUEST_URL = "https://api.ringr.callback/v1/request"
```

## 2. Crear el agente

Crea `agents/callback_agent.py` con una clase que herede de `Agent` e implemente sus tres métodos abstractos:

| Método | Qué debe hacer |
| --- | --- |
| `normalize_data(parsed_data)` | Validar y normalizar la salida del parser, actualizar los datos temporales y asignar `self.key` cuando la acción esté lista. Mientras falten datos, `self.key` debe seguir en `None` |
| `exec_action()` | Ejecutar la acción con los datos temporales. Lanzar `ActionFailedError` si falla |
| `clear_temp_data()` | Vaciar los datos temporales. La clase base lo llama tras una acción con éxito o un duplicado |

```python
from typing import Any

from agents.agent import ActionFailedError, Agent
from config import API_TOKEN, CALLBACK_REQUEST_URL
from integrations.http import HttpClient
from models.conversation_model import ConversationModel
from models.parser_model import ParserModel


class CallbackAgent(Agent):
    """Registers the phone number a person wants to be called back on."""

    def __init__(
        self,
        conversation_model: ConversationModel,
        parser_model: ParserModel,
        http_client: HttpClient | None = None,
    ) -> None:
        super().__init__(conversation_model, parser_model)
        self.http_client = http_client if http_client is not None else HttpClient()
        self.temp_phone: str | None = None

    def clear_temp_data(self) -> None:
        self.temp_phone = None

    def normalize_data(self, parsed_data: dict[str, Any]) -> None:
        raw_phone = parsed_data.get("callback_phone")
        if isinstance(raw_phone, str) and raw_phone.strip():
            self.temp_phone = raw_phone.strip()
        elif raw_phone is not None:
            self.temp_phone = None
        self.key = self.temp_phone

    def exec_action(self) -> None:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "callback_phone": self.temp_phone,
        }
        body = {"callback_phone": self.temp_phone}
        status = self.http_client.post(CALLBACK_REQUEST_URL, headers, body)
        if status != 200:
            raise ActionFailedError(f"Callback request failed with HTTP {status}")
```

A tener en cuenta:

- **Llama a `super().__init__`** para que la clase base cree los modelos, `key` y el conjunto de claves registradas
- **La clave debe ser hashable** (un `str`, una `tuple`...), porque se guarda en un `set`. Es lo que decide qué cuenta como duplicado
- **Comprueba la ausencia de clave con `is None`**, no por su valor de verdad, para no perder valores válidos como la cadena vacía
- **`None` del parser significa «no aportado en este turno»**. En ese caso conserva el valor guardado, como hacen los agentes existentes
- **La acción no tiene por qué ser HTTP.** La clase base solo necesita que `exec_action` termine si va bien y lance `ActionFailedError` si falla. Un agente que no use HTTP no necesita `http_client`
- **Construye la cabecera `Authorization` de forma explícita** con el token de `config.py`, y añade solo los campos de datos conocidos como cabeceras adicionales, para que los datos del parser no puedan sobrescribirla
- **Recibe el cliente HTTP como parámetro opcional**, para que los tests puedan pasar un cliente que falle

## 3. Añadir tests

Crea `tests/test_callback_agent.py`. Usa los mocks de `tests/mocked_models/` para guionizar la conversación y el parser, y `FailingHttpClient` para probar la rama de fallo:

```python
import unittest

from agents.callback_agent import CallbackAgent
from mocked_models.mock_conversation_model import MockConversationModel
from mocked_models.mock_parser_model import MockParserModel


class CallbackAgentScenarioTests(unittest.TestCase):
    """CallbackAgent · conversation scenarios"""

    def test_phone_is_sent_once(self):
        agent = CallbackAgent(
            MockConversationModel(["Call me on 600 000 000", "Call me on 600 000 000"]),
            MockParserModel([{"callback_phone": "600 000 000"}, {"callback_phone": "600 000 000"}]),
        )

        agent.handle_turn()
        agent.handle_turn()

        self.assertEqual(len(agent.http_client.requests), 1)
```

`tests/run_tests.py` agrupa la salida usando la primera línea del docstring de cada `TestCase`, con el formato `"Componente · tema"`. Los archivos nuevos llamados `test_*.py` se detectan automáticamente.

## 4. Añadir conversaciones simuladas (opcional)

Para mostrar el agente en la simulación guionizada, modifica `tests/simulations/scripted_conversation.py`:

1. Añade una función como `debt_scenario` o `assistance_scenario` que indique `"agent"` (por ejemplo, `"callback"`), la clase del agente y los datos temporales que se mostrarán
2. Añade las conversaciones a `SCENARIOS`

`tests/run_simulation.py` obtiene los nombres de los agentes de `SCENARIOS`, así que `python3 tests/run_simulation.py callback` funciona sin cambiar el runner. Describe las conversaciones nuevas en `docs/scripted_conversations.es.md` y en su versión en inglés.

## Resumen

| Archivo | Cambio |
| --- | --- |
| `config.py` | Endpoint nuevo, si el agente llama a uno |
| `agents/<nombre>_agent.py` | Clase nueva que hereda de `Agent` |
| `tests/test_<nombre>_agent.py` | Tests del agente nuevo |
| `tests/simulations/scripted_conversation.py` | Opcional: conversaciones para la simulación |
| `docs/scripted_conversations.md` y `.es.md` | Opcional: descripción de esas conversaciones |

No hay que modificar ningún otro agente ni `agents/agent.py`.
