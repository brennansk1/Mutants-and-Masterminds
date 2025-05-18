# heroforge-mm-streamlit/ui_sections/power_builder_ui.py

import streamlit as st
import copy
import math
import uuid # For unique IDs for modifiers in the form state etc.
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Assuming core_engine is in the parent directory
    from ..core_engine import CoreEngine, CharacterState, RuleData, PowerDefinition, AdvantageDefinition, SkillDefinition, VariableConfigTrait 
else:
    CoreEngine = Any
    CharacterState = Dict[str, Any]
    RuleData = Dict[str, Any]
    PowerDefinition = Dict[str, Any]
    AdvantageDefinition = Dict[str, Any]
    SkillDefinition = Dict[str, Any]
    VariableConfigTrait = Dict[str, Any]


# --- Helper for unique keys in loops specific to Power Builder ---
def _uk_pb(base: str, *args: Any) -> str:
    """Creates a unique key for Streamlit widgets within the Power Builder."""
    str_args = [str(a).replace(":", "_").replace(" ", "_").replace("[", "_").replace("]", "_").replace("(", "_").replace(")", "_").replace("/", "_") for a in args if a is not None]
    return f"pb_{base}_{'_'.join(str_args)}"

# --- Function to get the default state for the power form ---
def get_default_power_form_state(rule_data: RuleData) -> Dict[str, Any]:
    """
    Initializes or resets the power form state dictionary.
    This is used by app.py and advanced_mode_ui.py to manage st.session_state.power_form_state.
    """
    default_base_effect_id = None
    power_effects_list = rule_data.get('power_effects', [])
    if power_effects_list:
        damage_effect = next((eff['id'] for eff in power_effects_list if eff['id'] == 'eff_damage'), None)
        default_base_effect_id = damage_effect if damage_effect else power_effects_list[0]['id']
    
    default_ally_stat_block = {
        "name": "New Creation", "type": "Minion", "pl_for_ally": 5, 
        "cost_pp_asserted_by_user": 0,
        "abilities_summary_text": "STR 0, STA 0, AGL 0, DEX 0, FGT 0, INT 0, AWE 0, PRE 0",
        "defenses_summary_text": "Dodge 0, Parry 0, Toughness 0, Fortitude 0, Will 0",
        "skills_summary_text": "Perception +0",
        "powers_advantages_summary_text": "None",
        "notes": "Basic creation."
    }
    
    default_variable_config_trait_builder = {
        'trait_type': 'Power', 
        'name': 'Configured Trait',
        'baseEffectId': default_base_effect_id, 
        'rank': 1,
        'modifiers_text_desc': '', 
        'enhanced_trait_category': 'Ability',
        'enhanced_trait_id': 'STR', 
        'enhancementAmount': 1,
        'pp_cost_in_variable': 0 
    }

    return {
        'editing_power_id': None, 
        'name': 'New Power',
        'descriptors': '', 
        'baseEffectId': default_base_effect_id,
        'rank': 1,
        'modifiersConfig': [], 
        'sensesConfig': [],    
        'immunityConfig': [],   
        'variableDescriptors': "", 
        'variableConfigurations': [], 
        'ally_notes_and_stats_structured': copy.deepcopy(default_ally_stat_block), 
        'create_params': { 
            'movable': False, 'stationary': False, 'innate_object': False, 
            'selective_create': False, 'subtle_object': 0, 
            'toughness_override': None, 
            'volume_override': None    
        },
        'affliction_params': { 
            'degree1': 'Dazed', 'degree2': 'Stunned', 'degree3': 'Incapacitated',
            'resistance_type': 'Fortitude', 
            'cumulative': False, 'progressive': False
        },
        'enhanced_trait_params': { 
            'category': 'Ability', 
            'trait_id': 'STR', 
            'enhancementAmount': 1 
        },
        'movement_params': { 
            'description_of_movements': "" # Simplified to text for now
            # 'selected_movements': [] # More complex: List of {'id': move_type_id, 'rank': X}
        },
        'morph_params': { 
            'description_of_forms': '',
            'transform_scope_choice_id': None, # For Transform effect
            'metamorph_rank': 0 
        },
        'nullify_params': {
            'descriptor_to_nullify': '',
            'broad_nullify': False, # These might be better as actual modifiers
            'simultaneous_nullify': False
        },
        'linkedCombatSkill': None, 
        'arrayId': None,         
        'isAlternateEffectOf': None, 
        'isArrayBase': False,
        'isDynamicArray': False, 
        'ui_state': {
            'variable_config_trait_builder': copy.deepcopy(default_variable_config_trait_builder),
            'modifier_to_add_id': None 
        } 
    }

# --- Helper UI Rendering Functions for Power Builder Sub-sections ---

