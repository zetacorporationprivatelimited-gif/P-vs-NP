"""
P vs NP Interactive Explorer
==============================
A Streamlit app that teaches Cook-Levin tableau reductions,
NP-completeness proofs, and proof barriers — with Claude AI
explaining each step in plain language.

Run locally:
    streamlit run app.py
"""

import subprocess
import sys

# Ensure anthropic is installed (handles Streamlit Cloud edge cases)
try:
    import anthropic
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic==0.40.0"])
    import anthropic

import streamlit as st
import time
import json
import base64
import hashlib

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="P vs NP Explorer",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');

/* Global */
html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

/* Hide default Streamlit chrome */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Background */
.stApp { background: #08090d; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0e1017;
    border-right: 1px solid #252c3e;
}

/* Cards */
.card {
    background: #131720;
    border: 1px solid #252c3e;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}
.card-accent-purple { border-left: 4px solid #7c6af7; }
.card-accent-teal   { border-left: 4px solid #2dd4bf; }
.card-accent-amber  { border-left: 4px solid #f59e0b; }
.card-accent-red    { border-left: 4px solid #ef4444; }
.card-accent-green  { border-left: 4px solid #22c55e; }

/* Labels */
.micro-label {
    font-size: 9px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #4a5168;
    margin-bottom: 8px;
}
/* Step symbol badge */
.step-badge {
    display: inline-block;
    width: 32px; height: 32px;
    border-radius: 8px;
    background: #1f2535;
    border: 1px solid #2a2f3d;
    text-align: center;
    line-height: 32px;
    font-size: 14px;
    margin-right: 8px;
    vertical-align: middle;
}
/* Tableau cell */
.tcell {
    display: inline-block;
    width: 26px; height: 26px;
    border-radius: 3px;
    border: 1px solid #252c3e;
    background: #131720;
    text-align: center;
    line-height: 26px;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: #4a5168;
    margin: 1px;
}
.tcell-active  { background: #191e2b; color: #8891a8; border-color: #323c57; }
.tcell-current { background: #1a1633; color: #7c6af7; border-color: #7c6af7; box-shadow: 0 0 6px #7c6af733; }
.tcell-done    { background: #111318; color: #5a5280; }
/* Barrier card */
.barrier {
    background: #131720;
    border-radius: 10px;
    padding: 16px;
    border: 1px solid #252c3e;
    margin-bottom: 10px;
    cursor: pointer;
}
/* Certificate block */
.cert-block {
    background: #0e1017;
    border-radius: 8px;
    padding: 14px;
    border: 1px solid #252c3e;
    margin-bottom: 10px;
}
/* Mono text */
.mono { font-family: 'DM Mono', monospace; font-size: 12px; }
/* Proof chain */
.chain-item {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    margin-bottom: 8px;
    font-size: 13px;
    color: #8891a8;
}
/* Share URL */
.share-box {
    background: #0e1017;
    border: 1px solid #323c57;
    border-radius: 8px;
    padding: 12px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #7c6af7;
    word-break: break-all;
}
/* Fun fact box */
.funfact {
    background: #0e1017;
    border-left: 3px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 12px 14px;
    font-size: 12px;
    color: #94a3b8;
    font-style: italic;
}
/* Streamlit button overrides */
.stButton > button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    letter-spacing: 0.04em !important;
}
/* Progress */
.progress-outer {
    height: 3px;
    background: #1f2535;
    border-radius: 2px;
    margin: 8px 0;
    overflow: hidden;
}
.progress-inner {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
}
</style>
""", unsafe_allow_html=True)

# ─── All problem data ─────────────────────────────────────────────────────────

PROBLEMS = {
    "SAT": {
        "label": "SAT",
        "full_name": "Boolean Satisfiability",
        "year": 1971,
        "by": "Cook / Levin",
        "color": "#7c6af7",
        "accent": "purple",
        "icon": "⊨",
        "desc": "Can a Boolean formula be satisfied by some TRUE/FALSE assignment?",
        "formal": "Given φ = C₁ ∧ C₂ ∧ … ∧ Cₘ, does there exist σ: {x₁,…,xₙ}→{0,1} such that φ(σ)=1?",
        "example": "(x₁ ∨ ¬x₂ ∨ x₃) ∧ (¬x₁ ∨ x₂) ∧ (x₂ ∨ ¬x₃)",
        "certificate": "x₁=T, x₂=T, x₃=F  →  all three clauses satisfied",
        "source": "Cook (1971) STOC; Levin (1973)",
        "sketch": "Every NP language has a poly-time verifier V. Encode V as a Turing machine. Build a Boolean formula φ whose satisfying assignments exactly encode accepting computations of V. This φ is constructible in polynomial time.",
        "fun_fact": "Cook's original paper was 14 pages. It is one of the most cited papers in all of computer science.",
        "open": "Is there an algorithm for 3SAT running in O(1.99ⁿ)? Best known is ~O(1.307ⁿ).",
        "steps": [
            {
                "title": "Encode the Verifier as a Turing Machine",
                "symbol": "M",
                "color": "#7c6af7",
                "short": "Every NP language has a poly-time verifier. Encode it as TM M.",
                "detail": "Fix an NP language L with verifier V running in time p(n). Encode V as a standard Turing machine M = (Q, Γ, b, Σ, δ, q₀, q_acc) with state set Q, tape alphabet Γ, and transition function δ. The machine M accepts (w, c) in exactly p(|w|) steps whenever V accepts — the time bound is what makes everything polynomial.",
                "math": "M = (Q, Γ, b, Σ, δ, q₀, q_acc)   runs in time p(n)",
                "obligation": "M must accept (w,c) in exactly p(|w|) steps whenever V accepts.",
            },
            {
                "title": "Build the Computation Tableau",
                "symbol": "T",
                "color": "#2dd4bf",
                "short": "A p(n)×p(n) table where each row is one step of the computation.",
                "detail": "The tableau T has rows indexed by time t ∈ [0, p(n)] and columns by tape position j ∈ [0, p(n)]. Each cell T[t][j] contains a tape symbol or (head position, state) if the head is at column j at time t. This gives p(n)² cells — polynomial in n. A valid accepting tableau exists if and only if there exists a certificate c that causes M to accept.",
                "math": "T: [0..p(n)] × [0..p(n)] → Q ∪ Γ      |cells| = p(n)²",
                "obligation": "A valid, accepting tableau ↔ ∃ certificate c that causes M to accept.",
            },
            {
                "title": "Introduce Boolean Variables",
                "symbol": "x",
                "color": "#f59e0b",
                "short": "One variable per (time, position, symbol) triple.",
                "detail": "For each t ∈ [0,p(n)], j ∈ [0,p(n)], s ∈ Q∪Γ, introduce variable x_{t,j,s} meaning 'at time t, position j contains symbol s'. This creates O(p(n)² · |Q∪Γ|) variables. Since |Q| and |Γ| are constants (fixed by M), this is polynomial in n. A satisfying assignment to these variables encodes exactly one tableau.",
                "math": "x_{t,j,s} ∈ {0,1}   ∀ t,j ∈ [p(n)],  s ∈ Q∪Γ",
                "obligation": "Satisfying assignment ↔ valid tableau ↔ accepting computation.",
            },
            {
                "title": "Add Cell-Validity Clauses",
                "symbol": "C",
                "color": "#22c55e",
                "short": "Each cell must contain exactly one symbol.",
                "detail": "For each (t,j): (a) At-least-one clause: ⋁_{s} x_{t,j,s} — something is in the cell. (b) At-most-one: for all s≠s', clause (¬x_{t,j,s} ∨ ¬x_{t,j,s'}) — at most one symbol per cell. This is O(|Γ|²) clauses per cell, O(p(n)²·|Γ|²) total. Every constant factor is absorbed — still polynomial.",
                "math": "∀t,j: (⋁ₛ x_{t,j,s}) ∧ ⋀_{s≠s'} (¬x_{t,j,s} ∨ ¬x_{t,j,s'})",
                "obligation": "Exactly one symbol per cell in any satisfying assignment.",
            },
            {
                "title": "Encode Transition Constraints",
                "symbol": "δ",
                "color": "#ef4444",
                "short": "Adjacent rows must follow δ. Cells away from the head are unchanged.",
                "detail": "For each time t and transition (q,a) →δ (q',b,D): add clauses forcing x_{t,j,q} ∧ x_{t,j,a} → x_{t+1,j',q'} ∧ x_{t+1,j,b} where j'=j±1. For cells not under the head: x_{t,j,s} → x_{t+1,j,s}. Each implication becomes 2-3 clauses. Total: O(p(n)² · |δ|) clauses — polynomial.",
                "math": "(¬x_{t,j,q} ∨ ¬x_{t,j,a} ∨ x_{t+1,j',q'}) for each δ(q,a)=(q',b,D)",
                "obligation": "Every row must follow from the previous by exactly one application of δ.",
            },
            {
                "title": "Add Initial and Accepting Clauses",
                "symbol": "✓",
                "color": "#a855f7",
                "short": "Row 0 encodes input w. Final row must contain the accepting state.",
                "detail": "Initial configuration: unit clauses x_{0,j,w_j}=1 for each input symbol, q₀ at position 0. These force the first row to match the actual input. Acceptance: add clause ⋁_{t,j} x_{t,j,q_acc} — the accepting state must appear somewhere. This single disjunction is satisfiable iff the machine accepts.",
                "math": "Unit clauses for x_{0,j,wⱼ}=1,   acceptance: ⋁ⱼ x_{p(n),j,q_acc}",
                "obligation": "Satisfying assignment ↔ M accepts w with certificate encoded in the variables.",
            },
        ],
        "graph_nodes": [
            {"id":"x1","label":"x₁","x":90,"y":55,"color":"#7c6af7"},
            {"id":"x2","label":"x₂","x":200,"y":55,"color":"#7c6af7"},
            {"id":"x3","label":"x₃","x":145,"y":140,"color":"#7c6af7"},
            {"id":"c1","label":"C₁","x":55,"y":185,"color":"#2dd4bf"},
            {"id":"c2","label":"C₂","x":160,"y":205,"color":"#2dd4bf"},
            {"id":"c3","label":"C₃","x":250,"y":155,"color":"#2dd4bf"},
        ],
        "graph_edges": [
            ("x1","c1"),("x2","c1"),("x3","c1"),
            ("x1","c2"),("x2","c3"),("x3","c2"),
            ("x2","c2"),("x3","c3"),
        ],
        "cert_edges": {("x1","c1"),("x2","c1"),("x2","c2"),("x2","c3")},
        "cert_nodes": {"x1","x2","c1","c2","c3"},
    },
    "CLIQUE": {
        "label": "Clique",
        "full_name": "k-Clique",
        "year": 1972,
        "by": "Richard Karp",
        "color": "#2dd4bf",
        "accent": "teal",
        "icon": "△",
        "desc": "Does a graph contain k vertices that are all mutually adjacent?",
        "formal": "Given G=(V,E) and k ∈ ℕ, does there exist S ⊆ V, |S|=k, such that ∀u,v ∈ S: {u,v} ∈ E?",
        "example": "Graph G with 6 nodes (v₁–v₆), 9 edges.  k = 3",
        "certificate": "Clique: {v₁, v₂, v₆} — all three pairs are edges",
        "source": "Karp (1972) 'Reducibility Among Combinatorial Problems'",
        "sketch": "Reduce 3SAT → Clique. Given k clauses, create 3k nodes (one per literal). Connect nodes from different clauses iff literals are consistent. A k-clique picks one true literal per clause — exactly a satisfying assignment.",
        "fun_fact": "Karp's 1972 paper listed 21 NP-complete problems in one go. It is still one of the most cited papers in CS theory.",
        "open": "Best algorithm for k-Clique: O(n^{ωk/3}) where ω<2.373. Whether O(n^{(1-ε)k}) is possible for any ε>0 is the 'Clique Conjecture' — open.",
        "steps": [
            {
                "title": "Start from a 3SAT Instance",
                "symbol": "φ",
                "color": "#7c6af7",
                "short": "Input: 3CNF formula with k clauses, each exactly 3 literals.",
                "detail": "Given φ = C₁ ∧ … ∧ Cₖ where each Cᵢ = (lᵢ₁ ∨ lᵢ₂ ∨ lᵢ₃). We construct graph G in polynomial time such that G has a k-clique if and only if φ is satisfiable. The key invariant: a k-clique will correspond exactly to choosing one TRUE literal per clause, consistently.",
                "math": "φ = ⋀ᵢ Cᵢ,   |Cᵢ| = 3,   k = number of clauses",
                "obligation": "Reduction must run in O(k²) time — polynomial in formula size.",
            },
            {
                "title": "Create One Node per Literal",
                "symbol": "N",
                "color": "#2dd4bf",
                "short": "For each literal lᵢⱼ in clause Cᵢ, create node (i,j). Total: 3k nodes.",
                "detail": "V = { (i,j) : i ∈ [k], j ∈ {1,2,3} }. Each node (i,j) represents literal lᵢⱼ appearing in clause Cᵢ. We tag each node with its clause index i and its literal value. This gives exactly 3k nodes — one for each literal slot in the formula.",
                "math": "V = {(i,j) : i∈[k], j∈[3]},   |V| = 3k",
                "obligation": "Every literal in the formula has exactly one corresponding node.",
            },
            {
                "title": "Add Consistency Edges",
                "symbol": "E",
                "color": "#f59e0b",
                "short": "Connect (i,j)–(i',j') iff i≠i' and the literals don't contradict each other.",
                "detail": "Add edge {(i,j),(i',j')} if and only if: (a) i ≠ i' (different clauses), AND (b) lᵢⱼ ≠ ¬lᵢ'ⱼ' (the two literals are not negations of each other — they can be simultaneously true). No edges between nodes of the same clause. This is the key gadget: any clique must be consistent.",
                "math": "{(i,j),(i',j')} ∈ E  ⟺  i≠i'  ∧  lᵢⱼ ≢ ¬lᵢ'ⱼ'",
                "obligation": "A k-clique selects one literal per clause with no contradictions.",
            },
            {
                "title": "Prove the Equivalence",
                "symbol": "↔",
                "color": "#22c55e",
                "short": "k-clique ↔ satisfying assignment. Both directions.",
                "detail": "(→) If S is a k-clique, it has one node per clause (no two from the same clause, since intra-clause edges are absent). All pairs are consistent, so set each selected literal to TRUE. This satisfies all k clauses. (←) If σ satisfies φ, pick one TRUE literal per clause. These k nodes form a k-clique: different clauses by construction, consistent because σ makes them all true simultaneously.",
                "math": "S k-clique  ⟺  {lᵢ,jᵢ : (i,jᵢ) ∈ S} is a satisfying partial assignment",
                "obligation": "Biconditional holds exactly — no false positives, no false negatives.",
            },
            {
                "title": "Extract the Certificate",
                "symbol": "🔑",
                "color": "#ef4444",
                "short": "The clique S encodes the satisfying variable assignment directly.",
                "detail": "Given a k-clique S = {(i,jᵢ)}: for each variable x, set σ(x)=T if some node in S contains literal x, set σ(x)=F if some node has ¬x, otherwise either value. Verify σ satisfies φ in O(k·|φ|) time — polynomial. The clique itself IS the poly-time verifiable certificate that puts this problem in NP.",
                "math": "Certificate = S (k nodes).  Verifier: check |S|=k, all edges present, all clauses covered.",
                "obligation": "Verification in polynomial time — confirming Clique ∈ NP.",
            },
        ],
        "graph_nodes": [
            {"id":"v1","label":"v₁","x":140,"y":35,"color":"#2dd4bf"},
            {"id":"v2","label":"v₂","x":240,"y":90,"color":"#2dd4bf"},
            {"id":"v3","label":"v₃","x":215,"y":195,"color":"#2dd4bf"},
            {"id":"v4","label":"v₄","x":100,"y":210,"color":"#2dd4bf"},
            {"id":"v5","label":"v₅","x":35,"y":125,"color":"#2dd4bf"},
            {"id":"v6","label":"v₆","x":155,"y":130,"color":"#22c55e"},
        ],
        "graph_edges": [
            ("v1","v2"),("v2","v3"),("v3","v4"),("v4","v5"),("v5","v1"),
            ("v1","v6"),("v2","v6"),("v6","v3"),("v4","v6"),
        ],
        "cert_edges": {("v1","v2"),("v1","v6"),("v2","v6")},
        "cert_nodes": {"v1","v2","v6"},
    },
    "3COL": {
        "label": "3-Color",
        "full_name": "3-Colorability",
        "year": 1972,
        "by": "Karp / Stockmeyer",
        "color": "#f59e0b",
        "accent": "amber",
        "icon": "⬡",
        "desc": "Can graph vertices be colored with 3 colors so no two adjacent vertices share a color?",
        "formal": "Given G=(V,E), does there exist c: V→{1,2,3} such that ∀{u,v}∈E: c(u)≠c(v)?",
        "example": "A 5-cycle (pentagon). Is it 3-chromatic?",
        "certificate": "c(v₁)=R, c(v₂)=G, c(v₃)=B, c(v₄)=R, c(v₅)=G",
        "source": "Karp (1972); gadget construction by Stockmeyer (1973)",
        "sketch": "Reduce 3SAT → 3COL. Build a 'palette triangle' T-F-B. Variable gadgets force each variable to color TRUE or FALSE. Clause OR-gadgets are 3-colorable iff at least one literal is TRUE-colored.",
        "fun_fact": "4-Colorability of PLANAR graphs is in P (Four Color Theorem, 1976). But 3-Colorability of general graphs is NP-complete. Planarity is what makes the difference.",
        "open": "Does every planar 4-connected graph have a Hamiltonian cycle? Tutte proved yes in 1956. Whether 3-colorability of planar graphs with max degree 4 is NP-complete — yes, Dailey 1980.",
        "steps": [
            {
                "title": "Build the Palette Triangle",
                "symbol": "▲",
                "color": "#7c6af7",
                "short": "Three special nodes T, F, B — all connected to each other.",
                "detail": "Add nodes TRUE (T), FALSE (F), BASE (B) and edges {T,F}, {F,B}, {T,B}. In any proper 3-coloring, these three nodes use all three colors. We fix: T gets color 'TRUE', F gets color 'FALSE', B gets 'BASE'. Every other node's color is now constrained relative to this palette.",
                "math": "K₃ on {T,F,B};  fix c(T)=TRUE, c(F)=FALSE, c(B)=BASE",
                "obligation": "Every 3-coloring of G restricts to the same palette on {T,F,B}.",
            },
            {
                "title": "Variable Gadgets",
                "symbol": "⬡",
                "color": "#2dd4bf",
                "short": "For each xᵢ: nodes xᵢ and ¬xᵢ, both connected to each other and to B.",
                "detail": "For each variable xᵢ: add nodes xᵢ and ¬xᵢ. Add edges {xᵢ,¬xᵢ}, {xᵢ,B}, {¬xᵢ,B}. Since xᵢ and ¬xᵢ are adjacent they get different colors. Since both are adjacent to B, neither can be BASE-colored. So one gets TRUE and the other gets FALSE. This is exactly the truth assignment for xᵢ.",
                "math": "xᵢ—¬xᵢ,  xᵢ—B,  ¬xᵢ—B   ⟹  {c(xᵢ),c(¬xᵢ)} = {TRUE,FALSE}",
                "obligation": "Variable gadget enforces exactly two valid states: xᵢ=T and xᵢ=F.",
            },
            {
                "title": "OR-Gadget for Each Clause",
                "symbol": "⊕",
                "color": "#f59e0b",
                "short": "6-node gadget that is 3-colorable iff ≥1 input literal is TRUE.",
                "detail": "For clause C=(l₁∨l₂∨l₃): build a binary OR tree with 6 intermediate nodes a,b,c,d,e,f. Connect them so: if all three inputs are FALSE-colored, the output node is forced to be FALSE-colored — but the output is also adjacent to F, giving a contradiction. If any input is TRUE, a valid coloring exists for the gadget.",
                "math": "OR(l₁,l₂,l₃)-gadget: 3-colorable  iff  c(l₁)=T ∨ c(l₂)=T ∨ c(l₃)=T",
                "obligation": "Gadget is 3-colorable ↔ at least one literal in the clause is TRUE-colored.",
            },
            {
                "title": "Connect Gadgets to the Palette",
                "symbol": "↔",
                "color": "#22c55e",
                "short": "Clause gadget output connects to F — forcing at least one literal TRUE.",
                "detail": "The output node of each OR-gadget is adjacent to FALSE (F). This means the output cannot be colored FALSE. But if all literals are FALSE-colored, the gadget logic forces the output to be FALSE — contradiction. Therefore the full graph is 3-colorable if and only if every clause gadget avoids this contradiction, i.e., every clause has at least one TRUE literal.",
                "math": "output(Cᵢ) adjacent to F  ⟹  output ≠ FALSE  ⟹  ≥1 literal TRUE in Cᵢ",
                "obligation": "Global 3-colorability ↔ all clause gadgets satisfiable ↔ φ satisfiable.",
            },
            {
                "title": "Extract the Certificate",
                "symbol": "🔑",
                "color": "#ef4444",
                "short": "Read off the coloring: TRUE-colored variable nodes give the assignment.",
                "detail": "Given a valid 3-coloring c: for each variable xᵢ, set σ(xᵢ) = (c(xᵢ) == TRUE). This is well-defined since c(xᵢ) ∈ {TRUE, FALSE} by the variable gadget analysis. By the OR-gadget property, every clause has at least one TRUE-colored literal, so σ satisfies φ. Verification time: O(|V|+|E|) — polynomial.",
                "math": "σ(xᵢ) := [c(xᵢ)=TRUE]   →   σ satisfies φ",
                "obligation": "Certificate (the coloring) is verifiable in polynomial time.",
            },
        ],
        "graph_nodes": [
            {"id":"T","label":"T","x":140,"y":30,"color":"#ef4444"},
            {"id":"F","label":"F","x":50,"y":175,"color":"#3b82f6"},
            {"id":"B","label":"B","x":230,"y":175,"color":"#22c55e"},
            {"id":"x1","label":"x₁","x":85,"y":95,"color":"#ef4444"},
            {"id":"nx1","label":"¬x₁","x":200,"y":95,"color":"#3b82f6"},
            {"id":"x2","label":"x₂","x":140,"y":195,"color":"#22c55e"},
        ],
        "graph_edges": [
            ("T","F"),("F","B"),("T","B"),
            ("x1","nx1"),("x1","B"),("nx1","B"),
            ("x2","T"),("x2","F"),
        ],
        "cert_edges": {("T","F"),("F","B"),("T","B")},
        "cert_nodes": {"T","F","B"},
    },
    "HAMCYCLE": {
        "label": "Ham. Cycle",
        "full_name": "Hamiltonian Cycle",
        "year": 1972,
        "by": "Richard Karp",
        "color": "#ef4444",
        "accent": "red",
        "icon": "∮",
        "desc": "Does a graph have a cycle visiting every vertex exactly once?",
        "formal": "Given G=(V,E), does there exist a permutation (v₁,…,vₙ) of V with {vᵢ,vᵢ₊₁}∈E for all i and {vₙ,v₁}∈E?",
        "example": "A graph on 6 vertices. Does a cycle through all 6 exist?",
        "certificate": "Cycle: S → A → B → C → D → E → S",
        "source": "Karp (1972); detailed construction by Garey-Johnson (1979)",
        "sketch": "Reduce 3SAT → Ham. Cycle. Variable gadgets are chains traversed L→R (TRUE) or R→L (FALSE). Clause nodes can only be visited via a detour from a TRUE-direction traversal.",
        "fun_fact": "William Rowan Hamilton sold a puzzle in 1857 about visiting all 20 vertices of a dodecahedron. It was a commercial failure. The complexity wasn't understood for 115 more years.",
        "open": "Is Hamiltonian Cycle NP-complete on planar 4-regular graphs? Yes. On planar cubic bipartite graphs? Also yes (Akiyama et al. 1980).",
        "steps": [
            {
                "title": "Variable Path Gadgets",
                "symbol": "→",
                "color": "#7c6af7",
                "short": "For each xᵢ, build a horizontal chain of 2(m+1) nodes.",
                "detail": "For variable xᵢ appearing in m clauses, create a chain: [aᵢ,₀ — bᵢ,₁ — aᵢ,₁ — bᵢ,₂ — … — bᵢ,ₘ — aᵢ,ₘ]. The Hamiltonian cycle must traverse this chain either L→R (encoding xᵢ=TRUE) or R→L (encoding xᵢ=FALSE). No other traversal option exists due to the chain structure — the gadget is a binary encoding device.",
                "math": "xᵢ-gadget: chain of 2(m+1) nodes;  direction = truth value of xᵢ",
                "obligation": "Every Hamiltonian cycle traverses each variable gadget in exactly one direction.",
            },
            {
                "title": "Chain All Variable Gadgets",
                "symbol": "⛓",
                "color": "#2dd4bf",
                "short": "Link gadgets in series, creating a backbone the cycle must follow.",
                "detail": "Add edges connecting the right end of xᵢ's gadget to the left end of xᵢ₊₁'s gadget, and the right end of the last gadget back to the left end of the first. This creates a large cycle backbone. The Hamiltonian cycle must follow this backbone — which forces it to choose a direction (truth value) for each variable in sequence.",
                "math": "aᵢ,ₘ → aᵢ₊₁,₀  for each i;   aₙ,ₘ → a₁,₀  (close the backbone)",
                "obligation": "Backbone forces exactly one truth-value choice per variable.",
            },
            {
                "title": "Add Clause Check Nodes",
                "symbol": "◆",
                "color": "#f59e0b",
                "short": "One extra node cⱼ per clause — must be visited exactly once.",
                "detail": "For each clause Cⱼ, add a single node cⱼ not on the backbone. This node must be visited by the Hamiltonian cycle exactly once. The only way to visit cⱼ is via a 'detour' from within a variable gadget — specifically from a literal-node whose literal is TRUE in clause Cⱼ.",
                "math": "Add m extra nodes {c₁,…,cₘ}, each must appear in the Hamiltonian cycle",
                "obligation": "Every clause node must be visited — requiring at least one TRUE literal per clause.",
            },
            {
                "title": "Add Literal-to-Clause Detour Edges",
                "symbol": "↗",
                "color": "#22c55e",
                "short": "If xᵢ appears in Cⱼ, add edges enabling a detour through cⱼ when xᵢ=TRUE.",
                "detail": "For literal xᵢ in clause Cⱼ: add edges aᵢ,ⱼ—cⱼ and cⱼ—bᵢ,ⱼ. If the cycle traverses xᵢ's gadget L→R (xᵢ=T), it can take the detour: …→aᵢ,ⱼ→cⱼ→bᵢ,ⱼ→… visiting cⱼ. If traversed R→L (xᵢ=F), no such detour is available for this literal.",
                "math": "aᵢ,ⱼ — cⱼ — bᵢ,ⱼ  for each literal xᵢ in clause Cⱼ",
                "obligation": "Detour edges enable visiting cⱼ only via TRUE-direction traversal.",
            },
            {
                "title": "Extract the Certificate",
                "symbol": "🔑",
                "color": "#ef4444",
                "short": "Traversal direction through each gadget gives the satisfying assignment.",
                "detail": "Given a Hamiltonian cycle H: for each xᵢ, set σ(xᵢ)=T if H traverses xᵢ's gadget L→R, else F. Since every clause node cⱼ must appear in H, at least one literal in each clause was traversed in the TRUE direction. So σ satisfies all clauses. Verification: O(|V|+|E|) — polynomial.",
                "math": "σ(xᵢ) := [H traverses xᵢ-gadget L→R]   →   σ satisfies φ",
                "obligation": "The Hamiltonian cycle itself is the certificate — verifiable in polynomial time.",
            },
        ],
        "graph_nodes": [
            {"id":"s","label":"S","x":140,"y":30,"color":"#ef4444"},
            {"id":"a","label":"A","x":235,"y":90,"color":"#ef4444"},
            {"id":"b","label":"B","x":240,"y":185,"color":"#ef4444"},
            {"id":"c","label":"C","x":145,"y":220,"color":"#ef4444"},
            {"id":"d","label":"D","x":50,"y":185,"color":"#ef4444"},
            {"id":"e","label":"E","x":40,"y":90,"color":"#ef4444"},
        ],
        "graph_edges": [
            ("s","a"),("a","b"),("b","c"),("c","d"),("d","e"),("e","s"),
            ("s","c"),("a","d"),("b","e"),
        ],
        "cert_edges": {("s","a"),("a","b"),("b","c"),("c","d"),("d","e"),("e","s")},
        "cert_nodes": {"s","a","b","c","d","e"},
    },
}

BARRIERS = {
    "relativization": {
        "label": "Relativization",
        "icon": "⊘",
        "color": "#7c6af7",
        "year": "Baker-Gill-Solovay 1975",
        "summary": "There exist oracles A, B such that Pᴬ=NPᴬ and Pᴮ≠NPᴮ. Any proof technique that works the same in the presence of any oracle — a 'relativizing' technique — cannot resolve P vs NP.",
        "detail": "An oracle Turing machine queries a set A in O(1). A proof 'relativizes' if it works for all oracles simultaneously. BGS showed: relative to oracle A, P=NP; relative to oracle B, P≠NP. Since both can't be true at once, no relativizing proof can settle P vs NP. All diagonalization arguments relativize — so diagonalization alone cannot work.",
        "blocks": "Diagonalization, time-hierarchy-style arguments, Turing machine simulation tricks.",
        "does_not_block": "Circuit complexity arguments (they are non-relativizing). Geometric/algebraic approaches.",
        "cite": "Baker, Gill, Solovay. SIAM J. Comput. 4(4):431–442, 1975.",
    },
    "naturalProofs": {
        "label": "Natural Proofs",
        "icon": "⊗",
        "color": "#f59e0b",
        "year": "Razborov-Rudich 1994",
        "summary": "A 'natural' proof of circuit lower bounds — one that is constructive and applies to most random functions — could be used to break pseudorandom functions. Since PRFs likely exist, natural proofs likely can't prove P≠NP.",
        "detail": "A property P of Boolean functions is 'natural' if it is: (1) Constructive — checkable in 2^{O(n)} time; (2) Large — most random functions satisfy P. Razborov-Rudich showed: if such a P proves no polynomial circuit computes some function, then pseudorandom generators of that size don't exist — contradicting standard cryptographic assumptions. Most combinatorial lower-bound proofs are natural.",
        "blocks": "Combinatorial lower bounds, switching lemma arguments, approximation methods, most circuit complexity techniques known before 1994.",
        "does_not_block": "Non-constructive proofs. Proofs exploiting specific NP structure, not random functions. Non-'large' properties.",
        "cite": "Razborov, Rudich. J. Comput. Syst. Sci. 55(1):24–35, 1997.",
    },
    "algebrization": {
        "label": "Algebrization",
        "icon": "⊛",
        "color": "#2dd4bf",
        "year": "Aaronson-Wigderson 2009",
        "summary": "A strengthening of relativization using algebraic extensions of oracles. Most algebraic proof techniques — including those that proved IP=PSPACE — are algebrizing and cannot separate P from NP.",
        "detail": "An 'algebraic oracle' Ã is a low-degree polynomial extension of A over a large field. A proof algebrizes if it works with any algebraic oracle. Aaronson-Wigderson showed: NP ⊄ P/poly relative to some algebraic oracle, but P=NP relative to another. The proofs of IP=PSPACE and MIP*=RE algebrize — meaning their core techniques cannot extend to resolving P vs NP. This strictly subsumes relativization.",
        "blocks": "Arithmetization, sum-check protocol generalizations, algebraic proof systems, LFKN/Shamir-style arguments applied to P vs NP.",
        "does_not_block": "Genuinely non-algebrizing techniques (if any can be found). Proofs based on new mathematical frameworks not yet discovered.",
        "cite": "Aaronson, Wigderson. TOCT 1(1):2, 2009.",
    },
}

PROBLEM_ORDER = ["SAT", "CLIQUE", "3COL", "HAMCYCLE"]

# ─── Session state initialization ────────────────────────────────────────────

def init_state():
    defaults = {
        "active_problem": "SAT",
        "step": 0,
        "active_tab": "reduction",
        "claude_text": "",
        "barrier_text": "",
        "cert_data": None,
        "share_url": "",
        "last_explained": (-1, ""),   # (step, problem) — avoid re-fetching
        "last_barrier": ("", ""),     # (barrier, attempt)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Claude helper ────────────────────────────────────────────────────────────

def get_claude_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("⚠️ No ANTHROPIC_API_KEY found. Add it in Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)

def stream_explanation(system: str, user_msg: str, placeholder) -> str:
    client = get_claude_client()
    full_text = ""
    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            placeholder.markdown(
                f'<div class="card card-accent-purple" style="margin-top:0">'
                f'<div class="micro-label">✦ Claude Explanation</div>'
                f'<div style="font-size:13px;line-height:1.9;color:#dde3f0">{full_text}▌</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    placeholder.markdown(
        f'<div class="card card-accent-purple" style="margin-top:0">'
        f'<div class="micro-label">✦ Claude Explanation</div>'
        f'<div style="font-size:13px;line-height:1.9;color:#dde3f0">{full_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    return full_text

# ─── SVG graph renderer ───────────────────────────────────────────────────────

def render_graph_svg(problem_key: str) -> str:
    p = PROBLEMS[problem_key]
    nodes = {n["id"]: n for n in p["graph_nodes"]}
    cert_nodes = p["cert_nodes"]
    cert_edges = p["cert_edges"]

    lines = ['<svg viewBox="0 0 290 250" width="100%" xmlns="http://www.w3.org/2000/svg">']
    lines.append('<rect width="290" height="250" fill="#131720" rx="8"/>')

    # Edges
    for src, tgt in p["graph_edges"]:
        n1, n2 = nodes[src], nodes[tgt]
        is_cert = (src, tgt) in cert_edges or (tgt, src) in cert_edges
        color = p["color"] if is_cert else "#2a2f3d"
        width = "2.5" if is_cert else "1"
        opacity = "1" if is_cert else "0.5"
        lines.append(
            f'<line x1="{n1["x"]}" y1="{n1["y"]}" x2="{n2["x"]}" y2="{n2["y"]}" '
            f'stroke="{color}" stroke-width="{width}" opacity="{opacity}"/>'
        )

    # Nodes
    for nid, n in nodes.items():
        is_cert = nid in cert_nodes
        col = n.get("color") or p["color"]
        stroke_w = "2" if is_cert else "1.2"
        lines.append(
            f'<circle cx="{n["x"]}" cy="{n["y"]}" r="16" '
            f'fill="{col}22" stroke="{col}" stroke-width="{stroke_w}"/>'
        )
        lines.append(
            f'<text x="{n["x"]}" y="{n["y"]}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="11" font-weight="600" '
            f'fill="{col}" font-family="DM Mono, monospace">{n["label"]}</text>'
        )

    lines.append('</svg>')
    return "\n".join(lines)

# ─── Tableau renderer ─────────────────────────────────────────────────────────

SYMS = ['q', '0', '1', '·', 'b', '⊤', '⊥', 'δ', 'σ', 'a']

def render_tableau(step: int, color: str) -> str:
    rows, cols = 7, 10
    cells_html = []
    for r in range(rows):
        for c in range(cols):
            seed = (r * 7 + c * 13 + max(step, 1) * 3) % len(SYMS)
            if step == 0:
                sym, cls = '?', 'tcell'
            elif r == step - 1:
                sym, cls = SYMS[seed], 'tcell tcell-current'
            elif r < step - 1:
                sym, cls = SYMS[seed], 'tcell tcell-done'
            else:
                sym, cls = '?', 'tcell'
            cells_html.append(f'<span class="{cls}">{sym}</span>')
    return "".join(cells_html)

# ─── Certificate generator ────────────────────────────────────────────────────

def generate_certificate(problem_key: str) -> dict:
    p = PROBLEMS[problem_key]
    client = get_claude_client()

    system = (
        "You are generating a formal NP complexity certificate in JSON. "
        "Return ONLY valid JSON, no markdown, no commentary.\n"
        "Required keys: problem, complexity_class, instance_description, "
        "certificate_value, verification_steps (list of 4 strings), "
        "npc_proof_chain (list of 3 strings), historical_note, open_problem, "
        "verification_time."
    )
    user_msg = (
        f"Generate a certificate for: {p['full_name']}\n"
        f"Description: {p['desc']}\n"
        f"Formal: {p['formal']}\n"
        f"Example instance: {p['example']}\n"
        f"Example certificate: {p['certificate']}\n"
        f"NPC source: {p['source']}\n"
        f"NPC sketch: {p['sketch']}\n"
        f"Fun fact: {p['fun_fact']}"
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# ─── Share URL encoder ────────────────────────────────────────────────────────

def make_share_url(problem_key: str, cert: dict) -> str:
    payload = json.dumps({"problem": problem_key, "cert": cert}, separators=(",", ":"))
    token = base64.urlsafe_b64encode(payload.encode()).decode()
    checksum = hashlib.sha256(payload.encode()).hexdigest()[:8]
    return f"https://your-app.streamlit.app/?cert={token}.{checksum}"

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:12px 0 20px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#4f3bde,#7c6af7);
          display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff;
          font-family:'DM Mono',monospace">P?</div>
        <div>
          <div style="font-size:14px;font-weight:800;color:#dde3f0">P vs NP Explorer</div>
          <div style="font-size:9px;color:#4a5168;letter-spacing:.12em;text-transform:uppercase">Cook-Levin Theorem</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="micro-label" style="padding:0 4px">NP-Complete Problems</div>', unsafe_allow_html=True)

    for key in PROBLEM_ORDER:
        p = PROBLEMS[key]
        is_active = st.session_state.active_problem == key
        border = f"border-left:3px solid {p['color']}" if is_active else "border-left:3px solid transparent"
        bg = "background:#191e2b" if is_active else ""
        if st.button(
            f"{p['icon']}  {p['full_name']}",
            key=f"prob_{key}",
            use_container_width=True,
        ):
            st.session_state.active_problem = key
            st.session_state.step = 0
            st.session_state.claude_text = ""
            st.session_state.last_explained = (-1, "")
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="micro-label" style="padding:0 4px">Navigate</div>', unsafe_allow_html=True)
    if st.button("⬡ Tableau Reduction", use_container_width=True):
        st.session_state.active_tab = "reduction"
        st.rerun()
    if st.button("⊘ Proof Barriers", use_container_width=True):
        st.session_state.active_tab = "barriers"
        st.rerun()
    if st.button("⬢ Certificate", use_container_width=True):
        st.session_state.active_tab = "certificate"
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#4a5168;line-height:1.7">'
        'Cook/Levin 1971 · Karp 1972<br>'
        'BGS 1975 · Razborov-Rudich 1994<br>'
        'Aaronson-Wigderson 2009'
        '</div>',
        unsafe_allow_html=True,
    )

# ─── Active problem ───────────────────────────────────────────────────────────

key  = st.session_state.active_problem
p    = PROBLEMS[key]
tab  = st.session_state.active_tab
step = st.session_state.step
total_steps = len(p["steps"]) + 1   # steps + conclusion

# ─── Problem banner ───────────────────────────────────────────────────────────

st.markdown(f"""
<div style="display:flex;align-items:flex-start;gap:16px;margin-bottom:24px">
  <div style="width:52px;height:52px;border-radius:12px;background:#1f2535;border:1px solid #252c3e;
    display:flex;align-items:center;justify-content:center;font-size:26px;flex-shrink:0">{p['icon']}</div>
  <div>
    <div style="font-size:24px;font-weight:800;color:{p['color']};letter-spacing:-.01em">{p['full_name']}</div>
    <div style="font-size:10px;color:#4a5168;font-family:'DM Mono',monospace;margin-top:2px;letter-spacing:.06em">
      {p['year']} · {p['by']} · NP-Complete
    </div>
    <div style="font-size:13px;color:#8891a8;margin-top:5px;max-width:560px;line-height:1.65">{p['desc']}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Tab indicator
tabs_html = ""
for t_key, t_label in [("reduction","⬡ Tableau Reduction"),("barriers","⊘ Proof Barriers"),("certificate","⬢ Certificate")]:
    color = p["color"] if tab == t_key else "#4a5168"
    border = f"border-bottom:2px solid {p['color']}" if tab == t_key else "border-bottom:2px solid transparent"
    tabs_html += f'<span style="padding:8px 16px;font-size:13px;font-weight:700;color:{color};{border};margin-right:4px">{t_label}</span>'
st.markdown(f'<div style="display:flex;margin-bottom:20px;border-bottom:1px solid #252c3e">{tabs_html}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB: TABLEAU REDUCTION
# ════════════════════════════════════════════════════════════════════════════

if tab == "reduction":
    left, right = st.columns([3, 2], gap="large")

    with left:
        # ── Tableau ──────────────────────────────────────────────────────────
        step_color = p["color"]
        if 0 < step <= len(p["steps"]):
            step_color = p["steps"][step - 1]["color"]

        st.markdown(
            f'<div class="card">'
            f'<div class="micro-label">Cook-Levin Tableau · {key} · Step {step}/{total_steps}</div>'
            f'<div style="line-height:1.4;margin-bottom:12px">{render_tableau(step, step_color)}</div>',
            unsafe_allow_html=True,
        )

        # Progress bar
        pct = int((step / total_steps) * 100)
        st.markdown(
            f'<div class="progress-outer"><div class="progress-inner" '
            f'style="width:{pct}%;background:{step_color}"></div></div>',
            unsafe_allow_html=True,
        )

        # Step card content
        if step == 0:
            st.markdown(
                f'<div style="border-left:3px solid {p["color"]};background:#191e2b;'
                f'border-radius:0 8px 8px 0;padding:12px 14px;margin-top:12px">'
                f'<div style="font-size:13px;font-weight:700;color:{p["color"]};margin-bottom:6px">'
                f'⬡ Introduction: {p["full_name"]}</div>'
                f'<div style="font-size:12px;color:#8891a8;line-height:1.7">{p["desc"]}</div>'
                f'<div style="font-family:DM Mono,monospace;font-size:11px;color:#4a5168;'
                f'background:#0e1017;border-radius:6px;padding:8px 10px;margin-top:8px;'
                f'border:1px solid #252c3e">{p["formal"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif step <= len(p["steps"]):
            s = p["steps"][step - 1]
            st.markdown(
                f'<div style="border-left:3px solid {s["color"]};background:#191e2b;'
                f'border-radius:0 8px 8px 0;padding:12px 14px;margin-top:12px">'
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
                f'<span style="font-size:18px">{s["symbol"]}</span>'
                f'<span style="font-size:13px;font-weight:700;color:{s["color"]}">{s["title"]}</span>'
                f'</div>'
                f'<div style="font-size:12px;color:#8891a8;line-height:1.75">{s["detail"]}</div>'
                f'<div style="font-family:DM Mono,monospace;font-size:11px;color:#4a5168;'
                f'background:#0e1017;border-radius:6px;padding:7px 10px;margin-top:8px;'
                f'border:1px solid #252c3e">{s["math"]}</div>'
                f'<div style="font-size:10px;color:#22c55e;margin-top:8px;display:flex;gap:5px">'
                f'<span>✓</span><span>Proof obligation: {s["obligation"]}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="border-left:3px solid #22c55e;background:#191e2b;'
                f'border-radius:0 8px 8px 0;padding:12px 14px;margin-top:12px">'
                f'<div style="font-size:13px;font-weight:700;color:#22c55e;margin-bottom:6px">'
                f'✓ Reduction Complete — NP-Completeness Established</div>'
                f'<div style="font-size:12px;color:#8891a8;line-height:1.75">{p["sketch"]}</div>'
                f'<div style="font-family:DM Mono,monospace;font-size:11px;color:#4a5168;'
                f'background:#0e1017;border-radius:6px;padding:7px 10px;margin-top:8px;'
                f'border:1px solid #252c3e">Source: {p["source"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)  # close card

        # ── Controls ─────────────────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns([1, 1, 3, 1, 1])
        with c1:
            if st.button("⏮", disabled=step == 0, key="first"):
                st.session_state.step = 0
                st.session_state.claude_text = ""
                st.session_state.last_explained = (-1, "")
                st.rerun()
        with c2:
            if st.button("◀", disabled=step == 0, key="prev"):
                st.session_state.step = max(0, step - 1)
                st.session_state.last_explained = (-1, "")
                st.rerun()
        with c3:
            if st.button(f"▶  Explain This Step with Claude", use_container_width=True, key="explain"):
                st.session_state.last_explained = (-1, "")  # force re-fetch
                st.rerun()
        with c4:
            if st.button("▶", disabled=step >= total_steps, key="next"):
                st.session_state.step = min(total_steps, step + 1)
                st.session_state.last_explained = (-1, "")
                st.rerun()
        with c5:
            if st.button("⏭", disabled=step >= total_steps, key="last"):
                st.session_state.step = total_steps
                st.session_state.last_explained = (-1, "")
                st.rerun()

        # ── Claude panel ──────────────────────────────────────────────────────
        claude_placeholder = st.empty()

        should_explain = (
            st.session_state.last_explained != (step, key)
        )

        if should_explain and step >= 0:
            # Build prompt
            if step == 0:
                user_msg = (
                    f"Introduce the {p['full_name']} problem for NP-completeness. "
                    f"Formal definition: {p['formal']}. "
                    f"Proven NP-complete by {p['by']} in {p['year']}. "
                    f"Give 2-3 paragraphs: what the problem asks, why it matters, what the Cook-Levin reduction will show."
                )
            elif step <= len(p["steps"]):
                s = p["steps"][step - 1]
                user_msg = (
                    f"Explain step {s['title']} of the Cook-Levin reduction for {p['full_name']}.\n"
                    f"Short: {s['short']}\nDetail: {s['detail']}\nMath: {s['math']}\n"
                    f"Obligation: {s['obligation']}\n\n"
                    f"Write 2-3 paragraphs: intuition first, then formal content, then why this step is necessary."
                )
            else:
                user_msg = (
                    f"Summarize the completed Cook-Levin reduction for {p['full_name']}. "
                    f"Proof source: {p['source']}. Sketch: {p['sketch']}. "
                    f"Fun fact: {p['fun_fact']}. Open question: {p['open']}. "
                    f"Write 2-3 paragraphs: what was proved, what it means for P vs NP, one memorable takeaway."
                )

            system = (
                "You are a theoretical computer scientist explaining NP-completeness to a sharp student. "
                "Be precise, vivid, and concrete. 2-3 paragraphs. No bullet lists. No headers. "
                "Use Unicode math where helpful. First paragraph: intuition. Middle: formal content. "
                "Last: why this matters / connects to the bigger picture."
            )

            with claude_placeholder:
                st.markdown(
                    '<div class="card card-accent-purple">'
                    '<div class="micro-label">✦ Claude Explanation</div>'
                    '<div class="thinking-dots" style="display:flex;gap:5px;padding:8px 0">'
                    '<span style="color:#7c6af7">Thinking...</span>'
                    '</div></div>',
                    unsafe_allow_html=True,
                )

            text = stream_explanation(system, user_msg, claude_placeholder)
            st.session_state.claude_text = text
            st.session_state.last_explained = (step, key)

        elif st.session_state.claude_text:
            claude_placeholder.markdown(
                f'<div class="card card-accent-purple">'
                f'<div class="micro-label">✦ Claude Explanation</div>'
                f'<div style="font-size:13px;line-height:1.9;color:#dde3f0">{st.session_state.claude_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Fun fact
        st.markdown(
            f'<div class="funfact">{p["fun_fact"]}</div>',
            unsafe_allow_html=True,
        )

    with right:
        # ── Step list ─────────────────────────────────────────────────────────
        st.markdown('<div class="card"><div class="micro-label">Reduction Steps</div>', unsafe_allow_html=True)
        for i, s in enumerate(p["steps"]):
            idx = i + 1
            is_cur = step == idx
            is_done = step > idx
            num_color = s["color"] if (is_cur or is_done) else "#4a5168"
            num_bg = s["color"] + "22" if is_cur else ("#1f2535" if is_done else "#131720")
            label_color = "#dde3f0" if is_cur else ("#8891a8" if is_done else "#4a5168")
            check = "✓" if is_done else str(idx)
            bg = "#191e2b" if is_cur else "transparent"
            border = f"1px solid {s['color']}44" if is_cur else "1px solid transparent"

            if st.button(
                f"{s['symbol']}  {s['title']}",
                key=f"step_{key}_{idx}",
                use_container_width=True,
            ):
                st.session_state.step = idx
                st.session_state.last_explained = (-1, "")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Graph ─────────────────────────────────────────────────────────────
        st.markdown('<div class="card"><div class="micro-label">Problem Instance</div>', unsafe_allow_html=True)
        st.markdown(render_graph_svg(key), unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#0e1017;border:1px solid #252c3e;border-radius:6px;'
            f'padding:8px 12px;font-family:DM Mono,monospace;font-size:11px;color:#22c55e;'
            f'margin-top:8px">✓ {p["certificate"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB: PROOF BARRIERS
# ════════════════════════════════════════════════════════════════════════════

elif tab == "barriers":
    st.markdown("""
    <div class="card" style="margin-bottom:20px">
      <div class="micro-label">Why P vs NP Has Resisted Proof for 50+ Years</div>
      <div style="font-size:13px;color:#8891a8;line-height:1.75">
        Three structural results show that entire <em>classes</em> of proof techniques
        cannot work — not a specific failed proof, but a sweeping impossibility for any
        argument of that type. Understanding the barriers is understanding why this problem
        is genuinely hard, not just unsolved.
      </div>
    </div>
    """, unsafe_allow_html=True)

    attempt = st.text_area(
        "Propose a proof approach or shortcut",
        placeholder=(
            "Describe your idea...\n\n"
            "Examples:\n"
            "  • Diagonalize over all polynomial-time algorithms\n"
            "  • Apply Fourier analysis over GF(2) to circuit lower bounds\n"
            "  • Extend the IP=PSPACE proof to push NP into P\n"
            "  • Use a pseudorandom generator to force NP ⊄ P/poly"
        ),
        height=120,
        key="attempt_input",
    )

    st.markdown("**Click a barrier to see where your attempt hits it:**")

    barrier_placeholder = st.empty()

    cols = st.columns(3)
    for i, (bkey, b) in enumerate(BARRIERS.items()):
        with cols[i]:
            st.markdown(
                f'<div style="background:#131720;border:1px solid #252c3e;border-left:3px solid {b["color"]};'
                f'border-radius:10px;padding:14px;margin-bottom:8px">'
                f'<div style="font-size:20px;margin-bottom:6px">{b["icon"]}</div>'
                f'<div style="font-size:14px;font-weight:700;color:{b["color"]};margin-bottom:4px">{b["label"]}</div>'
                f'<div style="font-size:9px;color:#4a5168;font-family:DM Mono,monospace;margin-bottom:8px">{b["year"]}</div>'
                f'<div style="font-size:11px;color:#6b7280;line-height:1.6">{b["summary"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Analyze with Claude →", key=f"barrier_{bkey}", use_container_width=True):
                attempt_text = attempt.strip() or "Use a diagonalization argument over all polynomial-time algorithms"
                cache_key = (bkey, attempt_text)
                if cache_key != st.session_state.last_barrier:
                    system = (
                        "You are a complexity theorist explaining proof barriers to P vs NP. "
                        "The student has proposed a concrete approach. "
                        "Take their proposal seriously. Identify precisely which barrier it hits. "
                        "Explain the technical mechanism — not just the name, but WHY it blocks. "
                        "End with what WOULD be needed to overcome this barrier. "
                        "3-4 paragraphs. No headers. Rigorous but clear. Unicode math welcome."
                    )
                    user_msg = (
                        f"Barrier: {b['label']} ({b['year']})\n"
                        f"Summary: {b['summary']}\n"
                        f"Technical detail: {b['detail']}\n"
                        f"Blocks: {b['blocks']}\n"
                        f"Does NOT block: {b['does_not_block']}\n"
                        f"Citation: {b['cite']}\n\n"
                        f"Student's proposed approach: \"{attempt_text}\"\n\n"
                        f"Analyze this approach precisely against the {b['label']} barrier."
                    )
                    with barrier_placeholder:
                        st.markdown(
                            f'<div class="card" style="border-left:3px solid {b["color"]}">'
                            f'<div class="micro-label" style="color:{b["color"]}">✦ Claude Analysis · {b["label"]}</div>'
                            f'<div style="color:#4a5168">Analyzing...</div></div>',
                            unsafe_allow_html=True,
                        )
                    text = stream_explanation(system, user_msg, barrier_placeholder)
                    st.session_state.barrier_text = text
                    st.session_state.last_barrier = cache_key
                    # Re-render with correct accent color
                    barrier_placeholder.markdown(
                        f'<div class="card" style="border-left:3px solid {b["color"]}">'
                        f'<div class="micro-label" style="color:{b["color"]}">✦ Claude Analysis · {b["label"]}</div>'
                        f'<div style="font-size:13px;line-height:1.9;color:#dde3f0">{text}</div></div>',
                        unsafe_allow_html=True,
                    )

    # Show cached barrier analysis
    if st.session_state.barrier_text and st.session_state.last_barrier[0]:
        bkey_cached = st.session_state.last_barrier[0]
        b_cached = BARRIERS.get(bkey_cached, {})
        barrier_placeholder.markdown(
            f'<div class="card" style="border-left:3px solid {b_cached.get("color","#7c6af7")}">'
            f'<div class="micro-label" style="color:{b_cached.get("color","#7c6af7")}">✦ Claude Analysis · {b_cached.get("label","")}</div>'
            f'<div style="font-size:13px;line-height:1.9;color:#dde3f0">{st.session_state.barrier_text}</div></div>',
            unsafe_allow_html=True,
        )

    # Technical details in expanders
    st.markdown("---")
    st.markdown("**Technical Details**")
    for bkey, b in BARRIERS.items():
        with st.expander(f"{b['icon']} {b['label']} — {b['year']}"):
            st.markdown(f"**Technical detail:** {b['detail']}")
            st.markdown(f"**Blocks:** {b['blocks']}")
            st.markdown(f"**Does NOT block:** {b['does_not_block']}")
            st.markdown(f"*{b['cite']}*")


# ════════════════════════════════════════════════════════════════════════════
# TAB: CERTIFICATE
# ════════════════════════════════════════════════════════════════════════════

elif tab == "certificate":
    st.markdown(f"""
    <div class="card" style="margin-bottom:20px">
      <div class="micro-label">What Is an NP Certificate?</div>
      <div style="font-size:13px;color:#8891a8;line-height:1.75">
        A problem is in NP if, for every YES instance, there exists a short certificate (a witness)
        that can be <em>verified</em> in polynomial time. The certificate does not need to be easy to
        <em>find</em> — only easy to check. This is the fundamental asymmetry that might separate P from NP.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div class="card" style="border-left:3px solid {p["color"]}">'
        f'<div class="micro-label">Selected Problem</div>'
        f'<div style="font-size:18px;font-weight:800;color:{p["color"]}">{p["full_name"]}</div>'
        f'<div style="font-size:12px;color:#4a5168;font-family:DM Mono,monospace;margin-top:2px">{p["source"]}</div>'
        f'<div style="font-size:12px;color:#8891a8;margin-top:8px;line-height:1.65">{p["sketch"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        f"⬡  Generate Complexity Certificate for {p['full_name']}",
        type="primary",
        use_container_width=True,
        key="gen_cert",
    ):
        with st.spinner("Claude is generating your certificate..."):
            try:
                cert = generate_certificate(key)
                st.session_state.cert_data = cert
                st.session_state.share_url = make_share_url(key, cert)
            except Exception as e:
                st.error(f"Certificate generation failed: {e}")

    if st.session_state.cert_data:
        cert = st.session_state.cert_data

        # Header
        st.markdown(
            f'<div style="background:#131720;border:2px solid {p["color"]};border-radius:12px;'
            f'padding:18px;margin:16px 0">'
            f'<div style="font-size:20px;font-weight:800;color:{p["color"]}">'
            f'{cert.get("problem", p["full_name"])}</div>'
            f'<div style="font-size:11px;color:#4a5168;font-family:DM Mono,monospace;margin-top:2px">'
            f'{cert.get("complexity_class", "NP-Complete")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="cert-block"><div class="micro-label">Instance</div>'
                f'<div class="mono" style="color:#dde3f0;line-height:1.7">'
                f'{cert.get("instance_description","—")}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="cert-block"><div class="micro-label">Certificate Value</div>'
                f'<div class="mono" style="color:#22c55e;line-height:1.7">'
                f'{cert.get("certificate_value","—")}</div></div>',
                unsafe_allow_html=True,
            )

        # Verification steps
        steps_html = ""
        for i, s in enumerate(cert.get("verification_steps", [])):
            steps_html += (
                f'<div class="chain-item">'
                f'<div style="min-width:22px;height:22px;border-radius:50%;'
                f'background:{p["color"]}22;border:1px solid {p["color"]}44;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:10px;color:{p["color"]};flex-shrink:0">{i+1}</div>'
                f'<div>{s}</div></div>'
            )
        st.markdown(
            f'<div class="cert-block"><div class="micro-label">Verification Steps (Poly-Time)</div>'
            f'{steps_html}</div>',
            unsafe_allow_html=True,
        )

        # Proof chain
        chain_html = ""
        for i, s in enumerate(cert.get("npc_proof_chain", [])):
            chain_html += (
                f'<div class="chain-item">'
                f'<div style="min-width:22px;height:22px;border-radius:50%;'
                f'background:{p["color"]}22;border:1px solid {p["color"]}44;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:10px;color:{p["color"]};flex-shrink:0">{i+1}</div>'
                f'<div>{s}</div></div>'
            )
        st.markdown(
            f'<div class="cert-block"><div class="micro-label">NP-Completeness Proof Chain</div>'
            f'{chain_html}</div>',
            unsafe_allow_html=True,
        )

        col3, col4 = st.columns(2)
        with col3:
            st.markdown(
                f'<div class="cert-block"><div class="micro-label">Historical Note</div>'
                f'<div style="font-size:12px;color:#8891a8;line-height:1.65">'
                f'{cert.get("historical_note","—")}</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f'<div class="cert-block"><div class="micro-label">Open Problem</div>'
                f'<div style="font-size:12px;color:#8891a8;line-height:1.65">'
                f'{cert.get("open_problem","—")}</div></div>',
                unsafe_allow_html=True,
            )

        # Share URL
        st.markdown(
            f'<div class="cert-block"><div class="micro-label">Shareable URL (copy this)</div>'
            f'<div class="share-box">{st.session_state.share_url}</div></div>',
            unsafe_allow_html=True,
        )
        st.code(st.session_state.share_url, language=None)
