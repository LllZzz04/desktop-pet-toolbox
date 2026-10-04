"""A small AST evaluator with a numeric and syntax allowlist; never eval()."""
import ast
import math
import operator

FUNCTIONS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
             "tan": math.tan, "log": math.log}
CONSTANTS = {"pi": math.pi, "e": math.e}
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.Pow: operator.pow}


def calculate(expression):
    if not expression.strip() or len(expression) > 256:
        raise ValueError("表达式为空或过长（最多 256 字符）")
    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 128:
            raise ValueError("表达式过于复杂")

        def visit(node, depth=0):
            if depth > 24:
                raise ValueError("表达式嵌套过深")
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                value = float(node.value)
            elif isinstance(node, ast.Name) and node.id in CONSTANTS:
                value = CONSTANTS[node.id]
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                operand = visit(node.operand, depth + 1)
                value = operand if isinstance(node.op, ast.UAdd) else -operand
            elif isinstance(node, ast.BinOp) and type(node.op) in BINARY:
                left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
                if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                    raise ValueError("指数过大")
                value = BINARY[type(node.op)](left, right)
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id in FUNCTIONS and len(node.args) == 1 and not node.keywords):
                value = FUNCTIONS[node.func.id](visit(node.args[0], depth + 1))
            else:
                raise ValueError("仅支持基本数学、pi、e 和 sqrt / sin / cos / tan / log")
            if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e100:
                raise ValueError("结果超出支持范围")
            return value

        return visit(tree.body)
    except ZeroDivisionError as error:
        raise ValueError("不能除以零") from error
    except (SyntaxError, RecursionError) as error:
        raise ValueError("表达式格式不正确") from error
    except (OverflowError, TypeError) as error:
        raise ValueError("结果超出支持范围") from error
    except ValueError as error:
        if str(error) == "math domain error":
            raise ValueError("函数输入超出定义域") from error
        raise