def _render_modifier_parameter_input(
    st_obj: Any, 
    mod_rule: Dict[str, Any],        
    mod_config_entry: Dict[str, Any], 
    form_key_prefix: str,            
    char_state: CharacterState,      
    rule_data: RuleData,             
    engine: CoreEngine,
    power_form_state_ref: Dict[str, Any] 
) -> None:
    param_type = mod_rule.get('parameter_type')
    param_prompt = mod_rule.get('parameter_prompt', f"Details for {mod_rule.get('name', mod_rule.get('id'))}:")
    
    if 'params' not in mod_config_entry: # Ensure 'params' dict exists in the modifier instance
        mod_config_entry['params'] = {}
    
    # Most parameters are stored within the 'params' sub-dictionary of the modifier instance
    # The key within 'params' can be defined by 'parameter_storage_key' in mod_rule, or defaults to mod_rule['id']
    param_storage_key = mod_rule.get('parameter_storage_key', mod_rule.get('id', 'detail'))
    value_source = mod_config_entry['params']


    if param_type == "text":
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "text")
        value_source[param_storage_key] = st_obj.text_input(
            param_prompt, 
            value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', '')), 
            key=widget_key
        )
    elif param_type in ["text_long", "text_complex", "text_long_with_cost_note", "text_target_descriptor_or_trait", "text_long_environment_conditions", "text_long_transform_details", "text_long_summon_details"]:
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "textarea")
        value_source[param_storage_key] = st_obj.text_area(
            param_prompt, 
            value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', '')), 
            height=100, 
            key=widget_key,
            help=mod_rule.get('description', '') 
        )
    elif param_type == "number_rank": 
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "num_rank")
        max_r = mod_rule.get('maxRanks', 20)
        if mod_rule.get('maxRanks_source') == 'powerRank' or mod_rule.get('maxRanks_source') == 'powerRankOfBaseEffect':
             max_r = power_form_state_ref.get('rank', max_r) 
        
        value_source[param_storage_key] = st_obj.number_input(
            param_prompt, 
            value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', 1)), 
            min_value=mod_rule.get('minRanks', 1), 
            max_value=max_r, 
            step=1, 
            key=widget_key
        )
    elif param_type == "number_dc":
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "num_dc")
        value_source[param_storage_key] = st_obj.number_input(
            param_prompt, 
            value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', 10)), 
            min_value=0, 
            step=1, 
            key=widget_key
        )
    elif param_type == "number_rank_max_3": 
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "num_max3")
        value_source[param_storage_key] = st_obj.number_input(
            param_prompt, 
            value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', 1)), 
            min_value=1, max_value=3, step=1, key=widget_key
        )
    elif param_type == "select_from_options" and mod_rule.get('parameter_options'):
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "selectopt")
        options_list = mod_rule['parameter_options'] 
        
        options_map_vals = [opt['value'] for opt in options_list]
        options_map_labels = {opt['value']: opt.get('label', str(opt['value'])) for opt in options_list}
        
        current_selection = value_source.get(param_storage_key, mod_rule.get('parameter_default_value'))
        if current_selection not in options_map_vals and options_map_vals:
            current_selection = options_map_vals[0]
        
        sel_idx = options_map_vals.index(current_selection) if current_selection in options_map_vals else 0
        
        value_source[param_storage_key] = st_obj.selectbox(
            param_prompt, 
            options=options_map_vals,
            format_func=lambda x: options_map_labels.get(x, str(x)),
            index=sel_idx,
            key=widget_key
        )
    elif param_type == "select_skill":
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "selskill")
        all_skills_base_list = rule_data.get('skills', {}).get('list', [])
        char_specialized_skills = {
            sk_id: sk_id.replace(bs['id']+"_", "").replace("_"," ").title() + f" ({bs['name']})"
            for bs in all_skills_base_list if bs.get('specialization_possible')
            for sk_id in char_state.get('skills', {}).keys() if sk_id.startswith(bs['id']+"_")
        }
        skill_options = {"": "Select Skill..."}
        skill_options.update({s['id']: s['name'] for s in all_skills_base_list if not s.get('specialization_possible')})
        skill_options.update(char_specialized_skills)
        
        filter_hint = mod_rule.get('parameter_filter_hint', '').lower()
        skill_options_to_display = skill_options
        if filter_hint:
            filtered_options_dict = {"": "Select Skill..."}
            for s_id, s_name in skill_options.items():
                if not s_id: continue
                if any(hint_part in s_name.lower() or hint_part in s_id.lower() for hint_part in filter_hint.split(',')):
                    filtered_options_dict[s_id] = s_name
            skill_options_to_display = filtered_options_dict
        
        current_skill_id = value_source.get(param_storage_key)
        sel_idx_skill = list(skill_options_to_display.keys()).index(current_skill_id) if current_skill_id in skill_options_to_display else 0
        value_source[param_storage_key] = st_obj.selectbox(
            param_prompt, options=list(skill_options_to_display.keys()),
            format_func=lambda x: skill_options_to_display.get(x, "Choose..."),
            index=sel_idx_skill,
            key=widget_key
        )
    elif param_type == "select_sense_type": 
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "sel_sense_type")
        sense_type_options = ["Visual", "Auditory", "Olfactory", "Tactile", "Mental", "Radio", "Special"] 
        current_sense_type = value_source.get(param_storage_key, sense_type_options[0])
        sel_idx_sense = sense_type_options.index(current_sense_type) if current_sense_type in sense_type_options else 0
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=sense_type_options, index=sel_idx_sense, key=widget_key)

    elif param_type == "select_defense_type": 
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "sel_def_type")
        defense_options = ["Dodge", "Parry", "Fortitude", "Will", "Toughness"]
        current_def_type = value_source.get(param_storage_key, defense_options[0])
        sel_idx_def = defense_options.index(current_def_type) if current_def_type in defense_options else 0
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=defense_options, index=sel_idx_def, key=widget_key)

    elif param_type == "select_power_for_link": 
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "sel_pwr_link")
        linkable_powers = {"": "Select Power to Link..."}
        editing_power_id = power_form_state_ref.get('editing_power_id') 
        for p_other in char_state.get('powers', []):
            if p_other.get('id') != editing_power_id: 
                linkable_powers[p_other.get('id')] = p_other.get('name', 'Unnamed Power')
        
        current_linked_id = value_source.get(param_storage_key, "")
        sel_idx_link = list(linkable_powers.keys()).index(current_linked_id) if current_linked_id in linkable_powers else 0
        value_source[param_storage_key] = st_obj.selectbox(
            param_prompt, 
            options=list(linkable_powers.keys()), 
            format_func=lambda x: linkable_powers.get(x, "Choose..."), 
            index=sel_idx_link, 
            key=widget_key
        )
    elif param_type == "boolean_checkbox":
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "bool_check")
        value_source[param_storage_key] = st_obj.checkbox(
            param_prompt,
            value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', False)),
            key=widget_key
        )
    else:
        st_obj.warning(f"Unsupported parameter_type '{param_type}' for modifier '{mod_rule.get('name')}'. Using default text input.", icon="⚠️")
        widget_key = _uk_pb(form_key_prefix, param_storage_key, "text_fallback")
        value_source[param_storage_key] = st_obj.text_input(
            param_prompt, 
            value=str(value_source.get(param_storage_key, mod_rule.get('parameter_default_value', ''))), 
            key=widget_key
        )

# --- Senses Configuration UI ---
def _render_senses_config_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("👁️ Configure Senses")
    st_obj.caption("Select individual sense abilities. Total cost is the sum of chosen sense abilities.")
    sense_ability_rules: List[Dict] = rule_data.get('power_senses_config', [])
    if not sense_ability_rules: st_obj.warning("Senses configuration data not found."); return
    sense_options_map = {s['id']: f"{s['name']} (Cost: {s.get('cost', 0)} PP)" for s in sense_ability_rules}
    current_senses_config_ids: List[str] = power_form_state.get('sensesConfig', [])
    senses_by_category: Dict[str, List[Dict]] = {}
    for sense_rule in sense_ability_rules:
        cat = sense_rule.get('sense_type_group', 'General')
        if cat not in senses_by_category: senses_by_category[cat] = []
        senses_by_category[cat].append(sense_rule)
    final_selected_ids = []
    for category, senses_in_cat in sorted(senses_by_category.items()):
        st_obj.markdown(f"**{category}**")
        cat_cols = st_obj.columns(2) 
        for idx, sense_rule in enumerate(sorted(senses_in_cat, key=lambda x: x.get('name',''))):
            sense_id = sense_rule['id']
            is_selected = sense_id in current_senses_config_ids
            key_sense_cb = _uk_pb("sense_cb", power_form_state.get('editing_power_id', 'new'), sense_id)
            checkbox_state = cat_cols[idx % 2].checkbox(sense_options_map[sense_id], value=is_selected, key=key_sense_cb, help=sense_rule.get('description',''))
            if checkbox_state: final_selected_ids.append(sense_id)
    if set(final_selected_ids) != set(current_senses_config_ids):
        power_form_state['sensesConfig'] = final_selected_ids
    current_senses_cost = sum(s_rule.get('cost',0) for s_id in power_form_state['sensesConfig'] for s_rule in sense_ability_rules if s_rule['id'] == s_id)
    st_obj.metric("Cost from Selected Senses:", f"{current_senses_cost} PP")
    power_form_state['rank'] = 0 

