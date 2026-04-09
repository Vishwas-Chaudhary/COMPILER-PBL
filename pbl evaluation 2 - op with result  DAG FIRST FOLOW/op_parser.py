"""
op_parser.py - Operator Precedence Parser

Parses arithmetic expressions using an operator precedence table.
This is a shift-reduce parser.

Supported operators : + - * / ^ ( )
Operands            : any identifier (a, b, x) or number (1, 2, 3.14)
End marker          : $ (added automatically)
"""

# --- Operator set (used to distinguish terminals from non-terminals) ---
OPERATORS = {'+', '-', '*', '/', '^', '(', ')', '$'}

# --- Operator Precedence Relation Table ---
# Row    = top terminal on the stack
# Column = current input symbol
# '<'  yield precedence  → Shift (push current symbol)
# '>'  takes precedence  → Reduce (pop handle, push E)
# '='  equal precedence  → Shift (used for matching parentheses)
# ''   no relation       → Error

PREC_TABLE = {
    #        +     -     *     /     ^     (     )     $
    '+': {'+':'>', '-':'>', '*':'<', '/':'<', '^':'<', '(':'<', ')':'>', '$':'>'},
    '-': {'+':'>', '-':'>', '*':'<', '/':'<', '^':'<', '(':'<', ')':'>', '$':'>'},
    '*': {'+':'>', '-':'>', '*':'>', '/':'>', '^':'<', '(':'<', ')':'>', '$':'>'},
    '/': {'+':'>', '-':'>', '*':'>', '/':'>', '^':'<', '(':'<', ')':'>', '$':'>'},
    '^': {'+':'>', '-':'>', '*':'>', '/':'>', '^':'<', '(':'<', ')':'>', '$':'>'},
    '(': {'+':'<', '-':'<', '*':'<', '/':'<', '^':'<', '(':'<', ')':'=', '$':''},
    ')': {'+':'>', '-':'>', '*':'>', '/':'>', '^':'>', '(':'' , ')':'>', '$':'>'},
    '$': {'+':'<', '-':'<', '*':'<', '/':'<', '^':'<', '(':'<', ')':'',  '$':'='},
}


def get_top_terminal(stack):
    """Return the topmost terminal (operator or $) from the stack, skipping E."""
    for item in reversed(stack):
        if item in OPERATORS:
            return item
    return None


def tokenize_expression(expr):
    """
    Split expression into a list of tokens.
    Multi-character operands (identifiers / numbers) are kept as single tokens.
    Appends '$' as the end marker.
    """
    tokens = []
    i = 0
    expr = expr.strip()
    while i < len(expr):
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c.isalnum() or c == '.':
            j = i
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '.'):
                j += 1
            tokens.append(expr[i:j])
            i = j
        elif c in OPERATORS:
            tokens.append(c)
            i += 1
        else:
            tokens.append(c)   # unknown char → will trigger error
            i += 1
    tokens.append('$')
    return tokens


def pop_handle(stack):
    """
    Identify and remove the handle from the stack.

    Strategy:
      1. Find the topmost terminal (β).
      2. Scan leftward to find the nearest terminal α where PREC[α][β] == '<'.
      3. The handle is everything from α+1 to the top of the stack.
    """
    # Find index of topmost terminal
    top_term_pos = len(stack) - 1
    while top_term_pos >= 0 and stack[top_term_pos] not in OPERATORS:
        top_term_pos -= 1

    if top_term_pos < 0:
        return stack[:]          # safety fallback

    top_term = stack[top_term_pos]

    # Scan left to find the '<' boundary
    boundary = 1                 # default: right after '$'
    j = top_term_pos - 1
    current_right = top_term
    while j >= 0:
        sym = stack[j]
        if sym in OPERATORS:
            rel = PREC_TABLE.get(sym, {}).get(current_right, '')
            if rel == '<':
                boundary = j + 1
                break
            current_right = sym
        j -= 1

    handle = stack[boundary:]
    del stack[boundary:]
    return handle


