"""
lexer.py - Breaks grammar into tokens and builds a symbol table.
"""


def tokenize_grammar(grammar):
    """Break grammar rules into tokens (smallest meaningful pieces)."""
    tokens = []

    for lhs, productions in grammar.items():
        tokens.append({"type": "Non-terminal", "value": lhs})
        tokens.append({"type": "Symbol", "value": "->"})

        for i, prod in enumerate(productions):
            for ch in prod:
                if ch.isupper():
                    tokens.append({"type": "Non-terminal", "value": ch})
                elif ch in ('#', 'e'):
                    tokens.append({"type": "Epsilon", "value": "ε"})
                else:
                    tokens.append({"type": "Terminal", "value": ch})

            # Add '|' between alternatives (not after the last one)
            if i < len(productions) - 1:
                tokens.append({"type": "Symbol", "value": "|"})

    return tokens


def display_tokens(tokens):
    """Print all tokens in a table."""
    print(f"\n{'=' * 56}")
    print("  PHASE 1: LEXICAL ANALYSIS")
    print(f"{'=' * 56}")
    print(f"  {'Token #':<10}{'Type':<18}Value")
    print(f"  {'-' * 46}")

    for i, tok in enumerate(tokens, 1):
        print(f"  {i:<10}{tok['type']:<18}{tok['value']}")

    print(f"{'=' * 56}")


def build_symbol_table(grammar):
    """Build a table listing every symbol used in the grammar."""
    table = {}
    start = list(grammar.keys())[0]

    # Add all non-terminals from left-hand side
    for lhs in grammar:
        role = "LHS (Start Symbol)" if lhs == start else "LHS"
        table[lhs] = {
            "name": lhs, "type": "Non-terminal", "role": role,
            "defined_in": [f"{lhs} -> {' | '.join(grammar[lhs])}"],
            "used_in": []
        }

    # Scan right-hand side for all symbols
    for lhs, productions in grammar.items():
        for prod in productions:
            rule = f"{lhs} -> {prod}"
            for ch in prod:
                if ch.isupper() and ch in table:
                    # Non-terminal already defined on LHS — mark as both
                    if "RHS" not in table[ch]["role"] and "&" not in table[ch]["role"]:
                        table[ch]["role"] = table[ch]["role"].replace("LHS", "LHS & RHS")
                    if rule not in table[ch]["used_in"]:
                        table[ch]["used_in"].append(rule)
                elif ch.isupper():
                    # Non-terminal only on RHS (undefined)
                    table[ch] = {
                        "name": ch, "type": "Non-terminal", "role": "RHS",
                        "defined_in": [], "used_in": [rule]
                    }
                elif ch.islower():
                    # Terminal
                    if ch not in table:
                        table[ch] = {
                            "name": ch, "type": "Terminal", "role": "RHS",
                            "defined_in": [], "used_in": []
                        }
                    if rule not in table[ch]["used_in"]:
                        table[ch]["used_in"].append(rule)

    return list(table.values())


def display_symbol_table(symbol_table):
    """Print the symbol table."""
    print(f"\n{'=' * 72}")
    print("  SYMBOL TABLE")
    print(f"{'=' * 72}")
    print(f"  {'Symbol':<10}{'Type':<16}{'Role':<22}Appears In")
    print(f"  {'-' * 66}")

    # Non-terminals first, then terminals
    nt = [s for s in symbol_table if s["type"] == "Non-terminal"]
    t = [s for s in symbol_table if s["type"] == "Terminal"]

    for entry in nt + t:
        appears = ", ".join(entry["defined_in"] + entry["used_in"]) or "-"
        if len(appears) > 40:
            appears = appears[:37] + "..."
        print(f"  {entry['name']:<10}{entry['type']:<16}{entry['role']:<22}{appears}")

    print(f"{'=' * 72}")
