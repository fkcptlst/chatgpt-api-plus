import time
import os


class ChatLogger:
    def __init__(self, log_dir, conversation_name=None):
        self.log_dir = log_dir
        self.conversation_name = conversation_name  # optional, e.g. "conversation_chatgpt"
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
            print(f"Created log directory: {os.path.abspath(log_dir)}")

        self.current_conversation = str(int(time.time()))
        self.log_path = os.path.join(log_dir, f"{self.current_conversation}.{self.conversation_name}.log")
        self.last_conversation_count = 0

    def start_new_conversation(self, conversation_name=None):
        if conversation_name is not None:
            self.conversation_name = conversation_name
        self.current_conversation = str(int(time.time()))
        self.log_path = os.path.join(self.log_dir, f"{self.current_conversation}.{self.conversation_name}.log")
        self.last_conversation_count = 0

    def get_conversation_count(self):
        try:
            with open(self.log_path, "r", encoding='utf-8') as f:
                return len(f.read().split("====="))
        except FileNotFoundError:
            return 0

    def record_conversation(self, conversation_dict):
        current_idx = self.get_conversation_count()
        current_idx = 1 if current_idx == 0 else current_idx
        with open(self.log_path, "a", encoding='utf-8') as f:
            print(f"{current_idx}-----", file=f)
            print(f"You: {conversation_dict['you']}", file=f)
            print(f"AI: {conversation_dict['ai']}", file=f)
            print("=====", file=f)
