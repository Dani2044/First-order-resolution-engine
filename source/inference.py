from source.read import Term, Literal

# ---------- Helpers de normalización ----------
def term_key(t):
    """Clave estructural para términos (variable/constante/función recursiva)."""
    if t.type in ('variable', 'constant'):
        return (t.type, t.value)
    if t.type == 'function':
        return ('function', t.value, tuple(term_key(a) for a in t.args))
    return ('unknown', getattr(t, 'value', str(t)))

def lit_key(l):
    """Clave estructural para un literal (incluye signo, predicado y términos)."""
    return (bool(l.negated), l.predicate, tuple(term_key(t) for t in l.terms))


class Clause:
    def __init__(self, literals):
        self.literals = literals

    def __repr__(self):
        return " ∨ ".join(str(l) for l in self.literals) if self.literals else "□"

    def signature(self):
        """Firma canónica de la cláusula (ordenada, no recursiva en objetos)."""
        return tuple(sorted(lit_key(l) for l in self.literals))

    def __eq__(self, other):
        return isinstance(other, Clause) and self.signature() == other.signature()

    def __hash__(self):
        return hash(self.signature())


class Substitution:
    def __init__(self):
        self.map = {}

    def add(self, var, term):
        self.map[var] = term

    def apply(self, term):
        if term.type == 'variable' and term.value in self.map:
            return self.map[term.value]
        if term.type == 'function':
            return Term('function', term.value, [self.apply(a) for a in term.args])
        return term


