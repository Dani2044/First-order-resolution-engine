import os
import sys

from read import read_formulas_from_file, parse_formulas
from fnc import FNCConverter, print_detailed_structure
from inference import Clause, Literal, Term, perform_inference

def convert_and_save(input_path, fnc_out_path, read_out_path):
    txt = read_formulas_from_file(input_path)
    if not txt:
        print("No se pudo leer el archivo de entrada.")
        return [], None

    # Separar líneas y detectar la última (pregunta)
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    question_line = lines[-1]
    premise_lines = lines[:-1]
    premise_text = "\n".join(premise_lines)

    # parsear premisas y pregunta por separado
    formulas = parse_formulas(premise_text)
    question_formula = parse_formulas(question_line)[0]

    # guardar estructura de las premisas
    os.makedirs(os.path.dirname(read_out_path) if os.path.dirname(read_out_path) else 'output', exist_ok=True)
    with open(read_out_path, 'w', encoding='utf-8') as f:
        f.write("ANÁLISIS DE FÓRMULAS ORIGINALES\n")
        f.write("="*50 + "\n\n")
        f.write("Contenido del archivo:\n")
        f.write("-"*50 + "\n")
        f.write(txt + "\n")
        f.write("-"*50 + "\n\n")
        f.write("Fórmulas parseadas (premisas):\n")
        f.write("-"*50 + "\n")
        for i, fm in enumerate(formulas, 1):
            f.write(f"{i}. {fm}\n")
        f.write(f"\nPregunta (para refutación): {question_formula}\n\n")
        f.write("Estructura detallada de las premisas:\n")
        f.write("-"*50 + "\n")
        for i, fm in enumerate(formulas, 1):
            f.write(f"\n--- Fórmula {i} ---\n")
            f.write(print_detailed_structure(fm) + "\n")

    # Convertir las premisas a FNC
    conv = FNCConverter()
    all_clauses = []
    with open(fnc_out_path, 'w', encoding='utf-8') as f:
        f.write("FORMA NORMAL CONJUNTIVA\n")
        f.write("=" * 50 + "\n\n")
        for fm in formulas:
            cnf = conv.convert_to_fnc(fm)
            cls = conv.formula_to_clauses(cnf)
            for lits in cls:
                line = conv.clause_to_string(lits)
                if line.strip():
                    f.write(line + "\n")
                    all_clauses.append(line)
    return question_formula


def infer(fnc_path, inference_out_path, question_formula):
    """Niega la pregunta final del archivo y prueba por refutación."""
    if question_formula.type != 'literal':
        print("La pregunta debe ser una fórmula literal simple.")
        return

    # Convertir la fórmula literal directamente a cláusula
    lit = question_formula.content
    query_clause = Clause([Literal(lit.predicate, lit.terms, lit.negated)])
    ok, _ = perform_inference(fnc_path, inference_out_path, query_clause=query_clause)

    final = (
        "VERDADERO - la afirmación final se deduce de las premisas"
        if ok else "FALSO - no se pudo deducir la afirmación final"
    )
    with open(inference_out_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*60 + "\n")
        f.write("RESULTADO FINAL: " + final + "\n")
        f.write("="*60 + "\n")
    print(final)


def main():
    # Rutas por defecto
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = "data/curiosidad.txt"

    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    fnc_out = os.path.join(out_dir, "fnc.txt")
    read_out = os.path.join(out_dir, "read.txt")
    inference_out = os.path.join(out_dir, "inference.txt")

    question = convert_and_save(input_path, fnc_out, read_out)
    if question:
        infer(fnc_out, inference_out, question)
    else:
        print("No se detectó una pregunta para refutación.")

if __name__ == "__main__":
    main()