# --- Immunity Configuration UI ---
def _render_immunity_config_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🛡️ Configure Immunities")
    st_obj.caption("Select immunities. Total cost is the sum of chosen immunities.")
    immunity_rules: List[Dict] = rule_data.get('power_immunities_config', [])
    if not immunity_rules: st_obj.warning("Immunity configuration data not found."); return
    current_immunity_config_ids: List[str] = power_form_state.get('immunityConfig', [])
    immunity_categories: Dict[str, List[Dict]] = {}
    for im_rule in immunity_rules:
        cat = im_rule.get('category', 'General')
        if cat not in immunity_categories: immunity_categories[cat] = []
        immunity_categories[cat].append(im_rule)
    final_selected_immunity_ids = []
    for category, im_list in sorted(immunity_categories.items()):
        st_obj.markdown(f"**{category}**")
        im_cols = st_obj.columns(2) 
        for idx, im_rule in enumerate(sorted(im_list, key=lambda x: x.get('cost',0))):
            im_id = im_rule['id']
            is_selected = im_id in current_immunity_config_ids
            label = f"{im_rule['name']} ({im_rule['cost']} PP)"
            key_imm_cb = _uk_pb("imm_cb", power_form_state.get('editing_power_id', 'new'), im_id)
            checkbox_state_imm = im_cols[idx % 2].checkbox(label, value=is_selected, key=key_imm_cb, help=im_rule.get('description',''))
            if checkbox_state_imm: final_selected_immunity_ids.append(im_id)
    if set(final_selected_immunity_ids) != set(current_immunity_config_ids):
        power_form_state['immunityConfig'] = final_selected_immunity_ids
    current_immunity_cost = sum(im_rule.get('cost',0) for im_id in power_form_state['immunityConfig'] for im_rule in immunity_rules if im_rule['id'] == im_id)
    st_obj.metric("Cost from Selected Immunities:", f"{current_immunity_cost} PP")
    power_form_state['rank'] = 0 

# --- Variable Power: Trait Builder UI ---
def _render_variable_config_trait_builder_ui(st_obj: Any, trait_builder_state: VariableConfigTrait, rule_data: RuleData, form_key_prefix: str ):
    st_obj.markdown("##### Add Trait to Current Configuration")
    trait_type_options = ["Power", "EnhancedAbility", "EnhancedSkill", "EnhancedDefense", "EnhancedAdvantage", "CustomText"]
    current_trait_type = trait_builder_state.get('trait_type', "Power")
    if current_trait_type == "Power" and not trait_builder_state.get('baseEffectId'):
        power_effects_list = rule_data.get('power_effects', [])
        if power_effects_list: trait_builder_state['baseEffectId'] = power_effects_list[0]['id']
    trait_builder_state['trait_type'] = st_obj.selectbox("Trait Type:", trait_type_options, index=trait_type_options.index(current_trait_type), key=_uk_pb(form_key_prefix, "var_trait_type"))
    trait_builder_state['name'] = st_obj.text_input("Trait Name/Description:", value=trait_builder_state.get('name', "Configured Trait"), key=_uk_pb(form_key_prefix, "var_trait_name"))
    if trait_builder_state['trait_type'] == "Power":
        eff_opts = {"": "Select Effect..."}; eff_opts.update({eff['id']: eff['name'] for eff in rule_data.get('power_effects', [])})
        trait_builder_state['baseEffectId'] = st_obj.selectbox("Base Effect:", options=list(eff_opts.keys()), format_func=lambda x: eff_opts.get(x, "Choose..."), key=_uk_pb(form_key_prefix, "var_trait_pwr_effect"), index=list(eff_opts.keys()).index(trait_builder_state.get('baseEffectId')) if trait_builder_state.get('baseEffectId') in eff_opts else 0)
        trait_builder_state['rank'] = st_obj.number_input("Rank:", min_value=1, value=trait_builder_state.get('rank',1), key=_uk_pb(form_key_prefix, "var_trait_pwr_rank"))
        trait_builder_state['modifiers_text_desc'] = st_obj.text_area("Modifiers (Text Description):", value=trait_builder_state.get('modifiers_text_desc',''), key=_uk_pb(form_key_prefix, "var_trait_pwr_mods_text"), height=75)
        trait_builder_state['pp_cost_in_variable'] = st_obj.number_input("Asserted PP Cost for this Power:", min_value=0, value=trait_builder_state.get('pp_cost_in_variable',0), key=_uk_pb(form_key_prefix, "var_trait_pwr_asserted_cost"))
    elif trait_builder_state['trait_type'] == "EnhancedAbility":
        ab_opts = {"": "Select Ability..."}; ab_opts.update({ab['id']:ab['name'] for ab in rule_data.get('abilities',{}).get('list',[])})
        trait_builder_state['enhanced_trait_id'] = st_obj.selectbox("Ability to Enhance:", options=list(ab_opts.keys()), format_func=lambda x: ab_opts.get(x, "Choose..."), key=_uk_pb(form_key_prefix, "var_trait_enab_id"), index=list(ab_opts.keys()).index(trait_builder_state.get('enhanced_trait_id')) if trait_builder_state.get('enhanced_trait_id') in ab_opts else 0)
        trait_builder_state['enhancementAmount'] = st_obj.number_input("Enhancement Amount (+ ranks):", min_value=1, value=trait_builder_state.get('enhancementAmount',1), key=_uk_pb(form_key_prefix, "var_trait_enab_amt"))
        trait_builder_state['pp_cost_in_variable'] = trait_builder_state['enhancementAmount'] * 2 
        st_obj.caption(f"Calculated Cost: {trait_builder_state['pp_cost_in_variable']} PP")
    elif trait_builder_state['trait_type'] == "EnhancedSkill":
        skill_opts = {"": "Select Skill..."}; all_skills_base_list = rule_data.get('skills', {}).get('list', []); skill_opts.update({s['id']: s['name'] for s in all_skills_base_list}) 
        trait_builder_state['enhanced_trait_id'] = st_obj.selectbox("Skill to Enhance:", options=list(skill_opts.keys()), format_func=lambda x: skill_opts.get(x, "Choose..."), key=_uk_pb(form_key_prefix, "var_trait_ensk_id"), index=list(skill_opts.keys()).index(trait_builder_state.get('enhanced_trait_id')) if trait_builder_state.get('enhanced_trait_id') in skill_opts else 0)
        trait_builder_state['enhancementAmount'] = st_obj.number_input("Enhancement Amount (+ ranks bought):", min_value=1, value=trait_builder_state.get('enhancementAmount',1), key=_uk_pb(form_key_prefix, "var_trait_ensk_amt"))
        trait_builder_state['pp_cost_in_variable'] = math.ceil(trait_builder_state['enhancementAmount'] * 0.5)
        st_obj.caption(f"Calculated Cost: {trait_builder_state['pp_cost_in_variable']} PP")
    elif trait_builder_state['trait_type'] == "CustomText":
        trait_builder_state['pp_cost_in_variable'] = st_obj.number_input("Asserted PP Cost for this Custom Trait:", min_value=0, value=trait_builder_state.get('pp_cost_in_variable',0), key=_uk_pb(form_key_prefix, "var_trait_cust_asserted_cost"))

