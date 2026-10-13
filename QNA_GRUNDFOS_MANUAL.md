# Grundfos CR/CRI/CRN Manual — Q&A Ground Truth

Source: `sample_data/real_world/grundfos_CR_pump_manual.pdf`
Manual covers: Grundfos CR, CRI, CRN multistage in-line centrifugal pumps, 0.37–75 kW.
English section: pp. 4–26 (sections 1–10). The rest of the PDF is multilingual translations and distributor contacts — not useful for Q&A.

---

## Section 6 — Maintenance & Servicing

### Q1. Are the pump bearings and shaft seal on a Grundfos CR pump maintenance-free?

**Expected answer:**
- **Pump bearings and shaft seal: YES — maintenance-free** (Section 6.3.1)
- **Motor bearings: depends on motor type**
  - Motors without grease nipples → maintenance-free
  - Motors with grease nipples → must be lubricated with **high-temperature, lithium-based grease** (see fan cover label)
- Seasonal note: if motor is idle for **more than 6 months**, grease the motor when taking it out of service

**Cite:** Section 6.3 Maintaining the product / Section 6.3.1 Pump / Section 6.3.2 Motor

---

### Q2. What are the motor bearing replacement and lubrication intervals for a Grundfos CR pump?

**Expected answer (from Section 6.3.2 table):**

**Bearing replacement intervals — 2-pole motors:**

| Motor size | 40 °C | 45 °C | 50 °C | 55 °C | 60 °C |
|---|---|---|---|---|---|
| 0.37–0.75 kW | 18,000 hr | — | — | — | — |
| 1.1–7.5 kW | 20,000 hr | 15,500 hr | 12,500 hr | 10,000 hr | 7,500 hr |

**Lubrication intervals — larger motors (2-pole):**

| Motor size | 40 °C | 45 °C | 50 °C | 55 °C | 60 °C |
|---|---|---|---|---|---|
| 11–18.5 kW | 4,500 hr | 3,400 hr | 2,500 hr | 1,700 hr | 1,100 hr |
| 22 kW | 4,000 hr | 3,100 hr | 2,300 hr | 1,500 hr | 1,000 hr |
| 30–55 kW | 4,000 hr | 3,000 hr | 2,000 hr | 1,500 hr | — |
| 75 kW | 2,000 hr | 1,500 hr | 1,000 hr | 500 hr | — |

**4-pole motors: intervals are TWICE those for 2-pole motors.**

If ambient temperature is below 40 °C, use the 40 °C values.

---

### Q3. What grease type should be used for Grundfos CR motor bearing lubrication?

**Expected answer:**
- **High-temperature, lithium-based grease**
- Exact specification is on the **fan cover label** of the specific motor
- Only applies to motors fitted with grease nipples; motors without grease nipples are maintenance-free

---

## Section 4 — Startup & Operation

### Q4. What is the maximum number of starts per hour for a Grundfos CR pump?

**Expected answer (Section 4.2):**

| Motor size | Max starts/hour |
|---|---|
| 0.37–2.2 kW | **250** |
| 3–4 kW | **100** |
| 5.5–11 kW | **50** |
| 18.5–22 kW | **40** |
| 30 kW | **90** |
| 37 kW | **50** |
| 45 kW | **80** |
| 55 kW | **50** |
| 75 kW | **50** |

---

### Q5. When should the bypass valve on a CR 1s–5 pump be used, and when must it be closed?

**Expected answer (Section 4 startup procedure + Section 7.1):**
- Open the bypass valve **during startup** — it connects inlet and outlet sides to make filling/venting easier
- Close it **once operation is stable**
- If pumping liquids containing air at pressures **below 6 bar**: leave bypass valve open
- **Must be closed if operating pressure constantly exceeds 6 bar** — high liquid velocity causes material wear at the opening
- For frost protection / draining: screw the bypass valve out against the stop before removing drain plug

---

### Q6. What shaft seal run-in procedure does the manual require?

**Expected answer (Section 4.1):**
- The shaft seal faces are lubricated by the **pumped liquid** — some leakage is expected during run-in
- A run-in period is required when:
  - Starting the pump **for the first time**
  - Installing a **new shaft seal**
  - Any time **operating conditions change** (a new run-in starts)
- Under normal conditions, leaking liquid will **evaporate** — no visible leakage after run-in
- **Do not run the pump dry** — this will damage bearings and shaft seal

---

## Section 9 — Technical Data / Operating Limits

### Q7. What is the maximum liquid temperature for a Grundfos CR pump, and what happens above it?

