---
name: class-inventory
description: Use when the user wants a complete inventory of document classes in the IBM Content Services repository — grouped by domain (HR, Contracts/Legal, Tax Administration, System/Technical) with verified counts. Activate on phrases like "document class inventory", "list all classes", "what classes do we have", or "class overview".
---

# Document Class Inventory

Produce a grouped, count-verified inventory of all document classes in the IBM Content Services repository.

## Step 1 — Fetch the raw class list

Call `list_all_classes` with `root_class: "Document"`.
1. Parse the JSON array returned by the API.
2. Record `N = len(classes)`. **Do not estimate or hardcode `N`.**
3. Keep the full list in memory for deterministic filtering.

## Step 2 — Apply deterministic grouping rules

Assign every item in the list to **exactly one** domain using these explicit rules in order:

### 1. HR
- Symbolic name starts with `HR` (e.g., `HRDocument`).

### 2. Contracts / Legal
- Symbolic name is `Contract` or starts with `Contract`.

### 3. Tax Administration
- Symbolic name starts with any of:
  `Aangifte`, `BTW`, `Belasting`, `Bezwaar`, `Beroep`, `Correctie`, `Douane`, `Fiscaal`, `Invoer`, `Jaarrekening`, `Kwartaal`, `Loonbelasting`, `Motorrijtuigen`, `Origine`, `Transit`, `Uitvoer`, `Vereenvoudigde`, `Voorlopig`, `Voortaxatie`, `Winst`, `Aanslag`.

### 4. System / Technical
- All remaining classes that do not match HR, Contracts/Legal, or Tax Administration rules (e.g., `CodeModule`, `Document`, `Email`, `EntryTemplate`, `FormData`, `FormPolicy`, `FormTemplate`, `MsResource`, `PreferencesDocument`, `RecordsTemplate`, `ScenarioDefinition`, `Simulation`, `StoredSearch`, `WebContentTemplate`, `WebFormTemplate`, `WorkflowDefinition`, `XMLPropertyMappingScript`).

## Step 3 — Strict Count & Reconciliation (Pre-Output Verification)

Before rendering the output:
1. Count the exact number of entries placed in each group:
   - `hr_count = len(hr_classes)`
   - `contract_count = len(contract_classes)`
   - `tax_count = len(tax_classes)`
   - `sys_count = len(sys_classes)`
2. Compute `total = hr_count + contract_count + tax_count + sys_count`.
3. Count the number of markdown rows actually formatted in each table. Ensure header numbers (e.g., `### Tax Administration (X)`) strictly match the exact row count in that specific table.
4. **Assert `total == N`**.
   - If `total != N`, identify which items were duplicated or omitted, reconcile before presenting.

## Step 4 — Present the results

**Output only the following — nothing else:**

1. A `## Document Class Inventory` heading.
2. One markdown table per group (with heading and row count), columns: **Display Name** | **Symbolic Name**. Sort each table alphabetically by Display Name.
3. A single verification line at the end, computed strictly from the reconciled counts:

```
✅ Verification: {hr_count} (HR) + {contract_count} (Contracts / Legal) + {tax_count} (Tax Administration) + {sys_count} (System / Technical) = {total} total (API returned: {N})
```

**Do NOT output any intermediate reasoning**, grouping logic narration, prefix lists, symbolic-name sorting steps, or any text other than the heading, the four tables, and the verification line.