# --- Variable Power: Main Configuration UI ---
def _render_variable_configurations_ui(st_obj: Any, power_form_state: Dict[str, Any], char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, generate_id_func: Callable):
    st_obj.subheader("⚙️ Define Variable Configurations")
    power_rank = power_form_state.get('rank', 1); variable_pool_pp = power_rank * 5
    st_obj.info(f"Available Variable Pool for each configuration: **{variable_pool_pp} PP**")
    power_form_state['variableDescriptors'] = st_obj.text_area("Variable Descriptors:", value=power_form_state.get('variableDescriptors', ''), key=_uk_pb(power_form_state.get('editing_power_id','new'), "var_descriptors"))
    if 'variableConfigurations' not in power_form_state: power_form_state['variableConfigurations'] = []
    configs_to_keep = []
    for i, config_entry in enumerate(power_form_state['variableConfigurations']):
        config_id = config_entry.get('id', generate_id_func("var_cfg_")); config_entry['id'] = config_id
        with st_obj.expander(f"Configuration #{i+1}: {config_entry.get('configName', 'Unnamed Config')}", expanded=True):
            cols_cfg_header = st_obj.columns([0.8, 0.2])
            config_entry['configName'] = cols_cfg_header[0].text_input("Config Name:", value=config_entry.get('configName', f'Form {i+1}'), key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_name", config_id))
            st_obj.markdown("**Traits in this Configuration:**"); config_total_cost = 0
            if not config_entry.get('configTraits'): st_obj.caption("No traits added yet.")
            traits_to_keep_in_config = []
            for t_idx, trait in enumerate(config_entry.get('configTraits',[])):
                trait_id_inst = trait.get('id', generate_id_func("var_trait_")); trait['id'] = trait_id_inst
                t_cost = trait.get('pp_cost_in_variable', 0); config_total_cost += t_cost
                t_cols = st_obj.columns([0.8,0.2])
                t_cols[0].markdown(f"- **{trait.get('name','Trait')}** ({trait.get('trait_type','N/A')}, R{trait.get('rank',trait.get('enhancementAmount','N/A')) if 'rank' in trait or 'enhancementAmount' in trait else ''}) - *Cost: {t_cost} PP*")
                if t_cols[1].button("➖", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_rem_trait", config_id, trait_id_inst), help="Remove Trait"): pass
                else: traits_to_keep_in_config.append(trait)
            if len(traits_to_keep_in_config) != len(config_entry.get('configTraits',[])): config_entry['configTraits'] = traits_to_keep_in_config; st.rerun()
            _render_variable_config_trait_builder_ui(st_obj, power_form_state['ui_state']['variable_config_trait_builder'], rule_data, _uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_traitbuild", config_id))
            if st_obj.button("➕ Add Trait to This Configuration", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_add_trait_btn", config_id)):
                new_trait_to_add = copy.deepcopy(power_form_state['ui_state']['variable_config_trait_builder']); new_trait_to_add['id'] = generate_id_func("var_trait_")
                if 'configTraits' not in config_entry: config_entry['configTraits'] = []
                config_entry['configTraits'].append(new_trait_to_add)
                power_form_state['ui_state']['variable_config_trait_builder'] = copy.deepcopy(get_default_power_form_state(rule_data)['ui_state']['variable_config_trait_builder'])
                st.rerun()
            st_obj.metric(f"Config Total Cost:", f"{config_total_cost} / {variable_pool_pp} PP", delta_color="normal" if config_total_cost <= variable_pool_pp else "inverse")
            if config_total_cost > variable_pool_pp: st_obj.error("Config cost exceeds Variable Pool!", icon="⚠️")
            if cols_cfg_header[1].button("🗑️ Remove Config", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_remove_btn", config_id), type="secondary"): pass
            else: configs_to_keep.append(config_entry)
    if len(configs_to_keep) != len(power_form_state['variableConfigurations']): power_form_state['variableConfigurations'] = configs_to_keep; st.rerun()
    if st_obj.button("➕ Add New Configuration Slot", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_add_slot_btn")):
        new_config_id = generate_id_func("var_cfg_"); power_form_state['variableConfigurations'].append({'id': new_config_id, 'configName': f'Config {len(power_form_state["variableConfigurations"])+1}', 'configTraits': [], 'assertedConfigCost': 0}); st.rerun()

# --- Ally (Summon/Duplication) Stat Block UI ---
def _render_ally_creation_stat_block_ui(st_obj: Any, power_form_state: Dict[str, Any], char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, base_effect_rule: Dict[str, Any]):
    st_obj.subheader(f"🐾 Define {base_effect_rule.get('name','Creation')} Details")
    if 'ally_notes_and_stats_structured' not in power_form_state: power_form_state['ally_notes_and_stats_structured'] = copy.deepcopy(get_default_power_form_state(rule_data)['ally_notes_and_stats_structured'])
    ally_data = power_form_state['ally_notes_and_stats_structured']
    for key, default_val in get_default_power_form_state(rule_data)['ally_notes_and_stats_structured'].items():
        if key not in ally_data: ally_data[key] = default_val
    allotted_pp = power_form_state.get('rank',0) * base_effect_rule.get('grantsAllyPointsFactor',15)
    st_obj.info(f"This {base_effect_rule.get('name','Creation')} uses **{allotted_pp} PP** (from power rank {power_form_state.get('rank',0)}).")
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), base_effect_rule.get('id','ally'))
    ally_data['name'] = st_obj.text_input(f"{base_effect_rule.get('name','Creation')} Name/Type:", value=ally_data.get('name', f"My {base_effect_rule.get('name','Creation')}"), key=_uk_pb(form_key_prefix, "name"))
    ally_data['pl_for_ally'] = st_obj.number_input(f"{base_effect_rule.get('name','Creation')}'s PL:", min_value=0, value=ally_data.get('pl_for_ally', char_state.get('powerLevel',10) - 2), key=_uk_pb(form_key_prefix, "pl"))
    ally_data['cost_pp_asserted_by_user'] = st_obj.number_input(f"User-Asserted PP for Build:", min_value=0, value=ally_data.get('cost_pp_asserted_by_user',0), key=_uk_pb(form_key_prefix, "asserted_cost"), help=f"Must be <= {allotted_pp} PP.")
    if ally_data['cost_pp_asserted_by_user'] > allotted_pp: st_obj.error(f"Asserted cost ({ally_data['cost_pp_asserted_by_user']}) exceeds pool ({allotted_pp})!", icon="⚠️")
    st_obj.markdown("**Simplified Stat Block:**")
    ally_data['abilities_summary_text'] = st_obj.text_area("Key Abilities:", value=ally_data.get("abilities_summary_text",""), height=50, key=_uk_pb(form_key_prefix,"abil_sum"))
    ally_data['defenses_summary_text'] = st_obj.text_area("Key Defenses:", value=ally_data.get("defenses_summary_text",""), height=50, key=_uk_pb(form_key_prefix,"def_sum"))
    ally_data['skills_summary_text'] = st_obj.text_area("Key Skills:", value=ally_data.get("skills_summary_text",""), height=75, key=_uk_pb(form_key_prefix,"skills_sum"))
    ally_data['powers_advantages_summary_text'] = st_obj.text_area("Key Powers/Advantages:", value=ally_data.get("powers_advantages_summary_text",""), height=100, key=_uk_pb(form_key_prefix,"pwr_adv_sum"))
    ally_data['notes'] = st_obj.text_area("Notes:", value=ally_data.get("notes",""), height=75, key=_uk_pb(form_key_prefix,"notes"))

# --- Affliction Parameters UI ---
def _render_affliction_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🤢 Configure Affliction Parameters")
    aff_params = power_form_state.get('affliction_params', {})
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), "aff")
    aff_params['degree1'] = st_obj.text_input("1st Degree Condition(s):", value=aff_params.get('degree1', 'Dazed'), key=_uk_pb(form_key_prefix,"deg1"))
    aff_params['degree2'] = st_obj.text_input("2nd Degree Condition(s):", value=aff_params.get('degree2', 'Stunned'), key=_uk_pb(form_key_prefix,"deg2"))
    aff_params['degree3'] = st_obj.text_input("3rd Degree Condition(s):", value=aff_params.get('degree3', 'Incapacitated'), key=_uk_pb(form_key_prefix,"deg3"))
    resistance_options = ["Fortitude", "Will", "Dodge"]; current_res = aff_params.get('resistance_type', 'Fortitude')
    res_idx = resistance_options.index(current_res) if current_res in resistance_options else 0
    aff_params['resistance_type'] = st_obj.selectbox("Resisted By:", options=resistance_options, index=res_idx, key=_uk_pb(form_key_prefix,"res_type"))
    # Cumulative & Progressive are standard Extras, should be added via modifier system.
    # If they are intrinsic to Affliction and not general modifiers, keep here.
    # DHH p.121 lists them as common extras for Affliction.
    # For now, assuming they are handled by the main modifier system.
    # aff_params['cumulative'] = st_obj.checkbox("Cumulative Extra?", value=aff_params.get('cumulative', False), key=_uk_pb(form_key_prefix,"cumulative_cb"))
    # aff_params['progressive'] = st_obj.checkbox("Progressive Extra?", value=aff_params.get('progressive', False), key=_uk_pb(form_key_prefix,"progressive_cb"))
    power_form_state['affliction_params'] = aff_params

# --- Enhanced Trait UI ---
def _render_enhanced_trait_params_ui(st_obj: Any, power_form_state: Dict[str, Any], char_state: CharacterState, rule_data: RuleData, engine: CoreEngine):
    st_obj.subheader("➕ Configure Enhanced Trait")
    et_params = power_form_state.get('enhanced_trait_params', {})
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), "et")
    base_effect_rule = next((eff for eff in rule_data.get('power_effects', []) if eff['id'] == 'eff_enhanced_trait'), {})
    trait_categories = base_effect_rule.get('enhancementTargetCategories', ["Ability", "Skill", "Advantage", "Defense", "PowerRank"])
    current_cat = et_params.get('category', trait_categories[0]); cat_idx = trait_categories.index(current_cat) if current_cat in trait_categories else 0
    
    new_cat = st_obj.selectbox("Trait Category to Enhance:", options=trait_categories, index=cat_idx, key=_uk_pb(form_key_prefix,"cat"))
    if new_cat != et_params.get('category'):
        et_params['category'] = new_cat
        et_params['trait_id'] = None # Reset trait ID when category changes
        st.rerun() # Rerun to update trait_id options

    trait_options = {"": f"Select {et_params['category']}..."}
    if et_params['category'] == "Ability": trait_options.update({ab['id']: ab['name'] for ab in rule_data.get('abilities',{}).get('list',[])})
    elif et_params['category'] == "Skill":
        all_skills_base_list = rule_data.get('skills', {}).get('list', [])
        char_specialized_skills = { sk_id: sk_id.replace(bs['id']+"_", "").replace("_"," ").title() + f" ({bs['name']})" for bs in all_skills_base_list if bs.get('specialization_possible') for sk_id in char_state.get('skills', {}).keys() if sk_id.startswith(bs['id']+"_")}
        trait_options.update({s['id']: s['name'] for s in all_skills_base_list if not s.get('specialization_possible')}); trait_options.update(char_specialized_skills)
    elif et_params['category'] == "Advantage": trait_options.update({adv['id']: adv['name'] for adv in rule_data.get('advantages_v1',[])})
    elif et_params['category'] == "Defense": trait_options.update({d_id: d_id for d_id in ["Dodge", "Parry", "Toughness", "Fortitude", "Will"]})
    elif et_params['category'] == "PowerRank": trait_options.update({pwr['id']: pwr.get('name','Unnamed Power') for pwr in char_state.get('powers',[]) if pwr.get('id') != power_form_state.get('editing_power_id')})
    
    current_trait_id = et_params.get('trait_id')
    # Ensure current_trait_id is valid for the new category, or default to first if None
    if current_trait_id not in trait_options and len(trait_options) > 1:
        current_trait_id = list(trait_options.keys())[1] # Default to first actual option
        et_params['trait_id'] = current_trait_id # Update state

    trait_idx = list(trait_options.keys()).index(current_trait_id) if current_trait_id in trait_options else 0
    et_params['trait_id'] = st_obj.selectbox(f"Specific {et_params['category']} to Enhance:", options=list(trait_options.keys()), format_func=lambda x: trait_options.get(x, "Choose..."), index=trait_idx, key=_uk_pb(form_key_prefix,"trait_id"))
    
    # Rank of Enhanced Trait power IS the enhancementAmount
    power_form_state['rank'] = st_obj.number_input("Enhancement Amount (+ Ranks):", min_value=1, value=power_form_state.get('rank',1), step=1, key=_uk_pb(form_key_prefix,"amount"))
    et_params['enhancementAmount'] = power_form_state['rank'] # Sync them

    power_form_state['enhanced_trait_params'] = et_params

