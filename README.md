# 🧩 First-Order Resolution Engine

A Python project that reads first-order logic (FOL) formulas, converts them into **Conjunctive Normal Form (CNF)**, and applies **resolution refutation** to automatically test logical entailment.

---

## 🚀 Overview

This system automates the reasoning process in first-order logic:

1. **Reads logical formulas** from a text file (with quantifiers, connectives, and predicates).  
2. **Converts** them step-by-step into **CNF (Conjunctive Normal Form)**:
   - Eliminates biconditionals and implications  
   - Pushes negations inward  
   - Standardizes variables  
   - Applies Skolemization  
   - Removes universal quantifiers  
   - Distributes disjunctions over conjunctions  
3. **Performs resolution-based inference** by contradiction to determine whether a given query logically follows from the premises.

---

## 🧠 Example

### Input (`data/amistad.txt`)
```text
∀x∀y (Amigo(x,y) ↔ Amigo(y,x))
Amigo(Ana,Carlos)
Amigo(Carlos,Ana)
````

### Output (`output/fnc.txt`)

```text
FORMA NORMAL CONJUNTIVA
==================================================

¬Amigo(x,y) ∨ Amigo(y,x)
¬Amigo(y,x) ∨ Amigo(x,y)
Amigo(Ana,Carlos)
```

### Output (`output/inference.txt`)

```text
INFERENCIA POR RESOLUCIÓN
==================================================

Consulta: Amigo(Carlos,Ana)
Negada: ¬Amigo(Carlos,Ana)

Proceso de inferencia (pasos útiles):
--------------------------------------------------
Paso 1: Resuelvo (¬Amigo(x,y) ∨ Amigo(y,x)) con (Amigo(Ana,Carlos)) ⇒ Amigo(Carlos,Ana)
Paso 2: Resuelvo (Amigo(Carlos,Ana)) con (¬Amigo(Carlos,Ana)) ⇒ □ (contradicción)

Resultado final: VERDADERO (contradicción encontrada)
```

---

## 📂 Project Structure

```
├── data/
│   ├── amistad.txt         # Example input formulas
│   └── curiosidad.txt      # Another test file
├── output/
│   ├── fnc.txt             # CNF conversion result
│   ├── read.txt            # Parsing and structure output
│   └── inference.txt       # Resolution steps and results
├── fnc.py                  # CNF transformation logic
├── inference.py            # Resolution and unification engine
├── read.py                 # Formula and term parser
├── main.py                 # Main pipeline and file handling
└── README.md
```

---

## ⚙️ How to Run

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/first-order-resolution-engine.git
   cd first-order-resolution-engine
   ```

2. Run with a dataset:

   ```bash
   python3 main.py data/amistad.txt
   ```

3. Results will appear in the `output/` folder.

---

## ✨ Features

* Supports **∀** (forall) and **∃** (exists) quantifiers.
* Handles logical connectives: **¬, ∧, ∨, →, ↔**.
* Full CNF transformation pipeline.
* Implements **unification** and **resolution refutation**.
* Generates detailed text reports for each phase.
* 100% written in **pure Python**, no external dependencies.

---

## 🧩 Example Logic Supported

```text
∀x (Planeta(x) → Esferico(x))
Planeta(Tierra)
Esferico(Tierra)
```

The system proves the conclusion **Esferico(Tierra)** from the premises.

---

## 🧑‍💻 Authors & Credits

Developed by **Daniel Castro**
As part of an academic AI reasoning project (FOL and Resolution Logic).

---

## 🪐 License

MIT License © 2025 Daniel Castro

```