**Expected answer (Section 9.1.1 + 9.1.3):**
- Max liquid temperature varies by shaft seal type:
  - HQQE seal: **−40 to +120 °C** (0.37–45 kW motors)
  - HQQV seal: **−20 to +90 °C**
  - HBQE seal: **0 to +120 °C** (55–75 kW motors)
  - HBQV seal: **0 to +90 °C**
- Above 120 °C: **"not suitable for long periods"** — causes periodic noise and reduced pump life
- CIP cleaning (CRI/CRN with EPDM H-type seal): max **64 °C** for max **15 minutes**

---

### Q8. What is the effect of high ambient temperature or altitude on motor loading?

**Expected answer (Section 9.1.2 + Fig. 19):**
- If ambient temperature or altitude exceeds limits, **motor must not be fully loaded** (overheating risk)
- Example: IE3 motor at **70 °C ambient** → max load **89 %** of rated output
- Example: pump at **4,750 m above sea level** → also max load **89 %**
- Both conditions simultaneously: multiply derating factors → **0.89 × 0.89 = 0.79** (79% of rated output)
- Motor ambient temperature limits:
  - 0.37–0.55 kW Grundfos MG: **+40 °C**, 1,000 m max altitude
  - 0.75–22 kW Grundfos MG IE3: **+60 °C**, 3,500 m max altitude
  - 30–75 kW Siemens IE3: **+55 °C**, 2,750 m max altitude

---

### Q9. What minimum inlet pressure is required and how is suction lift calculated?

**Expected answer (Section 9.1.4):**
- Suction lift formula: **H = Pb × 10.2 − NPSH − Hf − Hv − Hs**
  - Pb = barometric pressure (bar), set to 1 bar
  - NPSH = Net Positive Suction Head from pump curve (m head)
  - Hf = friction loss in inlet pipe (m head)
  - Hv = vapour pressure of liquid (m head)
  - Hs = safety margin = **minimum 0.5 m head**
- Worked example: CR 15 at 15 m³/h, 60 °C liquid → H = 3.5 m head suction lift = 0.343 bar

---

## Section 3 — Installation

### Q10. What foundation specifications does the Grundfos manual require?

**Expected answer (Sections 3.1.3 + 3.1.4 + 3.1.5):**
- Concrete foundation: **mass at least 1.5× total pump mass**
- Foundation length and width: **200 mm larger** than base plate on each side
- Motors ≥ 37 kW: foundation always **1.5 × 1.5 m minimum** (Lf × Bf)
- Surface must be **absolutely level and even**; align with shims if needed
- For quiet/vibration-sensitive areas: foundation mass up to **5× pump mass**
- Bolt quality: **minimum class 8.8**
- The pump can be installed **vertically or horizontally** — but motor must not fall below horizontal plane or be installed upside down

---

### Q11. What are the safe operating limits to avoid running against a closed valve?

**Expected answer:**
- **DANGER — never run the pump against a closed outlet valve**
- Listed as a WARNING with consequence: "Too high pressure and leakage — Death or serious personal injury"
- Included in Section 4.3 Operating the product

---

## Section 3.2 — Electrical

### Q12. What motor protection does the Grundfos manual require?

**Expected answer (Section 3.2):**
- External main switch that can be **locked in OFF position**
- Motor-protective circuit breaker with **IEC trip class 10 or 20** — Grundfos recommends **trip class 20**
- Current setting must match **nominal current on the motor nameplate**
- For frequency converter operation with cable > 25 m or mains > 460 V: **sine-wave filters required**
- Motors from frame size 225 (≥ 45 kW/2-pole): **insulated bearings** recommended

---

## Section 8 — Fault Finding

### Q13. What does the Grundfos fault-finding guide say about pump noise?

**Expected answer (Section 8, Fault 9):**

| Cause | Remedy |
|---|---|
| Cavitation | Check inlet conditions |
| Pump does not rotate freely — incorrect shaft position / frictional resistance | Adjust the pump shaft |
| Frequency converter operation | See Section 3.2.5 |

---

### Q14. What are the causes of shaft seal leakage on a Grundfos CR pump?

**Expected answer (Section 8, Fault 8):**
- **Shaft seal is defective → replace the shaft seal**
- Normal: some leakage is expected during run-in period; under normal conditions it evaporates
- Abnormal: persistent leakage after run-in = seal defective

---

### Q15. The pump runs but gives no water — what should be checked?