# --- Create Effect Parameters UI ---
def _render_create_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🛠️ Configure Create Effect")
    create_params = power_form_state.get('create_params', {})
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), "create")

    # These are often Extras, but DHH lists them under Create's description.
    # If they are defined as general modifiers, they should be added there.
    # For now, treating them as specific params for Create.
    create_params['movable'] = st_obj.checkbox("Movable Extra?", value=create_params.get('movable', False), key=_uk_pb(form_key_prefix,"movable"), help="Created object can be moved. (+1 PP/rank)")
    create_params['stationary'] = st_obj.checkbox("Stationary Extra? (Immobile, Tethered)", value=create_params.get('stationary', False), key=_uk_pb(form_key_prefix,"stationary"), help="Object cannot be moved once created. (+0 PP/rank)")
    
    # Toughness/Volume are usually = Create Rank. Overrides are rare.
    # These might be better as Features of the Create power if they deviate.
    # For now, simple overrides.
    create_params['toughness_override'] = st_obj.number_input(
        "Override Object Toughness (Optional, default = Create Rank):", 
        min_value=0, value=create_params.get('toughness_override') if create_params.get('toughness_override') is not None else power_form_state.get('rank',1), 
        step=1, format="%d",
        key=_uk_pb(form_key_prefix,"tough_override"), help="Set to 0 to explicitly use power rank."
    )
    if create_params['toughness_override'] == 0: create_params['toughness_override'] = None # Use rank

    # Volume Rank is usually equal to Create Rank. No separate input unless a specific modifier changes this.
    st_obj.caption(f"Object Volume Rank will be equal to Create Power Rank ({power_form_state.get('rank',1)}).")
    power_form_state['create_params'] = create_params

