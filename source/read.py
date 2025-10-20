import re

class Term:
    def __init__(self, type, value, args=None):
        self.type = type
        self.value = value
        self.args = args or []

    def __repr__(self):
        if self.type == 'function':
            return f"{self.value}({', '.join(str(a) for a in self.args)})"
        return self.value

class Literal:
    def __init__(self, predicate, terms, negated=False):
        self.type = 'literal'
        self.predicate = predicate
        self.terms = terms
        self.negated = negated

    def __repr__(self):
        sign = "¬" if self.negated else ""
        return f"{sign}{self.predicate}({', '.join(str(t) for t in self.terms)})"

class Formula:
    def __init__(self, type, content, children=None, quantifier_var=None):
        self.type = type
        self.content = content
        self.children = children or []
        self.quantifier_var = quantifier_var

    def __repr__(self):
        if self.type == 'literal':
            return self.content.__repr__()
        if self.type == 'quantifier':
            return f"{self.content}{self.quantifier_var} ({' '.join(str(c) for c in self.children)})"
        return f"({' {} '.format(self.content).join(str(c) for c in self.children)})"

def read_formulas_from_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error al leer {path}: {e}")
        return None

def parse_formulas(txt):
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    return [parse_single_formula(ln) for ln in lines]

def parse_single_formula(s):
    s = s.strip()
    while s.startswith('(') and s.endswith(')') and _balanced(s[1:-1]):
        s = s[1:-1].strip()

    # Cuantificadores
    if s.startswith('∀') or s.startswith('∃'):
        return _parse_quantifier(s)

    # Negación
    if s.startswith('¬'):
        inner = parse_single_formula(s[1:].strip())
        if inner.type == 'literal':
            lit = inner.content
            return Formula('literal', Literal(lit.predicate, lit.terms, not lit.negated))
        return Formula('connective', '¬', [inner])

    # Orden de precedencia: bicondicional ↔ / ⇔ / <->, luego →, ⇒, luego ∨, luego ∧
    for conn in ['↔', '⇔', '<->', '→', '⇒', '∨', '∧']:
        pos = _find_conn(s, conn)
        if pos != -1:
            left = parse_single_formula(s[:pos].strip())
            right = parse_single_formula(s[pos+len(conn):].strip())
            return Formula('connective', conn, [left, right])

    # Literal con argumentos
    m = re.match(r'^([A-Za-z_][A-Za-z_0-9]*)\(([^)]*)\)$', s)
    if m:
        pred = m.group(1)
        args_s = m.group(2).strip()
        terms = []
        if args_s:
            for t in split_args(args_s):
                t = t.strip()
                if '(' in t and t.endswith(')'):
                    fname = t[:t.index('(')]
                    inner = t[t.index('(')+1:-1]
                    inner_terms = [_make_term(x.strip()) for x in split_args(inner)]
                    terms.append(Term('function', fname, inner_terms))
                else:
                    terms.append(_make_term(t))
        return Formula('literal', Literal(pred, terms))

    # Predicado 0-ario
    if s and s[0].isalpha():
        return Formula('literal', Literal(s, []))

    raise ValueError(f"No se pudo parsear: {s}")

# -------- Helpers de parseo --------

def _parse_quantifier(s):
    q = s[0] # '∀' o '∃'
    rest = s[1:].strip()
    m = re.match(r'^([a-zA-Z_][a-zA-Z_0-9]*)\s*(.*)$', rest)
    if not m:
        raise ValueError(f"Cuantificador mal formado: {s}")
    var = m.group(1)
    inner_str = m.group(2).strip()
    while inner_str.startswith('(') and inner_str.endswith(')') and _balanced(inner_str[1:-1]):
        inner_str = inner_str[1:-1].strip()
    inner = parse_single_formula(inner_str)
    return Formula('quantifier', q, [inner], var)

def _balanced(s):
    c = 0
    for ch in s:
        if ch == '(':
            c += 1
        elif ch == ')':
            c -= 1
        if c < 0:
            return False
    return c == 0

def _find_conn(s, conn):
    depth = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if depth == 0 and s.startswith(conn, i):
            return i
        i += 1
    return -1

def split_args(s):
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

def _make_term(token):
    if not token:
        return Term('constant', 'UNK')
    # Minúscula → variable; Mayúscula → constante
    if token[0].islower():
        return Term('variable', token)
    return Term('constant', token)
