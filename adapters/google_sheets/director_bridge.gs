function onOpen() {
  SpreadsheetApp.getUi().createMenu('Mirror Delivery JSON')
    .addItem('Prepare JSON I/O', 'mirrorPrepareJsonIO')
    .addItem('Import director state', 'mirrorImportDirectorState')
    .addItem('Export selected command', 'mirrorExportSelectedCommand')
    .addToUi();
}

function mirrorPrepareJsonIO() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName('JSON_IO');
  if (!sh) sh = ss.insertSheet('JSON_IO');
  sh.getRange('A1').setValue('DIRECTOR_STATE_JSON');
  sh.getRange('B1').setValue('DIRECTOR_COMMAND_JSON');
  sh.getRange('A1:B1').setFontWeight('bold');
  sh.setColumnWidth(1, 520);
  sh.setColumnWidth(2, 520);
  sh.getRange('A2:B2').setWrap(true);
}

function mirrorImportDirectorState() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  mirrorPrepareJsonIO();
  const raw = String(ss.getSheetByName('JSON_IO').getRange('A2').getValue() || '').trim();
  if (!raw) throw new Error('Paste director-state JSON into JSON_IO!A2 first.');
  const state = JSON.parse(raw);
  const control = ss.getSheetByName('00_CONTROL');
  if (control) {
    control.getRange('B6').setValue(state.campaign && state.campaign.campaign_id || '');
    control.getRange('B7').setValue(state.campaign && state.campaign.turn || 0);
    control.getRange('D7').setValue(state.campaign && state.campaign.state_version || 0);
    control.getRange('B8').setValue(((state.mission && state.mission.world_time_minutes) || 0) / 60);
    control.getRange('B9').setValue(state.mission && state.mission.current_location_id || '');
    control.getRange('D9').setValue('Imported projection');
  }
  ss.toast('Director projection imported. Engine memory remains authoritative.', 'Mirror Delivery', 5);
}

function mirrorExportSelectedCommand() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  mirrorPrepareJsonIO();
  const bridge = ss.getSheetByName('15_AI_BRIDGE');
  if (!bridge) throw new Error('15_AI_BRIDGE is not present.');
  const row = bridge.getActiveRange().getRow();
  if (row < 31 || row > 80) throw new Error('Select a command row between 31 and 80.');
  const v = bridge.getRange(row, 1, 1, 9).getDisplayValues()[0];
  let payload = {};
  if (v[4]) payload = JSON.parse(v[4]);

  const approvalMap = {'Not Required':'not_required','Pending Human':'pending_human','APPROVED':'approved','Denied':'denied'};
  const typeMap = {'Set Destination':'set_destination','Advance Scene':'advance_scene','Advance Clock':'advance_clock','Resolve Action':'resolve_action','Update Entity':'update_entity','Add Ledger Event':'append_ledger_event','Activate MIR':'activate_mir','Seal MIR':'seal_mir','Create Encounter':'create_encounter','Close Mission':'close_mission','Add Fact':'add_fact'};
  const type = typeMap[v[2]] || v[2];
  const status = approvalMap[v[5]] || 'pending_human';
  const command = {
    schema_version:'1.0.0', command_id:v[0], type:type,
    requested_by:v[1] === 'AI Director' ? 'ai_director' : 'human_gm',
    target_id:v[3] || null, payload:payload,
    approval:{required:type === 'activate_mir', status:status, approved_by:status === 'approved' ? 'human_gm' : null, approved_at:null},
    expected_state_version:null, idempotency_key:null
  };
  ss.getSheetByName('JSON_IO').getRange('B2').setValue(JSON.stringify(command, null, 2));
}
