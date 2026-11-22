🇪🇸 [Leer en español](scripted_conversations.es.md)

# Scripted conversations

The scripted simulation runs ten example conversations, five with `DebtAgent` and five with `AssistanceAgent`, and prints what happens in each turn.

It is a simplification to work without a real language model. The agent's questions, the person's replies, the processed text and the parser output are written in advance. The HTTP integration is the simulated one, so no network calls are made.

The simulation is meant to **show** how the agents behave, not to verify it. The same conversations are covered by automated tests in `tests/test_debt_agent.py` and `tests/test_assistance_agent.py`, which do check every result.

The dialogue is in Spanish, as in the project design. The tables below quote it as it appears in the simulation.

## Running it

From any directory:

```bash
python3 tests/run_simulation.py               # all ten conversations
python3 tests/run_simulation.py debt          # only the DebtAgent ones
python3 tests/run_simulation.py assistance 3  # only AssistanceAgent conversation 3
```

`python3 tests/simulations/scripted_conversation.py` also runs all ten conversations.

It requires Python 3.10 or later and has no external dependencies.

## What each turn shows

| Line | Meaning |
| --- | --- |
| `Agent` | Question the conversation model asks the person |
| `Person` | What the person replies |
| `Processed text` | Processed version of the reply that `answer_user` returns to the agent |
| `Parser` | Dictionary that `parse_data` returns from that text |
| `→ POST ...` / `→ No request sent` | Whether the agent sent a simulated request, with its URL and body |
| `Pending data` | Temporary data the agent keeps for the next turns |
| `Registered keys` | Keys of the actions already registered successfully in the conversation |

Each conversation starts with a new agent instance and an empty set of keys. Within a conversation the same instance is used throughout, as in a real conversation.

The debt scenarios use dates in 2090 so they are always later than the day the simulation runs.

## DebtAgent

The debt agent registers payment commitments. It needs a valid date (`commitment_date`) and a valid amount (`committed_amount`), which can arrive in the same turn or in different turns. It sends a POST to `https://api.ringr.debt/v1/commitment` once it has both.

### 1. Complete data in one turn

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «Pagaré 150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |

**What it checks**

- With a valid date and amount in the same turn, the agent sends a single POST with both fields in the body
- After the `200` response, the key `("2090-05-20", 150.0)` is registered
- The temporary data goes back to `None` and the agent is ready for another commitment

### 2. Data received in different turns

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «El 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": None}` |
| 2 | «150 euros» | `{"commitment_date": None, "committed_amount": 150.0}` |

**What it checks**

- In turn 1 the amount is missing: the agent stores the date and sends nothing
- In turn 2, `None` for the date means "not supplied in this turn", so the previous date is kept
- With both values complete, a POST is sent with the date from turn 1 and the amount from turn 2

### 3. New invalid data replaces the previous value

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «El 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": None}` |
| 2 | «Sí, al 30 de febrero de 2090» | `{"commitment_date": "2090-02-30", "committed_amount": None}` |
| 3 | «El 21 de mayo de 2090 y 150 euros» | `{"commitment_date": "2090-05-21", "committed_amount": 150.0}` |

**What it checks**

- 30 February has the right format but is not a real date, so it is rejected
- A new invalid date clears the valid date stored before: the field becomes `None`
- The agent does not reuse the previous date and only sends a POST with the new date from turn 3

### 4. Duplicate and different commitment on the same date

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |
| 2 | «Sí, 150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |
| 3 | «Sí, 200 euros para esa misma fecha» | `{"commitment_date": "2090-05-20", "committed_amount": 200.0}` |

**What it checks**

- In turn 2 the key is already registered: no new POST is sent, the temporary data is cleared and the registered keys do not change
- In turn 3 the date matches but the amount does not. It is a different commitment and it is sent
- Two POST requests are sent in total, not three, and both keys are registered

A commitment is identified by its date and amount. This is a simplification for the exercise: two real commitments with the same date and amount would be treated as one.

### 5. Unsuccessful HTTP response

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «150 euros el 20 de mayo de 2090» | `{"commitment_date": "2090-05-20", "committed_amount": 150.0}` |

In this conversation the HTTP integration is replaced by `FailingHttpClient`, which answers `500` instead of `200`.

**What it checks**

- The agent tries to send the request, gets the error and prints "Sorry, something went wrong. Please try again later" in red
- The key is not registered and the temporary data is kept
- `handle_turn` returns `False`, the conversation stops and there is no automatic retry

## AssistanceAgent

The assistance agent registers requests for human agents. It accepts any text in `request`, including the empty string, and normalizes it with `lower()` and `strip()`. It sends a POST to `https://api.ringr.assistance/v1/request` with the normalized text.

### 1. Valid request

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «Necesito una copia de mi contrato» | `{"request": "Necesito una copia de mi contrato"}` |

**What it checks**

- The request is normalized to `"necesito una copia de mi contrato"`
- A POST is sent with the normalized text in the body and in the `request` header
- After the `200` response, the key is registered and the temporary request goes back to `None`

### 2. No request

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «Solo quería saber el horario» | `{"request": None}` |

**What it checks**

- `None` means there is nothing to register
- No POST is sent and the registered keys stay empty

### 3. Duplicate after normalization

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «Necesito una copia de mi contrato» | `{"request": "Necesito una copia de mi contrato"}` |
| 2 | «Sí, necesito una copia de mi contrato» | `{"request": "  NECESITO UNA COPIA DE MI CONTRATO  "}` |

**What it checks**

- Turn 1 registers the normalized key
- In turn 2 the parser returns the same request in upper case and with spaces at both ends. After normalization the key matches, so it is a duplicate
- No new POST is sent. One is sent in total

The processed text is the same in both turns, but the parser returns different results. This is why the simulated parser returns its results by turn order and not based on the text it receives.

### 4. Empty string and another request

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | (types a string of spaces) | `{"request": "   "}` |
| 2 | «Una copia de mi contrato» | `{"request": "Una copia de mi contrato"}` |

**What it checks**

- After removing the spaces, the request becomes `""`. The empty string is a valid request, different from `None`, and it is sent
- The request in turn 2 is a different key from the empty one and is also sent
- Two POST requests are sent in total and both keys are registered

### 5. Unsuccessful HTTP response

| Turn | Person | Parser |
| --- | --- | --- |
| 1 | «Necesito una copia de mi contrato» | `{"request": "Necesito una copia de mi contrato"}` |

As in debt conversation 5, the HTTP integration answers `500`.

**What it checks**

- The agent prints the error message in red
- The normalized request and its key are kept, and nothing is registered
- `handle_turn` returns `False`, the conversation stops and there is no automatic retry

## Adding a conversation

The conversations are defined in the `SCENARIOS` list in `tests/simulations/scripted_conversation.py`. To add a new one:

1. Add an entry with `debt_scenario(...)` or `assistance_scenario(...)`, giving a number that is not in use, a title, the expected result and the list of turns
2. In each turn, set `agent`, `person`, `processed` and `parsed`
3. To simulate an HTTP failure, pass `http_client=failing_http_client`

The new conversation is available in `tests/run_simulation.py` straight away.
