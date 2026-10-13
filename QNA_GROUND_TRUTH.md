# Cortex — Q&A Ground Truth

Expected answers for every module, grounded in the 6 curated sample documents.
Use this to verify the system is working correctly during testing and the live demo.

---

## Source documents (what's ingested)

| File | Type | Key entities |
|---|---|---|
| `pump_P-101_maintenance_report.txt` | maintenance_report | P-101, SKF 6310, WO-2024-0512, R. Sharma, A. Mehta |
| `OEM_manual_P-101_excerpt.txt` | oem_manual | P-101, KSB Etanorm, ISO 10816-3 |
| `incident_report_C-150_compressor.txt` | incident_report | C-150, INC-2024-0731, Ariel JGK/4, OISD-STD-118 |
| `safety_procedure_hot_work.txt` | safety_procedure | SOP-SAF-014, P-101, V-200, C-150, PESO, Factory Act |
| `email_thread_V-200_relief_valve.eml` | email | V-200, OISD-STD-106, S. Nair, A. Mehta |
| `inspection_records.csv` | inspection | P-101, V-200, C-150, E-301 readings over time |

---

## Module 1 — Expert Copilot (Chat)

### Q1. Why did pump P-101 fail and how was it fixed?

**Expected answer (key facts — must all be present):**
- Vibration exceeded **7.1 mm/s RMS** (alarm threshold 4.5 mm/s per ISO 10816-3)
- Root cause: misalignment introduced during coupling replacement **(WO-2024-0188, Feb 2024)** + inadequate lubrication (6-month cycle vs OEM-recommended **3-month cycle**)
- Drive-end bearing (SKF 6310) showed **spalling on the outer race**
- Fix: replaced both bearings + mechanical seal (John Crane Type 21), laser-aligned shaft to **0.05 mm**
- Post-repair vibration: **2.3 mm/s RMS** (well below threshold)
- Performed under PTW-3391, OISD-STD-105

**Must cite:** `pump_P-101_maintenance_report.txt` + `OEM_manual_P-101_excerpt.txt`

---

### Q2. What is the OEM-recommended lubrication interval for P-101, and what was the plant doing wrong?

**Expected answer:**
- OEM (KSB manual, Section 7.2): re-grease every **3 months** using Shell Gadus S2 V220 or equivalent NLGI 2 lithium-complex grease — specifically for **continuous duty above 60 °C ambient**
- Plant was on a **6-month cycle** — double the OEM interval
- Under-greasing accelerates **spalling** (the exact failure mode found)
- This discrepancy is called out as a contributing root cause in the maintenance report

**Cross-document signal:** The OEM manual sets the spec; the maintenance report confirms the deviation. Answer should draw from **both** documents.

---

### Q3. What was the root cause of the C-150 compressor trip?

**Expected answer:**
- Immediate cause: **cracked 2nd-stage discharge valve plate** → gas recirculation → heat buildup
- Trip at **154 °C** (trip setpoint 150 °C), at 03:42 on 2024-07-28
- Valve plates had run **9,200 hours** vs OEM-recommended **8,000-hour** replacement interval
- Lubricant degradation (high TAN — total acid number) reduced cooling
- Rod drop was logged at **0.48 mm** (threshold 0.50 mm) on 2024-07-26 — a warning not escalated
- Root cause: no automated alarm-to-work-order escalation system

**Must cite:** `incident_report_C-150_compressor.txt`

---

### Q4. Which assets have shown vibration above threshold?

**Expected answer (from inspection_records.csv):**
- **P-101** exceeded threshold twice:
  - April 2024: 5.6 mm/s (threshold 4.5) → **ALARM**
  - May 2024: 7.1 mm/s → **ALARM**
  - After repair (May 12): 2.3 mm/s → OK
- C-150 discharge temp was 142 °C in May 2024 (threshold 150, OK at that reading) but tripped in July
- No other vibration alarms in the CSV

---

### Q5. Who is responsible for the hot work permit in Unit 2 and what are the gas testing requirements?

