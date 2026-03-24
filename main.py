"""
main.py
=======
FastAPI backend for the P vs NP Interactive Explorer.

Architecture:
  GET  /                       → serve index.html
  GET  /api/problems           → list all NPC problems (metadata only)
  GET  /api/problem/{key}      → full problem data including graph + reduction steps
  GET  /api/barriers           → all three proof barriers
  POST /api/explain/step       → Claude streaming: explain a reduction step
  POST /api/explain/barrier    → Claude streaming: explain a barrier vs user's attempt
  POST /api/certificate        → Claude JSON: generate complexity certificate
  GET  /api/share/{token}      → decode a shareable certificate token
  POST /api/share              → encode certificate → shareable token

All Claude calls use streaming SSE so the UI can render text token-by-token.
"""

import os
import json
import base64
import hashlib
import asyncio
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.complexity import (
    PROBLEMS, BARRIERS, PROBLEM_ORDER,
    problem_to_dict, barrier_to_dict,
    get_problem, get_barrier,
)

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pvsnp")

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="P vs NP Interactive Explorer",
    description="Cook-Levin tableau reductions, proof barriers, and complexity certificates.",
    version="1.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if the directory exists
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# ─── Claude client ────────────────────────────────────────────────────────────

def get_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not set. Set it as an environment variable.",
        )
    return anthropic.Anthropic(api_key=api_key)

MODEL = "claude-opus-4-5"

# ─── System prompts ──────────────────────────────────────────────────────────

STEP_SYSTEM = """You are a theoretical computer scientist explaining the Cook-Levin theorem
and NP-completeness reductions. Your audience is a strong undergraduate or graduate student
who knows discrete math and basic algorithms, but may be seeing complexity theory for the first time.

Style guide:
- 2–4 tight paragraphs. No bullet lists. No headers.
- First paragraph: concrete intuition — what is actually happening, using a physical analogy if helpful.
- Middle paragraph(s): the formal mathematical content. Be precise. Use Unicode math symbols: ∀ ∃ ∧ ∨ ¬ → ↔ ⊆ ∈ ℕ.
- Final paragraph: why this step is NECESSARY — what breaks if you skip it, and how it connects to the next step.
- Never say "great question" or use filler phrases.
- Avoid passive voice where possible.
- Write as if you have thought about this for years and found the clearest way to say it."""

BARRIER_SYSTEM = """You are a complexity theorist explaining proof barriers to P vs NP.
The student has proposed a concrete approach. Your job is to:
1. Take their proposal seriously and engage with its strongest form.
2. Precisely identify which barrier it runs into.
3. Explain the technical mechanism that blocks it — not just "it relativizes" but WHY.
4. End with what WOULD be needed to overcome this barrier (even if unknown).

Style: 3–5 paragraphs. Rigorous but clear. Use Unicode math. No headers. No filler."""

CERT_SYSTEM = """You are generating a formal NP complexity certificate in JSON.
Return ONLY valid JSON, no markdown fences, no commentary.

Required schema:
{
  "problem": string,
  "complexity_class": string,
  "instance_description": string,
  "instance_formal": string,
  "certificate_value": string,
  "certificate_type": string,
  "verification_algorithm": string,
  "verification_steps": [string, string, string, string],
  "verification_time": string,
  "npc_proof_chain": [string, string, string],
  "reduction_from": string,
  "historical_note": string,
  "open_problem": string
}

All fields must be technically accurate. verification_steps should be concrete pseudo-algorithm steps.
npc_proof_chain should trace the chain of reductions: SAT ≤ₚ X or X ≤ₚ SAT."""


# ─── Request models ───────────────────────────────────────────────────────────

class StepRequest(BaseModel):
    problem_key: str = Field(..., description="SAT | CLIQUE | 3COL | HAMCYCLE")
    step_index: int  = Field(..., ge=0, description="0 = intro, 1–N = step index, N+1 = conclusion")


class BarrierRequest(BaseModel):
    barrier_key: str  = Field(..., description="relativization | naturalProofs | algebrization")
    user_attempt: str = Field(..., min_length=1, description="User's proposed shortcut or proof technique")
    problem_key: Optional[str] = Field(None, description="Optional: which NPC problem they were thinking about")


