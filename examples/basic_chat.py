# Basic Chat Example

from aicortex import chat

# Simple chat
response = chat("Explain recursion in simple terms")
print(response)

# Chat with specific model
response = chat("Write a Python hello world", model="llama3.2:3b")
print(response)