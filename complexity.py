"""
core/complexity.py
==================
All complexity-theoretic data: NP-complete problems, Cook-Levin reduction
steps, barrier definitions, and certificate structures.

This module is intentionally pure-data — no I/O, no side effects.
Every string here is either a verified citation or a pedagogically-accurate
simplification labelled as such.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ComplexityClass(str, Enum):
    P = "P"
    NP = "NP"
    NPC = "NP-Complete"
    NPHARD = "NP-Hard"
    PSPACE = "PSPACE"
    EXPTIME = "EXPTIME"


@dataclass(frozen=True)
class ReductionStep:
    index: int
    title: str
    symbol: str
    color: str
    short_desc: str
    technical_detail: str
    latex_sketch: str          # LaTeX-style pseudomath for the panel
    proof_obligation: str      # What this step must demonstrate


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    x: float
    y: float
    color: Optional[str] = None
    highlight: bool = False
    node_type: str = "default"   # default | special | certificate


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    weight: float = 1.0
    highlight: bool = False
    edge_type: str = "default"   # default | reduction | certificate


@dataclass(frozen=True)
class ProblemGraph:
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    certificate_nodes: List[str]     # node IDs that are part of the solution
    certificate_edges: List[tuple]   # (src, tgt) pairs that are part of the solution


@dataclass(frozen=True)
class NPCProblem:
    key: str
    label: str
    full_name: str
    year_proven: int
    proven_by: str
    complexity_class: ComplexityClass
    accent_color: str

    description: str
    formal_definition: str
    decision_question: str
    example_instance: str
    example_certificate: str

    npc_proof_source: str        # The actual reduction used to prove NPC
    npc_proof_sketch: str

    reduction_steps: List[ReductionStep]
    graph: ProblemGraph

    fun_fact: str
    open_question: str


# ─── SAT ─────────────────────────────────────────────────────────────────────

SAT = NPCProblem(
    key="SAT",
    label="SAT",
    full_name="Boolean Satisfiability",
    year_proven=1971,
    proven_by="Stephen Cook / Leonid Levin",
    complexity_class=ComplexityClass.NPC,
    accent_color="#7c6af7",

    description="Can a Boolean formula be satisfied by some assignment of TRUE/FALSE to its variables?",
    formal_definition="Given φ = C₁ ∧ C₂ ∧ … ∧ Cₘ where each Cᵢ is a disjunction of literals, does there exist an assignment σ: {x₁,…,xₙ} → {0,1} such that φ(σ) = 1?",
    decision_question="Is φ satisfiable?",
    example_instance="(x₁ ∨ ¬x₂ ∨ x₃) ∧ (¬x₁ ∨ x₂) ∧ (x₂ ∨ ¬x₃)",
    example_certificate="x₁ = T,  x₂ = T,  x₃ = F",

    npc_proof_source="Cook (1971) STOC; Levin (1973) Problemy Peredachi Informatsii",
    npc_proof_sketch="Every NP language L has a polynomial-time verifier V. Given input w, construct a Boolean formula φ encoding 'V accepts (w, c) for some certificate c of length poly(|w|)'. This is satisfiable iff w ∈ L. The construction is O(n^k) in formula size.",

    reduction_steps=[
        ReductionStep(
            index=1,
            title="Encode the Verifier as a Turing Machine",
            symbol="M",
            color="#7c6af7",
            short_desc="Every NP language has a poly-time verifier. Encode it as a TM M.",
            technical_detail="Fix an NP language L with verifier V running in time p(n). We encode V as a standard k-tape Turing machine M with state set Q, tape alphabet Γ, and transition function δ: Q × Γᵏ → Q × Γᵏ × {L,R,S}ᵏ.",
            latex_sketch="M = (Q, Γ, b, Σ, δ, q₀, q_acc)",
            proof_obligation="M must accept (w,c) in exactly p(|w|) steps whenever V accepts.",
        ),
        ReductionStep(
            index=2,
            title="Build the Computation Tableau",
            symbol="T",
            color="#2dd4bf",
            short_desc="A p(n) × p(n) table where each row is one configuration of M.",
            technical_detail="The tableau T has rows indexed by time t ∈ [0, p(n)] and columns by tape position j ∈ [0, p(n)]. Cell T[t][j] ∈ Q ∪ Γ encodes either a tape symbol or (head position, state) if the head is at column j at time t. This gives p(n)² cells.",
            latex_sketch="T: [0..p(n)] × [0..p(n)] → Q ∪ Γ",
            proof_obligation="A valid, accepting tableau exists ↔ ∃ certificate c that causes M to accept.",
        ),
        ReductionStep(
            index=3,
            title="Introduce Boolean Variables",
            symbol="x",
            color="#f59e0b",
            short_desc="One variable per (time, position, symbol) triple.",
            technical_detail="For each t ∈ [0,p(n)], j ∈ [0,p(n)], s ∈ Q∪Γ, introduce variable x_{t,j,s} meaning 'at time t, column j contains symbol s'. This gives O(p(n)² · |Q∪Γ|) variables, polynomial in n.",
            latex_sketch="x_{t,j,s} ∈ {0,1}  ∀ t,j ∈ [p(n)],  s ∈ Q∪Γ",
            proof_obligation="Satisfying assignment ↔ valid tableau ↔ accepting computation.",
        ),
        ReductionStep(
            index=4,
            title="Add Cell-Validity Clauses",
            symbol="C",
            color="#22c55e",
            short_desc="Each cell must contain exactly one symbol.",
            technical_detail="For each (t,j): (a) At-least-one: ⋁_{s} x_{t,j,s}. (b) At-most-one: for all s≠s', add clause (¬x_{t,j,s} ∨ ¬x_{t,j,s'}). This is O(|Γ|²) clauses per cell, O(p(n)² · |Γ|²) total — still polynomial.",
            latex_sketch="∀t,j: (⋁ₛ x_{t,j,s}) ∧ ⋀_{s≠s'} (¬x_{t,j,s} ∨ ¬x_{t,j,s'})",
            proof_obligation="Exactly one symbol per cell in any satisfying assignment.",
        ),
        ReductionStep(
            index=5,
            title="Encode Transition Constraints",
            symbol="δ",
            color="#ef4444",
            short_desc="Adjacent rows must follow δ; cells away from the head are unchanged.",
            technical_detail="For each time t and each transition (q, a) →δ (q', b, D): add clauses forcing x_{t,j,q} ∧ x_{t,j,a} → x_{t+1,j',q'} ∧ x_{t+1,j,b} where j'=j±1. Cells not under the head: x_{t,j,s} → x_{t+1,j,s}. These are implications, each convertible to 2-3 clauses.",
            latex_sketch="(¬x_{t,j,q} ∨ ¬x_{t,j,a} ∨ x_{t+1,j',q'}) for each δ(q,a)=(q',b,D)",
            proof_obligation="Every row must follow from the previous by exactly one application of δ.",
        ),
        ReductionStep(
            index=6,
            title="Add Initial and Accepting Clauses",
            symbol="✓",
            color="#a855f7",
            short_desc="Row 0 encodes input w; final row must contain q_acc.",
            technical_detail="Initial configuration: set x_{0,j,w_j} = 1 for input symbols, q₀ at head position 0. These become unit clauses. Acceptance: add clause ⋁_{t,j} x_{t,j,q_acc} — the accepting state appears somewhere in the last row. This unit disjunction is satisfiable iff the TM accepts.",
            latex_sketch="Unit clauses for x_{0,j,wⱼ}=1,  acceptance clause ⋁ⱼ x_{p(n),j,q_acc}",
            proof_obligation="Satisfying assignment ↔ M accepts w with certificate encoded in variables.",
        ),
    ],

    graph=ProblemGraph(
        nodes=[
            GraphNode("x1", "x₁", 90, 55, color="#7c6af7", node_type="special"),
            GraphNode("x2", "x₂", 200, 55, color="#7c6af7", node_type="special"),
            GraphNode("x3", "x₃", 145, 140, color="#7c6af7", node_type="special"),
            GraphNode("c1", "C₁", 55, 185, color="#2dd4bf", node_type="default"),
            GraphNode("c2", "C₂", 160, 205, color="#2dd4bf", node_type="default"),
            GraphNode("c3", "C₃", 250, 155, color="#2dd4bf", node_type="default"),
        ],
        edges=[
            GraphEdge("x1","c1"), GraphEdge("x2","c1"), GraphEdge("x3","c1"),
            GraphEdge("x1","c2"), GraphEdge("x2","c3"), GraphEdge("x3","c2"),
            GraphEdge("x2","c2"), GraphEdge("x3","c3"),
        ],
        certificate_nodes=["x1","x2","c1","c2","c3"],
        certificate_edges=[("x1","c1"),("x2","c1"),("x2","c2"),("x2","c3")],
    ),

    fun_fact="Cook's 1971 STOC paper was 14 pages. Levin independently discovered the same result in the USSR and published in 1973. The theorem is sometimes called 'Cook-Levin' in both their honors.",
    open_question="Is there an algorithm for SAT that runs in O(1.99ⁿ) time? The best known is ~O(1.307ⁿ) (DPLL with random restarts). Even shaving the base is an open research problem.",
)


# ─── CLIQUE ───────────────────────────────────────────────────────────────────

CLIQUE = NPCProblem(
    key="CLIQUE",
    label="Clique",
    full_name="k-Clique",
    year_proven=1972,
    proven_by="Richard Karp",
    complexity_class=ComplexityClass.NPC,
    accent_color="#2dd4bf",

    description="Does a graph contain k vertices that are all mutually adjacent (a complete subgraph Kₖ)?",
    formal_definition="Given G=(V,E) and k ∈ ℕ, does there exist S ⊆ V with |S|=k such that ∀u,v ∈ S, u≠v: {u,v} ∈ E?",
    decision_question="Does G contain a k-clique?",
    example_instance="G with 6 nodes (v₁–v₆), 9 edges. k = 3.",
    example_certificate="Clique: {v₁, v₂, v₆} — all three pairs are edges.",

    npc_proof_source="Karp (1972) 'Reducibility Among Combinatorial Problems'",
    npc_proof_sketch="Reduce 3SAT → Clique. Given a 3CNF with k clauses, build graph G: one node per literal per clause (3k nodes total). Add edge between nodes from different clauses iff their literals are consistent (no variable assigned both T and F). G has a k-clique iff the formula is satisfiable.",

    reduction_steps=[
        ReductionStep(
            index=1,
            title="Start from 3SAT Instance",
            symbol="φ",
            color="#7c6af7",
            short_desc="Input: a 3CNF formula with k clauses, each with exactly 3 literals.",
            technical_detail="Given φ = C₁ ∧ … ∧ Cₖ where each Cᵢ = (lᵢ₁ ∨ lᵢ₂ ∨ lᵢ₃). We will construct a graph G = (V, E) in polynomial time such that G has a k-clique ↔ φ is satisfiable.",
            latex_sketch="φ = ⋀ᵢ Cᵢ,   |Cᵢ| = 3,   k = number of clauses",
            proof_obligation="The reduction must be computable in O(k²) time — polynomial in the formula size.",
        ),
        ReductionStep(
            index=2,
            title="Create Literal Nodes",
            symbol="N",
            color="#2dd4bf",
            short_desc="For each literal lᵢⱼ in each clause Cᵢ, create node (i,j).",
            technical_detail="V = { (i,j) : i ∈ [k], j ∈ {1,2,3} }. This gives exactly 3k nodes. Node (i,j) represents literal lᵢⱼ in clause Cᵢ. We tag each node with its clause index i and its literal lᵢⱼ.",
            latex_sketch="V = {(i,j) : i∈[k], j∈[3]},   |V| = 3k",
            proof_obligation="Every literal in the formula has a corresponding node in G.",
        ),
        ReductionStep(
            index=3,
            title="Add Consistency Edges",
            symbol="E",
            color="#f59e0b",
            short_desc="Connect (i,j)–(i',j') iff i≠i' and lᵢⱼ and lᵢ'ⱼ' are consistent.",
            technical_detail="Add edge {(i,j),(i',j')} iff: (a) i ≠ i' (different clauses), and (b) lᵢⱼ ≠ ¬lᵢ'ⱼ' (literals are not negations of each other). No edges within a clause. This ensures any clique represents a consistent partial assignment.",
            latex_sketch="{(i,j),(i',j')} ∈ E  ⟺  i≠i'  ∧  lᵢⱼ ≢ ¬lᵢ'ⱼ'",
            proof_obligation="A k-clique selects one literal per clause with no contradictions — exactly a satisfying assignment.",
        ),
        ReductionStep(
            index=4,
            title="Clique ↔ Satisfying Assignment",
            symbol="↔",
            color="#22c55e",
            short_desc="Prove the equivalence: k-clique ↔ satisfying assignment.",
            technical_detail="(→) If S is a k-clique, it selects one node per clause (no two from the same clause since intra-clause edges are missing). All pairs are consistent, so we can set each selected literal to TRUE — this satisfies all k clauses. (←) If σ satisfies φ, pick one TRUE literal per clause. These form a k-clique: different clauses by construction, consistent by σ.",
            latex_sketch="S k-clique ⟺ {lᵢ,jᵢ : (i,jᵢ) ∈ S} is a satisfying partial assignment",
            proof_obligation="The biconditional must hold exactly — no false positives or false negatives.",
        ),
        ReductionStep(
            index=5,
            title="Extract the Certificate",
            symbol="🔑",
            color="#ef4444",
            short_desc="The clique S encodes the variable assignment directly.",
            technical_detail="Given a k-clique S = {(i,jᵢ)}, define σ: for each variable x, set σ(x)=T if some node in S has literal x, σ(x)=F if some node has ¬x, and either arbitrarily otherwise. Verify σ satisfies φ in O(k·|φ|) time — polynomial. The clique itself is the poly-time verifiable certificate.",
            latex_sketch="Certificate = S (k nodes). Verifier: check |S|=k, all edges present, all clauses satisfied.",
            proof_obligation="Verification must run in polynomial time — confirming Clique ∈ NP.",
        ),
    ],

    graph=ProblemGraph(
        nodes=[
            GraphNode("v1", "v₁", 140, 35, node_type="default"),
            GraphNode("v2", "v₂", 240, 90, node_type="default"),
            GraphNode("v3", "v₃", 215, 195, node_type="default"),
            GraphNode("v4", "v₄", 100, 210, node_type="default"),
            GraphNode("v5", "v₅", 35, 125, node_type="default"),
            GraphNode("v6", "v₆", 155, 130, color="#2dd4bf", node_type="certificate"),
        ],
        edges=[
            GraphEdge("v1","v2"), GraphEdge("v2","v3"), GraphEdge("v3","v4"),
            GraphEdge("v4","v5"), GraphEdge("v5","v1"),
            GraphEdge("v1","v6",highlight=True), GraphEdge("v2","v6",highlight=True),
            GraphEdge("v6","v3"), GraphEdge("v4","v6"),
            GraphEdge("v1","v2",highlight=True),
        ],
        certificate_nodes=["v1","v2","v6"],
        certificate_edges=[("v1","v2"),("v1","v6"),("v2","v6")],
    ),

    fun_fact="Karp's 1972 paper listed 21 NP-complete problems — now considered one of the most cited papers in theoretical computer science.",
    open_question="The best known algorithm for k-Clique runs in O(n^{ω·k/3}) time where ω < 2.373 (matrix mult. exponent). Whether it can be improved to O(n^{(1-ε)k}) for any ε > 0 would break the 'Clique conjecture'.",
)


# ─── 3-COLORABILITY ──────────────────────────────────────────────────────────

THREECOLOR = NPCProblem(
    key="3COL",
    label="3-Color",
    full_name="3-Colorability",
    year_proven=1972,
    proven_by="Richard Karp (via Stockmeyer 1973 for the gadget)",
    complexity_class=ComplexityClass.NPC,
    accent_color="#f59e0b",

    description="Can graph vertices be colored with 3 colors so no two adjacent vertices share a color?",
    formal_definition="Given G=(V,E), does there exist a function c: V → {1,2,3} such that ∀{u,v} ∈ E: c(u) ≠ c(v)?",
    decision_question="Is G 3-colorable?",
    example_instance="Petersen graph (10 vertices, 15 edges). Is it 3-chromatic?",
    example_certificate="c(v₁)=R, c(v₂)=G, c(v₃)=B, c(v₄)=R, c(v₅)=G  [for 5-cycle in example]",

    npc_proof_source="Karp (1972); complete gadget construction by Stockmeyer (1973)",
    npc_proof_sketch="Reduce 3SAT → 3COL. Build a palette triangle (TRUE, FALSE, BASE). For each variable xᵢ, add a complementary pair (xᵢ, ¬xᵢ) connected to each other and to BASE. For each clause, attach an OR-gadget: a 6-node subgraph that cannot be 3-colored if all three of its input literals are FALSE.",

    reduction_steps=[
        ReductionStep(
            index=1,
            title="Build the Palette Triangle",
            symbol="▲",
            color="#7c6af7",
            short_desc="Three special nodes T, F, B — all connected to each other.",
            technical_detail="Add nodes {T (TRUE), F (FALSE), B (BASE)} and edges {T,F}, {F,B}, {T,B}. In any proper 3-coloring, these three nodes must receive all three colors. We WLOG label the colors so T gets color 'TRUE', F gets 'FALSE', B gets 'BASE'.",
            latex_sketch="K₃ on {T,F,B}; fix coloring c(T)=TRUE, c(F)=FALSE, c(B)=BASE",
            proof_obligation="Every 3-coloring of G restricted to {T,F,B} induces the same palette structure.",
        ),
        ReductionStep(
            index=2,
            title="Variable Gadgets",
            symbol="⬡",
            color="#2dd4bf",
            short_desc="For each variable xᵢ: add nodes xᵢ, ¬xᵢ, connected to each other and to B.",
            technical_detail="For each variable xᵢ: add nodes xᵢ and ¬xᵢ. Add edges {xᵢ, ¬xᵢ} and {xᵢ, B} and {¬xᵢ, B}. Since xᵢ and ¬xᵢ are adjacent, they get different colors; since both are adjacent to B, neither gets color BASE. So one gets TRUE and the other gets FALSE — this encodes the truth value of xᵢ.",
            latex_sketch="Gadget: xᵢ—¬xᵢ, xᵢ—B, ¬xᵢ—B  ⟹  {c(xᵢ),c(¬xᵢ)} = {TRUE,FALSE}",
            proof_obligation="Variable gadget enforces exactly two valid states: xᵢ=T and xᵢ=F.",
        ),
        ReductionStep(
            index=3,
            title="OR-Gadget for Each Clause",
            symbol="⊕",
            color="#f59e0b",
            short_desc="6-node gadget that is 3-colorable iff at least one input literal is TRUE.",
            technical_detail="For clause C = (l₁ ∨ l₂ ∨ l₃): build a binary OR tree. First OR(l₁, l₂) using 3 intermediate nodes a,b,c connected as: a—l₁, a—l₂, a—B, b—a, b—F, c—b, c—l₃, c—B. Output of gadget connects to F. If all inputs are FALSE-colored, the output is forced to F — contradiction. If any input is TRUE-colored, a valid 3-coloring exists.",
            latex_sketch="OR(l₁,l₂,l₃)-gadget: 3-colorable iff c(l₁)=T ∨ c(l₂)=T ∨ c(l₃)=T",
            proof_obligation="Gadget is 3-colorable ↔ at least one literal in the clause is TRUE-colored.",
        ),
        ReductionStep(
            index=4,
            title="Connect Gadgets to Palette",
            symbol="↔",
            color="#22c55e",
            short_desc="Clause gadget output must not be colored FALSE — enforcing clause satisfaction.",
            technical_detail="The output node of each OR-gadget is connected to F. This means the output cannot be colored FALSE. But if all clause literals are FALSE-colored, the gadget forces the output to be FALSE — contradiction. So the full graph is 3-colorable iff every clause gadget can avoid this contradiction, i.e., every clause has at least one TRUE literal.",
            latex_sketch="output(Cᵢ) adjacent to F  ⟹  output cannot be FALSE  ⟹  ≥1 literal TRUE",
            proof_obligation="Global 3-colorability ↔ all clause gadgets are satisfiable ↔ φ is satisfiable.",
        ),
        ReductionStep(
            index=5,
            title="Extract the Certificate",
            symbol="🔑",
            color="#ef4444",
            short_desc="Read off the coloring: TRUE-colored variable nodes give the satisfying assignment.",
            technical_detail="Given a valid 3-coloring c of G: for each variable xᵢ, set σ(xᵢ) = (c(xᵢ) == TRUE). This is well-defined since c(xᵢ) ∈ {TRUE, FALSE} by the variable gadget. By the OR-gadget analysis, every clause has at least one literal colored TRUE, so σ satisfies all clauses. Verification time: O(|V| + |E|) = polynomial.",
            latex_sketch="σ(xᵢ) := [c(xᵢ) = TRUE]  →  σ satisfies φ",
            proof_obligation="Certificate (the coloring) verifiable in polynomial time.",
        ),
    ],

    graph=ProblemGraph(
        nodes=[
            GraphNode("T", "T", 140, 30, color="#ef4444", node_type="special"),
            GraphNode("F", "F", 50, 175, color="#3b82f6", node_type="special"),
            GraphNode("B", "B", 230, 175, color="#22c55e", node_type="special"),
            GraphNode("x1", "x₁", 85, 95, color="#ef4444", node_type="default"),
            GraphNode("nx1", "¬x₁", 200, 95, color="#3b82f6", node_type="default"),
            GraphNode("x2", "x₂", 140, 195, color="#22c55e", node_type="default"),
        ],
        edges=[
            GraphEdge("T","F"), GraphEdge("F","B"), GraphEdge("T","B"),
            GraphEdge("x1","nx1"), GraphEdge("x1","B"), GraphEdge("nx1","B"),
            GraphEdge("x2","T"), GraphEdge("x2","F"),
        ],
        certificate_nodes=["T","F","B","x1","x2"],
        certificate_edges=[("T","F"),("F","B"),("T","B")],
    ),

    fun_fact="4-Colorability of PLANAR graphs is decidable in P (the Four Color Theorem, proved by computer in 1976). But 3-Colorability of general graphs is NP-complete — planarity is what makes the difference.",
    open_question="Is there a polynomial-time algorithm to 4-color planar graphs that doesn't use a computer-verified proof? The existing proof (Appel-Haken 1976; Robertson et al. 1997) requires checking ~633 configurations computationally.",
)


# ─── HAMILTONIAN CYCLE ────────────────────────────────────────────────────────

HAMCYCLE = NPCProblem(
    key="HAMCYCLE",
    label="Ham. Cycle",
    full_name="Hamiltonian Cycle",
    year_proven=1972,
    proven_by="Richard Karp",
    complexity_class=ComplexityClass.NPC,
    accent_color="#ef4444",

    description="Does a graph contain a cycle that visits every vertex exactly once?",
    formal_definition="Given G=(V,E), does there exist a permutation (v₁, v₂, …, v_n) of V such that {vᵢ, vᵢ₊₁} ∈ E for all i and {vₙ, v₁} ∈ E?",
    decision_question="Does G contain a Hamiltonian cycle?",
    example_instance="Dodecahedron graph (20 vertices, 30 edges). Hamilton found a cycle in 1857.",
    example_certificate="Cycle: v₁→v₃→v₇→v₂→v₅→v₈→v₄→v₆→v₉→v₁₀→v₁",

    npc_proof_source="Karp (1972); detailed construction by Garey-Johnson (1979)",
    npc_proof_sketch="Reduce 3SAT → Hamiltonian Cycle. For each variable xᵢ, build a path-gadget: a chain of nodes that the Hamiltonian cycle traverses either left-to-right (xᵢ=T) or right-to-left (xᵢ=F). For each clause Cⱼ, add a clause node cⱼ that can be visited via a detour from a literal node — but only if that literal is TRUE.",

    reduction_steps=[
        ReductionStep(
            index=1,
            title="Variable Path Gadgets",
            symbol="→",
            color="#7c6af7",
            short_desc="For each variable xᵢ, build a horizontal chain of 2(m+1) nodes.",
            technical_detail="For variable xᵢ with m clauses referencing it, create a chain: [aᵢ,₀ — bᵢ,₁ — aᵢ,₁ — bᵢ,₂ — aᵢ,₂ — … — bᵢ,ₘ — aᵢ,ₘ]. The Hamiltonian cycle must traverse this chain either L→R (encoding xᵢ=TRUE) or R→L (encoding xᵢ=FALSE). There are no other valid traversal options due to the chain structure.",
            latex_sketch="xᵢ-gadget: chain of 2(m+1) nodes; direction encodes truth value of xᵢ",
            proof_obligation="Every Hamiltonian cycle traverses each variable gadget in exactly one direction.",
        ),
        ReductionStep(
            index=2,
            title="Chain All Variable Gadgets",
            symbol="⛓",
            color="#2dd4bf",
            short_desc="Link gadgets in series: aₙ₋₁,ₘ → a₀,₀, creating a variable-selection backbone.",
            technical_detail="Add edges connecting the right end of xᵢ's gadget to the left end of xᵢ₊₁'s gadget, and the right end of the last gadget back to the left end of the first. This creates a large cycle backbone that the Hamiltonian cycle must follow — committing to a truth value for each variable in order.",
            latex_sketch="aᵢ,ₘ → aᵢ₊₁,₀  for each i;   aₙ,ₘ → a₁,₀  (close the backbone)",
            proof_obligation="The backbone forces the Hamiltonian cycle to make exactly one choice per variable.",
        ),
        ReductionStep(
            index=3,
            title="Add Clause Check Nodes",
            symbol="◆",
            color="#f59e0b",
            short_desc="One extra node cⱼ per clause, placed off the backbone.",
            technical_detail="For each clause Cⱼ = (l₁ ∨ l₂ ∨ l₃), add a single node cⱼ not on the backbone. This node must be visited by the Hamiltonian cycle exactly once. The only way to visit cⱼ is via a 'detour' from within a variable gadget — specifically from a literal node that encodes a TRUE literal in Cⱼ.",
            latex_sketch="|extra nodes| = m (one per clause); these must all appear in the Ham. cycle",
            proof_obligation="Every clause node must be visited, requiring at least one TRUE literal per clause.",
        ),
        ReductionStep(
            index=4,
            title="Add Literal-to-Clause Detour Edges",
            symbol="↗",
            color="#22c55e",
            short_desc="If literal lᵢⱼ appears in clause Cⱼ, add edges enabling a detour through cⱼ.",
            technical_detail="For literal xᵢ in clause Cⱼ (if xᵢ is the j-th clause): add edges aᵢ,ⱼ—cⱼ and cⱼ—bᵢ,ⱼ. If the cycle traverses xᵢ's gadget L→R (xᵢ=T), it can detour: ...→aᵢ,ⱼ→cⱼ→bᵢ,ⱼ→... visiting cⱼ. If traversed R→L (xᵢ=F), no detour is available for this literal from this gadget.",
            latex_sketch="aᵢ,ⱼ — cⱼ — bᵢ,ⱼ  for each literal xᵢ occurring in clause Cⱼ",
            proof_obligation="Detour edges enable visiting cⱼ exactly via TRUE-direction traversal.",
        ),
        ReductionStep(
            index=5,
            title="Extract the Certificate",
            symbol="🔑",
            color="#ef4444",
            short_desc="The traversal direction through each gadget gives the satisfying assignment.",
            technical_detail="Given a Hamiltonian cycle H: for each variable xᵢ, set σ(xᵢ)=T if H traverses xᵢ's gadget L→R, else F. Since every clause node cⱼ appears in H, at least one literal in each clause was traversed in the TRUE direction — which means σ satisfies all clauses. Verification in O(|V|+|E|) time.",
            latex_sketch="σ(xᵢ) := [H traverses xᵢ-gadget L→R]  →  σ satisfies φ",
            proof_obligation="Certificate (the Hamiltonian cycle) verifiable in polynomial time.",
        ),
    ],

    graph=ProblemGraph(
        nodes=[
            GraphNode("s", "S", 140, 30, node_type="special"),
            GraphNode("a", "A", 235, 90, node_type="default"),
            GraphNode("b", "B", 240, 185, node_type="default"),
            GraphNode("c", "C", 145, 220, node_type="default"),
            GraphNode("d", "D", 50, 185, node_type="default"),
            GraphNode("e", "E", 40, 90, node_type="default"),
        ],
        edges=[
            GraphEdge("s","a"), GraphEdge("a","b"), GraphEdge("b","c"),
            GraphEdge("c","d"), GraphEdge("d","e"), GraphEdge("e","s"),
            GraphEdge("s","c"), GraphEdge("a","d"), GraphEdge("b","e"),
        ],
        certificate_nodes=["s","a","b","c","d","e"],
        certificate_edges=[("s","a"),("a","b"),("b","c"),("c","d"),("d","e"),("e","s")],
    ),

    fun_fact="William Rowan Hamilton sold a puzzle in 1857 called the 'Icosian Game': find a cycle visiting all 20 vertices of a dodecahedron. The puzzle was a commercial failure. The complexity of his namesake problem wasn't understood for another 115 years.",
    open_question="Is Hamiltonian Cycle in planar 3-regular graphs NP-complete? Yes (Garey-Johnson-Tarjan 1976). Does a planar 4-connected graph always have a Hamiltonian cycle? Tutte's theorem says yes — proved in 1956.",
)


# ─── Barriers ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Barrier:
    key: str
    label: str
    icon: str
    color: str
    year: int
    authors: str
    headline: str
    summary: str
    technical_detail: str
    what_it_blocks: str
    does_not_block: str
    citation: str


BARRIERS: Dict[str, Barrier] = {
    "relativization": Barrier(
        key="relativization",
        label="Relativization",
        icon="⊘",
        color="#7c6af7",
        year=1975,
        authors="Baker, Gill & Solovay",
        headline="Baker-Gill-Solovay 1975",
        summary="There exist oracles A, B such that Pᴬ=NPᴬ and Pᴮ≠NPᴮ. Any proof technique that works identically in the presence of any oracle — a 'relativizing' technique — cannot resolve P vs NP.",
        technical_detail="An oracle TM can query an oracle set A in O(1). A proof technique 'relativizes' if it proves Pᴬ=NPᴬ for all A, or Pᴮ≠NPᴮ for all B. BGS showed there exist specific A and B witnessing opposite separations. All known diagonalization arguments relativize. Since the truth of P vs NP doesn't relativize (it can't be both simultaneously true), no relativizing proof can resolve it.",
        what_it_blocks="Diagonalization, time-hierarchy theorem techniques, most 'clever Turing machine simulation' arguments.",
        does_not_block="Circuit complexity arguments (they don't relativize). Algebraic techniques (partially). Combinatorial/combinatorics-based approaches.",
        citation="T. Baker, J. Gill, R. Solovay. Relativizations of the P=?NP Question. SIAM J. Comput. 4(4):431–442, 1975.",
    ),
    "naturalProofs": Barrier(
        key="naturalProofs",
        label="Natural Proofs",
        icon="⊗",
        color="#f59e0b",
        year=1994,
        authors="Razborov & Rudich",
        headline="Razborov-Rudich 1994",
        summary="A 'natural' proof of circuit lower bounds — one that is constructive and large — could be used to efficiently break pseudorandom functions. Since PRFs likely exist (under standard crypto assumptions), natural proofs likely cannot prove P≠NP.",
        technical_detail="A property P of Boolean functions is 'natural' if: (1) Constructivity: P is computable in 2^{O(n)} time; (2) Largeness: a 2^n-random function satisfies P with high probability. Razborov-Rudich show: if a natural proof proves that no circuit of size s(n) computes some function f, then PRFs of size s'(n) don't exist. Under the PRF assumption (implied by P≠NP), natural proofs cannot prove superpolynomial lower bounds — a circular impossibility.",
        what_it_blocks="Most combinatorial lower-bound arguments. Current state-of-the-art circuit complexity. Switching lemma arguments (Håstad, Razborov). Approximation methods.",
        does_not_block="Non-constructive proofs. Proofs that use specific structure of NP (not generic random functions). Geometric/algebraic proofs that aren't 'large' in the Razborov-Rudich sense.",
        citation="A. Razborov, S. Rudich. Natural Proofs. J. Comput. Syst. Sci. 55(1):24–35, 1997. (Conference version STOC 1994.)",
    ),
    "algebrization": Barrier(
        key="algebrization",
        label="Algebrization",
        icon="⊛",
        color="#2dd4bf",
        year=2009,
        authors="Aaronson & Wigderson",
        headline="Aaronson-Wigderson 2009",
        summary="A strengthening of relativization using algebraic extensions of oracles. Most algebraic proof techniques — including those used to prove IP=PSPACE and MIP*=RE — are algebrizing. Algebrizing proofs cannot separate P from NP or prove NP ⊄ P/poly.",
        technical_detail="An 'algebraic oracle' Ã is a low-degree extension of a Boolean function A over a large field 𝔽. A proof technique 'algebrizes' if it works relative to any algebraic oracle. Aaronson-Wigderson show: NP ⊄ P/poly relative to some algebraic oracle, and P = NP relative to another. They also show the proofs of IP=PSPACE and MA-EXP ⊄ P/poly algebrize — so these techniques cannot be extended to separate NP from P. This subsumes relativization (Boolean oracle = special case of algebraic oracle).",
        what_it_blocks="Arithmetization. Sum-check protocol generalizations. Algebraic proof systems. LFKN/Shamir/IP=PSPACE style arguments applied naively to P vs NP.",
        does_not_block="Non-algebrizing techniques (if any can be found). Proofs based on new mathematical structures (e.g., quantum information, geometry). Techniques exploiting specific properties of NP-complete problems rather than generic oracle separation.",
        citation="S. Aaronson, A. Wigderson. Algebrization: A New Barrier in Complexity Theory. TOCT 1(1):2, 2009.",
    ),
}


# ─── Registry ─────────────────────────────────────────────────────────────────

PROBLEMS: Dict[str, NPCProblem] = {
    "SAT": SAT,
    "CLIQUE": CLIQUE,
    "3COL": THREECOLOR,
    "HAMCYCLE": HAMCYCLE,
}

PROBLEM_ORDER = ["SAT", "CLIQUE", "3COL", "HAMCYCLE"]


def get_problem(key: str) -> Optional[NPCProblem]:
    return PROBLEMS.get(key)


def get_barrier(key: str) -> Optional[Barrier]:
    return BARRIERS.get(key)


def problem_to_dict(p: NPCProblem) -> dict:
    return {
        "key": p.key,
        "label": p.label,
        "full_name": p.full_name,
        "year_proven": p.year_proven,
        "proven_by": p.proven_by,
        "complexity_class": p.complexity_class.value,
        "accent_color": p.accent_color,
        "description": p.description,
        "formal_definition": p.formal_definition,
        "decision_question": p.decision_question,
        "example_instance": p.example_instance,
        "example_certificate": p.example_certificate,
        "npc_proof_source": p.npc_proof_source,
        "npc_proof_sketch": p.npc_proof_sketch,
        "fun_fact": p.fun_fact,
        "open_question": p.open_question,
        "reduction_steps": [
            {
                "index": s.index,
                "title": s.title,
                "symbol": s.symbol,
                "color": s.color,
                "short_desc": s.short_desc,
                "technical_detail": s.technical_detail,
                "latex_sketch": s.latex_sketch,
                "proof_obligation": s.proof_obligation,
            }
            for s in p.reduction_steps
        ],
        "graph": {
            "nodes": [
                {"id": n.id, "label": n.label, "x": n.x, "y": n.y,
                 "color": n.color, "highlight": n.highlight, "node_type": n.node_type}
                for n in p.graph.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "weight": e.weight,
                 "highlight": e.highlight, "edge_type": e.edge_type}
                for e in p.graph.edges
            ],
            "certificate_nodes": p.graph.certificate_nodes,
            "certificate_edges": [list(e) for e in p.graph.certificate_edges],
        },
    }


def barrier_to_dict(b: Barrier) -> dict:
    return {
        "key": b.key,
        "label": b.label,
        "icon": b.icon,
        "color": b.color,
        "year": b.year,
        "authors": b.authors,
        "headline": b.headline,
        "summary": b.summary,
        "technical_detail": b.technical_detail,
        "what_it_blocks": b.what_it_blocks,
        "does_not_block": b.does_not_block,
        "citation": b.citation,
    }
