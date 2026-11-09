# Product Requirements Document (PRD)
## Simplified Single-Station Airspace Enhancements: Multi-Volume Control Areas & Self-Contained Exclusions

| Document Metadata | Details |
|---|---|
| **Document ID** | PRD-ATC-2026-CA01 |
| **Status** | Ready for Review / Sprint Planning |
| **Target Sprint** | Next Sprint |
| **Component Scope** | `radar-trainer/src/control_area.py`, `data/control_areas/*.json`, `frontend/src/` |
| **Related Documents** | `docs/CONTROL_AREA_DATA_HANDOFF.md`, `data/control_areas/VOCB.json`, `outputs/control-area-review/catalogue.md` |

---

## 1. Executive Summary & Objective

In the current radar simulator, **77 airports** have reviewed, live-monitored Control Areas (CTRs and CTAs), while **47 airports** remain quarantined as drafts in `outputs/control-area-review/`. 

A significant portion of these quarantined airports (including major traffic airports like **Mangaluru `VOML`**, **Nagpur `VANP`**, **Indore `VAID`**, **Jaipur `VIJP`**, **Vadodara `VABO`**, and **Surat `VASU`**) are stalled not because of missing official AIP data, but because of rigid schema/engine constraints in `src/control_area.py`:
1. Artificial prohibition of chained/nested exclusions.
2. Lack of a native radial annulus (ring) shape primitive.
3. Lack of support for local, self-contained exclusion cutouts (cross-airport or military zones).
4. Absence of a standardized JSON authoring pattern for stepped concentric altitude tiers.

### Architectural Core Principle: Single-Station Isolation
The simulator is designed as a **single-station radar trainer** focused on one radar position at a time (e.g., Coimbatore Approach, Jaipur Radar). There is **no inter-facility coordination, automated handoff across FIR boundaries, or distributed station network**.

Therefore, all airspace enhancements must remain **100% self-contained within each airport's `<ICAO>.json` file**, requiring:
- **No central airspace registry**
- **No cross-file dependency lookups**
- **No multi-coordinate projection managers**
- **No dynamic CSG (Constructive Solid Geometry) runtime engines**

---

## 2. User Stories & Problem Statements

### User Story 1: Handling Radar Rings / Annuli without Nested Exclusions (e.g. Mangaluru `VOML`)
> *As a radar trainee at Mangaluru (`VOML`), I need to see and be monitored within CTA Area B ($5500\text{ ft AMSL} \to \text{FL } 145$), which is defined between $25\text{ NM}$ and $50\text{ NM}$ from the aerodrome.*
- **Problem**: `control_area.py` only supports `circle` and single-ring `polygon`. Slicing an annulus into two semi-circular polygons with reverse arcs is fragile, while creating a 50 NM circle that excludes a 25 NM circle triggers the validator's `Nested exclusions are unsupported` exception if the 25 NM circle itself excludes the CTR.
- **Solution**: Native `shape: "annulus"` defined by `inner_radius_nm` and `outer_radius_nm`.

### User Story 2: Neighboring Aerodrome Cutouts without Cross-File Coupling (e.g. Jaipur `VIJP`)
> *As an approach controller at Jaipur (`VIJP`), I vector aircraft throughout Jaipur CTA 1, but must not control traffic inside Kishangarh CTR (`VIKG`), which is an enclave inside Jaipur's lateral sector.*
- **Problem**: In the AIP, Jaipur CTA 1 explicitly states: *"excluding airspace of Kishangarh CTR"*. Currently, Kishangarh is a separate airport profile (`VIKG`). Referencing `"VIKG:ctr"` fails `validate()`, while building a cross-airport loader introduces brittle multi-file loading dependencies.
- **Solution**: Self-contained exclusion volume embedded directly in `VIJP.json` with `"monitored": false`.

### User Story 3: Stepped Altitude Floors (e.g. Nagpur `VANP` & Indore `VAID`)
> *As a controller at Nagpur (`VANP`), aircraft climbing out within $25\text{ NM}$ should enter controlled airspace at $2100\text{ ft AMSL}$, whereas aircraft between $25–50\text{ NM}$ enter at $\text{FL } 55$, and beyond $50\text{ NM}$ enter at $\text{FL } 95$.*
- **Problem**: The AIP publishes this as a single named sector with prose describing concentric altitude steps. The current engine expects one `lower` and one `upper` limit per area object.
- **Solution**: Decompose the published prose sector into discrete, non-overlapping sibling tier volumes sharing a common display prefix (`"cta-tier1"`, `"cta-tier2"`, `"cta-tier3"`).

