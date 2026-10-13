# GraphQL Metadata Recreation Set

This folder contains a staged set of GraphQL files that (re)create the full repository metadata schema:
the [`HRDocument`](../HR_Document_Class_Description.md) class with all its properties, the 30 Dutch Tax Administration document classes, and the domain-specific properties for those Tax classes.

---

## Files

| # | File | Type | Purpose |
|---|---|---|---|
| 01 | [`01-choice-lists.graphql`](01-choice-lists.graphql) | mutation | Creates choice lists for business-controlled HR string fields (JobRole, Department, etc.) |
| 02 | [`02-property-templates.graphql`](02-property-templates.graphql) | mutation | Creates all custom property templates for `HRDocument` |
| 03 | [`03-class-definition.graphql`](03-class-definition.graphql) | mutation | Creates the `HRDocument` class and binds the property templates from file 02 |
| 04 | [`04-tax-class-definitions.graphql`](04-tax-class-definitions.graphql) | mutation | Creates the 30 Tax document class shells (name + description only, no properties yet) |
| 05 | [`05-update-consolidation-candidates.graphql`](05-update-consolidation-candidates.graphql) | mutation | Rewrites the descriptions of the 5 consolidation-candidate Tax classes to plain Dutch so that their overlap with canonical classes is semantically apparent without being stated explicitly |
| 06 | [`06-update-hrdocument-description.graphql`](06-update-hrdocument-description.graphql) | mutation | Sets the Dutch descriptive text on the `HRDocument` class itself |
| 07 | [`07-count-hrdocument-properties.graphql`](07-count-hrdocument-properties.graphql) | **query** | Retrieves all property definitions on `HRDocument` for verification — **not a mutation; use `curl` directly** |
| 09 | [`09-tax-property-templates.graphql`](09-tax-property-templates.graphql) | mutation | Creates 30 Dutch property templates for the Tax domain (e.g. `Belastingjaar`, `RSIN`, `BSN`, `IsCorrectie`, `Kenteken`, `DouaneAangifteNummer`) each with a Dutch descriptive text |
| 10 | [`10-tax-class-properties.graphql`](10-tax-class-properties.graphql) | mutation | Binds the Tax property templates to all 30 Tax classes (≤ 10 properties each). The 5 consolidation-candidate classes receive a strict property subset of their canonical counterpart, making the redundancy visible by schema inspection |
| 11 | [`11-contract-class-properties.graphql`](11-contract-class-properties.graphql) | mutation | Deletes the old `Contract` class (which carried HR-domain templates), creates 8 Dutch Contract property templates, and recreates the class with only those 8 domain-specific properties |

> **Why are files 05 and 06 not in the original execution order?**
> They were added after the initial setup as follow-on patches. File 05 rewrites the 5 duplicate-candidate class descriptions to subtler Dutch prose (removing any explicit "consolidate me" wording), and file 06 adds a Dutch description to `HRDocument` itself. Both are **idempotent** — safe to run on an existing repository without side effects.

---

## Runner

Use [`run_graphql.py`](run_graphql.py) to execute any mutation file.

**Setup — do this once:**
1. Create either `graphql/.env` or `.env` in the project root.
2. Add these three values:
   ```
   USERNAME=your-username
   PASSWORD=your-password
   SERVER_URL=https://your-server/content-services-graphql/graphql
   ```

**Run a file:**
```
python graphql/run_graphql.py graphql/<filename>.graphql
```

The runner splits the file into individual `mutation` blocks and sends them one by one. It prints success/failure per mutation and exits non-zero if any mutation fails.

> File 07 is a **query**, not a mutation. The runner only handles mutations. Use `curl` or the GraphQL explorer to run it.

---

## Execution order

### Scenario A — Fresh environment (nothing exists yet)

Run every file in sequence:

```
python graphql/run_graphql.py graphql/01-choice-lists.graphql
python graphql/run_graphql.py graphql/02-property-templates.graphql
python graphql/run_graphql.py graphql/03-class-definition.graphql
python graphql/run_graphql.py graphql/04-tax-class-definitions.graphql
python graphql/run_graphql.py graphql/05-update-consolidation-candidates.graphql
python graphql/run_graphql.py graphql/06-update-hrdocument-description.graphql
python graphql/run_graphql.py graphql/09-tax-property-templates.graphql
python graphql/run_graphql.py graphql/10-tax-class-properties.graphql
python graphql/run_graphql.py graphql/11-contract-class-properties.graphql
```

**Why this order?**

| Step | Depends on |
|---|---|
| 01 — choice lists | nothing |
| 02 — HR property templates | choice list IDs from 01 |
| 03 — HRDocument class | HR property template symbolic names from 02 |
| 04 — Tax class shells | nothing (independent) |
| 05 — Tax description patches | Tax classes must exist (04) |
| 06 — HRDocument description patch | HRDocument class must exist (03) |
| 09 — Tax property templates | nothing |
| 10 — Tax class property bindings | Tax classes (04) + Tax property templates (09) |
| 11 — Contract class rebuild | no class instances may exist; run before uploading lab documents |

