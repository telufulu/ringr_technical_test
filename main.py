""" INIT PROGRAMM
    Here I put the min flow of the programm and functions that serve only
    to init the flow
"""
# Imported agents
from agents.agent import Agent
from agents.debt_agent import DebtAgent
from agents.assistance_agent import AssistanceAgent

# Config
from config import ROUTES
from config import WELCOME_MSG, BYE_MSG

def build_agents() -> dict[str, Agent]:
    return {
        "debt": DebtAgent(),
        "asssistance": AssistanceAgent(),
        "basic": Agent(),
    }

def main():
    agents = build_agents()

    print(WELCOME_MSG)
    while True:
        try:
            message = input("> ").strip()
            agent_name = ROUTES.get(message.strip().lower())
            if agent_name in agents:
                agents[agent_name].handle_turn()
            else:
                print("¿En qué te puedo ayudar?")
        except (KeyboardInterrupt, EOFError):
            print(BYE_MSG)
            break

if __name__ == "__main__":
    main()