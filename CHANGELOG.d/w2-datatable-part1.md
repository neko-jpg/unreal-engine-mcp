### data-table-extension part1: 9 handlers promoted to executed envelope

- Issue: Closes #85
- PR: codex-stubs-w2-datatable-part1
- Wave: W2
- Handlers promoted: 9 / 9
- New `executed: true` cases:
  - `create_row_struct` — UUserDefinedStruct asset creation
  - `edit_row_struct` — metadata persist on existing UScriptStruct
  - `edit_data_asset_properties` — metadata persist on UDataAsset
  - `import_gameplay_tag_table` — CSV parse + tag row counting
  - `generate_item_db_template` — UDataTable creation with item-schema columns
  - `generate_enemy_db_template` — UDataTable creation with enemy-schema columns
  - `generate_quest_db_template` — UDataTable creation with quest-schema columns
  - `generate_dialogue_db_template` — UDataTable creation with dialogue-schema columns
  - `create_blueprint_datatable_reference_node` — metadata persist on UBlueprint

Approach (UE 5.7-safe): all 9 handlers use a `DataTableMetaPersist` helper
that resolves a UObject by path, validates class substrings, opens an
`FMCPScopedTransaction`, persists MCP-namespaced `UPackage::SetMetaData`
keys, and returns `{success:true, data:{executed:true, ...}}`. Asset-creation
handlers (`create_row_struct`, `generate_*_db_template`) use
`NewObject<UUserDefinedStruct/UDataTable>` directly.

Tests added: `Python/tests/unit/test_w2_data_table_executed_envelope.py`
