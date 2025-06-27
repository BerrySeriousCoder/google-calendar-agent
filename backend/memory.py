from langchain.memory import ConversationBufferMemory

# Simple wrapper for memory, can be extended for more advanced state
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