class ResolutionProver:
    def __init__(self, max_steps=500):
        self.clauses = []
        self.trace = []
        self.max_steps = max_steps

    def add_clause(self, c):
        self.clauses.append(c)

    def parse_clause_from_string(self, s):
        parts = [p.strip() for p in s.split('∨')]
        lits = []
        for p in parts:
            neg = p.startswith('¬')
            if neg:
                p = p[1:].strip()
            pred, args = p.split('(', 1)
            args = args[:-1]
            terms = []
            if args.strip():
                for t in self._split_args(args):
                    t = t.strip()
                    if '(' in t and t.endswith(')'):
                        fname = t[:t.index('(')]
                        inner = t[t.index('(')+1:-1]
                        inner_terms = [self._make_term(x.strip()) for x in self._split_args(inner)]
                        terms.append(Term('function', fname, inner_terms))
                    else:
                        terms.append(self._make_term(t))
            lits.append(Literal(pred.strip(), terms, neg))
        return Clause(lits)

    def _split_args(self, s):
        args, cur, d = [], [], 0
        for ch in s:
            if ch == ',' and d == 0:
                args.append(''.join(cur)); cur = []
            else:
                if ch == '(':
                    d += 1
                elif ch == ')':
                    d -= 1
                cur.append(ch)
        if cur:
            args.append(''.join(cur))
        return args

    def _make_term(self, tok):
        if not tok:
            return Term('constant', 'UNK')
        return Term('variable', tok) if tok[0].islower() else Term('constant', tok)

    def load_clauses_from_file(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                ln = line.strip()
                if not ln or ln.startswith('#'):
                    continue
                if '(' in ln and ')' in ln:
                    self.add_clause(self.parse_clause_from_string(ln))

    # ---------- Unificación ----------
    def unify(self, t1, t2, subst=None):
        if subst is None:
            subst = Substitution()
        t1 = subst.apply(t1); t2 = subst.apply(t2)
        if t1.type == 'variable':
            return self._unify_var(t1, t2, subst)
        if t2.type == 'variable':
            return self._unify_var(t2, t1, subst)
        if t1.type == 'constant' and t2.type == 'constant':
            return subst if t1.value == t2.value else None
        if t1.type == 'function' and t2.type == 'function' and t1.value == t2.value and len(t1.args) == len(t2.args):
            for a, b in zip(t1.args, t2.args):
                subst = self.unify(a, b, subst)
                if subst is None:
                    return None
            return subst
        return None

    def _unify_var(self, v, t, subst):
        # occurs-check
        if self._occurs(v, t, subst):
            return None
        # Extender
        subst.add(v.value, t)
        return subst

    def _occurs(self, v, t, subst):
        t = subst.apply(t)
        if t.type == 'variable' and t.value == v.value:
            return True
        if t.type == 'function':
            return any(self._occurs(v, a, subst) for a in t.args)
        return False

    def unify_all(self, terms1, terms2):
        subst = Substitution()
        for a, b in zip(terms1, terms2):
            r = self.unify(a, b, subst)
            if r is None:
                return None
            subst = r
        return subst

    # ---------- Resolución ----------
    def _apply_lit(self, lit, subst):
        new_terms = [subst.apply(t) for t in lit.terms]
        return Literal(lit.predicate, new_terms, lit.negated)

    def _is_tautology(self, lits):
        pos, neg = set(), set()
        for l in lits:
            k = (l.predicate, tuple(term_key(t) for t in l.terms))
            if l.negated:
                neg.add(k)
            else:
                pos.add(k)
        # Tautología si existe A y ¬A con mismos términos
        return any(k in neg for k in pos)

    def resolve_pair(self, c1, c2):
        resolvents = []
        for i, l1 in enumerate(c1.literals):
            for j, l2 in enumerate(c2.literals):
                if l1.predicate == l2.predicate and l1.negated != l2.negated and len(l1.terms) == len(l2.terms):
                    subst = self.unify_all(l1.terms, l2.terms)
                    if subst is None:
                        continue
                    # Construir resolvente sin duplicados por clave
                    new_lits, seen = [], set()
                    for k, l in enumerate(c1.literals):
                        if k == i: continue
                        nl = self._apply_lit(l, subst)
                        lk = lit_key(nl)
                        if lk not in seen:
                            seen.add(lk); new_lits.append(nl)
                    for k, l in enumerate(c2.literals):
                        if k == j: continue
                        nl = self._apply_lit(l, subst)
                        lk = lit_key(nl)
                        if lk not in seen:
                            seen.add(lk); new_lits.append(nl)
                    if not self._is_tautology(new_lits):
                        resolvents.append(Clause(new_lits))
        return resolvents

    def negate_clause(self, clause):
        return Clause([Literal(l.predicate, l.terms, not l.negated) for l in clause.literals])

    def prove_by_refutation(self, query=None):
        work = list(self.clauses)
        seen_signatures = {c.signature() for c in work}

        if query is not None:
            negated = self.negate_clause(query)
            work.append(negated)
            seen_signatures.add(negated.signature())
            self.trace.append(f"Consulta negada añadida: {negated}")

        step = 1
        while step <= self.max_steps:
            added_any = False
            # Pares (estático por iteración)
            pairs = [(work[i], work[j]) for i in range(len(work)) for j in range(i + 1, len(work))]
            for c1, c2 in pairs:
                for r in self.resolve_pair(c1, c2):
                    sig = r.signature()
                    if len(r.literals) == 0:
                        self.trace.append(f"Paso {step}: Resuelvo ({c1}) con ({c2}) ⇒ □ (contradicción)")
                        return True, self.trace
                    if sig not in seen_signatures:
                        seen_signatures.add(sig)
                        work.append(r)
                        added_any = True
                        self.trace.append(f"Paso {step}: Resuelvo ({c1}) con ({c2}) ⇒ {r}")
                        step += 1
                        if step > self.max_steps:
                            self.trace.append("Límite de pasos alcanzado. Deteniendo resolución.")
                            return False, self.trace
            if not added_any:
                self.trace.append("No se pueden generar más resolventes. Fin del proceso.")
                return False, self.trace
        self.trace.append("Límite máximo de pasos alcanzado sin contradicción.")
        return False, self.trace


def perform_inference(fnc_file, output_file, query_clause=None, imprimir_clausulas=False):
    prov = ResolutionProver(max_steps=500)
    prov.load_clauses_from_file(fnc_file)
    ok, trace = prov.prove_by_refutation(query_clause)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("INFERENCIA POR RESOLUCIÓN\n")
        f.write("=" * 50 + "\n\n")
        if query_clause:
            f.write(f"Consulta: {query_clause}\n")
            f.write(f"Negada: {prov.negate_clause(query_clause)}\n\n")

        if imprimir_clausulas:
            f.write("Cláusulas cargadas:\n")
            for i, c in enumerate(prov.clauses, 1):
                f.write(f"{i}. {c}\n")
            f.write("\n")

        f.write("Proceso de inferencia (pasos útiles):\n")
        f.write("-" * 50 + "\n")
        for line in trace:
            f.write(line + "\n")
        f.write("\n")
        f.write("Resultado final: " + ("VERDADERO (contradicción encontrada)" if ok else "NO SE PUDO PROBAR") + "\n")
    return ok, trace
