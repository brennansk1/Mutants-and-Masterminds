# heroforge-mm-streamlit/ui_sections/power_builder_ui.py

import streamlit as st
import copy
import math
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core_engine import CoreEngine, CharacterState, RuleData, PowerDefinition # type: ignore
else:
    CoreEngine = Any
    CharacterState = Dict[str, Any]
    RuleData = Dict[str, Any]
    PowerDefinition = Dict[str, Any]

# --- Helper for unique keys in loops ---
def _uk_pb(base: str, *args): # Power Builder Unique Key
    # Ensure all args are string-castable and clean for keys
    str_args = [str(a).replace(":", "_").replace(" ", "_") for a in args if a is not None]
    return f"pb_{base}_{'_'.join(str_args)}"

# --- Helper UI Rendering Functions for Power Builder Sub-sections ---

def _render_modifier_parameter_input(
    st_obj: Any, 
    mod_rule: Dict[str, Any], 
    mod_config_entry: Dict[str, Any], 
    form_key_prefix: str, 
    char_state: CharacterState, 
    rule_data: RuleData
):
    """Renders dynamic input widgets for a modifier's parameters."""
    param_type = mod_rule.get('parameter_type', 'text')
    param_prompt = mod_rule.get('parameter_prompt', f"Details for {mod_rule['name']}:")
    param_key_ui = _uk_pb(form_key_prefix, mod_rule['id'], "param_val")

    if param_type == "text":
        mod_config_entry['userInput'] = st_obj.text_input(param_prompt, value=mod_config_entry.get('userInput', ''), key=param_key_ui)
    elif param_type == "text_long":
        mod_config_entry['userInput'] = st_obj.text_area(param_prompt, value=mod_config_entry.get('userInput', ''), height=75, key=param_key_ui)
    elif param_type == "text_complex": # Could be used for detailed descriptions like Ritualist spells
        mod_config_entry['userInput'] = st_obj.text_area(param_prompt, value=mod_config_entry.get('userInput', ''), height=100, key=param_key_ui)
    elif param_type == "number_rank": # For ranks of the modifier itself, if different from main 'rank' field
        mod_config_entry['userInput'] = st_obj.number_input(param_prompt, value=mod_config_entry.get('userInput', 1), min_value=1, max_value=mod_rule.get('maxRanks',20), step=1, key=param_key_ui)
    elif param_type == "number_dc":
        mod_config_entry['userInput'] = st_obj.number_input(param_prompt, value=mod_config_entry.get('userInput', 10), min_value=0, step=1, key=param_key_ui)
    elif param_type == "select_skill" or param_type == "select_skill_expertise_ritualist" or param_type == "select_skill_technology_inventor":
        skill_opts = {"": "Choose Skill..."}
        skill_list_for_select = rule_data.get('skills', [])
        if param_type == 'select_skill_expertise_ritualist':
            skill_list_for_select = [s for s in skill_list_for_select if s.get('name','').lower().startswith('expertise: magic') or s.get('name','').lower().startswith('expertise: occult')]
        elif param_type == 'select_skill_technology_inventor':
            skill_list_for_select = [s for s in skill_list_for_select if s.get('name','').lower() == 'technology']
        skill_opts.update({sk['id']: sk['name'] for sk in skill_list_for_select})
        current_skill_val = mod_config_entry.get('userInput','')
        mod_config_entry['userInput'] = st_obj.selectbox(param_prompt, options=list(skill_opts.keys()), format_func=lambda x: skill_opts.get(x, "Choose..."), index=list(skill_opts.keys()).index(current_skill_val) if current_skill_val in skill_opts else 0, key=param_key_ui)
    elif param_type == "select_power_for_link":
        linkable_powers = {"": "Select Power to Link..."}
        # Exclude the current power being edited from linkable options
        editing_power_id = st_obj.session_state.power_form_state.get('editing_power_id')
        for p_other in char_state.get('powers', []):
            if p_other.get('id') != editing_power_id:
                linkable_powers[p_other.get('id')] = p_other.get('name')
        current_linked_id = mod_config_entry.get('userInput', '')
        mod_config_entry['userInput'] = st_obj.selectbox(param_prompt, options=list(linkable_powers.keys()), format_func=lambda x: linkable_powers.get(x, "Choose..."), index=list(linkable_powers.keys()).index(current_linked_id) if current_linked_id in linkable_powers else 0, key=param_key_ui)
    elif param_type == "select" and mod_rule.get('parameter_options'):
        current_param_val = mod_config_entry.get('userInput')
        param_opts = mod_rule['parameter_options']
        param_idx = param_opts.index(current_param_val) if current_param_val in param_opts else 0
        mod_config_entry['userInput'] = st_obj.selectbox(param_prompt, options=param_opts, index=param_idx, key=param_key_ui)
    # Add more parameter types as defined in ruleData (e.g., for Area shapes, Duration choices)
    else: # Default to text if type not specifically handled yet
        mod_config_entry['userInput'] = st_obj.text_input(param_prompt, value=mod_config_entry.get('userInput', ''), key=param_key_ui)