**Expected answer (from safety_procedure_hot_work.txt SOP-SAF-014):**
- Area Authority: **A. Mehta** (issues permit, area control)
- HSE Inspector: **S. Nair** (gas testing verification + PPE audit)
- Executing Technician: **R. Sharma**
- Gas testing must confirm **< 10% LEL** before and during work
- Zone 1/Zone 2 areas require additional controls per **PESO hazardous area classification**
- Fire watch required during work and for **30 minutes afterward**

---

### Q6. What inspection finding was raised about V-200 and what action was taken?

**Expected answer (from email thread):**
- March inspection: relief valve set pressure measured at **18.5 bar** vs design set point **18.0 bar** — drifting high
- Wall thickness: **12.4 mm** (minimum allowable 11.0 mm) — vessel integrity OK
- Action: A. Mehta raised a **work order for bench test and re-certification** under **OISD-STD-106**
- Noted as the **second pressure-relief drift** this year → added relief-valve set-pressure trending to compliance review

---

### Q7. What parts were used to repair P-101?

**Expected answer:**
- **SKF 6310 bearing × 2**
- **John Crane Type 21 mechanical seal × 1**
- **Shell Gadus S2 V220 grease**

---

### Q8. What maintenance does the OEM manual recommend for P-101's shaft alignment?

**Expected answer (OEM manual Section 7.3):**
- Verify with **laser alignment tool** after any coupling work
- Acceptable parallel misalignment: **≤ 0.05 mm**
- Misalignment is a leading cause of **premature bearing wear and seal failure**
- The maintenance report confirms alignment was corrected to exactly 0.05 mm after the May 2024 repair

---

## Module 2 — Maintenance RCA

### RCA for P-101

**Expected output:**
```
Immediate cause:    Bearing spalling (outer race, SKF 6310 drive-end bearing)
Contributing:       Mechanical seal scoring (light, John Crane Type 21)
Root cause 1:       Shaft misalignment from coupling replacement (WO-2024-0188, Feb 2024)
Root cause 2:       Lubrication interval 6 months vs OEM 3 months
Evidence:           Vibration 7.1 mm/s (ALARM ×2 in inspection CSV), post-repair 2.3 mm/s
Recommendations:
  - Revise lubrication PM to 3-month cycle
  - Mandatory laser alignment after all coupling work
  - Continuous bearing temperature + vibration trending
Confidence:         HIGH (cross-document corroboration)
```

---

### RCA for C-150

**Expected output:**
```
Immediate cause:    Cracked 2nd-stage discharge valve plate → recirculation → thermal trip at 154°C
Contributing:       High TAN lubricant (degraded cooling); rod drop 0.48 mm (near threshold)
Root cause 1:       Valve plates at 9,200 hr (overdue vs 8,000 hr OEM interval)
Root cause 2:       No alarm-to-work-order escalation for rod drop trend
Evidence:           INC-2024-0731 report, inspection CSV (discharge temp 142°C May 2024)
Recommendations:
  - Reduce valve-plate interval to 6,000 hr for high-duty service
  - Automated escalation from condition monitoring to CMMS
  - Oil TAN trending monthly
Confidence:         HIGH
```

---

## Module 3 — Compliance Intelligence

### Full scan — expected scores per checklist item

| Framework | Requirement | Expected Status |
|---|---|---|
| OISD-STD-105 | Preventive maintenance for rotating equipment with defined intervals | **PARTIAL** — P-101 PM existed but interval was wrong (6M not 3M) |
| OISD-STD-106 | Pressure vessel & relief valve inspection + certification | **PARTIAL** — V-200 inspected but relief valve re-cert still pending (work order raised) |
| PESO | Hazardous area classification + licensing for flammable storage | **MET** — SOP-SAF-014 references PESO Zone 1/2 classification |
| Factory Act 1948 | Permit-to-work / LOTO for maintenance | **MET** — PTW-3391, PTW-4102, and SOP-SAF-014 all reference LOTO/PTW |
| Factory Act 1948 | Periodic safety inspections + PPE records | **PARTIAL** — PPE in SOP, inspections in CSV, but no explicit audit trail document |
| OISD-STD-118 | Incident reporting, investigation, root-cause closure | **MET** — INC-2024-0731 fully documented per OISD-STD-118 |