class CertificateRequest(BaseModel):
    problem_key: str = Field(..., description="SAT | CLIQUE | 3COL | HAMCYCLE")


class ShareEncodeRequest(BaseModel):
    certificate: dict
    problem_key: str


# ─── Streaming helper ─────────────────────────────────────────────────────────

async def stream_claude(
    system: str,
    user_message: str,
    max_tokens: int = 1200,
) -> AsyncGenerator[bytes, None]:
    """
    Stream Claude's response as Server-Sent Events.
    Each chunk: b'data: {"token": "..."}\n\n'
    Final chunk: b'data: {"done": true}\n\n'
    """
    client = get_claude()

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                payload = json.dumps({"token": text})
                yield f"data: {payload}\n\n".encode()
                await asyncio.sleep(0)   # yield control to event loop

        yield b'data: {"done": true}\n\n'

    except anthropic.APIError as e:
        error_payload = json.dumps({"error": str(e)})
        yield f"data: {error_payload}\n\n".encode()
        yield b'data: {"done": true}\n\n'


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serve the single-page application."""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Frontend not found. Run the build step.")
    with open(html_path, encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/problems")
async def list_problems():
    """Return metadata for all NPC problems in display order."""
    return {
        "problems": [
            {
                "key": k,
                "label": PROBLEMS[k].label,
                "full_name": PROBLEMS[k].full_name,
                "year_proven": PROBLEMS[k].year_proven,
                "proven_by": PROBLEMS[k].proven_by,
                "accent_color": PROBLEMS[k].accent_color,
                "description": PROBLEMS[k].description,
                "step_count": len(PROBLEMS[k].reduction_steps),
            }
            for k in PROBLEM_ORDER
        ]
    }


@app.get("/api/problem/{key}")
async def get_problem_detail(key: str):
    """Return full problem data including graph, reduction steps, and metadata."""
    p = get_problem(key)
    if not p:
        raise HTTPException(status_code=404, detail=f"Problem '{key}' not found.")
    return {"problem": problem_to_dict(p)}


@app.get("/api/barriers")
async def list_barriers():
    """Return all three proof barriers."""
    return {
        "barriers": {k: barrier_to_dict(v) for k, v in BARRIERS.items()}
    }


@app.post("/api/explain/step")
async def explain_step(req: StepRequest):
    """
    Stream Claude's explanation of a specific reduction step.
    step_index = 0  → introduction to the problem
    step_index = N  → step N (1-indexed)
    step_index > N  → conclusion / what was proved
    """
    p = get_problem(req.problem_key)
    if not p:
        raise HTTPException(status_code=404, detail=f"Problem '{req.problem_key}' not found.")

    n = len(p.reduction_steps)

    if req.step_index == 0:
        user_msg = (
            f"Give an introduction to the {p.full_name} problem in the context of NP-completeness. "
            f"Cover: what the problem asks ({p.decision_question}), "
            f"why it matters, and what a Cook-Levin tableau reduction will demonstrate. "
            f"Formal definition: {p.formal_definition}. "
            f"It was proven NP-complete by {p.proven_by} in {p.year_proven}."
        )
    elif req.step_index <= n:
        step = p.reduction_steps[req.step_index - 1]
        user_msg = (
            f"Explain step {step.index} of the Cook-Levin reduction for {p.full_name}.\n\n"
            f"Step title: {step.title}\n"
            f"Short description: {step.short_desc}\n"
            f"Technical detail: {step.technical_detail}\n"
            f"Mathematical sketch: {step.latex_sketch}\n"
            f"Proof obligation: {step.proof_obligation}\n\n"
            f"Explain: (1) the intuition behind this step, (2) the formal construction, "
            f"(3) why this step is necessary and what proof obligation it discharges."
        )
    else:
        user_msg = (
            f"The Cook-Levin reduction for {p.full_name} is complete. "
            f"Summarize what was proven: why {p.full_name} is NP-complete, "
            f"what the polynomial reduction established, "
            f"and what this means for the broader P vs NP question. "
            f"Historical note: {p.npc_proof_source}. "
            f"Fun fact: {p.fun_fact}. "
            f"Open question: {p.open_question}."
        )

    return StreamingResponse(
        stream_claude(STEP_SYSTEM, user_msg, max_tokens=900),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/explain/barrier")
async def explain_barrier(req: BarrierRequest):
    """
    Stream Claude's analysis of a user's proposed proof attempt vs a specific barrier.
    """
    b = get_barrier(req.barrier_key)
    if not b:
        raise HTTPException(status_code=404, detail=f"Barrier '{req.barrier_key}' not found.")

    problem_ctx = ""
    if req.problem_key:
        p = get_problem(req.problem_key)
        if p:
            problem_ctx = f"\nThe student was working on: {p.full_name} — {p.description}"

    user_msg = (
        f"Barrier: {b.label} ({b.headline})\n"
        f"Barrier summary: {b.summary}\n"
        f"Technical mechanism: {b.technical_detail}\n"
        f"What it blocks: {b.what_it_blocks}\n"
        f"What it does NOT block: {b.does_not_block}\n"
        f"Citation: {b.citation}\n"
        f"{problem_ctx}\n\n"
        f"The student's proposed approach: \"{req.user_attempt}\"\n\n"
        f"Analyze this approach: take it seriously, identify exactly where and how "
        f"the {b.label} barrier applies to it, and explain what would be needed to "
        f"circumvent this barrier (even if nobody knows how to do that yet)."
    )

    return StreamingResponse(
        stream_claude(BARRIER_SYSTEM, user_msg, max_tokens=1100),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/certificate")
async def generate_certificate(req: CertificateRequest):
    """
    Generate a full NP complexity certificate via Claude (non-streaming, returns JSON).
    """
    p = get_problem(req.problem_key)
    if not p:
        raise HTTPException(status_code=404, detail=f"Problem '{req.problem_key}' not found.")

    client = get_claude()

    user_msg = (
        f"Generate a formal NP complexity certificate for: {p.full_name}\n\n"
        f"Problem description: {p.description}\n"
        f"Formal definition: {p.formal_definition}\n"
        f"Decision question: {p.decision_question}\n"
        f"Example instance: {p.example_instance}\n"
        f"Example certificate: {p.example_certificate}\n"
        f"NPC proof: {p.npc_proof_source}\n"
        f"NPC sketch: {p.npc_proof_sketch}\n"
        f"Fun fact: {p.fun_fact}\n"
        f"Open question: {p.open_question}\n\n"
        f"complexity_class should be: NP-Complete\n"
        f"reduction_from: for SAT use 'Cook-Levin (1971)'; for others use 'SAT via Karp (1972)'\n"
        f"npc_proof_chain: trace the 3-step chain from a universal NP problem to this one."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=CERT_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        certificate = json.loads(raw)

        # Attach metadata
        certificate["_meta"] = {
            "problem_key": req.problem_key,
            "accent_color": p.accent_color,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model": MODEL,
        }

        return JSONResponse(content={"certificate": certificate})

    except json.JSONDecodeError as e:
        log.error(f"Certificate JSON parse error: {e}. Raw: {raw[:200]}")
        raise HTTPException(status_code=500, detail="Certificate generation produced invalid JSON.")
    except anthropic.APIError as e:
        raise HTTPException(status_code=503, detail=f"Claude API error: {e}")


@app.post("/api/share")
async def encode_share(req: ShareEncodeRequest):
    """
    Encode a certificate into a base64 URL token.
    Returns a shareable URL fragment: /share/{token}
    """
    payload = json.dumps({
        "problem_key": req.problem_key,
        "certificate": req.certificate,
        "version": "1",
    }, separators=(",", ":"))

    token = base64.urlsafe_b64encode(payload.encode()).decode()
    checksum = hashlib.sha256(payload.encode()).hexdigest()[:8]
    full_token = f"{token}.{checksum}"

    return {"token": full_token, "url_fragment": f"#cert={full_token}"}


@app.get("/api/share/{token}")
async def decode_share(token: str):
    """
    Decode a shareable certificate token.
    """
    try:
        b64_part = token.split(".")[0]
        padding = 4 - len(b64_part) % 4
        if padding != 4:
            b64_part += "=" * padding
        payload = base64.urlsafe_b64decode(b64_part).decode()
        data = json.loads(payload)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid share token: {e}")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "problems": len(PROBLEMS),
        "barriers": len(BARRIERS),
        "model": MODEL,
        "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