def _render_senses_config_ui(st_obj: Any, form_state_power: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("Configure Senses")
    st_obj.caption("Select individual sense abilities. The Power Rank for Senses is nominal; cost is sum of chosen abilities.")
    sense_ability_rules = rule_data.get('power_senses_config', [])
    sense_options = {s['id']: f"{s['name']} (Cost: {s['cost']} PP)" for s in sense_ability_rules}
    
    current_senses_config = form_state_power.get('sensesConfig', [])
    
    # Group by senseType for better UI if desired
    form_state_power['sensesConfig'] = st_obj.multiselect(
        "Select Sense Abilities:",
        options=list(sense_options.keys()),
        format_func=lambda x: sense_options.get(x, "Unknown Sense"),
        default=current_senses_config,
        key=_uk_pb(form_state_power.get('editing_power_id', 'new'), "senses_multisel")
    )
    current_senses_cost = sum(s_rule.get('cost',0) for s_id in form_state_power['sensesConfig'] for s_rule in sense_ability_rules if s_rule['id'] == s_id)
    st_obj.write(f"Cost from selected senses: {current_senses_cost} PP")
    form_state_power['rank'] = 0 # Nominal rank for Senses main power

def _render_immunity_config_ui(st_obj: Any, form_state_power: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("Configure Immunities")
    st_obj.caption("Select immunities. The Power Rank for Immunity is nominal; cost is sum of chosen immunities.")
    immunity_rules = rule_data.get('power_immunities_config', [])
    
    immunity_categories = {}
    for im_rule in immunity_rules:
        cat = im_rule.get('category', 'General')
        if cat not in immunity_categories: immunity_categories[cat] = []
        immunity_categories[cat].append(im_rule)

    selected_immunities = form_state_power.get('immunityConfig', [])
    
    for category, im_list in sorted(immunity_categories.items()):
        st_obj.markdown(f"**{category}**")
        for im_rule in sorted(im_list, key=lambda x: x.get('cost',0)): # Sort by cost within category
            is_selected = im_rule['id'] in selected_immunities
            if st_obj.checkbox(f"{im_rule['name']} ({im_rule['cost']} PP)", value=is_selected, key=_uk_pb(form_state_power.get('editing_power_id', 'new'), "imm", im_rule['id'])):
                if not is_selected: selected_immunities.append(im_rule['id'])
            elif is_selected:
                selected_immunities = [sid for sid in selected_immunities if sid != im_rule['id']]
    form_state_power['immunityConfig'] = list(set(selected_immunities))
    current_immunity_cost = sum(im_rule.get('cost',0) for im_id in form_state_power['immunityConfig'] for im_rule in immunity_rules if im_rule['id'] == im_id)
    st_obj.write(f"Cost from selected immunities: {current_immunity_cost} PP")
    form_state_power['rank'] = 0 # Nominal rank

def _render_variable_config_trait_builder_ui(
    st_obj: Any, 
    var_config_entry: Dict[str, Any], # The specific configuration being built
    config_index: int, # Index of this configuration
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine,
    power_form_key_prefix: str # Base key for the main power form
):
    """Renders UI for adding/editing ONE trait within a Variable configuration."""
    st_obj.markdown("---")
    st_obj.markdown(f"**Building Trait for '{var_config_entry.get('configName', f'Config {config_index+1}')}'**")

    # This is a "mini-builder" - it needs its own temporary state for the trait being built
    # For simplicity, we'll use dict access directly on var_config_entry['current_editing_trait']
    if 'current_editing_trait' not in var_config_entry:
        var_config_entry['current_editing_trait'] = {'type': 'Power'} # Default

    trait_builder_state = var_config_entry['current_editing_trait']
    
    trait_type_options = ["Power", "EnhancedAbility", "EnhancedSkill", "EnhancedDefense", "EnhancedAdvantage", "CustomText"]
    trait_builder_state['type'] = st_obj.selectbox(
        "Trait Type to Add to Config:", trait_type_options, 
        index=trait_type_options.index(trait_builder_state.get('type', "Power")),
        key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "trait_type")
    )

    if trait_builder_state['type'] == "Power":
        trait_builder_state['name'] = st_obj.text_input("Power Name (in config):", value=trait_builder_state.get('name', "Config Power"), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "pwr_name"))
        
        eff_opts = {"": "Select Effect..."}
        eff_opts.update({eff['id']: eff['name'] for eff in rule_data.get('power_effects', [])})
        trait_builder_state['baseEffectId'] = st_obj.selectbox("Base Effect:", options=list(eff_opts.keys()), format_func=lambda x: eff_opts.get(x), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "pwr_effect"))
        trait_builder_state['rank'] = st_obj.number_input("Rank (in config):", min_value=1, value=trait_builder_state.get('rank',1), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "pwr_rank"))
        
        # Simplified Modifier selection for Variable Config Power: Multiselect of common ones or text area
        trait_builder_state['modifiers_text_desc'] = st_obj.text_area("Modifiers (e.g., 'Ranged Extra, Limited: Fire Only'):", value=trait_builder_state.get('modifiers_text_desc',''), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "pwr_mods_text"))
        # TODO: A more robust UI would allow structured modifierConfig here. For "all features" this is needed.
        # For now, cost will be hard for engine to parse from this text. We will need user to assert cost.
        trait_builder_state['pp_cost_in_variable'] = st_obj.number_input("Asserted PP Cost for this Power in Config:", min_value=0, value=trait_builder_state.get('pp_cost_in_variable',0), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "pwr_asserted_cost"))


    elif trait_builder_state['type'] == "EnhancedAbility":
        ab_opts = {"": "Select Ability..."}; ab_opts.update({ab['id']:ab['name'] for ab in rule_data.get('abilities',[])})
        trait_builder_state['traitId'] = st_obj.selectbox("Ability:", options=list(ab_opts.keys()), format_func=lambda x: ab_opts.get(x), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "enhab_id"))
        trait_builder_state['enhancementAmount'] = st_obj.number_input("Enhancement Amount (+ ranks):", min_value=1, value=trait_builder_state.get('enhancementAmount',1), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "enhab_amt"))
        # Engine will calculate cost

    # ... Implement similar UI for EnhancedSkill, EnhancedDefense, EnhancedAdvantage ...
    
    elif trait_builder_state['type'] == "CustomText":
        trait_builder_state['name'] = st_obj.text_input("Trait Description (in config):", value=trait_builder_state.get('name', "Custom Trait"), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "cust_name"))
        trait_builder_state['pp_cost_in_variable'] = st_obj.number_input("Asserted PP Cost for this Custom Trait:", min_value=0, value=trait_builder_state.get('pp_cost_in_variable',0), key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "cust_asserted_cost"))


    if st_obj.button("Add Trait to This Configuration", key=_uk_pb(power_form_key_prefix, "varcfg", config_index, "add_trait_btn")):
        if 'configTraits' not in var_config_entry: var_config_entry['configTraits'] = []
        
        # Calculate cost for this specific trait using engine (if not purely asserted)
        current_trait_def = copy.deepcopy(trait_builder_state)
        if trait_builder_state['type'] != "CustomText" and 'pp_cost_in_variable' not in trait_builder_state : # Only if not asserted for complex powers
            cost_for_this_trait, _ = engine._calculate_cost_and_validate_trait_for_variable_or_ally(
                current_trait_def, 
                char_state.get('powerLevel',10), 
                char_state.get('abilities',{}),
                char_state.get('powers',[])
            )
            current_trait_def['pp_cost_in_variable'] = cost_for_this_trait
        
        var_config_entry['configTraits'].append(current_trait_def)
        var_config_entry['current_editing_trait'] = {'type': 'Power'} # Reset for next trait
        # No direct st.rerun here, parent form submission will handle it or main power form needs to update form_state

