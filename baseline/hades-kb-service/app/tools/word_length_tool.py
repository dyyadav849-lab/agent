from langchain_core.tools import tool


# This is a example Agent tool that calculates the length of a word
# Read complete guide to create a custom tool here:
# https://python.langchain.com/v0.1/docs/modules/tools/custom_tools/
@tool
def word_length_tool(word: str) -> int:
    """Returns a counter word"""
    return len(word)
