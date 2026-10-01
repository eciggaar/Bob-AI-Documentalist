## Counting items from tool output
- Never state a count from memory or estimation.
- When a tool returns a list, output it as a consistently formatted numbered list (1., 2., 3., ...)
  covering every item in the response, in order.
- Only after the list, state the total, and it must equal the last number
  in your list.
- Do not mention a count before the list.
- The flat numbered list must always come first. Any grouped, categorised, or summarised
  view may only follow after the complete flat numbered list and its verified total.

## Counting items from MCP tool JSON responses
- The authoritative count for any MCP tool response that returns a JSON array is
  **always `len(array)`** — the number of top-level objects in the returned array.
- Never derive a total by summing category sub-counts, claimed counts in labels,
  or any number that was not directly computed from the raw array length.
- When grouping items into categories after the flat list:
  - Count each category by iterating its actual members, not by reading a label.
  - Verify that the sum of all category counts equals the previously established
    `len(array)` total. If they do not match, stop and report the discrepancy
    before presenting any grouped view.
- When a property (e.g. `isSystemOwned`, `isSearchable`, `isHidden`) is used to
  split a list into two groups, the two group counts must add up to `len(array)`.
  State the equation explicitly: `A + B = total`.
- These checks apply equally to raw JSON pasted by the user and to JSON returned
  by a live tool call.