def _render_variable_configurations_ui(
    st_obj: Any, 
    form_state_power: Dict[str, Any], # This is st.session_state.power_form_state
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine
):
    st_obj.subheader("Define Variable Configurations")
    st_obj.caption("Detail different sets of traits this Variable power can manifest. Each configuration's total PP cost (calculated by engine) cannot exceed the Variable Pool.")
    variable_pool_display = (form_state_power.get('rank', 0) * 5)
    st_obj.info(f"Available Variable Pool for configurations: **{variable_pool_display} PP**")

    if 'variableConfigurations' not in form_state_power: form_state_power['variableConfigurations'] = []
    
    configs_to_keep = []
    for i, config_entry in enumerate(form_state_power['variableConfigurations']):
        with st_obj.container():
            st_obj.markdown(f"--- \n**Configuration #{i+1}**")
            cols_cfg_header = st_obj.columns([0.8, 0.2])
            config_entry['configName'] = cols_cfg_header[0].text_input(f"Name", value=config_entry.get('configName', f'Form {i+1}'), key=_uk_pb(form_state_power.get('editing_power_id','new'), "varcfg_name", i))
            
            # Display traits in this config
            if config_entry.get('configTraits'):
                st_obj.markdown("**Traits in this Configuration:**")
                for t_idx, trait in enumerate(config_entry.get('configTraits',[])):
                    # Display trait name, details, and its engine-calculated cost
                    # (Need to store calculated cost on trait when added by _render_variable_config_trait_builder_ui)
                    t_cost = trait.get('pp_cost_in_variable', 'N/A')
                    st_obj.markdown(f"- {trait.get('name', trait.get('type','Trait'))} (Rank {trait.get('rank',trait.get('enhancementAmount','N/A')) if 'rank' in trait or 'enhancementAmount' in trait else ''}) - Cost: {t_cost} PP")
            
            # "Mini-builder" UI to add more traits to *this specific* configuration
            with st_obj.expander("Add/Edit Traits for this Configuration", expanded=False):
                 _render_variable_config_trait_builder_ui(st_obj, i, config_entry, char_state, rule_data, engine, form_state_power.get('editing_power_id','new'))

            # Recalculate and display total cost for this config based on its internal traits
            # This requires engine to sum costs of traits in config_entry['configTraits']
            # For now, we'll rely on the user also inputting a total for the config if we don't fully calculate
            # But the goal is engine calculation.
            
            # Let's assume the engine calculates it during the main recalculate if configTraits is populated
            config_engine_cost = config_entry.get('calculated_config_cost_engine', 0) # Populated by engine
            if config_engine_cost > variable_pool_display:
                st_obj.error(f"Config Cost ({config_engine_cost} PP) exceeds Variable Pool ({variable_pool_display} PP)!", icon="⚠️")
            else:
                st_obj.success(f"Config Cost: {config_engine_cost} PP / {variable_pool_display} PP Pool", icon="✅")


            if cols_cfg_header[1].button("Remove Config", key=_uk_pb(form_state_power.get('editing_power_id','new'), "varcfg_remove", i), type="secondary"):
                # Will be removed by not appending to configs_to_keep
                pass
            else:
                configs_to_keep.append(config_entry)
    
    form_state_power['variableConfigurations'] = configs_to_keep # Update list if items removed

    if st_obj.button("Add New Configuration Slot", key=_uk_pb(form_state_power.get('editing_power_id','new'), "varcfg_add_slot")):
        form_state_power['variableConfigurations'].append({'configName': f'Config {len(form_state_power["variableConfigurations"])+1}', 'configTraits': [], 'current_editing_trait': {'type':'Power'}})
        st_obj.rerun() # Rerun to show new slot


