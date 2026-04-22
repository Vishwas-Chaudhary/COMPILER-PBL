"""
validator.py - Checks if the grammar is valid and finds problems.
"""


def validate_cfg(grammar):
    """Check if grammar follows CFG rules. Returns (is_valid, message)."""
    for lhs, productions in grammar.items():
        if len(lhs) != 1 or not lhs.isupper():
            return False, f"Invalid LHS '{lhs}': must be a single uppercase letter."
        for prod in productions:
            if not prod:
                return False, f"Empty production for '{lhs}'. Use 'e' or '#' for epsilon."

    return True, "Grammar is valid (CFG)."


def display_validation(valid, message):
    """Print whether the grammar passed validation."""
    print(f"\n{'=' * 56}")
    print("  PHASE 2: SYNTAX ANALYSIS — Grammar Validation")
    print(f"{'=' * 56}")
    print(f"  [{'PASS' if valid else 'FAIL'}] {message}")
    print(f"{'=' * 56}")


def semantic_analysis(grammar):
    """Find problems: undefined symbols, unreachable rules, left recursion."""
    warnings = []
    defined = set(grammar.keys())

    # 1. Find undefined non-terminals (used on RHS but never defined on LHS)
    referenced = set()
    for productions in grammar.values():
        for prod in productions:
            for ch in prod:
                if ch.isupper():
                    referenced.add(ch)

    for nt in sorted(referenced - defined):
        warnings.append(f"Undefined non-terminal '{nt}' used in production but never defined.")

    # 2. Find unreachable non-terminals (defined but can't be reached from start)
    if defined:
        start = list(grammar.keys())[0]
        reachable = set()
        stack = [start]

        while stack:
            current = stack.pop()
            if current in reachable:
                continue
            reachable.add(current)
            for prod in grammar.get(current, []):
                for ch in prod:
                    if ch.isupper() and ch not in reachable:
                        stack.append(ch)

        for nt in sorted(defined - reachable):
            warnings.append(f"Non-terminal '{nt}' is defined but unreachable from start symbol '{start}'.")

    # 3. Check for left recursion (direct and indirect)
    #    For each non-terminal, follow the leftmost symbols to see if it leads back to itself.
    for lhs in grammar:
        # Find all non-terminals reachable by following leftmost symbols
        left_reachable = set()
        to_visit = [lhs]

        while to_visit:
            current = to_visit.pop()
            for prod in grammar.get(current, []):
                if prod and prod[0].isupper() and prod[0] not in left_reachable:
                    left_reachable.add(prod[0])
                    if prod[0] != lhs:
                        to_visit.append(prod[0])

        if lhs in left_reachable:
            # Check if direct or indirect
            is_direct = any(prod and prod[0] == lhs for prod in grammar.get(lhs, []))
            if is_direct:
                for prod in grammar.get(lhs, []):
                    if prod and prod[0] == lhs:
                        warnings.append(
                            f"Direct left recursion detected: '{lhs} -> {prod}'."
                        )
            else:
                warnings.append(
                    f"Indirect left recursion detected involving '{lhs}'."
                )

    return warnings


def display_semantic_warnings(warnings):
    """Print all semantic warnings."""
    print(f"\n{'=' * 56}")
    print("  PHASE 3: SEMANTIC ANALYSIS")
    print(f"{'=' * 56}")
    if not warnings:
        print("  [OK] No semantic warnings found.")
    else:
        for i, w in enumerate(warnings, 1):
            print(f"  [WARNING {i}] {w}")
    print(f"{'=' * 56}")


def eliminate_left_recursion(grammar):
    """
    Eliminate both direct and indirect left recursion from the grammar.

    Algorithm:
      1. Order all non-terminals as they appear in the grammar.
      2. For each pair (i, j) where j < i:
         - If Ai has a production starting with Aj, substitute Aj's productions.
      3. After substitution, remove direct left recursion from each Ai.

    Since our parser uses single uppercase letters, new non-terminals (like A')
    are assigned unused uppercase letters (Z, Y, X, ...).

    Returns (new_grammar, changed, mapping, error)
      - new_grammar : the transformed grammar (ordered dict)
      - changed     : True if any transformation was done
      - mapping     : dict like {'E': 'X'} meaning X represents E'
      - error       : error message string, or None
    """
    # Copy grammar
    g = {}
    for k, v in grammar.items():
        g[k] = list(v)

    non_terminals = list(g.keys())

    # Collect all uppercase letters already used in the grammar
    used = set(non_terminals)
    for prods in g.values():
        for prod in prods:
            for ch in prod:
                if ch.isupper():
                    used.add(ch)

    # Letters available for new non-terminals (prefer end of alphabet)
    available = [c for c in 'ZYXWVUQPONMLKJIHGDCB' if c not in used]
    avail_idx = 0
    mapping = {}

    for i in range(len(non_terminals)):
        ai = non_terminals[i]

        # --- Substitute: replace productions starting with earlier non-terminals ---
        for j in range(i):
            aj = non_terminals[j]
            new_prods = []
            for prod in g[ai]:
                if prod and prod[0] == aj:
                    # Replace Aj with all of Aj's productions
                    rest = prod[1:]
                    for aj_prod in g[aj]:
                        if aj_prod in ('e', '#'):
                            # Aj -> epsilon, so just use the rest
                            new_prods.append(rest if rest else 'e')
                        else:
                            new_prods.append(aj_prod + rest)
                else:
                    new_prods.append(prod)
            g[ai] = new_prods

        # --- Remove direct left recursion from Ai ---
        left_rec = []       # productions like Ai -> Ai α  (store α)
        non_left_rec = []   # productions like Ai -> β

        for prod in g[ai]:
            if prod and prod[0] == ai:
                left_rec.append(prod[1:])   # α (everything after the leading Ai)
            else:
                non_left_rec.append(prod)

        if left_rec:
            if avail_idx >= len(available):
                return grammar, False, {}, "Not enough unused letters for new non-terminals."

            new_nt = available[avail_idx]
            avail_idx += 1
            mapping[ai] = new_nt

            # Ai -> β1 A' | β2 A' | ...
            new_ai_prods = []
            for beta in non_left_rec:
                if beta in ('e', '#'):
                    # β is epsilon, so Ai -> A'
                    new_ai_prods.append(new_nt)
                else:
                    new_ai_prods.append(beta + new_nt)
            g[ai] = new_ai_prods

            # A' -> α1 A' | α2 A' | ... | e
            g[new_nt] = [alpha + new_nt for alpha in left_rec] + ['e']

    return g, len(mapping) > 0, mapping, None

