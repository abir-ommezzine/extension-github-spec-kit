# data-model.md

Entity: Expense
- `id`: string (generated via `Date.now().toString()`)
- `amount`: number (in user's currency, required, >0)
- `currency`: string (ISO code, default `USD`)
- `category`: string (optional)
- `description`: string (optional)
- `date`: string (ISO 8601 date, required)

Validation rules:
- `amount` must be a positive number
- `date` must be a valid ISO date not in the future (optional constraint)

State transitions: For this simple app, expenses are created and deleted; no soft-delete or edits initially (edits can be added later).
