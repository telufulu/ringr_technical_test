from models.conversation_model import ConversationModel

class Agent:
    description = "Generic agent"

    def describe(self):
        return self.description

    def handle_turn(self):
        print(self.description)