**Expected answer (Section 8, Fault 6):**
1. Inlet pipe or pump blocked by impurities → clean
2. Foot or non-return valve blocked in closed position → repair
3. Leakage in inlet pipe → repair
4. Air in inlet pipe or pump → check inlet conditions
5. Motor running in **wrong direction of rotation** → change direction of rotation

---

## Section 5 — Product & Application

### Q16. What liquids is the Grundfos CR pump NOT suitable for?

**Expected answer (Sections 5.2.2 + 5.2.1):**
- **Not suitable for:** flammable, combustible, or explosive liquids (DANGER — fire/explosion)
- **Not suitable for:** liquids which can chemically attack pump materials
- **Not suitable for:** liquids with solid particles or fibres
- **CRN variant** (full stainless steel): for systems requiring all liquid-contact parts to be high-grade stainless steel
- CR/CRI/CRN are designed for thin, **clean, non-flammable, non-combustible, non-explosive** liquids

---

## Cross-document questions (Grundfos manual + sample data)

These are the interesting ones for the demo — they span the Grundfos OEM manual and your other 6 documents.

### Q17. Both the Grundfos CR manual and the KSB P-101 OEM manual discuss bearing lubrication. What are the similarities and differences?

**Expected answer (cross-document):**

| Aspect | Grundfos CR (this manual) | KSB Etanorm P-101 (OEM excerpt) |
|---|---|---|
| Pump bearings | Maintenance-free | SKF 6310 — grease every **3 months** |
| Lube type | High-temp lithium-based grease | Shell Gadus S2 V220 (NLGI 2 lithium-complex) |
| Bearing spec | Varies by motor size/temp | SKF 6310, max 80 °C |
| Interval basis | Operating hours (e.g. 20,000 hr at 40°C for 1.1–7.5 kW) | Calendar interval (3 months for continuous duty >60°C ambient) |
| Consequence of under-greasing | Bearing damage | Spalling — exactly what happened to P-101 |

Key insight: both manuals use lithium-based grease; the Grundfos uses hour-based intervals while KSB uses calendar intervals. P-101 was on a 6-month calendar cycle — the maintenance report confirms this was the root cause of the bearing failure.

---

### Q18. The Grundfos manual says shaft seal leakage is normal during run-in. The P-101 maintenance report mentions light seal scoring. Are these the same issue?

**Expected answer:**
- Grundfos: new seal run-in leakage is normal and expected — evaporates under normal conditions
- P-101 report: "light scoring on seal faces" found during bearing inspection — the seal was replaced as a precaution
- **Not the same issue** — run-in leakage is expected; scoring is physical wear damage (likely from misalignment + vibration)
- The Grundfos manual would classify P-101's scoring as Fault 8 (defective seal → replace), which is exactly what was done

---

### Q19. Can the Grundfos CR pump be used in a hot work zone (Unit 2 or Unit 3)?

**Expected answer (cross-document: Grundfos manual + SOP-SAF-014):**
- Grundfos: CR/CRI/CRN must NOT be used for flammable, combustible or explosive liquids
- If installed in a flammable area, explosion-proof motor variant must be used (manual references ATEX/Ex-rated instructions)
- SOP-SAF-014 covers Unit 2 (Gas Compression) and Unit 3 (Crude Distillation) as hot work zones requiring PESO hazardous area classification
- Answer: a standard Grundfos CR would **not** be suitable for Zone 1/Zone 2 flammable areas without explosion-proof certification — the manual explicitly marks this as a DANGER

---

## What to verify in Cortex after ingestion

| Check | Expected |
|---|---|
| Entity extracted: Equipment | `Grundfos CR`, `Grundfos CRI`, `Grundfos CRN` (or similar) |
| Doc type classified as | `oem_manual` or `safety_procedure` |
| Chunks count | ~129 (confirmed in previous parsing test) |
| Q2 bearing intervals | Exact numbers from the table — if LLM hallucinates these, retrieval failed |
| Q7 max temperature | 120 °C — specific number must come from doc, not hallucination |
| Q17 cross-document | Must cite BOTH this PDF and the KSB OEM excerpt — only possible if both are ingested |

## Red flag — what signals retrieval failure

| Symptom | Likely cause |
|---|---|
| Bearing intervals wrong (e.g. "12 months" instead of "20,000 hours") | LLM hallucinating; this doc was not chunked/retrieved |
| Max temperature given as "80°C" (from KSB P-101 doc) | Wrong document retrieved; chunk with Grundfos data not ranked |
| Q17 only cites one manual | Graph cross-linking not working |
| Fault table not reproduced | Section 8 chunks too far in doc; embedding retrieval cut off |