def parse_expression(expr):
    """
    Parse an arithmetic expression with the operator precedence algorithm.

    Returns
    -------
    accepted  : bool
    steps     : list of dicts  (step, stack, input, relation, action)
    error_msg : str or None
    """
    if not expr.strip():
        return False, [], "Empty expression."

    tokens = tokenize_expression(expr)
    stack = ['$']
    steps = []
    i = 0
    step_num = 1
    MAX_STEPS = 400

    while step_num <= MAX_STEPS:
        top_term = get_top_terminal(stack)
        current  = tokens[i] if i < len(tokens) else '$'

        stack_str = ' '.join(stack)
        input_str = ' '.join(tokens[i:])

        # ── Accept ────────────────────────────────────────────────────────────
        if len(stack) == 2 and stack[0] == '$' and stack[1] == 'E' and current == '$':
            steps.append({
                'step': step_num, 'stack': stack_str,
                'input': input_str, 'relation': '=', 'action': 'ACCEPT'
            })
            return True, steps, None

        # ── Operand → treat as E (shift immediately) ──────────────────────────
        if current not in OPERATORS:
            steps.append({
                'step': step_num, 'stack': stack_str,
                'input': input_str, 'relation': '-',
                'action': f'Shift operand "{current}" → E'
            })
            stack.append('E')
            i += 1
            step_num += 1
            continue

        # ── Get precedence relation ───────────────────────────────────────────
        if top_term is None:
            rel = ''
        else:
            rel = PREC_TABLE.get(top_term, {}).get(current, '')

        # ── Shift (<  or  =) ─────────────────────────────────────────────────
        if rel in ('<', '='):
            steps.append({
                'step': step_num, 'stack': stack_str,
                'input': input_str, 'relation': rel,
                'action': f'Shift "{current}"'
            })
            stack.append(current)
            i += 1

        # ── Reduce (>) ───────────────────────────────────────────────────────
        elif rel == '>':
            handle = pop_handle(stack)
            handle_str = ' '.join(handle)
            steps.append({
                'step': step_num, 'stack': stack_str,
                'input': input_str, 'relation': rel,
                'action': f'Reduce  {handle_str}  →  E'
            })
            stack.append('E')

        # ── Error ─────────────────────────────────────────────────────────────
        else:
            steps.append({
                'step': step_num, 'stack': stack_str,
                'input': input_str, 'relation': '?',
                'action': f'ERROR: no relation between "{top_term}" and "{current}"'
            })
            return False, steps, f'Parse error: unexpected "{current}" after "{top_term}".'

        step_num += 1

    return False, steps, "Exceeded maximum steps (possible infinite loop)."


def _apply_op(op, a, b):
    """Apply a binary operator to two numbers."""
    if op == '+': return a + b
    if op == '-': return a - b
    if op == '*': return a * b
    if op == '/':
        if b == 0:
            raise ZeroDivisionError("Division by zero!")
        return a / b
    if op == '^': return a ** b
    raise ValueError(f"Unknown operator: {op}")


def _should_reduce(stack_op, input_op):
    """Return True if the stack operator should reduce before the incoming input operator."""
    return PREC_TABLE.get(stack_op, {}).get(input_op, '') == '>'


def evaluate_expression(expr):
    """
    Evaluate a numeric arithmetic expression using two stacks:
      - val_stack  : holds numeric values
      - op_stack   : holds operators

    This mirrors the operator precedence algorithm but computes values.

    Returns
    -------
    result    : float or int (None if evaluation not possible)
    error_msg : str or None
    """
    if not expr.strip():
        return None, "Empty expression."

    tokens = tokenize_expression(expr)

    # Check that every operand is a valid number (no variable names)
    for tok in tokens:
        if tok == '$' or tok in OPERATORS:
            continue
        try:
            float(tok)
        except ValueError:
            return None, (
                f'"{tok}" is a variable — enter numbers only to evaluate '
                f'(e.g.  2 + 3 * 4  or  (10 - 2) ^ 2).'
            )

    val_stack = []    # numeric values
    op_stack  = ['$'] # operators (start with end-marker)

    def reduce_top():
        op = op_stack.pop()
        if op in ('(', '$'):
            return
        b = val_stack.pop()
        a = val_stack.pop()
        val_stack.append(_apply_op(op, a, b))

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok == '$':
            # End of input — drain remaining operators
            while op_stack and op_stack[-1] != '$':
                reduce_top()
            break

        if tok not in OPERATORS:
            # Number operand
            val_stack.append(float(tok))
            i += 1
            continue

        if tok == '(':
            op_stack.append('(')
            i += 1
            continue

        if tok == ')':
            # Reduce until matching '('
            while op_stack and op_stack[-1] != '(':
                reduce_top()
            if op_stack and op_stack[-1] == '(':
                op_stack.pop()  # discard '('
            i += 1
            continue

        # Regular operator: reduce higher/equal precedence ops first, then push
        while (op_stack
               and op_stack[-1] not in ('(', '$')
               and _should_reduce(op_stack[-1], tok)):
            reduce_top()
        op_stack.append(tok)
        i += 1

    if not val_stack:
        return None, "Evaluation failed — no value produced."

    result = val_stack[0]
    # Return as int if it's a whole number, else round to 6 decimal places
    if result == int(result):
        return int(result), None
    return round(result, 6), None


def get_precedence_table_display():
    """Return the precedence table as rows/cols for tabular display."""
    ops = ['+', '-', '*', '/', '^', '(', ')', '$']
    rows = []
    for r in ops:
        row = {'↓ stack  /  input →': r}
        for c in ops:
            row[c] = PREC_TABLE.get(r, {}).get(c, ' ')
        rows.append(row)
    return rows


