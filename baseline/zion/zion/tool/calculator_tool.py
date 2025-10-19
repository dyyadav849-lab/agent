from langchain.tools import tool
from simpleeval import simple_eval


@tool()
def calculator_tool(operation: str) -> str:
    """Useful to perform any mathematical calculations,
    like sum, minus, multiplication, division, etc.
    The input to this tool should be a mathematical
    expression, a couple examples are `200*7` or `5000/2*10`
    """
    try:
        return simple_eval(operation)
    except SyntaxError:
        return "Error: Invalid syntax in mathematical expression"