### User Story 4: Multi-Volume Hierarchical Exclusions (e.g. Surat `VASU`)
> *As an approach controller at Surat (`VASU`), CTA Area-B surrounds Area-A and excludes both the CTR and Area-A.*
- **Problem**: In `src/control_area.py`, line 51 explicitly throws `ValueError('Nested exclusions are unsupported')` if Area-A itself excludes the CTR, even though the runtime membership evaluator is already fully capable of evaluating multiple exclusions in parallel.
- **Solution**: Refine the validator to permit explicit exclusion lists containing any valid local base volume IDs (`"excludes": ["ctr", "cta-a"]`).

---

## 3. Detailed Feature Specifications

### Feature 1: Native Annulus Primitive (`shape: "annulus"`)

#### 1.1 JSON Schema Specification
Extend the `shape` union in `data/control_areas/<ICAO>.json`:
```json
{
  "id": "cta-b",
  "name": "Mangalore CTA B",
  "kind": "CTA",
  "classification": "D",
  "hours": "HO",
  "shape": "annulus",
  "center": [12.961944444444445, 74.88972222222222],
  "inner_radius_nm": 25.0,
  "outer_radius_nm": 50.0,
  "lower": { "reference": "AMSL", "value": 5500 },
  "upper": { "reference": "FL", "value": 145 },
  "excludes": []
}
```

#### 1.2 Validation Rules (`validate()`)
- `inner_radius_nm` and `outer_radius_nm` must be numbers where $0 < \text{inner\_radius\_nm} < \text{outer\_radius\_nm} \le 500$.
- `center` must be a valid WGS84 coordinate pair `[latitude, longitude]`.

#### 1.3 Mathematical Evaluation & Boundaries
- **Point Containment** in `membership()`:
  $$d = \text{hypot}(x - c_x, y - c_y)$$
  $$\text{inside\_annulus} = (\text{inner\_radius\_nm} \le d \le \text{outer\_radius\_nm})$$
- **Boundary Outline Sampling** in `boundary()`:
  Return points along the outer circle ($0^\circ \to 360^\circ$ at $1^\circ$ steps), followed by points along the inner circle in reverse direction ($360^\circ \to 0^\circ$).

---

### Feature 2: Self-Contained Exclusion / Cutout Volumes (`monitored: false`)

#### 2.1 JSON Schema Specification
Add an optional boolean field `"monitored"` (defaults to `true` if omitted):
```json
{
  "id": "kishangarh-ctr",
  "name": "Kishangarh CTR (Excluded)",
  "kind": "CTR",
  "classification": "D",
  "hours": "HO",
  "monitored": false,
  "lower": { "reference": "SFC" },
  "upper": { "reference": "FL", "value": 80 },
  "excludes": [],
  "shape": "circle",
  "center": [26.6067, 74.8206],
  "radius_nm": 15.0,
  "source": {
    "file": "Airport Layouts/Kishangarh/AD 2.1VIKG.pdf",
    "section": "AD 2.17",
    "evidence": "Kishangarh CTR: 15 NM radius centered at 263624N 0744914E, SFC to FL 80. Embedded as unmonitored cutout for VIJP CTA 1."
  }
}
```
In the parent volume (`VIJP` CTA 1):
```json
{
  "id": "cta-1",
  "name": "Jaipur CTA 1",
  "excludes": ["ctr", "kishangarh-ctr"]
}
```

#### 2.2 Evaluation Semantics (`evaluate()` in `control_area.py`)
1. Lateral and vertical containment `base[e]` is computed for all areas, including unmonitored ones.
2. In parent volume evaluation: if `base["kishangarh-ctr"]` is `True`, the parent volume is suppressed (`True in excluded`).
3. In final status determination: **unmonitored volumes are excluded from `inside` and `uncertain` reporting**:
   ```python
   for a in self.areas:
       if a.get('monitored') is False:
           continue  # Used solely for 3D geometric subtraction; not station jurisdiction
       ...
   ```