# ════════════════════════════════════════════════════════════════════════════
#  EXPRESSION TREE, DAG & THREE ADDRESS CODE
# ════════════════════════════════════════════════════════════════════════════

class ExprNode:
    """A single node in the expression tree (leaf = operand, internal = operator)."""

    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right
        self.is_leaf = (left is None and right is None)


def build_expression_tree(expr):
    """
    Build a binary expression tree using the operator precedence method.

    Uses two stacks — one for tree nodes (instead of values) and one for
    operators — same algorithm as evaluate_expression but builds a tree.

    Returns
    -------
    root : ExprNode or None
    error : str or None
    """
    if not expr.strip():
        return None, "Empty expression."

    tokens = tokenize_expression(expr)
    node_stack = []   # holds ExprNode objects
    op_stack = ['$']  # holds operator characters

    def reduce_top():
        op = op_stack.pop()
        if op in ('(', '$'):
            return
        right = node_stack.pop()
        left = node_stack.pop()
        node_stack.append(ExprNode(op, left, right))

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok == '$':
            while op_stack and op_stack[-1] != '$':
                reduce_top()
            break

        if tok not in OPERATORS:
            node_stack.append(ExprNode(tok))  # leaf node
            i += 1
            continue

        if tok == '(':
            op_stack.append('(')
            i += 1
            continue

        if tok == ')':
            while op_stack and op_stack[-1] != '(':
                reduce_top()
            if op_stack and op_stack[-1] == '(':
                op_stack.pop()
            i += 1
            continue

        # Regular operator
        while (op_stack
               and op_stack[-1] not in ('(', '$')
               and _should_reduce(op_stack[-1], tok)):
            reduce_top()
        op_stack.append(tok)
        i += 1

    if not node_stack:
        return None, "Could not build expression tree."
    return node_stack[0], None


def build_dag(tree_root):
    """
    Convert an expression tree into a DAG (Directed Acyclic Graph).

    Shares nodes when two subtrees are identical (same operator + same children).
    For example, in  (a+b) * (a+b)  the subtree  a+b  appears only once in the DAG.

    Returns
    -------
    dag_root : ExprNode  (a new tree where identical subtrees share the same node)
    """
    seen = {}  # maps a content-based key → ExprNode

    def _build(node):
        if node.is_leaf:
            key = ('leaf', node.value)
        else:
            left_dag, left_key = _build(node.left)
            right_dag, right_key = _build(node.right)
            key = (node.value, left_key, right_key)

        if key in seen:
            return seen[key], key

        if node.is_leaf:
            dag_node = ExprNode(node.value)
        else:
            dag_node = ExprNode(node.value, left_dag, right_dag)

        seen[key] = dag_node
        return dag_node, key

    dag_root, _ = _build(tree_root)
    return dag_root


def generate_three_address_code(node, use_dag=False):
    """
    Generate three-address code (TAC) from an expression tree or DAG.

    Each intermediate result gets a temporary variable: t1, t2, ...
    When use_dag=True, shared DAG nodes reuse their temp (avoids recomputing).

    Returns
    -------
    code   : list of strings  (e.g. ["t1 = a + b", "t2 = t1 * c"])
    result : str              (the final temp variable or operand)
    """
    code = []
    temp_count = [0]
    computed = {}  # maps node id → temp name (only used for DAG)

    def _gen(node):
        nid = id(node)

        # For DAG: if this node was already computed, reuse its temp
        if use_dag and nid in computed:
            return computed[nid]

        if node.is_leaf:
            if use_dag:
                computed[nid] = node.value
            return node.value

        left_result = _gen(node.left)
        right_result = _gen(node.right)

        temp_count[0] += 1
        temp_name = f"t{temp_count[0]}"
        code.append(f"{temp_name} = {left_result} {node.value} {right_result}")

        if use_dag:
            computed[nid] = temp_name
        return temp_name

    result = _gen(node)
    return code, result


def expr_tree_to_dot(node):
    """Convert an expression tree or DAG to Graphviz DOT format."""
    lines = [
        'digraph {',
        '    node [shape=circle, style=filled, fontsize=14];',
    ]
    counter = [0]
    visited = {}  # maps id(node) → graphviz node id

    def _add(node):
        nid = id(node)
        if nid in visited:
            return visited[nid]

        my_id = counter[0]
        counter[0] += 1
        visited[nid] = my_id

        color = '"#90EE90"' if node.is_leaf else '"#ADD8E6"'
        lines.append(f'    n{my_id} [label="{node.value}", fillcolor={color}];')

        if not node.is_leaf:
            left_id = _add(node.left)
            right_id = _add(node.right)
            lines.append(f'    n{my_id} -> n{left_id} [label="L"];')
            lines.append(f'    n{my_id} -> n{right_id} [label="R"];')

        return my_id

    _add(node)
    lines.append('}')
    return '\n'.join(lines)
