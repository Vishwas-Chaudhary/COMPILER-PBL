"""
app.py - Grammar Analyzer Web App (Streamlit)

Supports two parsers:
  1. Recursive Descent Parser  (for Context-Free Grammars)
  2. Operator Precedence Parser (for arithmetic expressions)

Run with:  python -m streamlit run app.py
"""

import streamlit as st
from lexer import tokenize_grammar, build_symbol_table
from validator import validate_cfg, semantic_analysis, eliminate_left_recursion
from cfg_parser import RecursiveDescentParser, get_first_follow, generate_cfg_assembly
from op_parser import (parse_expression, evaluate_expression, get_precedence_table_display,
                       build_expression_tree, build_dag, generate_three_address_code,
                       expr_tree_to_dot, generate_assembly_from_tac)

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Grammar Analyzer", layout="wide")

# ─── Graphviz Helper ────────────────────────────────────────────────────────
counter = [0]

def _add_nodes(node, lines, annotated=False):
    my_id = counter[0]
    counter[0] += 1
    if annotated:
        if node.is_terminal:
            label = f"{node.symbol}\\n[T]"
        elif node.production_used:
            label = f"{node.symbol}\\n{node.production_used}"
        else:
            label = f"{node.symbol}\\n[NT]"
    else:
        label = node.symbol
    color = "lightgreen" if node.is_terminal else ("lightyellow" if annotated else "lightblue")
    lines.append(f'    n{my_id} [label="{label}", fillcolor={color}];')
    for child in node.children:
        child_id = counter[0]
        _add_nodes(child, lines, annotated)
        lines.append(f"    n{my_id} -> n{child_id};")

def tree_to_dot(node, annotated=False):
    counter[0] = 0
    shape = "box" if annotated else "circle"
    lines = [
        "digraph Tree {",
        f'    node [shape={shape}, style=filled, fontsize={"12" if annotated else "14"}];'
    ]
    _add_nodes(node, lines, annotated)
    lines.append("}")
    return "\n".join(lines)

# ─── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("Parser Settings")

