# Google Sheets Adapter

Google Sheets is an optional human control surface for Mirror Delivery. JSON remains canonical.

Use `director-state` to export the current projection, paste it into `JSON_IO!A2`, and use the bridge to populate the accessible dashboard. A selected AI Bridge row can be exported as director-command JSON, validated by the engine, and only then translated into an engine operation.

The adapter must never overwrite a campaign save directly.

## Privacy

The companion Apps Script uses the active spreadsheet only. It has no `DriveApp`, no file/folder enumeration, and no external HTTP requests. The included manifest requests only `spreadsheets.currentonly` and `script.container.ui`.