4. **Result**: An aircraft inside Kishangarh CTR is correctly reported as `"outside"` Jaipur's jurisdiction, rather than falsely claiming Jaipur Approach has control or falsely reporting inside.

#### 2.3 Scope UI Rendering
- Volumes with `monitored: false` are rendered on the radar scope with a distinct styling:
  - Line color: Muted slate/grey (`#5a6e65` or dashed pattern).
  - Label: `"<Name> (Excluded)"`.

---

### Feature 3: Concentric Tiered Altitude Decomposition

#### 3.1 JSON Authoring Pattern
For airspaces like Nagpur (`VANP`) and Indore (`VAID`), do not alter simulation math. Standardize the JSON authoring to decompose the stepped sector into discrete geographic volumes:
```
Nagpur Control Area (AIP)
├── cta-tier1 (0 - 25 NM Circle)   : 2100 ft AMSL to FL 460  [excludes: ctr]
├── cta-tier2 (25 - 50 NM Annulus) : FL 55 to FL 460         [excludes: none]
└── cta-tier3 (50 - 100 NM Annulus): FL 95 to FL 460         [excludes: none]
```

#### 3.2 Benefits
- **Zero code changes**: Sibling volumes are evaluated in parallel by existing code.
- **Precise feedback**: Trainees see exactly which altitude tier the aircraft currently occupies.

---

### Feature 4: Refined Multi-Volume Exclusion Validation

#### 4.1 Specification Update in `src/control_area.py`
Replace the restrictive check in lines 50–52:
```python
# CURRENT CODE (Lines 51-52):
if any(next(b for b in areas if b['id'] == e)['excludes'] for a in areas for e in a['excludes']):
    raise ValueError('Nested exclusions are unsupported')
```
with an explicit acyclic dependency verification:
```python
# PROPOSED REFINED CHECK:
# Ensure exclusions do not contain circular references (A -> B -> A).
def check_cycles(area_id, visited, stack):
    visited.add(area_id)
    stack.add(area_id)
    area = next(a for a in areas if a['id'] == area_id)
    for neighbor in area.get('excludes', []):
        if neighbor not in visited:
            if check_cycles(neighbor, visited, stack): return True
        elif neighbor in stack:
            return True
    stack.remove(area_id)
    return False

visited, stack = set(), set()
for a in areas:
    if a['id'] not in visited:
        if check_cycles(a['id'], visited, stack):
            raise ValueError('Circular exclusion reference detected')
```

#### 4.2 Runtime Evaluation Support
In `evaluate()`, the current logic:
```python
base = {a['id']: membership(a) for a in self.areas}
```
already precomputes exact 3D membership for all volumes. By permitting `"excludes": ["ctr", "cta-a"]`, any outer volume cleanly carves out both interior volumes in a single evaluation step.

---

## 4. Impact Analysis & Target Airports Unlocked

Implementing these 4 targeted enhancements directly unlocks **12 major airports** currently quarantined in `outputs/control-area-review/`:

| Airport | ICAO | Primary Blocker Today | Unlocked By | Post-Enhancement Status |
|---|---|---|---|---|
| **Mangaluru** | `VOML` | CTA Area B is an annulus (25–50 NM) | Feature 1 (`annulus`) | **Reviewed** (CTR + CTA A + CTA B) |
| **Nagpur** | `VANP` | Stepped concentric altitudes | Feature 3 (Tier decomposition) | **Reviewed** (CTR + 3 CTA Tiers) |
| **Indore** | `VAID` | Stepped concentric altitudes | Feature 3 (Tier decomposition) | **Reviewed** (CTR + 2 CTA Tiers) |
| **Surat** | `VASU` | Area-B excludes Area-A | Feature 4 (Refined exclusions) | **Reviewed** (CTR + CTA A + CTA B) |
| **Jaipur** | `VIJP` | Excludes Kishangarh CTR (`VIKG`) | Feature 2 (`monitored: false`) | **Reviewed** (CTR + CTA 1 with Kishangarh cutout) |
| **Vadodara** | `VABO` | Area 1 & Area 2 combined in table | Feature 1 + Separate Tiers | **Reviewed** (CTR + Area 1 + Area 2) |
| **Rewa** | `VERW` | Overlapping vertical extents | Feature 4 (Refined exclusions) | **Reviewed** (CTR + CTA) |
| **Bhavnagar** | `VABV` | Multi-volume outer circle | Feature 1 (`annulus`) | **Reviewed** (CTR + CTA) |
| **Shirdi** | `VASD` | Arc cutouts | Feature 4 (Refined exclusions) | **Reviewed** (CTR + CTA) |
| **Cochin** | `VOCI` | Military restricted areas VOR 191 | Feature 2 (`monitored: false`) | **Reviewed** (CTR + CTA A + CTA B with Naval cutouts) |
| **Hyderabad**| `VOHS` | Military flying zones cutout | Feature 2 (`monitored: false`) | **Reviewed** (CTR + CTA with Hakimpet/Begumpet cutouts) |
| **Delhi** | `VIDP` | Excludes Jewar CTR (`VIND`) | Feature 2 (`monitored: false`) | **Reviewed** (CTR + CTA with Jewar cutout) |

*(Note: Airports clipped by unquantified international borders without coordinates, such as `VEAT` Agartala and `VIAR` Amritsar, will rightfully remain drafts until official FIR border coordinates are supplied).*

---

## 5. Technical Implementation Work Breakdown

### Sprint Task List

- [ ] **Task 1 (Backend - Schema & Validation)**:
  - Update `src/control_area.py:validate()`:
    - Add validation for `shape == "annulus"`.
    - Add optional `"monitored": bool` field validation.
    - Replace `Nested exclusions are unsupported` with acyclic graph cycle validation.
- [ ] **Task 2 (Backend - Geometric Evaluation)**:
  - Update `src/control_area.py:boundary()` to return sampled vertices for `shape == "annulus"`.
  - Update `src/control_area.py:membership()` with fast-path radial distance check for `annulus`.
  - Update `src/control_area.py:evaluate()` to filter out `monitored: false` from reported `inside` / `uncertain` area names.
- [ ] **Task 3 (Data Migration)**:
  - Migrate and validate the 12 unlocked airports (`VOML`, `VANP`, `VAID`, `VASU`, `VIJP`, `VABO`, `VERW`, `VOCI`, `VOHS`, `VIDP`, etc.) into `data/control_areas/<ICAO>.json`.
  - Run `scripts/validate_control_areas.py` to confirm zero schema or arc endpoint errors.
- [ ] **Task 4 (Frontend UI & Radar Scope)**:
  - Update `frontend/src/types.ts` to include `monitored?: boolean`.
  - Update `frontend/src/radar.ts` to render unmonitored cutout boundaries with dashed stroke styling.
- [ ] **Task 5 (Quality Assurance & Regression Testing)**:
  - Add unit tests in `tests/test_control_area.py`:
    - `test_annulus_membership_and_bounds()`
    - `test_unmonitored_cutout_volume_suppression()`
    - `test_chained_exclusion_resolution()`
  - Verify complete test suite execution (`pytest tests/`).

---

## 6. Acceptance Criteria

1. **Schema Integrity**:
   - `scripts/validate_control_areas.py` validates all newly added airport files with zero errors.
   - Any circular dependency in exclusions (`A` excludes `B`, `B` excludes `A`) is rejected with a clear error.
2. **Evaluator Correctness**:
   - For an annulus volume, an aircraft inside the hole ($r < r_{\text{inner}}$) evaluates to `"outside"`; an aircraft between radii evaluates to `"inside"`.
   - For an unmonitored cutout volume (e.g., Kishangarh in Jaipur scope), an aircraft inside the cutout does not trigger `"inside"` for either the parent CTA or the cutout.
3. **Zero Cross-File Dependencies**:
   - Moving or deleting `VIKG.json` has **zero** effect on `VIJP.json` loading or simulation runtime.
4. **Visual Verification**:
   - The radar scope draws both concentric annuli and exclusion cutout outlines cleanly without visual artifacting or fill corruption.
5. **Regression Safety**:
   - All 569 existing test cases in `pytest tests/` continue to pass without failure.
