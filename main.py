"""
main.py - Grammar Analyzer: The main program.

Usage: python main.py
"""

from lexer import tokenize_grammar, display_tokens, build_symbol_table, display_symbol_table
from validator import validate_cfg, display_validation, semantic_analysis, display_semantic_warnings, eliminate_left_recursion
from cfg_parser import (RecursiveDescentParser, display_parsing_result,
                        display_parse_tree, display_annotated_tree,
                        display_cfg_assembly)


BANNER = """
+==================================================+
|                                                  |
|         GRAMMAR  ANALYZER                        |
|         Mini Compiler Pipeline                   |
|         Context-Free Grammar (CFG)               |
|                                                  |
+==================================================+
"""


def read_grammar():
    """Ask user to type grammar rules. Returns a dictionary like {'S': ['aA', 'b']}."""
    print(f"\n{'-' * 56}")
    print("  Enter grammar rules (one per line).")
    print("  Format:  S -> aA | b")
    print("  Press ENTER on an empty line to finish.")
    print(f"{'-' * 56}")

    grammar = {}

    while True:
        line = input("  > ").strip()
        if line == "":
            break
        if "->" not in line:
            print("  [!] Invalid format - missing '->'. Try again.")
            continue

        lhs, rhs = line.split("->", 1)
        grammar[lhs.strip()] = [p.strip() for p in rhs.split("|")]

    if not grammar:
        print("  No grammar entered. Exiting.")
        exit(0)

    return grammar


def run_pipeline(grammar):
    """Run the full analysis pipeline on the grammar."""

    # Phase 1: Lexical Analysis
    tokens = tokenize_grammar(grammar)
    display_tokens(tokens)

    # Phase 2A: Validate grammar
    valid, message = validate_cfg(grammar)
    display_validation(valid, message)
    if not valid:
        print("  Aborting — grammar is not a valid CFG.")
        return

    # Phase 3: Semantic Analysis (check for problems)
    warnings = semantic_analysis(grammar)
    has_left_recursion = any("left recursion" in w.lower() for w in warnings)
    display_semantic_warnings(warnings)

    if has_left_recursion:
        print("\n  [!] Left recursion detected. Auto-transforming grammar...")
        new_grammar, changed, mapping, elim_error = eliminate_left_recursion(grammar)
        if elim_error:
            print(f"  [!] Error: {elim_error}")
            return
        if changed:
            print(f"\n{'=' * 56}")
            print("  TRANSFORMED GRAMMAR (Left Recursion Removed)")
            print(f"{'=' * 56}")
            for orig, new_nt in mapping.items():
                print(f"  {new_nt} represents {orig}' (primed version of {orig})")
            print()
            for lhs, prods in new_grammar.items():
                print(f"    {lhs} -> {' | '.join(prods)}")
            print(f"{'=' * 56}")
            grammar = new_grammar

    # Phase 2B: Parse a string
    print(f"\n{'-' * 56}")
    input_str = input("  Enter a string to parse: ").strip()
    print(f"{'-' * 56}")

    parser = RecursiveDescentParser(grammar)
    accepted, tree = parser.parse(input_str)
    display_parsing_result(accepted)
    display_parse_tree(tree)
    display_annotated_tree(tree)

    # Phase 4: Target Code Generation (Assembly)
    display_cfg_assembly(tree, input_str)

    # Symbol Table
    symbol_table = build_symbol_table(grammar)
    display_symbol_table(symbol_table)


def main():
    print(BANNER)
    grammar = read_grammar()

    start = list(grammar.keys())[0]
    print(f"\n  Start symbol : {start}")
    print(f"  Productions  : {len(grammar)}")
    for lhs, prods in grammar.items():
        print(f"    {lhs} -> {' | '.join(prods)}")

    run_pipeline(grammar)

    print(f"\n{'=' * 56}")
    print("  Analysis complete. Thank you!")
    print(f"{'=' * 56}\n")


if __name__ == "__main__":
    main()
