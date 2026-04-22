"""
cfg_parser.py - Recursive Descent Parser that builds a Parse Tree.

How it works:
  1. For each non-terminal, try each production rule one by one.
  2. If a production works, great! If not, backtrack and try the next.
  3. While parsing, build a tree showing how the string was parsed.

Also computes FIRST and FOLLOW sets used by the parser internally.
"""


class ParseTreeNode:
    """A single node in the parse tree."""

    def __init__(self, symbol, is_terminal, production_used=""):
        self.symbol = symbol
        self.is_terminal = is_terminal
        self.production_used = production_used
        self.children = []

    def add_child(self, child):
        self.children.append(child)


class RecursiveDescentParser:
    """Tries to parse an input string using the grammar rules."""

    def __init__(self, grammar):
        self.grammar = grammar
        self.start_symbol = list(grammar.keys())[0]
        self.input_string = ""
        self.pos = 0

    def current_char(self):
        """Get current character, or None if at end."""
        return self.input_string[self.pos] if self.pos < len(self.input_string) else None

    def match(self, expected):
        """Try to match expected char with current char. Move forward if it matches."""
        if self.current_char() == expected:
            self.pos += 1
            return True
        return False

    def try_production(self, non_terminal, production):
        """Try to apply one production rule. Backtracks on failure."""
        saved_pos = self.pos
        rule = f"{non_terminal} -> {production}"
        node = ParseTreeNode(non_terminal, is_terminal=False, production_used=rule)

        # Handle epsilon (empty) productions
        if production in ('e', '#'):
            node.add_child(ParseTreeNode("e", is_terminal=True))
            return node

        # Try to match each character in the production
        for ch in production:
            if ch.isupper():
                # Non-terminal — parse recursively
                child = self.parse_non_terminal(ch)
                if child is None:
                    self.pos = saved_pos  # Backtrack!
                    return None
                node.add_child(child)
            else:
                # Terminal — try to match
                if self.match(ch):
                    node.add_child(ParseTreeNode(ch, is_terminal=True))
                else:
                    self.pos = saved_pos  # Backtrack!
                    return None

        return node

    def parse_non_terminal(self, non_terminal):
        """Try all productions for a non-terminal. Return first that works."""
        for prod in self.grammar.get(non_terminal, []):
            result = self.try_production(non_terminal, prod)
            if result is not None:
                return result
        return None

    def parse(self, input_string):
        """Parse input string. Returns (True, tree) or (False, None)."""
        self.input_string = input_string
        self.pos = 0
        tree = self.parse_non_terminal(self.start_symbol)

        if tree is not None and self.pos == len(self.input_string):
            return True, tree
        return False, None


# ─── FIRST and FOLLOW Set Computation ───────────────────────────────────────

def compute_first_sets(grammar):
    """
    Compute FIRST sets for all non-terminals in the grammar.

    FIRST(A) = set of terminals that can appear as the first symbol
               of any string derived from A.
    Rules:
      1. If A -> a..., add 'a' to FIRST(A).  (a = terminal)
      2. If A -> e or A -> #, add epsilon ('ε') to FIRST(A).
      3. If A -> B..., add FIRST(B) - {ε} to FIRST(A);
         if ε ∈ FIRST(B), continue to the next symbol.
    """
    EPSILON = 'ε'
    first = {nt: set() for nt in grammar}

    changed = True
    while changed:
        changed = False
        for nt, productions in grammar.items():
            for prod in productions:
                # epsilon production
                if prod in ('e', '#', 'ε'):
                    if EPSILON not in first[nt]:
                        first[nt].add(EPSILON)
                        changed = True
                    continue

                # Walk symbols in the production
                all_nullable = True
                for sym in prod:
                    if sym.isupper():          # Non-terminal
                        if sym in first:
                            before = len(first[nt])
                            first[nt] |= (first[sym] - {EPSILON})
                            if len(first[nt]) != before:
                                changed = True
                            if EPSILON not in first[sym]:
                                all_nullable = False
                                break
                        else:
                            all_nullable = False
                            break
                    else:                      # Terminal
                        before = len(first[nt])
                        first[nt].add(sym)
                        if len(first[nt]) != before:
                            changed = True
                        all_nullable = False
                        break

                if all_nullable:
                    if EPSILON not in first[nt]:
                        first[nt].add(EPSILON)
                        changed = True

    return first


def compute_follow_sets(grammar, first_sets):
    """
    Compute FOLLOW sets for all non-terminals in the grammar.

    FOLLOW(A) = set of terminals (including $) that can appear
                immediately to the right of A in some sentential form.
    Rules:
      1. Add '$' to FOLLOW(start symbol).
      2. For each production B -> α A β:
           - Add FIRST(β) - {ε} to FOLLOW(A).
           - If ε ∈ FIRST(β), also add FOLLOW(B) to FOLLOW(A).
      3. For each production B -> α A (A at the end):
           - Add FOLLOW(B) to FOLLOW(A).
    """
    EPSILON = 'ε'
    non_terminals = list(grammar.keys())
    start = non_terminals[0]

    follow = {nt: set() for nt in non_terminals}
    follow[start].add('$')

    # Helper: compute FIRST of a sequence of symbols
    def first_of_sequence(symbols):
        result = set()
        for sym in symbols:
            if sym.isupper():
                result |= (first_sets.get(sym, set()) - {EPSILON})
                if EPSILON not in first_sets.get(sym, set()):
                    break
            else:
                result.add(sym)
                break
        else:
            result.add(EPSILON)   # entire sequence is nullable
        return result

    changed = True
    while changed:
        changed = False
        for lhs, productions in grammar.items():
            for prod in productions:
                if prod in ('e', '#', 'ε'):
                    continue
                for i, sym in enumerate(prod):
                    if sym.isupper() and sym in follow:
                        beta = prod[i + 1:]       # everything after sym
                        if beta:
                            first_beta = first_of_sequence(beta)
                            before = len(follow[sym])
                            follow[sym] |= (first_beta - {EPSILON})
                            if len(follow[sym]) != before:
                                changed = True
                            if EPSILON in first_beta:
                                before = len(follow[sym])
                                follow[sym] |= follow[lhs]
                                if len(follow[sym]) != before:
                                    changed = True
                        else:
                            # sym is the last symbol — inherit FOLLOW(lhs)
                            before = len(follow[sym])
                            follow[sym] |= follow[lhs]
                            if len(follow[sym]) != before:
                                changed = True
    return follow


