## [Unreleased]

### Changed

- **GAS #86**: Promote all 16 Gameplay Ability System stubs to executed envelope.
  - `enable_gas_plugin`: persists GAS-active metadata on editor world package
  - `add_ability_system_component`: creates and registers UAbilitySystemComponent on target actor
  - `create_attribute_set`: creates UAttributeSet subobject on actor's ASC
  - `create_gameplay_ability`: creates UGameplayAbility Blueprint asset
  - `create_gameplay_effect`: creates UGameplayEffect Blueprint asset
  - `create_gameplay_cue`: creates UGameplayCueNotify_Static Blueprint asset
  - `bind_ability_input`: binds input component to ASC for ability activation
  - `grant_ability`: grants a GameplayAbility to actor's ASC via GiveAbility()
  - `configure_ability_activation`: persists activation policy metadata
  - `configure_ability_cooldown`: persists cooldown metadata
  - `configure_ability_cost`: persists cost metadata
  - `initialize_attribute`: initializes attribute value on ASC
  - `bind_attribute_change_event`: persists attribute change callback metadata
  - `link_gameplay_tag`: links gameplay tag to actor's ASC
  - `configure_gas_replication`: sets replication mode on ASC (Minimal/Mixed/Full)
  - `configure_gas_prediction`: persists prediction metadata

- **AI/Nav #84**: Promote all 23 AI/Navigation stubs to executed envelope.
  - BT: `add_behavior_tree_node`, `connect_behavior_tree_nodes`, `create_bt_task`, `create_bt_service`, `create_bt_decorator`
  - Blackboard: `set_blackboard_template` (creates UBlackboardData with configurable keys)
  - AI Controller: `set_ai_controller_behavior_tree`, `spawn_run_behavior_tree_node`
  - Perception: `configure_ai_sense_hearing`, `configure_ai_sense_damage`, `configure_ai_sense_team`
  - EQS: `configure_eqs_generator`, `configure_eqs_test`, `set_eqs_debug`
  - Navigation: `set_smart_nav_link`, `create_nav_area_class`, `set_recast_navmesh_details`
  - Mass Entity: `bridge_mass_entity`
  - StateTree: `create_state_tree`, `add_state_tree_state`, `add_state_tree_task`
  - Misc: `set_ai_behavior_tag`, `configure_cognitive_ai_controller`
