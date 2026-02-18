import ast

class SecurityScanner:
    """
    Scans strategy code for potential security risks or logical cheats.
    """

    @staticmethod
    def scan_code(code: str) -> list[str]:
        warnings = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Check for .shift(-N) which implies lookahead
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == 'shift':
                        if node.args:
                            arg = node.args[0]
                            # Check if arg is negative number
                            if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, ast.USub):
                                warnings.append("Lookahead Bias detected: .shift() with negative value")
                            elif isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)) and arg.value < 0:
                                warnings.append("Lookahead Bias detected: .shift() with negative value")
        except Exception:
            pass # Parse error handled elsewhere

        return warnings