def get_first_follow(grammar):
    """
    Convenience function: compute and return both FIRST and FOLLOW sets.
    Returns (first_sets, follow_sets) where each is a dict {NT: set(str)}.
    """
    first_sets  = compute_first_sets(grammar)
    follow_sets = compute_follow_sets(grammar, first_sets)
    return first_sets, follow_sets


# --- Display functions ---

def display_parsing_result(accepted):
    """Print whether the string was accepted or rejected."""
    result = "ACCEPTED" if accepted else "REJECTED"
    print(f"\n{'=' * 56}")
    print("  PHASE 2: SYNTAX ANALYSIS — Parsing Result")
    print(f"{'=' * 56}")
    print(f"  +----------------------------------+")
    print(f"  |      >>> STRING {result} <<<      |")
    print(f"  +----------------------------------+")
    print(f"{'=' * 56}")


def _print_tree(node, prefix="", is_last=True, annotated=False):
    """Print tree nodes recursively (used for both plain and annotated trees)."""
    # Build label
    if annotated:
        if node.is_terminal:
            label = f"{node.symbol} [T]"
        elif node.production_used:
            label = f"{node.symbol} [NT | {node.production_used}]"
        else:
            label = f"{node.symbol} [NT]"
    else:
        label = node.symbol

    # Pick connector
    if prefix == "":
        connector = ""
    else:
        connector = "└── " if is_last else "├── "

    print(f"    {prefix}{connector}{label}")

    # Pick child prefix
    if prefix == "":
        child_prefix = ""
    else:
        child_prefix = prefix + ("    " if is_last else "│   ")

    # Print children
    for i, child in enumerate(node.children):
        _print_tree(child, child_prefix, i == len(node.children) - 1, annotated)


def display_parse_tree(node):
    """Print the parse tree."""
    print(f"\n{'=' * 56}")
    print("  PARSE TREE")
    print(f"{'=' * 56}")
    if node is None:
        print("  (no parse tree - input was rejected)")
    else:
        _print_tree(node)
    print(f"{'=' * 56}")


def display_annotated_tree(node):
    """Print the annotated parse tree."""
    print(f"\n{'=' * 56}")
    print("  ANNOTATED PARSE TREE")
    print(f"{'=' * 56}")
    if node is None:
        print("  (no annotated tree - input was rejected)")
    else:
        _print_tree(node, annotated=True)
    print(f"{'=' * 56}")


def display_cfg_assembly(tree, input_string):
    """Print the CFG target assembly to the terminal (CLI phase 4)."""
    asm = generate_cfg_assembly(tree, input_string)
    print(f"\n{'=' * 56}")
    print("  PHASE 4: TARGET CODE GENERATION (Assembly)")
    print(f"{'=' * 56}")
    for line in asm:
        print(f'  {line}')
    print(f"{'=' * 56}")


# ── Phase 4: Target Code Generation for CFG ──────────────────────────────

def generate_cfg_assembly(tree, input_string):
    """
    Emit minimal label-based assembly from a CFG parse tree.
    No boilerplate — just the essential CALL, CMP, JE, JMP, INC, RET.
    """
    lines   = []
    counter = [0]
    nt_count = {}   # tracks how many times each NT appears → unique label

    def e(line=''):
        lines.append(line)

    def new_lbl():
        counter[0] += 1
        return f'ok{counter[0]}'

    def nt_label(node):
        sym = node.symbol
        nt_count[sym] = nt_count.get(sym, 0) + 1
        n = nt_count[sym]
        return f'parse_{sym}' if n == 1 else f'parse_{sym}_{n}'

    def walk(node):
        if node.is_terminal:
            if node.symbol == 'e':
                e('    ; epsilon (match nothing)')
                return
            lbl = new_lbl()
            e(f"    CMP  [SI], '{node.symbol}'")
            e(f'    JE   {lbl}')
            e(f'    JMP  REJECT')
            e(f'{lbl}:')
            e(f'    INC  SI')
            return
        # non-terminal
        fn  = nt_label(node)
        rule = node.production_used or node.symbol
        e('')
        e(f'{fn}:                ; {rule}')
        for child in node.children:
            walk(child)
        e(f'    RET')

    # ── main entry ────────────────────────────────────────────────────────
    e(f'; input = "{input_string}"')
    e(f'; SI   = pointer to current character in memory')
    e('')
    e('main:')
    e(f'    MOV  SI, "{input_string}"')
    if tree is None:
        e('    JMP  REJECT')
    else:
        fn_start = nt_label(tree)
        # reset count so walk() can assign the same first label
        nt_count.clear()
        e(f'    CALL {fn_start}')
        e('    CMP  [SI], 0       ; end of input?')
        e('    JE   ACCEPT')
        e('    JMP  REJECT')
        e('')
        walk(tree)

    # ── accept / reject ───────────────────────────────────────────────────
    e('')
    e('ACCEPT:  print "ACCEPTED"')
    e('REJECT:  print "REJECTED"')

    return lines




