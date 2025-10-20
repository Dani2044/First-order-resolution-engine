# fnc.py
from source.read import Term, Literal, Formula

class FNCConverter:
    def __init__(self):
        self.sk_counter = 0

    # --- Pipeline ---
    def convert_to_fnc(self, formula):
        """Convierte una fórmula arbitraria en Forma Normal Conjuntiva (FNC)."""
        f = self._elim_biconditionals(formula)
        f = self._elim_implications(f)
        f = self._push_negations(f)
        f = self._standardize(f, {})
        f = self._skolemize(f, [])
        f = self._drop_forall(f)
        f = self._to_cnf(f)
        return f

    # --- 1. Eliminar bicondicionales (↔) ---
    def _elim_biconditionals(self, f):
        if f.type == 'connective' and f.content in ('↔', '⇔', '<->'):
            a, b = f.children
            # α ↔ β ≡ (α → β) ∧ (β → α)
            left = Formula('connective', '→', [a, b])
            right = Formula('connective', '→', [b, a])
            combined = Formula('connective', '∧', [left, right])
            return self._elim_biconditionals(combined)
        if f.type in ('connective', 'quantifier'):
            return Formula(f.type, f.content,
                           [self._elim_biconditionals(c) for c in f.children],
                           f.quantifier_var)
        return f

    # --- 2. Eliminar implicaciones (→) ---
    def _elim_implications(self, f):
        if f.type == 'connective' and f.content in ('→', '⇒'):
            a, b = f.children
            # α → β ≡ ¬α ∨ β
            return Formula('connective', '∨', [
                Formula('connective', '¬', [self._elim_implications(a)]),
                self._elim_implications(b)
            ])
        if f.type in ('connective', 'quantifier'):
            return Formula(f.type, f.content,
                           [self._elim_implications(c) for c in f.children],
                           f.quantifier_var)
        return f

    # --- 3. Mover negaciones hacia los literales ---
    def _push_negations(self, f):
        if f.type == 'connective' and f.content == '¬':
            a = f.children[0]
            # ¬¬φ = φ
            if a.type == 'connective' and a.content == '¬':
                return self._push_negations(a.children[0])
            # De Morgan
            if a.type == 'connective' and a.content == '∧':
                return self._make_or(
                    self._push_negations(Formula('connective', '¬', [a.children[0]])),
                    self._push_negations(Formula('connective', '¬', [a.children[1]]))
                )
            if a.type == 'connective' and a.content == '∨':
                return self._make_and(
                    self._push_negations(Formula('connective', '¬', [a.children[0]])),
                    self._push_negations(Formula('connective', '¬', [a.children[1]]))
                )
            # cuantificadores: ¬∀x φ ≡ ∃x ¬φ ; ¬∃x φ ≡ ∀x ¬φ
            if a.type == 'quantifier':
                flipped = '∃' if a.content == '∀' else '∀'
                inner = self._push_negations(Formula('connective', '¬', [a.children[0]]))
                return Formula('quantifier', flipped, [inner], a.quantifier_var)
            # Literal
            if a.type == 'literal':
                lit = a.content if isinstance(a.content, Literal) else a
                return Formula('literal', Literal(lit.predicate, lit.terms, not lit.negated))
        if f.type in ('connective', 'quantifier'):
            return Formula(f.type, f.content,
                           [self._push_negations(c) for c in f.children],
                           f.quantifier_var)
        return f

    # --- 4. Estandarizar variables (nombres únicos) ---
    def _standardize(self, f, env):
        if f.type == 'quantifier':
            old = f.quantifier_var
            new = self._fresh_var(old, env)
            subenv = env.copy()
            subenv[old] = new
            child = self._standardize(
                self._subst_var(f.children[0], old, Term('variable', new)), subenv
            )
            return Formula('quantifier', f.content, [child], new)
        if f.type == 'connective':
            return Formula('connective', f.content,
                           [self._standardize(c, env) for c in f.children])
        if f.type == 'literal':
            lit = f.content if isinstance(f.content, Literal) else f
            new_terms = []
            for t in lit.terms:
                if t.type == 'variable' and t.value in env:
                    new_terms.append(Term('variable', env[t.value]))
                else:
                    new_terms.append(t)
            return Formula('literal', Literal(lit.predicate, new_terms, lit.negated))
        return f

    # --- 5. Skolemización (eliminar ∃) ---
    def _skolemize(self, f, univ_vars):
        if f.type == 'quantifier':
            if f.content == '∀':
                return Formula('quantifier', '∀',
                               [self._skolemize(f.children[0], univ_vars + [f.quantifier_var])],
                               f.quantifier_var)
            else:  # ∃
                sk = self._sk_term(univ_vars)
                body = self._subst_var(f.children[0], f.quantifier_var, sk)
                return self._skolemize(body, univ_vars)
        if f.type == 'connective':
            return Formula('connective', f.content,
                           [self._skolemize(c, univ_vars) for c in f.children])
        return f

    # --- 6. Eliminar cuantificadores universales ---
    def _drop_forall(self, f):
        if f.type == 'quantifier' and f.content == '∀':
            return self._drop_forall(f.children[0])
        if f.type == 'connective':
            return Formula('connective', f.content,
                           [self._drop_forall(c) for c in f.children])
        return f

    # --- 7. Mover disyunciones y obtener CNF ---
    def _to_cnf(self, f):
        """Convierte la fórmula a CNF (conjunción de disyunciones)."""
        if f.type != 'connective':
            return f

        # Recursión sobre hijos
        children = [self._to_cnf(c) for c in f.children]

        if f.content == '∧':
            return self._make_and(children[0], children[1])
        if f.content == '∨':
            return self._distribute(children[0], children[1])
        if f.content == '¬':  # ¬ ya debería envolver literales
            return f
        return f

    # --- 8. Extraer cláusulas de una fórmula CNF ---
    def formula_to_clauses(self, f):
        """Extrae una lista de cláusulas (listas de Literales) desde una fórmula CNF."""
        clauses = []

        def walk(node):
            if node.type == 'connective' and node.content == '∧':
                walk(node.children[0])
                walk(node.children[1])
            else:
                lits = self._flatten_disjunction(node)
                if lits:
                    clauses.append(lits)

        walk(f)
        return clauses

    # --- Auxiliares de sustitución y Skolemización ---
    def _fresh_var(self, base, env):
        i = 1
        while True:
            cand = f"{base}{i}"
            if cand not in env.values():
                return cand
            i += 1

    def _subst_var(self, f, varname, term):
        if f.type == 'literal':
            lit = f.content if isinstance(f.content, Literal) else f
            new_terms = [self._subst_term(t, varname, term) for t in lit.terms]
            return Formula('literal', Literal(lit.predicate, new_terms, lit.negated))
        if f.type == 'connective':
            return Formula('connective', f.content,
                           [self._subst_var(c, varname, term) for c in f.children])
        if f.type == 'quantifier':
            if f.quantifier_var == varname:
                return f
            return Formula('quantifier', f.content,
                           [self._subst_var(f.children[0], varname, term)], f.quantifier_var)
        return f

    def _subst_term(self, t, varname, term):
        if t.type == 'variable' and t.value == varname:
            return term
        if t.type == 'function':
            return Term('function', t.value,
                        [self._subst_term(a, varname, term) for a in t.args])
        return t

    def _sk_term(self, univ_vars):
        if univ_vars:
            args = [Term('variable', v) for v in univ_vars]
            name = f"F{self.sk_counter}"
            self.sk_counter += 1
            return Term('function', name, args)
        else:
            name = f"C{self.sk_counter}"
            self.sk_counter += 1
            return Term('constant', name)

    # --- Utilidades lógicas ---
    def _make_and(self, a, b):
        if a is None:
            return b
        if b is None:
            return a
        return Formula('connective', '∧', [a, b])

    def _make_or(self, a, b):
        return Formula('connective', '∨', [a, b])

    def _distribute(self, a, b):
        # (a ∨ (b1 ∧ b2)) = (a ∨ b1) ∧ (a ∨ b2)
        # ((a1 ∧ a2) ∨ b) = (a1 ∨ b) ∧ (a2 ∨ b)
        if a.type == 'connective' and a.content == '∧':
            return self._make_and(self._distribute(a.children[0], b),
                                  self._distribute(a.children[1], b))
        if b.type == 'connective' and b.content == '∧':
            return self._make_and(self._distribute(a, b.children[0]),
                                  self._distribute(a, b.children[1]))
        return self._make_or(a, b)

    def _flatten_disjunction(self, node):
        """Devuelve lista de Literales de una disyunción (∨)."""
        lits = []

        def dfs(n):
            if n.type == 'connective' and n.content == '∨':
                dfs(n.children[0])
                dfs(n.children[1])
            elif n.type == 'literal':
                lit = n.content if isinstance(n.content, Literal) else n
                lits.append(lit)
            elif n.type == 'connective' and n.content == '¬' and n.children and n.children[0].type == 'literal':
                lit = n.children[0].content
                lits.append(Literal(lit.predicate, lit.terms, True))

        dfs(node)
        return lits

    def _literal_to_string(self, lit):
        sgn = "¬" if lit.negated else ""
        return f"{sgn}{lit.predicate}({', '.join(str(t) for t in lit.terms)})"
    
        # --- Conversión de cláusula a texto ---
    def clause_to_string(self, lits):
        """Convierte una lista de Literales en una representación textual."""
        parts = []
        for lit in lits:
            sign = "¬" if lit.negated else ""
            args = ", ".join(str(t) for t in lit.terms)
            parts.append(f"{sign}{lit.predicate}({args})")
        # Eliminar duplicados manteniendo orden
        seen, out = set(), []
        for p in parts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return " ∨ ".join(out)


# --- Pretty printer ---
def print_detailed_structure(formula, indent=0):
    pad = "  " * indent
    if formula.type == 'literal':
        lit = formula.content if isinstance(formula.content, Literal) else formula
        return (f"{pad}Literal: {lit}\n"
                f"{pad}  Predicado: {lit.predicate}\n"
                f"{pad}  Términos: {[str(t) for t in lit.terms]}\n"
                f"{pad}  Negado: {lit.negated}")
    if formula.type == 'quantifier':
        out = f"{pad}Cuantificador: {formula.content}{formula.quantifier_var}"
        for c in formula.children:
            out += "\n" + print_detailed_structure(c, indent + 1)
        return out
    if formula.type == 'connective':
        out = f"{pad}Conectivo: {formula.content}"
        for i, c in enumerate(formula.children):
            out += f"\n{pad}  Hijo {i + 1}:\n" + print_detailed_structure(c, indent + 2)
        return out
    return f"{pad}{formula}"