---

### Scenario B — HR already set up, only Tax properties are missing

The Tax class shells are already in the repository but have no properties yet:

```
python graphql/run_graphql.py graphql/09-tax-property-templates.graphql
python graphql/run_graphql.py graphql/10-tax-class-properties.graphql
```

---

### Scenario E — Rebuild the Contract class only

Use this when the Contract class needs to be replaced with the proper Contracts-domain version.
**Prerequisite:** all documents filed under the `Contract` class must be deleted first — FileNet will refuse to delete a class that has instances.

```
python graphql/run_graphql.py graphql/11-contract-class-properties.graphql
```

> The file handles the full sequence: delete old class → create 8 property templates → recreate class with only those 8 properties.

---

### Scenario C — Everything exists, apply description patches only

The classes and properties are all in place but you want to update the class descriptions:

```
python graphql/run_graphql.py graphql/05-update-consolidation-candidates.graphql
python graphql/run_graphql.py graphql/06-update-hrdocument-description.graphql
```

Both are idempotent — running them again on an already-patched repository is safe.

---

### Scenario D — Verify HRDocument property count (read-only check)

File 07 is a query, not a mutation. Run it directly with `curl`:

```bash
curl -s -u "$USERNAME:$PASSWORD" \
  -H "Content-Type: application/json" \
  -d @graphql/07-count-hrdocument-properties.graphql \
  "$SERVER_URL"
```

---

## Tax domain consolidation candidates

Five Tax classes are intentionally seeded as consolidation candidates for the lab exercise. An AI Documentalist should identify them when asked *"which classes look like duplicates or legacy entries?"*

| Consolidation candidate | Canonical counterpart | Redundancy signal |
|---|---|---|
| `AangifteBTWKwartaal` | `AangifteBTW` | Identical purpose; only filing frequency differs. Has 4 properties vs. 7 on the canonical class — missing `Belastingtijdvak` and `IsCorrectie`. |
| `CorrectieAangifteLoonheffingen` | `AangifteLoonheffingen` | Correction variant with no differentiating data model. Has 3 properties vs. 6 — missing `Belastingtijdvak`, `AangifteDatum`, and `IsCorrectie`. |
| `VoortaxatieVennootschapsbelasting` | `AangifteVennootschapsbelasting` | Preliminary vs. final filing. Has 3 properties vs. 6 — missing `AangifteDatum`, `VerschuldigdBedrag`, and `IsVoorlopig`. |
| `VereenvoudigdeDouaneaangifte` | `Douaneaangifte` | Simplified AEO variant. Has 3 properties vs. 6 — missing `GoederenomschrijvingCode`, `VerschuldigdBedrag`, and `IsAEOProcedure`. |
| `MotorrijtuigenbelastingAangifte` | `AangifteBPM` | Near-identical vehicle tax data model. Has 3 properties vs. 6 — missing `AangifteDatum`, `CO2UitstootGrKm`, and `BelastingsoortCode`. |

The intentional property gap makes these classes detectable by schema inspection without any explicit "TODO" comment in the description.

---

## Scope included

**HR domain:**
- Custom class: `HRDocument`
- Property groups: Employee Information, Employment Details, Organizational Structure, Dates, SAP integration, Salesforce integration, DocuFlow integration, Document Classification

**Tax domain:**
- 30 document subclasses across: BTW, Inkomstenbelasting, Loonheffingen, Vennootschapsbelasting, Overige belastingen, Naleving & Controle, Financiële verslaggeving, Douane & Handel
- 30 Dutch property templates with descriptive texts

**Not included:**
- Inherited base `Document` system properties
- Tenant-specific security or lifecycle policies
- Storage policies, ACLs, markings, subscriptions, workflow wiring

---

## Required replacements before execution

- `CHOICE_LIST_ID_*` placeholders in [`02-property-templates.graphql`](02-property-templates.graphql) — replace with actual choice list IDs created by file 01
- Any mutation name or input field name that differs in your tenant's GraphQL schema

---

## Important assumptions

- `admCreateChoiceList`, `admCreatePropertyTemplate`, `admCreateClassDefinition`, and `admUpdateClassDefinition` exist in the tenant schema
- `STRING`, `BOOLEAN`, `OBJECT`, `DATE`, `INTEGER`, and `DOUBLE` are valid `dataType` enum values
- `SINGLE` is the correct single-cardinality enum value
- String property templates can bind a choice list inline via `choiceList { identifier: "..." }`

---

## Source

Primary source for HR properties: [`HR_Document_Class_Description.md`](../HR_Document_Class_Description.md)