# --- Movement Effect Parameters UI ---
def _render_movement_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🏃 Configure Movement Effect")
    mov_params = power_form_state.get('movement_params', {})
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), "move")

    # DHH p.138: "Each rank in Movement costs 2 character points and gives you 1 rank in any of the following effects, or 2 ranks in effects costing 1 point per rank."
    # This is complex. For now, a text area for user to describe.
    # A full UI would list movement types from a rule file and allow allocating ranks.
    mov_params['description_of_movements'] = st_obj.text_area(
        "Describe Movement Types & Ranks (e.g., 'Wall-Crawling 1 (1PP), Sure-Footed 1 (1PP)' or 'Dimensional Travel 1 (2PP)' ):",
        value=mov_params.get('description_of_movements', ""),
        height=100,
        key=_uk_pb(form_key_prefix, "desc"),
        help="The main Movement power rank determines total PP available for specific movement types (Rank x 2 PP)."
    )
    power_form_state['movement_params'] = mov_params

# --- Morph/Transform Parameters UI ---
def _render_morph_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🎭 Configure Morph/Transform")
    morph_params = power_form_state.get('morph_params', {})
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), "morph")
    base_effect_id = power_form_state.get('baseEffectId')
    base_effect_rule = next((eff for eff in rule_data.get('power_effects', []) if eff['id'] == base_effect_id), None)

    morph_params['description_of_forms'] = st_obj.text_area(
        "Description of Forms Assumed/Transformation Effect:",
        value=morph_params.get('description_of_forms', ""),
        height=100,
        key=_uk_pb(form_key_prefix, "forms_desc"),
        help="Describe the range of forms or the nature of the transformation."
    )
    
    if base_effect_rule and base_effect_rule.get('isTransformContainer') and base_effect_rule.get('costOptions'):
        st_obj.markdown("**Transformation Scope (determines cost per rank):**")
        cost_options_map_labels = {opt['choice_id']: opt['label'] for opt in base_effect_rule['costOptions']}
        cost_options_map_vals = [opt['choice_id'] for opt in base_effect_rule['costOptions']]
        
        current_scope_choice_id = morph_params.get('transform_scope_choice_id', cost_options_map_vals[0] if cost_options_map_vals else None)
        
        sel_idx_scope = cost_options_map_vals.index(current_scope_choice_id) if current_scope_choice_id in cost_options_map_vals else 0
        
        new_scope_choice_id = st_obj.selectbox(
            "Select Transformation Scope:",
            options=cost_options_map_vals,
            format_func=lambda x: cost_options_map_labels.get(x, "Select Scope..."),
            index=sel_idx_scope,
            key=_uk_pb(form_key_prefix, "transform_scope_select")
        )
        if new_scope_choice_id != current_scope_choice_id:
            morph_params['transform_scope_choice_id'] = new_scope_choice_id
            # Engine uses this choice_id to find the costPerRank from power_effects.json
            # May need to trigger a cost update preview if possible.
    
    # Metamorph extra would be added via the general modifier system.
    power_form_state['morph_params'] = morph_params

# --- Nullify Parameters UI ---
def _render_nullify_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🚫 Configure Nullify")
    null_params = power_form_state.get('nullify_params', {})
    form_key_prefix = _uk_pb(power_form_state.get('editing_power_id','new'), "nullify")

    null_params['descriptor_to_nullify'] = st_obj.text_input(
        "Descriptor(s) or Specific Power to Nullify:",
        value=null_params.get('descriptor_to_nullify', ""),
        key=_uk_pb(form_key_prefix, "null_desc"),
        help="E.g., 'Fire powers', 'Magic', 'Flight power of Target X'. Broad/Simultaneous are Extras."
    )
    power_form_state['nullify_params'] = null_params