**Expected overall score:** ~65–70% (4 met or close, 2 partial)

---

## Module 4 — Knowledge Graph

### What nodes should exist after ingestion?

| Label | Key examples |
|---|---|
| Equipment | P-101, C-150, V-200, E-301 |
| Person | R. Sharma, A. Mehta, S. Nair, P. Verma |
| Location | Unit 2 (Gas Compression), Unit 3 (Crude Distillation), Unit 4 |
| Regulation | OISD-STD-105, OISD-STD-106, OISD-STD-118, PESO, Factory Act 1948 |
| Incident | INC-2024-0731 (C-150 trip) |
| Document | (one per ingested file) |

### What relationships should exist?

| Relationship | Example |
|---|---|
| MAINTAINED_BY | P-101 → R. Sharma / A. Mehta |
| LOCATED_AT | P-101, V-200 → Unit 3 |
| LOCATED_AT | C-150 → Unit 2 |
| HAS_INCIDENT | C-150 → INC-2024-0731 |
| REFERENCES_REGULATION | Documents → OISD-STD-105/106/118 |
| INVESTIGATED_BY | INC-2024-0731 → A. Mehta, S. Nair |
| REQUIRED_BY | Hot work procedure → PESO / Factory Act |

### Cross-document linking test

> **"Is P-101 linked to more than one document?"**

After ingesting all 6 files, P-101 should appear in **at least 3 documents**: maintenance report, OEM manual, and the hot work SOP (and indirectly the inspection CSV). The graph should have **one** P-101 node with 3+ `Document` neighbors — this proves MERGE-based cross-document deduplication works.

---

## Module 5 — Lessons Learned

### Expected patterns discovered

| Theme | Assets | Occurrences | What to look for |
|---|---|---|---|
| Lubrication interval deviation causing bearing failure | P-101 | 1 | Root cause from maintenance report |
| Overdue component replacement causing equipment trip | C-150 | 1 | Valve plates at 9,200 hr vs 8,000 hr OEM |
| Inspection finding not escalated to work order | C-150 | 1 | Rod drop noted 2 days before trip, no WO raised |

### Similarity search

> **"Find similar incidents to high temperature compressor trip"**

Expected top result: **INC-2024-0731** (C-150, 154°C trip on cracked valve plate) — semantic match on "high temperature" + "compressor" + "trip". Score should be >0.75.

---

## Demo-critical cross-document queries (use these with judges)

These are the ones that impress — the answer *cannot* come from a single document, so they prove the graph+RAG hybrid is doing real work:

1. **"What maintenance did P-101 need and did the OEM manual agree with what was done?"**
   - OEM says 3-month lube, laser alignment ≤0.05 mm
   - Maintenance report says they fixed both — confirms OEM compliance post-repair
   - Two documents, one coherent answer

2. **"Was the C-150 rod drop reading a warning sign, and was it acted on?"**
   - CSV shows 0.45 mm in May (OK), incident report shows 0.48 mm on July 26 (near threshold, not escalated)
   - The answer spans CSV + incident report + the gap (no work order) proves root cause

3. **"Which people are involved in both P-101 maintenance and V-200 inspection?"**
   - A. Mehta: WO-2024-0512 (P-101), V-200 email reply author
   - S. Nair: V-200 inspection (CSV + email), SOP-SAF-014 HSE inspector
   - Graph query — not in any single document

4. **"What compliance gaps exist and which asset is most exposed?"**
   - V-200 (relief valve re-cert pending) + P-101 (lubrication interval was wrong until May) = highest exposure
   - Crosses email + maintenance report + compliance checklist

---

## How to use this file during testing

1. Start the stack (`docker compose up -d`)
2. Ingest all 6 files via the upload UI
3. Open Copilot → paste each Q above → compare the answer against the expected facts
4. Open Compliance → run scan → verify status per table above
5. Open RCA → enter `P-101` and `C-150` → verify root causes match
6. Open Graph → verify node/relationship counts match the table above
7. **Red flag:** if any answer is missing the cross-document facts (e.g., copilot only cites one document for Q1), the hybrid retrieval or graph context is not working