parser_choice = st.sidebar.radio(
    "**Select Parser Type**",
    ["Recursive Descent Parser", "Operator Precedence Parser"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### Recursive Descent
- Works on **Context-Free Grammars**
- Uses **backtracking**
- You define your own grammar rules

### Operator Precedence
- Works on **arithmetic expressions**
- Uses a **precedence table**
- Supports: `+`  `-`  `*`  `/`  `^`  `()`
""")

# ─── Main Title ─────────────────────────────────────────────────────────────
st.title("Grammar Analyzer")
st.caption("Mini Compiler Pipeline — Choose a parser from the sidebar")

st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════
#  RECURSIVE DESCENT PARSER
# ════════════════════════════════════════════════════════════════════════════
if "Recursive" in parser_choice:

    st.header("Recursive Descent Parser")
    st.write("Define a Context-Free Grammar (CFG) and enter a string to check if it is accepted.")

    st.subheader("Step 1: Enter Grammar")
    st.caption("One rule per line. Format: `S -> aA | b`  •  Use `e` or `#` for epsilon.")

    grammar_text = st.text_area(
        "Grammar Rules:",
        value="S -> aA | b\nA -> a | bA",
        height=130,
    )
    input_string = st.text_input("String to Parse:", value="aa")
    analyze = st.button("Analyze", key="rdp_btn")

    if analyze:
        grammar = {}
        error = None

        for line in grammar_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if "->" not in line:
                error = f"Line '{line}' is missing '->'"
                break
            lhs, rhs = line.split("->", 1)
            lhs = lhs.strip()
            new_prods = [p.strip() for p in rhs.split("|")]
            if lhs in grammar:
                grammar[lhs].extend(new_prods)   # accumulate, don't overwrite
            else:
                grammar[lhs] = new_prods

        if error:
            st.error(error)
        elif not grammar:
            st.error("No grammar entered.")
        else:
            start = list(grammar.keys())[0]

            with st.expander("Your Grammar", expanded=True):
                st.write(f"**Start symbol:** `{start}`")
                for lhs, prods in grammar.items():
                    st.write(f"`{lhs}` → `{' | '.join(prods)}`")

            # Phase 1 – Lexical Analysis
            st.subheader("Phase 1 - Lexical Analysis (Tokens)")
            tokens = tokenize_grammar(grammar)
            st.table([{"#": i, "Type": t["type"], "Value": t["value"]}
                      for i, t in enumerate(tokens, 1)])

            # Phase 2A – Grammar Validation
            st.subheader("Phase 2 - Grammar Validation")
            valid, message = validate_cfg(grammar)
            if valid:
                st.success("PASS — " + message)
            else:
                st.error("FAIL — " + message)
                st.stop()

            # Phase 3 – Semantic Analysis
            st.subheader("Phase 3 - Semantic Analysis")
            warnings = semantic_analysis(grammar)
            if not warnings:
                st.success("No warnings found.")
            else:
                for w in warnings:
                    st.warning(w)

            if any("left recursion" in w.lower() for w in warnings):
                st.info("Left recursion detected — auto-transforming grammar...")
                new_grammar, changed, mapping, elim_error = eliminate_left_recursion(grammar)
                if elim_error:
                    st.error(f"Could not eliminate left recursion: {elim_error}")
                    st.stop()
                if changed:
                    st.subheader("Transformed Grammar (Left Recursion Removed)")
                    for orig, new_nt in mapping.items():
                        st.caption(f"`{new_nt}` represents `{orig}'` (primed version of {orig})")
                    for lhs, prods in new_grammar.items():
                        st.write(f"`{lhs}` -> `{' | '.join(prods)}`")
                    grammar = new_grammar
                    start = list(grammar.keys())[0]

            # Phase 2B – Parsing
            st.subheader("Parsing Result")
            parser = RecursiveDescentParser(grammar)
            accepted, tree = parser.parse(input_string)
            if accepted:
                st.success(f'String  **"{input_string}"**  is  **ACCEPTED**')
            else:
                st.error(f'String  **"{input_string}"**  is  **REJECTED**')

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Parse Tree")
                if tree:
                    st.graphviz_chart(tree_to_dot(tree))
                else:
                    st.info("No parse tree (string rejected)")
            with col2:
                st.subheader("Annotated Parse Tree")
                if tree:
                    st.graphviz_chart(tree_to_dot(tree, annotated=True))
                else:
                    st.info("No annotated tree (string rejected)")

            # Symbol Table
            st.subheader("Symbol Table")
            symbol_table = build_symbol_table(grammar)
            st.table([{
                "Symbol": e["name"], "Type": e["type"], "Role": e["role"],
                "Appears In": ", ".join(e["defined_in"] + e["used_in"]) or "-"
            } for e in symbol_table])

            # ── FIRST and FOLLOW Sets ────────────────────────────────────────
            st.subheader("FIRST and FOLLOW Sets")
            st.caption(
                "These sets are computed from the grammar and are used internally "
                "by the Recursive Descent Parser to decide which production to try."
            )

            first_sets, follow_sets = get_first_follow(grammar)

            def fmt_set(s):
                """Format a set for display, sorting terminals nicely."""
                parts = []
                for sym in sorted(s):
                    if sym == 'ε':
                        parts.append('**ε** (epsilon)')
                    elif sym == '$':
                        parts.append('**$** (end-of-input)')
                    else:
                        parts.append(f'`{sym}`')
                return ',  '.join(parts) if parts else '∅ (empty)'

            ff_rows = []
            for nt in grammar.keys():
                ff_rows.append({
                    "Non-Terminal": nt,
                    "FIRST Set": fmt_set(first_sets.get(nt, set())),
                    "FOLLOW Set": fmt_set(follow_sets.get(nt, set())),
                })

            # Render as a markdown table so bold/code renders properly
            header = "| Non-Terminal | FIRST Set | FOLLOW Set |\n|:---:|:---|:---|\n"
            rows_md = "".join(
                f"| `{r['Non-Terminal']}` | {r['FIRST Set']} | {r['FOLLOW Set']} |\n"
                for r in ff_rows
            )
            st.markdown(header + rows_md)

            with st.expander("How are FIRST and FOLLOW computed? (click for rules)"):
                st.markdown("""
**FIRST(A)** — terminals that can begin a string derived from A:
- If `A → a…`, add `a` to FIRST(A)
- If `A → ε`, add `ε` to FIRST(A)
- If `A → Bα`, add FIRST(B) − {ε} to FIRST(A); if ε ∈ FIRST(B), also add FIRST(α)

**FOLLOW(A)** — terminals that can appear immediately *after* A in any sentential form:
- Add `$` to FOLLOW(start symbol)
- If `B → αAβ`, add FIRST(β) − {ε} to FOLLOW(A)
- If `B → αA` or ε ∈ FIRST(β), add FOLLOW(B) to FOLLOW(A)

*These sets drive the predictive parsing decisions inside the Recursive Descent Parser.*
""")

            # ── Phase 4: Assembly Code Generation ───────────────────────────────
            st.subheader("💻 Phase 4 — Assembly Code Generation")
            st.caption(
                "The compiler translates the parse tree into x86 assembly. "
                "Each grammar rule becomes a labelled function; each character check becomes a compare instruction."
            )

            with st.expander("📌 What each part of the assembly code means", expanded=True):
                st.markdown("""
**`; input = "aa"`**  
A comment showing what input string is loaded into memory.

**`main:`**  
Program starts here. `MOV SI, "aa"` loads the address of the input into `SI` — the pointer that moves through memory character by character.

**`CALL parse_S`**  
Jump into the function for the start symbol `S`. Each non-terminal in your grammar becomes its own labelled function.

**`parse_S:  ; S -> aA`**  
Function body for non-terminal `S`, applying rule `S -> aA`. After checking all characters, `RET` returns to the caller.

**`CMP [SI], 'a'`**  
Compare the character currently at `SI` (the input pointer) with the expected terminal. This is how the compiler checks one character.

**`JE ok1`** / **`ok1:`**  
If the character matched → jump to `ok1`, then `INC SI` moves the pointer one step forward in memory.

**`JMP REJECT`**  
Character did not match → skip everything and go to REJECT.

**`ACCEPT:` / `REJECT:`**  
If the pointer reached end of input (`0`) → print `ACCEPTED`. Otherwise → print `REJECTED`.

**`; epsilon (match nothing)`**  
An epsilon production matches no character — no `CMP` is emitted and `SI` does not move.
""")

            asm_lines = generate_cfg_assembly(tree, input_string)
            st.code('\n'.join(asm_lines), language='nasm')

            st.success("Analysis complete!")



# ════════════════════════════════════════════════════════════════════════════
#  OPERATOR PRECEDENCE PARSER
# ════════════════════════════════════════════════════════════════════════════
else:
    st.header("Operator Precedence Parser")
    st.write(
        "Parses **arithmetic expressions** using an operator precedence table. "
        "Supports `+`  `-`  `*`  `/`  `^`  `( )`  with correct precedence and associativity."
    )

    # Precedence Table expander
    with st.expander("Operator Precedence Table  (click to expand)", expanded=False):
        st.markdown(
            "**Relations:** `<` = shift (yield)  •  `>` = reduce (takes)  •  `=` = equal  •  ` ` = error"
        )
        rows = get_precedence_table_display()
        st.table(rows)

    st.subheader("Enter an Arithmetic Expression")
    st.caption("Use letters/numbers as operands, e.g.  `a + b * c`  or  `(1 + 2) * 3`")

    expr_input = st.text_input(
        "Expression:",
        value="a + b * c",
        help="Operands can be any identifier or number. Operators: + - * / ^ ( )"
    )
    parse_btn = st.button("Parse Expression", key="opp_btn")

    if parse_btn:
        if not expr_input.strip():
            st.error("Please enter an expression.")
        else:
            accepted, steps, error_msg = parse_expression(expr_input)

            # Result banner
            st.subheader("Result")
            if accepted:
                st.success(f'Expression  **`{expr_input}`**  is  **ACCEPTED**')
            else:
                st.error(f'Expression  **`{expr_input}`**  is  **REJECTED**')
                if error_msg:
                    st.error(f"Reason: {error_msg}")

            # Step-by-step trace
            st.subheader("Step-by-Step Parsing Trace")
            st.caption(
                "Each row shows one move of the operator precedence algorithm. "
                "Relation symbols: `<` shift · `>` reduce · `=` shift (parens) · `-` operand"
            )

            step_data = []
            for s in steps:
                step_data.append({
                    "Step":            s["step"],
                    "Stack":           s["stack"],
                    "Input Remaining": s["input"],
                    "Relation":        s["relation"],
                    "Action":          s["action"],
                })
            st.table(step_data)

            # ── Result Evaluator ──────────────────────────────────────────────
            if accepted:
                st.subheader("Computed Result")
                result, eval_err = evaluate_expression(expr_input)
                if eval_err:
                    st.info(eval_err)
                else:
                    st.success(f"`{expr_input}`  **=  {result}**")

                # ── Expression Tree & DAG ─────────────────────────────────────
                tree_root, tree_err = build_expression_tree(expr_input)

                if tree_root and not tree_err:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Expression Tree")
                        st.graphviz_chart(expr_tree_to_dot(tree_root))

                    with col2:
                        st.subheader("DAG (Directed Acyclic Graph)")
                        dag_root = build_dag(tree_root)
                        st.graphviz_chart(expr_tree_to_dot(dag_root))
                        st.caption("Common sub-expressions share the same node. "
                                   "Try `(a+b) * (a+b)` to see node sharing.")

                    # ── Three Address Code ────────────────────────────────────
                    st.subheader("Three Address Code")

                    tac_col1, tac_col2 = st.columns(2)

                    with tac_col1:
                        st.markdown("**From Expression Tree:**")
                        tac_tree, tac_tree_result = generate_three_address_code(tree_root, use_dag=False)
                        if tac_tree:
                            for line in tac_tree:
                                st.code(line, language="text")
                            st.caption(f"Result in: `{tac_tree_result}`")
                        else:
                            st.info(f"Single operand: `{tac_tree_result}`")

                    with tac_col2:
                        st.markdown("**From DAG (optimized):**")
                        tac_dag, tac_dag_result = generate_three_address_code(dag_root, use_dag=True)
                        if tac_dag:
                            for line in tac_dag:
                                st.code(line, language="text")
                            st.caption(f"Result in: `{tac_dag_result}`")
                        else:
                            st.info(f"Single operand: `{tac_dag_result}`")

                    # ── Phase 4: Target Code Generation (Assembly) ─────────────
                    st.subheader("💻 Phase 4 — Assembly Code Generation")
                    st.caption(
                        "The compiler assigns every temporary variable a memory slot on the stack, "
                        "then loads operands into registers, computes the result, and stores it back."
                    )

                    with st.expander("📌 What each part of the assembly code means", expanded=True):
                        st.markdown("""
**`; t1 = b * c`**  
Shows which TAC instruction the next lines are translating.

**`LOAD  R1, mem[b]`**  
Load the value of variable `b` from memory into register `R1` (left operand).

**`LOAD  R2, mem[c]`**  
Load variable `c` into register `R2` (right operand).

**`MUL  R1, R2`** / **`ADD  R1, R2`** etc.  
Perform the operation. Result is placed in `R1`.

**`STORE  mem[t1], R1`**  
Write the result from `R1` back into memory under the name `t1`.

**`LOAD  R1, mem[t2]`** / **`RETURN R1`** *(last two lines)*  
Load the final result into `R1` and return it. This is the output of the whole expression.
""")

                    asm_col1, asm_col2 = st.columns(2)

                    with asm_col1:
                        st.markdown("**Assembly from Expression Tree TAC:**")
                        asm_tree, mmap_tree = generate_assembly_from_tac(
                            tac_tree, tac_tree_result)
                        st.code('\n'.join(asm_tree), language='nasm')
                        if mmap_tree:
                            st.caption("**Stack layout:**  " +
                                       "   ".join(f"`{v}` → `{s}`" for v,s in mmap_tree.items()))

                    with asm_col2:
                        st.markdown("**Assembly from DAG TAC (optimized):**")
                        asm_dag, mmap_dag = generate_assembly_from_tac(
                            tac_dag, tac_dag_result)
                        st.code('\n'.join(asm_dag), language='nasm')
                        if mmap_dag:
                            st.caption("**Stack layout:**  " +
                                       "   ".join(f"`{v}` → `{s}`" for v,s in mmap_dag.items()))

                st.success("Parsing complete!")
            else:
                st.info("Hover over the last row above to see where parsing failed.")