def _render_ally_creation_stat_block_ui(
    st_obj: Any, 
    form_state_power: Dict[str, Any], # For context like editing_power_id for keys
    ally_data_ref: Dict[str,Any], # Direct reference to the ally data block to be modified
    allotted_pp: int,
    ally_type_name: str # "Summon", "Duplicate"
):
    st_obj.subheader(f"Define {ally_type_name} Details")
    st_obj.info(f"This {ally_type_name} is built using **{allotted_pp} PP** from the power's rank.")

    ally_data_ref['name'] = st_obj.text_input(f"{ally_type_name} Name/Type:", value=ally_data_ref.get('name', f"My {ally_type_name}"), key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "name"))
    ally_data_ref['pl_for_ally'] = st_obj.number_input(f"{ally_type_name}'s Power Level (for reference):", min_value=0, value=ally_data_ref.get('pl_for_ally', char_state.get('powerLevel',10) - 2), key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "pl"))
    
    st_obj.markdown("**Key Abilities (Ranks):**")
    ally_abs = ally_data_ref.get('abilities_summary', {ab['id']: 0 for ab in rule_data.get('abilities', [])})
    ab_cols = st_obj.columns(4)
    for i, ab_id_key in enumerate(["STR", "STA", "AGL", "DEX", "FGT", "INT", "AWE", "PRE"]):
        ab_name_disp = next((ab['name'] for ab in rule_data.get('abilities',[]) if ab['id'] == ab_id_key), ab_id_key)
        ally_abs[ab_id_key] = ab_cols[i % 4].number_input(f"{ab_name_disp}", value=ally_abs.get(ab_id_key,0), min_value=-5, max_value=20, step=1, key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "ab", ab_id_key))
    ally_data_ref['abilities_summary'] = ally_abs

    ally_data_ref['key_defenses'] = st_obj.text_input(f"{ally_type_name}'s Key Defenses (e.g., Tough 8, Dodge 6):", value=ally_data_ref.get('key_defenses',''), key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "def"))
    ally_data_ref['key_skills'] = st_obj.text_area(f"{ally_type_name}'s Key Skills (e.g., Stealth +10):", value=ally_data_ref.get('key_skills',''), height=75, key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "skills"))
    ally_data_ref['key_powers_advantages'] = st_obj.text_area(f"{ally_type_name}'s Key Powers/Advantages:", value=ally_data_ref.get('key_powers_advantages',''), height=100, key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "pwr_adv"))
    
    ally_data_ref['cost_pp_asserted_by_user'] = st_obj.number_input(
        f"User-Asserted Total PP for this {ally_type_name}'s Build:", min_value=0,
        value=ally_data_ref.get('cost_pp_asserted_by_user',0), 
        key=_uk_pb(form_state_power.get('editing_power_id','new'), ally_type_name, "asserted_cost"),
        help=f"Must be <= {allotted_pp} PP. Engine will validate this sum."
    )
    if ally_data_ref['cost_pp_asserted_by_user'] > allotted_pp:
        st_obj.error(f"Asserted cost ({ally_data_ref['cost_pp_asserted_by_user']}) exceeds allotted pool ({allotted_pp}) for this {ally_type_name}!")


