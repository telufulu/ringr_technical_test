🇪🇸 [Leer en español](ai_usage.es.md)

# AI usage

This document explains how AI assistants were used in this project, what they were used for and who made each decision.

## Summary

AI was used as a support tool throughout the project: to understand the brief, explore design alternatives, document decisions, review code and generate the tests, the simulation and part of the documentation. The architecture and every design decision were made by the author. AI explained options and their trade-offs, and recorded or applied the decisions once they were made.

Tools used:

- **Notion AI**: planning, explanations and documentation of the design decisions in the project notes
- **Claude Code**: code review and explanations during the implementation, and generation of the tests, mocks, simulation and documentation

## Principles

- **The author decides.** AI proposed alternatives and explained their limitations. The chosen option, and the reason for it, was always the author's
- **Decisions first, code later.** The design was agreed and written down before the implementation, and AI worked from those written decisions
- **Explicit assumptions.** When the brief left something open, AI pointed it out and the chosen interpretation was recorded as an assumption, not as a requirement
- **Everything is reviewed.** Generated content was reviewed by the author, and code was run and tested before being accepted

## Usage by area

### 1. Understanding the brief and planning

AI helped to read the brief and organize the work.

- Organized the project in four phases (documentation and design, test design, implementation, review) and turned them into tasks with filtered views to track them
- Explained the concepts behind the exercise: conversational agents, the agent lifecycle and turns, simulated models and HTTP integrations
- Separated what had to be implemented from what could be simulated, and found reference repositories on agent patterns and HTTP simulation

### 2. Exploring design alternatives

For each open question, AI explained the options and their limitations so the author could choose.

- **Responsibilities:** what belongs in the base class and what in each agent, and the difference between a generic action and an HTTP integration. The author decided that the base class defines the flow and that `exec_action` is generic
- **Duplicates:** whether to check them inside the normalization or as a separate step, and how a `set` can store keys of different types. The author chose a separate check, with a tuple key for debts and the normalized text for assistance
- **Edge cases:** the difference between `None` and an empty string, `float` precision and special values, and why line breaks are a problem in HTTP headers. Each one ended in a recorded decision or assumption

### 3. Documenting decisions

AI kept the design notes up to date as decisions were made.

- Recorded each decision with its justification: the turn order (normalize, check duplicates, run the action, register the key after a `200`), the handling of temporary data between turns, and stopping the conversation with a printed error instead of retrying
- Turned the agreed decisions into method signatures, without implementing them
- Reviewed the notes for consistency, pointed out contradictions without changing them, and kept the list of pending decisions current
- Wrote example conversations with expected results, which later became the tests and the scripted simulation

### 4. Implementation support

The author wrote the base implementation (`agents/`, `models/`, `integrations/`, `config.py`). AI supported that work without replacing it.

- Prepared reference implementations of the base architecture from the agreed decisions, which the author used as a guide
- Explained Python concepts as they came up, such as abstract classes, `Protocol`, `super()`, instance and class attributes, `@property` and regular expressions
- Reviewed each file as it was written, ran it and pointed out errors (missing imports, attributes declared with `:` instead of `=`, two classes merged into one) for the author to fix

### 5. Tests and simulation

The author defined what had to be tested: the example conversations and the rules in the design. The test and simulation code was generated with AI from them, so its implementation choices are the AI's.

- Generated the unit tests, one file per component, turning each example conversation into a test and adding validation edge cases
- Generated the test mocks: scripted conversation and parser models, and an HTTP client that answers `500` to test the failure branch
- Generated the scripted simulation with the example conversations, and the scripts that run the tests and the simulation with readable output

### 6. Project documentation

- Wrote the README in English and Spanish, following the author's README template adapted to this project
- Wrote the guides in `docs/`: how to add an agent and what each scripted conversation shows

## Responsibilities

| Area | AI | Author |
| --- | --- | --- |
| Planning | Proposed phases and tasks | Approved the plan |
| Design | Explained options and trade-offs | Made every decision |
| Design notes | Recorded the decisions | Reviewed them |
| Base implementation | Explained concepts and reviewed the code | Wrote the code |
| Tests and simulation | Generated them from the decisions | Defined the cases and reviewed the result |
| Documentation | Wrote the drafts | Defined the content and reviewed it |

## What AI did not do

- It did not make design decisions or choose between alternatives
- It did not write the base implementation that is in the repository
- It did not change decisions or fix contradictions in the notes without the author's approval
