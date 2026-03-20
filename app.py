"""
DAIS-10 Web Backend — app.py
Flask API running real DAIS-10 v1.1.8 engines.

Deploy to PythonAnywhere:
  1. Upload this file + dais10/ folder + Extra_files/ folder
  2. pip install flask flask-cors pandas pyyaml python-dateutil reportlab
  3. Set WSGI file to point here

Author: Dr. Usman Zafar · ZULFR
"""

import sys
import os
import csv
import json
import io
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# ── Path setup (same as GUI) ──────────────────────────────────────────────────
ROOT  = os.path.dirname(os.path.abspath(__file__))
EXTRA = os.path.join(ROOT, "Extra_files")
sys.path.insert(0, ROOT)
sys.path.insert(0, EXTRA)

app = Flask(__name__)
CORS(app, origins=[
    "https://zulfr.com",
    "https://usman19zafar.github.io",
    "http://localhost",
    "http://127.0.0.1",
    "null"   # file:// local testing
])

# ── Import all engines ────────────────────────────────────────────────────────
try:
    from dais10.core.types import (
        Context, SemanticDescriptor, Tier,
        GovernanceLevel, QualitativeCategory
    )
    from dais10.engines.sis   import SIS10
    from dais10.engines.mcm   import MCM10
    from dais10.engines.tier  import TIER10
    from dais10.engines.sicm  import SICM10
    from dais10.engines.difs  import DIFS10
    from dais10.engines.difs_v11 import DIFS10_v11
    from dais10.engines.sif   import SIF10
    from dais10.engines.qfim  import QFIM10
    from dais10.engines.amd   import AMD10
    from engines.explainability import ExplainabilityEngine
    from engines.sample_window  import SampleWindowGenerator, RowStatus
    from engines.cap_reasons    import CapReasonGenerator
    from governance.policy_engine import PolicyEngine
    from governance.risk_control  import RiskController
    from governance.validation    import DataValidator
    ENGINES_READY = True
except Exception as e:
    ENGINES_READY = False
    ENGINE_ERROR  = str(e)

# ── Instantiate engines once at startup ──────────────────────────────────────
if ENGINES_READY:
    _sis      = SIS10()
    _mcm      = MCM10()
    _tier_eng = TIER10()
    _sicm     = SICM10()
    _difs     = DIFS10()
    _difsv11  = DIFS10_v11()
    _sif      = SIF10()
    _qfim     = QFIM10()
    _amd      = AMD10()
    _explain  = ExplainabilityEngine()
    _sampler  = SampleWindowGenerator()
    _capgen   = CapReasonGenerator()
    _policy   = PolicyEngine()
    _risk     = RiskController()
    _validate = DataValidator()


# ── File parser ───────────────────────────────────────────────────────────────
def parse_file(file) -> List[Dict]:
    """Parse uploaded CSV or JSON into list of dicts."""
    name    = file.filename.lower()
    content = file.read().decode("utf-8", errors="replace")
    if name.endswith(".json"):
        data = json.loads(content)
        return data if isinstance(data, list) else [data]
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader]


# ── Health ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "service": "DAIS-10 API v1.1.8",
        "engines": "ready" if ENGINES_READY else f"error: {ENGINE_ERROR if not ENGINES_READY else ''}",
        "author":  "Dr. Usman Zafar · ZULFR"
    })