# --- Main Power Builder Form Rendering Function ---
def render_power_builder_form(
    st_obj: Any, 
    char_state: CharacterState, # Main character state for context
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, # To update main char_state['powers']
    power_form_state: Dict[str, Any], # This is st.session_state.power_form_state
    generate_id_func: Callable[[str], str]
):
    form_key_prefix = power_form_state.get('editing_power_id', 'new_power') # Unique prefix for keys in this form instance

    with st_obj.form(key=_uk_pb("power_form", form_key_prefix), clear_on_submit=False): # Persist form state until explicitly saved/reset
        if power_form_state.get('editing_power_id'):
            st_obj.subheader(f"Editing Power: {power_form_state.get('name', '')}")
        else:
            st_obj.subheader("Add New Power")

        # --- Basic Power Info ---
        power_form_state['name'] = st_obj.text_input("Power Name:", value=power_form_state.get('name', 'New Power'), key=_uk_pb(form_key_prefix, "name"))
        
        effect_options = {"": "Select Base Effect..."}
        effect_options.update({eff['id']: eff['name'] for eff in rule_data.get('power_effects', [])})
        current_effect_id = power_form_state.get('baseEffectId', "")
        effect_keys_list = list(effect_options.keys())
        effect_idx = effect_keys_list.index(current_effect_id) if current_effect_id in effect_keys_list else 0
        
        new_base_effect_id = st_obj.selectbox(
            "Base Effect:", options=effect_keys_list, format_func=lambda x: effect_options.get(x),
            index=effect_idx, key=_uk_pb(form_key_prefix, "base_effect")
        )
        if new_base_effect_id != current_effect_id:
            power_form_state['baseEffectId'] = new_base_effect_id
            # Reset specific configs if base effect changes
            power_form_state['sensesConfig'] = []
            power_form_state['immunityConfig'] = []
            power_form_state['variableConfigurations'] = []
            power_form_state['current_ally_stats'] = get_default_ally_stat_block()
            # May need to reset rank or set a default based on new effect type
            st_obj.experimental_rerun() # Rerun to show new context

        selected_base_effect_rule = next((e for e in rule_data.get('power_effects', []) if e['id'] == power_form_state.get('baseEffectId')), None)

        # --- Rank Input (conditional based on effect type) ---
        show_std_rank = True
        if selected_base_effect_rule:
            if selected_base_effect_rule.get('isSenseContainer') or selected_base_effect_rule.get('isImmunityContainer'):
                show_std_rank = False; power_form_state['rank'] = 0
            elif selected_base_effect_rule.get('isVariableContainer'):
                power_form_state['rank'] = st_obj.number_input("Variable Power Rank:", min_value=1, value=power_form_state.get('rank',1), key=_uk_pb(form_key_prefix, "var_rank"))
                show_std_rank = False
            elif selected_base_effect_rule.get('isTransformContainer'):
                # Scope selection determines base CPR, rank is separate
                # ... (Transform scope selectbox as per previous app.py) ...
                # power_form_state['transform_scope_cost_per_rank'] = ...
                power_form_state['rank'] = st_obj.number_input("Transform Rank:", min_value=1, value=power_form_state.get('rank',1), key=_uk_pb(form_key_prefix, "trans_rank"))
                show_std_rank = False
            elif selected_base_effect_rule.get('isCreateEffect'):
                power_form_state['rank'] = st_obj.number_input("Create Effect Rank:", min_value=1, value=power_form_state.get('rank',1), key=_uk_pb(form_key_prefix, "create_rank"))
                show_std_rank = False
            elif selected_base_effect_rule.get('isAllyEffect'): # Summon/Duplication
                power_form_state['rank'] = st_obj.number_input(f"{selected_base_effect_rule.get('name')} Rank:", min_value=1, value=power_form_state.get('rank',1), key=_uk_pb(form_key_prefix, "ally_eff_rank"))
                show_std_rank = False
            elif selected_base_effect_rule.get('isEnhancementEffect'):
                # Rank for Enhanced Trait is the 'enhancementAmount'
                # ... (UI for selecting trait category, trait ID, enhancementAmount) ...
                # power_form_state['enhancementAmount'] = st_obj.number_input(...)
                # power_form_state['rank'] = power_form_state['enhancementAmount']
                st_obj.warning("Enhanced Trait config UI to be fully detailed here.")
                show_std_rank = False

        if show_std_rank:
            power_form_state['rank'] = st_obj.number_input("Power Rank:", min_value=1, max_value=30, value=power_form_state.get('rank',1), key=_uk_pb(form_key_prefix, "std_rank"))

        # --- Contextual Measurement Display ---
        temp_pwr_def_for_measure = copy.deepcopy(power_form_state) # Use current form state
        measurement_str = engine.get_power_measurement_details(temp_pwr_def_for_measure)
        if measurement_str: st_obj.caption(measurement_str)

        # --- Effect-Specific Configuration UIs ---
        if selected_base_effect_rule:
            if selected_base_effect_rule.get('isSenseContainer'):
                _render_senses_config_ui(st_obj, power_form_state, rule_data)
            elif selected_base_effect_rule.get('isImmunityContainer'):
                _render_immunity_config_ui(st_obj, power_form_state, rule_data)
            elif selected_base_effect_rule.get('isVariableContainer'):
                _render_variable_configurations_ui(st_obj, power_form_state, char_state, rule_data, engine)
            elif selected_base_effect_rule.get('isAllyEffect'): # Summon/Duplication
                allotted_pp = power_form_state.get('rank',0) * selected_base_effect_rule.get('grantsAllyPointsFactor',15)
                # Ensure ally_notes_and_stats_structured exists in power_form_state
                if 'ally_notes_and_stats_structured' not in power_form_state:
                    power_form_state['ally_notes_and_stats_structured'] = get_default_ally_stat_block()
                _render_ally_creation_stat_block_ui(st_obj, power_form_state, power_form_state['ally_notes_and_stats_structured'], allotted_pp, selected_base_effect_rule.get('name','Creation'))
            # ... Add elif for Create, Transform specific inputs if any beyond modifiers ...

        # --- Comprehensive Modifier UI ---
        st_obj.subheader("Modifiers (Extras & Flaws)")
        # ... (Full dynamic modifier selection and configuration UI from previous response,
        #      using _render_modifier_parameter_input helper. Manages power_form_state['modifiersConfig']) ...
        st_obj.warning("Full dynamic Modifier UI needs to be implemented here as per prior detailed plans.")


        # --- Array Configuration UI ---
        st_obj.subheader("Array Configuration")
        # ... (UI for Is AE, AE Of, Is Array Base, Array ID, Is Dynamic Array, as per previous) ...
        # This updates fields like power_form_state['isAlternateEffectOf'], ['arrayId'], etc.
        # If 'isDynamicArray' is checked, ensure 'mod_dynamic_array' is added to modifiersConfig.
        st_obj.warning("Full Array Configuration UI needs to be implemented here.")

        # --- Linked Combat Skill ---
        # ... (UI for power_form_state['linkedCombatSkill'] as per previous) ...
        st_obj.warning("Linked Combat Skill UI needs to be implemented here.")


        # --- Live Cost Preview ---
        st_obj.markdown("---")
        # Create a temporary power definition from the current form state for costing
        preview_power_def = copy.deepcopy(power_form_state)
        # Remove temporary UI state fields if any, ensure it matches PowerDefinition structure
        preview_power_def.pop('editing_power_id', None) 
        preview_power_def.pop('current_ally_stats', None) # This is for UI building, not direct costing
        preview_power_def.pop('current_variable_config_trait_builder', None)
        
        cost_details_preview = engine.calculate_individual_power_cost(preview_power_def, char_state.get('powers',[]))
        st_obj.markdown(f"**Estimated Power Cost: {cost_details_preview.get('totalCost',0)} PP**")
        st_obj.caption(f" (Cost/Rank: {cost_details_preview.get('costPerRankFinal','N/A')}, Breakdown: Base {cost_details_preview.get('costBreakdown',{}).get('base',0)}, Extras {cost_details_preview.get('costBreakdown',{}).get('extras_cpr',0)}, Flaws {cost_details_preview.get('costBreakdown',{}).get('flaws_cpr',0)}, Flat {cost_details_preview.get('costBreakdown',{}).get('flat_total',0)})")


        # --- Form Actions ---
        col_save, col_reset = st_obj.columns(2)
        if col_save.form_submit_button("💾 Save Power to Character", type="primary"):
            # Construct final power object from power_form_state
            final_power_data: PowerDefinition = {
                'id': power_form_state.get('editing_power_id') or generate_id_func("pwr_"),
                'name': power_form_state['name'],
                'baseEffectId': power_form_state['baseEffectId'],
                'rank': power_form_state['rank'],
                'modifiersConfig': power_form_state.get('modifiersConfig', []),
                'sensesConfig': power_form_state.get('sensesConfig', []),
                'immunityConfig': power_form_state.get('immunityConfig', []),
                'variableDescriptors': power_form_state.get('variableDescriptors', ""),
                'variableConfigurations': power_form_state.get('variableConfigurations', []),
                'transform_scope_cost_per_rank': power_form_state.get('transform_scope_cost_per_rank'),
                'transform_description': power_form_state.get('transform_description',""),
                'linkedCombatSkill': power_form_state.get('linkedCombatSkill') or None,
                'arrayId': power_form_state.get('arrayId') or None,
                'isAlternateEffectOf': power_form_state.get('isAlternateEffectOf') or None,
                'isArrayBase': power_form_state.get('isArrayBase', False),
                # Store ally stat block if this is a Summon/Duplication power
                'ally_notes_and_stats_structured': copy.deepcopy(power_form_state.get('ally_notes_and_stats_structured')) if selected_base_effect_rule and selected_base_effect_rule.get('isAllyEffect') else None,
                # Cost, isAttack, attackType, etc., will be derived by engine.recalculate()
            }

            current_powers_list = copy.deepcopy(char_state.get('powers', []))
            if power_form_state.get('editing_power_id'): # Update existing
                updated = False
                for i, p in enumerate(current_powers_list):
                    if p.get('id') == power_form_state.get('editing_power_id'):
                        current_powers_list[i] = final_power_data
                        updated = True
                        break
                if not updated: # Should not happen if editing_power_id is valid
                    current_powers_list.append(final_power_data) 
            else: # Add new
                current_powers_list.append(final_power_data)
            
            update_char_value(['powers'], current_powers_list) # This will trigger recalculate
            st_obj.session_state.power_form_state = get_default_power_form_state() # Reset form
            st_obj.session_state.show_power_builder_form = False # Flag to hide form after save
            st_obj.success(f"Power '{final_power_data['name']}' saved!")
            st_obj.experimental_rerun() # Rerun to reflect changes and hide form

        if col_reset.form_submit_button("Reset Form / Cancel Edit"):
            st_obj.session_state.power_form_state = get_default_power_form_state()
            st_obj.session_state.show_power_builder_form = False # Flag to hide form
            st_obj.experimental_rerun()


# This main function would be called from advanced_mode_ui.py or directly by app.py
# when the power section is active and user wants to add/edit a power.
# The visibility of the form itself would be controlled by a session_state flag like
# st.session_state.show_power_builder_form = True/False
# and st.session_state.power_form_state would be populated with an existing power's data if editing.