# --- Main Power Builder Form ---
def render_power_builder_form(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    power_form_state: Dict[str, Any], 
    generate_id_func: Callable[[str], str]
):
    form_key_prefix = power_form_state.get('editing_power_id') or "new_power_form" # Ensure unique form key
    
    with st_obj.form(key=_uk_pb("power_form_main", form_key_prefix), clear_on_submit=False): # Persist state on reruns within form
        editing_id = power_form_state.get('editing_power_id')
        if editing_id:
            st_obj.subheader(f"Edit Power: {power_form_state.get('name', '')} (ID: {editing_id})")
        else:
            st_obj.subheader("✨ Add New Power ✨")

        # --- Basic Info ---
        col1, col2 = st_obj.columns([3,1])
        with col1:
            power_form_state['name'] = st.text_input("Power Name:", value=power_form_state.get('name', 'New Power'), key=_uk_pb(form_key_prefix, "name"))
        
        effect_options = {"": "Select Base Effect..."}
        power_effects_list = rule_data.get('power_effects', [])
        effect_options.update({eff['id']: eff['name'] for eff in power_effects_list})
        
        current_effect_id = power_form_state.get('baseEffectId', list(effect_options.keys())[1] if len(effect_options)>1 else "")
        if current_effect_id not in effect_options and effect_options: # Ensure valid default
            current_effect_id = list(effect_options.keys())[1] if len(effect_options) > 1 else list(effect_options.keys())[0]
            power_form_state['baseEffectId'] = current_effect_id

        effect_idx = list(effect_options.keys()).index(current_effect_id) if current_effect_id in effect_options else 0
        
        with col2:
            new_base_effect_id = st.selectbox(
                "Base Effect:", options=list(effect_options.keys()), 
                format_func=lambda x: effect_options.get(x, "Choose..."),
                index=effect_idx, key=_uk_pb(form_key_prefix, "base_effect_select")
            )
        
        if new_base_effect_id != current_effect_id:
            power_form_state['baseEffectId'] = new_base_effect_id
            # When base effect changes, reset specific params and potentially rank/modifiers
            # This is a complex state reset; for now, rely on user to adjust.
            # A full reset might be too aggressive if user is just exploring.
            # Consider resetting only if new_base_effect_id is substantially different.
            st.rerun() 

        selected_base_effect_rule = next((e for e in power_effects_list if e['id'] == power_form_state.get('baseEffectId')), None)

        # --- Rank Input & Descriptors ---
        col_rank, col_desc = st_obj.columns(2)
        with col_rank:
            if selected_base_effect_rule and not (selected_base_effect_rule.get('isSenseContainer') or selected_base_effect_rule.get('isImmunityContainer')):
                if not selected_base_effect_rule.get('isEnhancementEffect'): # Enhanced Trait rank is its amount
                     power_form_state['rank'] = st.number_input(
                        "Power Rank:", min_value=0, max_value=char_state.get('powerLevel', 10) * 2, 
                        value=power_form_state.get('rank',1), 
                        step=1, key=_uk_pb(form_key_prefix, "rank_input"),
                        help=selected_base_effect_rule.get('description','') if selected_base_effect_rule else ""
                    )
            elif selected_base_effect_rule and (selected_base_effect_rule.get('isSenseContainer') or selected_base_effect_rule.get('isImmunityContainer')):
                power_form_state['rank'] = 0 
        
        with col_desc:
            power_form_state['descriptors'] = st.text_input("Descriptors (comma-separated, e.g., Fire, Magical):", value=power_form_state.get('descriptors',''), key=_uk_pb(form_key_prefix, "descriptors"))

        if selected_base_effect_rule:
            st.caption(f"Base Effect: {selected_base_effect_rule.get('name', 'N/A')} - {selected_base_effect_rule.get('description', '')}")
        
        if selected_base_effect_rule and power_form_state.get('rank',0) >= 0 : # Show for rank 0 too for Senses/Immunity
            measurement_str = engine.get_power_measurement_details(power_form_state, rule_data) 
            if measurement_str: st.info(f"ℹ️ {measurement_str}", icon="📏")

        # --- Effect-Specific Configuration UIs ---
        st.markdown("---")
        if selected_base_effect_rule:
            st.markdown(f"**Effect Specific Configuration for: {selected_base_effect_rule.get('name')}**")
            if selected_base_effect_rule.get('isSenseContainer'):
                _render_senses_config_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('isImmunityContainer'):
                _render_immunity_config_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('isVariableContainer'):
                _render_variable_configurations_ui(st, power_form_state, char_state, rule_data, engine, generate_id_func)
            elif selected_base_effect_rule.get('isAllyEffect'):
                _render_ally_creation_stat_block_ui(st, power_form_state, char_state, rule_data, engine, selected_base_effect_rule)
            elif selected_base_effect_rule.get('id') == 'eff_affliction':
                _render_affliction_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('isEnhancementEffect'):
                _render_enhanced_trait_params_ui(st, power_form_state, char_state, rule_data, engine)
            elif selected_base_effect_rule.get('isCreateEffect'):
                _render_create_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('id') == 'eff_movement':
                _render_movement_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('id') in ['eff_morph', 'eff_transform']:
                _render_morph_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('id') == 'eff_nullify':
                _render_nullify_params_ui(st, power_form_state, rule_data)
            else:
                st.caption("This effect has no special parameters beyond standard modifiers.")
        
        st.markdown("---")
        # --- Modifier Management UI ---
        st.subheader("✨ Modifiers (Extras & Flaws)")
        
        if power_form_state.get('modifiersConfig'):
            st.markdown("**Applied Modifiers:**")
            modifiers_to_keep = []
            for idx, mod_conf_instance in enumerate(power_form_state.get('modifiersConfig', [])):
                mod_rule_id = mod_conf_instance.get('id')
                mod_instance_id = mod_conf_instance.get('instance_id') # Should have been set when added
                if not mod_instance_id: # Fallback if somehow missing
                    mod_instance_id = generate_id_func("mod_inst_")
                    mod_conf_instance['instance_id'] = mod_instance_id

                mod_rule_def = next((m for m in rule_data.get('power_modifiers',[]) if m['id'] == mod_rule_id), None)
                if not mod_rule_def: continue

                mod_disp_name = mod_rule_def.get('name', mod_rule_id)
                mod_rank_val = mod_conf_instance.get('rank',1) if mod_rule_def.get('ranked') else None
                mod_rank_disp = f" (Rank {mod_rank_val})" if mod_rank_val is not None else ""
                
                with st.expander(f"{mod_disp_name}{mod_rank_disp} [{mod_rule_def.get('type', '')}]", expanded=False):
                    if mod_rule_def.get('parameter_needed'):
                        _render_modifier_parameter_input(st, mod_rule_def, mod_conf_instance, _uk_pb(form_key_prefix,"mod_edit", mod_instance_id), char_state, rule_data, engine, power_form_state)
                    else:
                        st.caption("No parameters for this modifier.")
                    
                    if st.button("➖ Remove this Modifier", key=_uk_pb(form_key_prefix, "mod_remove_btn", mod_instance_id), type="secondary"):
                        pass 
                    else:
                        modifiers_to_keep.append(mod_conf_instance)
            
            if len(modifiers_to_keep) != len(power_form_state.get('modifiersConfig', [])):
                power_form_state['modifiersConfig'] = modifiers_to_keep
                st.rerun() 

        st.markdown("*Add New Modifier:*")
        mod_options = {"": "Select Modifier..."}
        mod_options.update({m['id']: f"{m['name']} ({m.get('type','')}, Cost: {m.get('costChangePerRank', m.get('flatCost', m.get('flatCostChange', '?')))}{'/r' if m.get('costType')=='perRank' or m.get('costType')=='perRankOfModifier' else ' flat'})" 
                            for m in rule_data.get('power_modifiers',[])})
        
        selected_mod_to_add_id_from_select = st.selectbox(
            "Available Modifiers:", options=list(mod_options.keys()),
            format_func=lambda x: mod_options.get(x, "Choose..."),
            index = 0, # Always default to "Select Modifier..."
            key=_uk_pb(form_key_prefix, "mod_select_to_add_key") # Unique key for selectbox
        )
        
        # Store selection in ui_state to persist it for parameter configuration area
        if selected_mod_to_add_id_from_select != power_form_state.get('ui_state',{}).get('modifier_to_add_id'):
            power_form_state['ui_state']['modifier_to_add_id'] = selected_mod_to_add_id_from_select
            # If a new modifier is selected, reset its temporary config state
            power_form_state['ui_state']['temp_new_mod_config'] = {'id': selected_mod_to_add_id_from_select, 'rank': 1, 'params': {}}
            st.rerun()


        if power_form_state.get('ui_state',{}).get('modifier_to_add_id'):
            current_mod_to_add_id = power_form_state['ui_state']['modifier_to_add_id']
            selected_mod_to_add_rule = next((m for m in rule_data.get('power_modifiers',[]) if m['id'] == current_mod_to_add_id), None)
            
            if selected_mod_to_add_rule:
                # Use a temporary dict in ui_state to hold parameters for the modifier being added
                if 'temp_new_mod_config' not in power_form_state['ui_state'] or power_form_state['ui_state']['temp_new_mod_config'].get('id') != current_mod_to_add_id:
                    power_form_state['ui_state']['temp_new_mod_config'] = {'id': current_mod_to_add_id, 'rank': 1, 'params': {}}
                
                temp_new_mod_config_state = power_form_state['ui_state']['temp_new_mod_config']

                if selected_mod_to_add_rule.get('ranked'):
                    temp_new_mod_config_state['rank'] = st.number_input("Modifier Rank:", min_value=1, 
                                                                        max_value=selected_mod_to_add_rule.get('maxRanks',20), # Simplified max
                                                                        value=temp_new_mod_config_state.get('rank',1),
                                                                        key=_uk_pb(form_key_prefix, "mod_add_rank", current_mod_to_add_id))


                if selected_mod_to_add_rule.get('parameter_needed'):
                    st.caption(f"Configure parameters for: {selected_mod_to_add_rule['name']}")
                    _render_modifier_parameter_input(st, selected_mod_to_add_rule, temp_new_mod_config_state, _uk_pb(form_key_prefix,"mod_add_new_param", current_mod_to_add_id), char_state, rule_data, engine, power_form_state)
                
                if st.button(f"➕ Add Modifier: {selected_mod_to_add_rule['name']}", key=_uk_pb(form_key_prefix, "mod_add_confirm_btn", current_mod_to_add_id)):
                    final_mod_to_add = copy.deepcopy(temp_new_mod_config_state)
                    final_mod_to_add['instance_id'] = generate_id_func("mod_inst_") 
                    power_form_state['modifiersConfig'].append(final_mod_to_add)
                    power_form_state['ui_state']['modifier_to_add_id'] = None # Reset selectbox
                    power_form_state['ui_state']['temp_new_mod_config'] = {} # Clear temp config
                    st.rerun()
        
        st.markdown("---")
        # --- Array Configuration UI ---
        st.subheader("🔗 Array Configuration")
        # ... (Implementation from Part 3, assumed complete and correct) ...
        power_form_state['isArrayBase'] = st.checkbox("Is this power the Base of a new Array?", value=power_form_state.get('isArrayBase',False), key=_uk_pb(form_key_prefix, "is_array_base_cb"))
        if power_form_state['isArrayBase']:
            power_form_state['arrayId'] = st.text_input("Array ID (e.g., 'energy_effects'):", value=power_form_state.get('arrayId',''), key=_uk_pb(form_key_prefix, "array_id_input"))
            power_form_state['isDynamicArray'] = st.checkbox("Make this Array Dynamic?", value=power_form_state.get('isDynamicArray',False), key=_uk_pb(form_key_prefix, "is_dynamic_array_cb"))
            if power_form_state.get('isAlternateEffectOf'): power_form_state['isAlternateEffectOf'] = None # Cannot be base and AE
        else:
            is_ae_val = power_form_state.get('isAlternateEffectOf') is not None
            if st.checkbox("Is this an Alternate Effect (AE) of an existing Array Base?", value=is_ae_val, key=_uk_pb(form_key_prefix, "is_ae_cb")):
                array_base_options = {"": "Select Array Base Power..."}
                for p_other in char_state.get('powers', []):
                    if p_other.get('isArrayBase') or p_other.get('arrayId'):
                        if editing_id and p_other.get('id') == editing_id: continue
                        array_base_options[p_other.get('id')] = f"{p_other.get('name')} (Array: {p_other.get('arrayId', 'Default')})"
                current_ae_base_id = power_form_state.get('isAlternateEffectOf')
                sel_idx_ae = list(array_base_options.keys()).index(current_ae_base_id) if current_ae_base_id in array_base_options else 0
                new_ae_base_id = st.selectbox("Select Base Power for this AE:", options=list(array_base_options.keys()), format_func=lambda x: array_base_options.get(x,"Choose..."), index=sel_idx_ae, key=_uk_pb(form_key_prefix, "ae_of_select"))
                if new_ae_base_id != current_ae_base_id:
                    power_form_state['isAlternateEffectOf'] = new_ae_base_id
                    if new_ae_base_id:
                        base_pwr_for_ae = next((p for p in char_state.get('powers',[]) if p.get('id') == new_ae_base_id), None)
                        if base_pwr_for_ae: power_form_state['arrayId'] = base_pwr_for_ae.get('arrayId')
                    else: power_form_state['arrayId'] = None
                    st.rerun()
            else: # Not an AE
                if power_form_state.get('isAlternateEffectOf') is not None: # If it was just unchecked
                    power_form_state['isAlternateEffectOf'] = None
                    power_form_state['arrayId'] = None 
                    st.rerun()


        # --- Linked Combat Skill ---
        st.subheader("⚔️ Linked Combat Skill")
        # ... (Implementation from Part 3, assumed complete and correct) ...
        skills_list = rule_data.get('skills',{}).get('list',[]); combat_skill_options = {"": "None"}
        for sk_rule in skills_list:
            if sk_rule.get('isCombatSkill'):
                combat_skill_options[sk_rule['id']] = sk_rule['name'] + " (General)"
                for sk_id_char, sk_rank_char in char_state.get('skills',{}).items():
                    if sk_id_char.startswith(sk_rule['id'] + "_"):
                         spec_name = sk_id_char.replace(sk_rule['id'] + "_", "").replace("_"," ").title()
                         combat_skill_options[sk_id_char] = f"{sk_rule['name']}: {spec_name}"
        current_linked_skill = power_form_state.get('linkedCombatSkill')
        sel_idx_lcs = list(combat_skill_options.keys()).index(current_linked_skill) if current_linked_skill in combat_skill_options else 0
        power_form_state['linkedCombatSkill'] = st.selectbox("Link to Combat Skill (for Attack Bonus):", options=list(combat_skill_options.keys()), format_func=lambda x: combat_skill_options.get(x, "None"), index=sel_idx_lcs, key=_uk_pb(form_key_prefix, "linked_skill_select"))


        # --- Live Cost Preview ---
        st.markdown("---")
        st.subheader("💰 Estimated Power Cost")
        preview_power_def_form = copy.deepcopy(power_form_state)
        preview_power_def_form.pop('ui_state', None) 
        cost_details_preview = engine.calculate_individual_power_cost(preview_power_def_form, char_state.get('powers',[]))
        st.metric("Total Cost:", f"{cost_details_preview.get('totalCost',0)} PP")
        cost_bd = cost_details_preview.get('costBreakdown',{})
        cost_per_rank_disp = cost_details_preview.get('costPerRankFinal','N/A')
        if isinstance(cost_per_rank_disp, float): cost_per_rank_disp = f"{cost_per_rank_disp:.1f}" # Format float
        st.caption(f"Cost/Rank: {cost_per_rank_disp} | Breakdown: Base Effect {cost_bd.get('base_effect_cpr', cost_bd.get('base',0)) * power_form_state.get('rank',1):.1f}, Extras {cost_bd.get('extras_cpr',0) * power_form_state.get('rank',1):.1f}, Flaws {cost_bd.get('flaws_cpr',0) * power_form_state.get('rank',1):.1f}, Flat {cost_bd.get('flat_total',0):.1f}")
        if cost_bd.get('senses',0) > 0: st.caption(f"Senses Cost: {cost_bd['senses']:.1f}")
        if cost_bd.get('immunities',0) > 0: st.caption(f"Immunities Cost: {cost_bd['immunities']:.1f}")

        # --- Form Actions ---
        submit_col, cancel_col = st.columns(2)
        with submit_col:
            if st.form_submit_button("💾 Save Power to Character", use_container_width=True, type="primary"):
                # Construct final power object from power_form_state, removing ui_state
                final_power_data_from_form = {k:v for k,v in power_form_state.items() if k != 'ui_state'}
                final_power_data_from_form['id'] = power_form_state.get('editing_power_id') or generate_id_func("pwr_")
                
                current_powers_list = list(char_state.get('powers', [])) 
                if power_form_state.get('editing_power_id'): 
                    updated = False
                    for i, p in enumerate(current_powers_list):
                        if p.get('id') == power_form_state.get('editing_power_id'):
                            current_powers_list[i] = final_power_data_from_form
                            updated = True; break
                    if not updated: current_powers_list.append(final_power_data_from_form) 
                else: 
                    current_powers_list.append(final_power_data_from_form)
                
                update_char_value(['powers'], current_powers_list) 
                
                default_pfs = get_default_power_form_state(rule_data)
                power_form_state.clear(); power_form_state.update(default_pfs)
                st.session_state.show_power_builder_form = False 
                
                st.success(f"Power '{final_power_data_from_form['name']}' saved!")
                st.rerun() 

        with cancel_col:
            if st.form_submit_button("❌ Cancel Edit", use_container_width=True):
                default_pfs = get_default_power_form_state(rule_data)
                power_form_state.clear(); power_form_state.update(default_pfs)
                st.session_state.show_power_builder_form = False
                st.rerun()