# ── Main analysis endpoint ────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze():
    if not ENGINES_READY:
        return jsonify({"error": f"Engines not ready: {ENGINE_ERROR}"}), 500

    # ── Parse input ──────────────────────────────────────────────────────────
    domain = request.form.get("domain", "general")
    mode   = request.form.get("mode", "inference")  # inference|sovereign|hybrid

    if "file" in request.files:
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "No file selected"}), 400
        try:
            rows = parse_file(f)
            filename = f.filename
        except Exception as ex:
            return jsonify({"error": f"Cannot parse file: {str(ex)}"}), 400
    elif request.is_json:
        body     = request.get_json()
        rows     = body.get("rows", [])
        domain   = body.get("domain", domain)
        filename = "inline_data"
    else:
        return jsonify({"error": "Send a file (CSV/JSON) or JSON body"}), 400

    if not rows:
        return jsonify({"error": "Dataset is empty"}), 400

    # Cap at 100k rows for web requests
    rows = rows[:100000]

    try:
        columns = list(rows[0].keys())
        ctx     = Context(domain=domain, purpose=f"{domain}_analysis")

        # ── PHASE 1: Column schema ────────────────────────────────────────────
        samples = {
            col: [str(r.get(col, "")) for r in rows[:100] if r.get(col)]
            for col in columns
        }
        col_schema:  Dict[str, Dict]          = {}
        descriptors: List[SemanticDescriptor] = []

        for col in columns:
            meta, pats = _sis.interpret(col, samples[col])
            role       = _mcm.classify_role(col, meta, pats, ctx)
            tobj       = _tier_eng.assign_tier(role, ctx)
            tv         = tobj.value
            imp        = _sicm.calculate_score(tobj, ctx)
            dr         = tobj.decay_rate

            sd = SemanticDescriptor(
                attribute_name=col, role=role, tier=tobj,
                score=imp, rationale=None, confidence=1.0
            )
            descriptors.append(sd)
            col_schema[col] = {
                "tier": tv, "importance": imp, "decay_rate": dr,
                "descriptor": sd
            }

        # SIF-10 normalised weights
        sif_weights = _sif.compute_weights(descriptors)
        for i, col in enumerate(col_schema):
            col_schema[col]["sif_weight"] = round(sif_weights[i], 5) if i < len(sif_weights) else 0.0

        # QFIM-10 per attribute
        qfim_map = {sd.attribute_name: _qfim.interpret(sd) for sd in descriptors}

        # AMD-10 diagnostics per attribute
        amd_map = {sd.attribute_name: _amd.run_diagnostics(sd, ctx) for sd in descriptors}

        # ── PHASE 2: Row scoring ──────────────────────────────────────────────
        all_rows     = []
        all_cap_evts = []

        for row_idx, row in enumerate(rows):
            cell_results = []
            cap_events   = []

            for col, cfg in col_schema.items():
                value     = row.get(col, "")
                imp       = cfg["importance"]
                tv        = cfg["tier"]
                dr        = cfg["decay_rate"]
                tobj      = Tier(tv)
                freshness = 1.0
                days_old  = 0

                if value is None or str(value).strip() == "":
                    if tv == "E":
                        cap = _capgen.generate_cap_reason(col, tv, "missing", None)
                        cap_events.append({
                            "row":         row_idx + 1,
                            "column":      col,
                            "cap_reason":  cap.code if cap else f"E_TIER_{col.upper()}_MISSING",
                            "legal_ref":   cap.legal_reference if cap else None,
                            "framework":   cap.regulatory_framework.value if (cap and cap.regulatory_framework) else None,
                            "remediation": cap.remediation_action if cap else None,
                        })
                    cell_results.append({
                        "column": col, "score": 0.0, "importance": imp, "tier": tv,
                        "reason": "Missing E-tier field" if tv == "E" else "Missing optional field",
                        "days_old": None, "freshness_score": 0.0,
                        "cap_applied": tv == "E",
                        "cap_reason": cap_events[-1]["cap_reason"] if tv == "E" and cap_events else None,
                    })
                else:
                    freshness  = _difs.apply_decay(100.0, tobj, 0) / 100.0
                    cell_score = imp * freshness
                    cell_results.append({
                        "column": col, "score": cell_score, "importance": imp, "tier": tv,
                        "reason": "Valid", "days_old": 0,
                        "freshness_score": round(freshness, 4),
                        "cap_applied": False, "cap_reason": None,
                    })

            row_score = _sif.calculate_row_score(cell_results)
            gov       = _qfim.determine_row_governance(cell_results, row_score)
            vector    = _explain.create_explainability_vector(
                row_score=row_score, governance_action=gov,
                cell_results=cell_results, top_k=3
            )
            top_contribs = [{
                "column":  c.column,
                "impact":  round(c.impact, 1),
                "reason":  c.reason,
                "score":   round(c.cell_score, 1),
                "cap_applied": c.cap_applied,
            } for c in vector.top_contributors]

            status = RowStatus.classify(row_score).value

            all_rows.append({
                "row_id":          row_idx + 1,
                "row_score":       round(row_score, 2),
                "governance":      gov,
                "status":          status,
                "top_contributors": top_contribs,
            })
            all_cap_evts.extend(cap_events)

        # SampleWindow + Governance + Risk
        sw          = _sampler.generate(all_rows)
        pol_result  = _policy.evaluate(descriptors)
        risk_result = _risk.assess(descriptors)

        # ── PHASE 3: Build response ───────────────────────────────────────────
        scores     = [r["row_score"] for r in all_rows]
        avg_score  = round(sum(scores) / len(scores), 2) if scores else 0
        prime_ct   = sum(1 for r in all_rows if r["status"] in ("PRIME", "GOOD"))
        fail_ct    = sum(1 for r in all_rows if r["status"] in ("FAILURE", "FAIL"))
        weak_ct    = sum(1 for r in all_rows if r["status"] in ("WEAK", "FAIR"))

        # Column summary (serialisable)
        columns_out = {}
        for col, cfg in col_schema.items():
            qi = qfim_map.get(col)
            ad = amd_map.get(col)
            columns_out[col] = {
                "tier":       cfg["tier"],
                "importance": round(cfg["importance"], 2),
                "sif_weight": cfg["sif_weight"],
                "role":       cfg["descriptor"].role.value,
                "governance": cfg["descriptor"].governance_level.value,
                "qfim": {
                    "category":       qi.category.value if qi else None,
                    "recommendation": qi.recommendation if qi else None,
                } if qi else None,
                "amd": {
                    "tests_run":     ad.tests_run if ad else 0,
                    "passed":        ad.passed if ad else 0,
                    "warnings":      ad.warnings if ad else 0,
                    "failed":        ad.failed if ad else 0,
                    "overall_status": ad.overall_status if ad else "UNKNOWN",
                } if ad else None,
            }

        # Risk level
        risk_level = "UNKNOWN"
        try:
            risk_level = risk_result.risk_level.value if hasattr(risk_result, "risk_level") else str(risk_result)
        except Exception:
            pass

        return jsonify({
            "status":      "ok",
            "filename":    filename,
            "domain":      domain,
            "total_rows":  len(rows),
            "total_columns": len(columns),
            "average_score": avg_score,
            "prime_count": prime_ct,
            "fail_count":  fail_ct,
            "weak_count":  weak_ct,
            "risk_level":  risk_level,
            "columns":     columns_out,
            "best_rows":   [_row_out(r) for r in (sw.best_rows  if hasattr(sw, "best_rows")  else all_rows[:10])],
            "worst_rows":  [_row_out(r) for r in (sw.worst_rows if hasattr(sw, "worst_rows") else all_rows[-10:])],
            "cap_events":  all_cap_evts[:100],   # first 100 cap violations
            "policy":      str(pol_result),
        })

    except Exception as ex:
        import traceback
        return jsonify({"error": str(ex), "trace": traceback.format_exc()}), 500


def _row_out(r) -> Dict:
    """Serialise a row result (handles both dict and object)."""
    if isinstance(r, dict):
        return {
            "row_id":    r.get("row_id"),
            "row_score": round(float(r.get("row_score", 0)), 2),
            "status":    r.get("status", ""),
            "governance": r.get("governance", ""),
            "top_contributors": r.get("top_contributors", []),
        }
    return {
        "row_id":    getattr(r, "row_id", None),
        "row_score": round(float(getattr(r, "row_score", 0)), 2),
        "status":    getattr(r, "status", ""),
        "governance": getattr(r, "governance", ""),
        "top_contributors": [],
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
