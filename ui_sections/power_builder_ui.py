# heroforge-mm-streamlit/ui_sections/power_builder_ui.py
# Version 1.2 (Full Effect UIs, Completed Parameters, Movement UI Finalized)

import streamlit as st
import copy
import math
import uuid # For unique IDs for modifiers in the form state etc.
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
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
        'pp_cost_in_variable': 0,
        'instance_id': str(uuid.uuid4())[:8] # For list management
    }

    return {
        'editing_power_id': None, 'name': 'New Power', 'descriptors': '', 
        'baseEffectId': default_base_effect_id, 'rank': 1, 'modifiersConfig': [], 
        'sensesConfig': [], 'immunityConfig': [], 'variableDescriptors': "", 
        'variableConfigurations': [], 
        'ally_notes_and_stats_structured': copy.deepcopy(default_ally_stat_block), 
        'create_params': { 
            'movable': False, 'stationary': False, 'innate_object': False, 
            'selective_create': False, 'subtle_object': 0, 
            'toughness_override': None, 'volume_override': None    
        },
        'affliction_params': { 
            'degree1': 'Dazed', 'degree2': 'Stunned', 'degree3': 'Incapacitated',
            'resistance_type': 'Fortitude', 'cumulative': False, 'progressive': False
        },
        'enhanced_trait_params': { 'category': 'Ability', 'trait_id': 'STR', 'enhancementAmount': 1 },
        'movement_params': { 'defined_movements': [] }, # List of {'description': str, 'ranks_consumed': int, 'instance_id': str}
        'morph_params': { 'description_of_forms': '', 'transform_scope_choice_id': None, 'metamorph_rank': 0 },
        'nullify_params': { 'descriptor_to_nullify': '', 'broad_nullify': False, 'simultaneous_nullify': False },
        'illusion_params': {'scope_id': None, 'affected_senses': [], 'visual_elements': '', 'auditory_elements': '', 'other_elements': ''},
        'remote_sensing_params': {'projected_senses': ['Visual', 'Auditory'], 'medium_flaw_desc': ''},
        'linkedCombatSkill': None, 'arrayId': None, 'isAlternateEffectOf': None, 
        'isArrayBase': False, 'isDynamicArray': False, 
        'ui_state': {
            'variable_config_trait_builder': copy.deepcopy(default_variable_config_trait_builder),
            'modifier_to_add_id': None,
            'temp_new_mod_config': {}
        } 
    }

# --- Helper UI Rendering Functions for Power Builder Sub-sections ---
def _render_modifier_parameter_input(
    st_obj: Any, mod_rule: Dict[str, Any], mod_config_entry: Dict[str, Any], 
    form_key_prefix: str, char_state: CharacterState, rule_data: RuleData, 
    engine: CoreEngine, power_form_state_ref: Dict[str, Any]
) -> None:
    param_type = mod_rule.get('parameter_type')
    param_prompt = mod_rule.get('parameter_prompt', f"Details for {mod_rule.get('name', mod_rule.get('id'))}:")
    if 'params' not in mod_config_entry: mod_config_entry['params'] = {}
    param_storage_key = mod_rule.get('parameter_storage_key', mod_rule.get('id', 'detail'))
    value_source = mod_config_entry['params']

    if param_type == "text":
        value_source[param_storage_key] = st_obj.text_input(param_prompt, value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', '')), key=_uk_pb(form_key_prefix, param_storage_key, "text"))
    elif param_type in ["text_long", "text_complex", "text_long_with_cost_note", "text_target_descriptor_or_trait", "text_long_environment_conditions", "text_long_transform_details", "text_long_summon_details"]:
        value_source[param_storage_key] = st_obj.text_area(param_prompt, value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', '')), height=75, key=_uk_pb(form_key_prefix, param_storage_key, "textarea"), help=mod_rule.get('description', ''))
    elif param_type == "number_rank": 
        max_r = mod_rule.get('maxRanks', 20)
        if mod_rule.get('maxRanks_source') == 'powerRank' or mod_rule.get('maxRanks_source') == 'powerRankOfBaseEffect':
             max_r = power_form_state_ref.get('rank', max_r) 
        value_source[param_storage_key] = st_obj.number_input(param_prompt, value=int(value_source.get(param_storage_key, mod_rule.get('parameter_default_value', 1))), min_value=mod_rule.get('minRanks', 1), max_value=max_r, step=1, key=_uk_pb(form_key_prefix, param_storage_key, "num_rank"))
    elif param_type == "number_dc":
        value_source[param_storage_key] = st_obj.number_input(param_prompt, value=int(value_source.get(param_storage_key, mod_rule.get('parameter_default_value', 10))), min_value=0, step=1, key=_uk_pb(form_key_prefix, param_storage_key, "num_dc"))
    elif param_type == "number_rank_max_3":
        value_source[param_storage_key] = st_obj.number_input(param_prompt, value=int(value_source.get(param_storage_key, mod_rule.get('parameter_default_value', 1))), min_value=1,max_value=3, step=1, key=_uk_pb(form_key_prefix,param_storage_key,"num_max3"))

    elif param_type == "select_from_options" and mod_rule.get('parameter_options'):
        options_list = mod_rule['parameter_options']; options_map_vals = [opt['value'] for opt in options_list]; options_map_labels = {opt['value']: opt.get('label', str(opt['value'])) for opt in options_list}
        current_selection = value_source.get(param_storage_key, mod_rule.get('parameter_default_value'))
        if current_selection not in options_map_vals and options_map_vals: current_selection = options_map_vals[0]
        try: sel_idx = options_map_vals.index(current_selection) if current_selection in options_map_vals else 0
        except ValueError: sel_idx = 0 
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=options_map_vals, format_func=lambda x: options_map_labels.get(x, str(x)), index=sel_idx, key=_uk_pb(form_key_prefix, param_storage_key, "selectopt"))
    
    elif param_type == "select_skill":
        all_skills_base_list = rule_data.get('skills', {}).get('list', []); char_specialized_skills = { sk_id: sk_id.replace(bs['id']+"_", "").replace("_"," ").title() + f" ({bs['name']})" for bs in all_skills_base_list if bs.get('specialization_possible') for sk_id in char_state.get('skills', {}).keys() if sk_id.startswith(bs['id']+"_")}
        skill_options = {"": "Select Skill..."}; skill_options.update({s['id']: s['name'] for s in all_skills_base_list if not s.get('specialization_possible')}); skill_options.update(char_specialized_skills)
        filter_hint = mod_rule.get('parameter_filter_hint','').lower(); skill_options_to_display = {k:v for k,v in skill_options.items() if not filter_hint or any(h in v.lower() or h in k.lower() for h in filter_hint.split(',')) or not k}; current_skill_id = value_source.get(param_storage_key); 
        try: sel_idx_skill = list(skill_options_to_display.keys()).index(current_skill_id) if current_skill_id in skill_options_to_display else 0
        except ValueError: sel_idx_skill = 0
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=list(skill_options_to_display.keys()),format_func=lambda x: skill_options_to_display.get(x,"Choose..."),index=sel_idx_skill,key=_uk_pb(form_key_prefix,param_storage_key,"selskill"))

    elif param_type == "select_power_for_link":
        linkable_powers = {"": "Select Power to Link..."}; editing_power_id = power_form_state_ref.get('editing_power_id')
        for p_other in char_state.get('powers', []):
            if p_other.get('id') != editing_power_id: linkable_powers[p_other.get('id')] = p_other.get('name', 'Unnamed Power')
        current_linked_id = value_source.get(param_storage_key, ""); 
        try: sel_idx_link = list(linkable_powers.keys()).index(current_linked_id) if current_linked_id in linkable_powers else 0
        except ValueError: sel_idx_link = 0
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=list(linkable_powers.keys()), format_func=lambda x: linkable_powers.get(x, "Choose..."), index=sel_idx_link, key=_uk_pb(form_key_prefix, param_storage_key, "sel_pwr_link"))

    elif param_type == "select_sense_type": 
        sense_type_opts = rule_data.get("sense_types_for_ui", ["Visual", "Auditory", "Olfactory", "Tactile", "Mental", "Radio", "Special (e.g., Detect)"]) 
        current_sense_type = value_source.get(param_storage_key, sense_type_opts[0] if sense_type_opts else "")
        try: sel_idx_sense = sense_type_opts.index(current_sense_type) if current_sense_type in sense_type_opts else 0
        except ValueError: sel_idx_sense = 0
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=sense_type_opts, index=sel_idx_sense, key=_uk_pb(form_key_prefix, param_storage_key, "sel_sense_type"))
    
    elif param_type == "select_defense_or_dc_type": # For Alternate Resistance
        options = ["Fortitude", "Will", "Dodge", "Toughness", "Perception DC", "Opposed Check (Skill)", "Opposed Check (Ability)"]
        current_val = value_source.get(param_storage_key, options[0])
        try: sel_idx = options.index(current_val) if current_val in options else 0
        except ValueError: sel_idx = 0
        value_source[param_storage_key] = st_obj.selectbox(param_prompt, options=options, index=sel_idx, key=_uk_pb(form_key_prefix,param_storage_key,"sel_alt_res_type"))
        if mod_rule.get('parameter_cost_options'):
            cost_opts_list = mod_rule['parameter_cost_options']
            cost_opt_vals = [opt['value'] for opt in cost_opts_list]
            cost_opt_labels = {opt['value']: opt['label'] for opt in cost_opts_list}
            cost_param_key = mod_rule.get('parameter_secondary_storage_key', 'cost_implication_choice')
            current_cost_choice = str(value_source.get(cost_param_key, cost_opt_vals[0] if cost_opt_vals else "0")) # Ensure string for comparison
            try: cost_sel_idx = cost_opt_vals.index(current_cost_choice) if current_cost_choice in cost_opt_vals else 0
            except ValueError: cost_sel_idx = 0
            value_source[cost_param_key] = st_obj.selectbox(
                mod_rule.get('parameter_secondary_prompt', "Cost Implication:"), options=cost_opt_vals,
                format_func=lambda x_cost: cost_opt_labels.get(x_cost,str(x_cost)), index=cost_sel_idx,
                key=_uk_pb(form_key_prefix, param_storage_key, "alt_res_cost_choice"),
                help="GM determines if the new resistance is harder. This choice directly impacts the modifier's cost per rank."
            )

    elif param_type == "select_sense_basic_or_detect":
        basic_senses = rule_data.get("sense_types_for_ui_basic", ["Visual", "Auditory", "Olfactory", "Tactile", "Mental", "Radio"])
        detect_option_val = "Detect_Custom"; options_with_detect = basic_senses + [detect_option_val]
        current_val = value_source.get(param_storage_key); custom_detect_value = ""
        if isinstance(current_val, dict) and current_val.get("type") == "Detect": selected_option_ui = detect_option_val; custom_detect_value = current_val.get("descriptor","")
        elif isinstance(current_val, str) and current_val.startswith("Detect:"): selected_option_ui = detect_option_val; custom_detect_value = current_val.replace("Detect:","").strip()
        elif current_val in basic_senses: selected_option_ui = current_val
        else: selected_option_ui = basic_senses[0] if basic_senses else ""
        try: sel_idx_sense_detect = options_with_detect.index(selected_option_ui) if selected_option_ui in options_with_detect else 0
        except ValueError: sel_idx_sense_detect = 0
        chosen_sense_base = st_obj.selectbox(param_prompt,options=options_with_detect,format_func=lambda x: "Detect (Specify)" if x==detect_option_val else x,index=sel_idx_sense_detect,key=_uk_pb(form_key_prefix,param_storage_key,"sel_sense_b_d"))
        if chosen_sense_base == detect_option_val:
            custom_detect_value = st_obj.text_input("Specify what is detected (e.g., Magic):", value=custom_detect_value, key=_uk_pb(form_key_prefix,param_storage_key,"cust_detect_text"))
            value_source[param_storage_key] = f"Detect: {custom_detect_value.strip()}" if custom_detect_value.strip() else detect_option_val
        else: value_source[param_storage_key] = chosen_sense_base
            
    elif param_type == "boolean_checkbox":
        value_source[param_storage_key] = st_obj.checkbox(param_prompt, value=value_source.get(param_storage_key, mod_rule.get('parameter_default_value', False)), key=_uk_pb(form_key_prefix, param_storage_key, "bool_check"))
    else:
        st_obj.warning(f"Unsupported param_type '{param_type}' for '{mod_rule.get('name')}'. Text input used.", icon="⚠️")
        value_source[param_storage_key] = st_obj.text_input(param_prompt, value=str(value_source.get(param_storage_key, mod_rule.get('parameter_default_value', ''))), key=_uk_pb(form_key_prefix, param_storage_key, "text_fallback"))

# --- Senses Configuration UI ---
def _render_senses_config_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("👁️ Configure Senses")
    st_obj.caption("Select individual sense abilities. Total cost is the sum of chosen sense abilities.")
    sense_ability_rules:List[Dict]=rule_data.get('power_senses_config', [])
    if not sense_ability_rules: st_obj.warning("Senses configuration data not found."); return
    sense_options_map={s['id']:f"{s['name']} (Cost: {s.get('cost',0)} PP)" for s in sense_ability_rules}
    current_senses_ids:List[str]=power_form_state.get('sensesConfig', [])
    senses_by_cat:Dict[str,List[Dict]]={}; [senses_by_cat.setdefault(s.get('sense_type_group','General'),[]).append(s) for s in sense_ability_rules]
    final_sel_ids=[]
    form_id_prefix_senses = power_form_state.get('editing_power_id','new_senses_power')
    for cat,senses_in_cat in sorted(senses_by_cat.items()):
        st_obj.markdown(f"**{cat}**",key=_uk_pb("sense_cat_header", form_id_prefix_senses, cat))
        cat_cols=st_obj.columns(max(1,min(len(senses_in_cat),2)))
        for idx,s_rule in enumerate(sorted(senses_in_cat,key=lambda x:x.get('name',''))):
            s_id=s_rule['id'];is_sel=s_id in current_senses_ids;key_cb=_uk_pb("sense_cb",form_id_prefix_senses, s_id)
            cb_state=cat_cols[idx%len(cat_cols)].checkbox(sense_options_map.get(s_id,s_id),value=is_sel,key=key_cb,help=s_rule.get('description',''))
            if cb_state:final_sel_ids.append(s_id)
    if set(final_sel_ids)!=set(current_senses_ids):power_form_state['sensesConfig']=final_sel_ids;st.rerun() 
    current_senses_cost=sum(s_r.get('cost',0) for s_id_sel in power_form_state.get('sensesConfig',[]) for s_r in sense_ability_rules if s_r['id']==s_id_sel)
    st_obj.metric("Cost from Senses:",f"{current_senses_cost} PP",key=_uk_pb("senses_cost_metric", form_id_prefix_senses))
    power_form_state['rank']=0 

# --- Immunity Configuration UI ---
def _render_immunity_config_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🛡️ Configure Immunities");st_obj.caption("Select immunities. Total cost is sum of choices.")
    immunity_rules:List[Dict]=rule_data.get('power_immunities_config', [])
    if not immunity_rules: st_obj.warning("Immunity configuration data not found."); return
    current_imm_ids:List[str]=power_form_state.get('immunityConfig', [])
    imm_cats:Dict[str,List[Dict]]={}; [imm_cats.setdefault(im.get('category','General'),[]).append(im) for im in immunity_rules]
    final_sel_imm_ids=[]
    form_id_prefix_imm = power_form_state.get('editing_power_id','new_imm_power')
    for cat,im_list in sorted(imm_cats.items()):
        st_obj.markdown(f"**{cat}**",key=_uk_pb("imm_cat_header",form_id_prefix_imm,cat));im_cols=st_obj.columns(max(1,min(len(im_list),2)))
        for idx,im_r in enumerate(sorted(im_list,key=lambda x:x.get('cost',0))):
            im_id=im_r['id'];is_sel_im=im_id in current_imm_ids;label=f"{im_r['name']} ({im_r['cost']} PP)";key_im_cb=_uk_pb("imm_cb",form_id_prefix_imm,im_id)
            cb_state_im=im_cols[idx%len(im_c)].checkbox(label,value=is_sel_im,key=key_im_cb,help=im_r.get('description',''))
            if cb_state_im:final_sel_imm_ids.append(im_id)
    if set(final_sel_imm_ids)!=set(current_imm_ids):power_form_state['immunityConfig']=final_sel_imm_ids;st.rerun()
    current_imm_cost=sum(im_r_sel.get('cost',0) for im_id_sel in power_form_state.get('immunityConfig',[]) for im_r_sel in immunity_rules if im_r_sel['id']==im_id_sel)
    st_obj.metric("Cost from Immunities:",f"{current_imm_cost} PP",key=_uk_pb("imm_cost_metric",form_id_prefix_imm))
    power_form_state['rank']=0

# --- Variable Power: Trait Builder UI ---
def _render_variable_config_trait_builder_ui(st_obj: Any, trait_builder_state: VariableConfigTrait, rule_data: RuleData, form_key_prefix: str, char_state_context: CharacterState ):
    st_obj.markdown("##### Add Trait to Current Configuration", key=_uk_pb(form_key_prefix,"var_trait_add_header"))
    trait_type_options = ["Power", "EnhancedAbility", "EnhancedSkill", "EnhancedDefense", "EnhancedAdvantage", "CustomText"]
    current_trait_type = trait_builder_state.get('trait_type', "Power")
    
    # Ensure baseEffectId is set if trait_type is Power and it's missing
    if current_trait_type == "Power" and not trait_builder_state.get('baseEffectId'):
        power_effects_list_vt = rule_data.get('power_effects', [])
        if power_effects_list_vt: trait_builder_state['baseEffectId'] = power_effects_list_vt[0]['id']

    new_trait_type = st_obj.selectbox("Trait Type:", trait_type_options, index=trait_type_options.index(current_trait_type), key=_uk_pb(form_key_prefix, "var_trait_type"))
    if new_trait_type != current_trait_type:
        trait_builder_state['trait_type'] = new_trait_type
        # Reset specific fields when type changes
        trait_builder_state.pop('baseEffectId', None); trait_builder_state.pop('enhanced_trait_id',None); trait_builder_state.pop('enhancementAmount',None)
        st.rerun() # Rerun to show correct fields for new type

    trait_builder_state['name'] = st_obj.text_input("Trait Name/Description:", value=trait_builder_state.get('name', "Configured Trait"), key=_uk_pb(form_key_prefix, "var_trait_name"))
    
    if trait_builder_state['trait_type'] == "Power":
        eff_opts_vt = {"": "Select Effect..."}; eff_opts_vt.update({eff['id']: eff['name'] for eff in rule_data.get('power_effects', [])})
        cur_eff_id_vt = trait_builder_state.get('baseEffectId')
        idx_eff_vt = list(eff_opts_vt.keys()).index(cur_eff_id_vt) if cur_eff_id_vt in eff_opts_vt else 0
        trait_builder_state['baseEffectId'] = st_obj.selectbox("Base Effect:", options=list(eff_opts_vt.keys()), format_func=lambda x: eff_opts_vt.get(x, "Choose..."), key=_uk_pb(form_key_prefix, "var_trait_pwr_effect"), index=idx_eff_vt)
        trait_builder_state['rank'] = st_obj.number_input("Rank:", min_value=0, value=trait_builder_state.get('rank',1), key=_uk_pb(form_key_prefix, "var_trait_pwr_rank"))
        trait_builder_state['modifiers_text_desc'] = st_obj.text_area("Modifiers (Text Description):", value=trait_builder_state.get('modifiers_text_desc',''), key=_uk_pb(form_key_prefix, "var_trait_pwr_mods_text"), height=75)
        trait_builder_state['pp_cost_in_variable'] = st_obj.number_input("Asserted PP Cost for this Power:", min_value=0, value=trait_builder_state.get('pp_cost_in_variable',0), key=_uk_pb(form_key_prefix, "var_trait_pwr_asserted_cost"), help="Manually enter the calculated cost for this power configuration.")
    
    elif trait_builder_state['trait_type'].startswith("Enhanced"):
        trait_builder_state['enhanced_trait_category'] = trait_builder_state['trait_type'].replace("Enhanced","") # Ability, Skill, etc.
        
        et_id_opts = {"": f"Select {trait_builder_state['enhanced_trait_category']}..."}
        if trait_builder_state['enhanced_trait_category'] == "Ability": et_id_opts.update({ab['id']:ab['name'] for ab in rule_data.get('abilities',{}).get('list',[])})
        elif trait_builder_state['enhanced_trait_category'] == "Skill": 
            all_sk_base = rule_data.get('skills',{}).get('list',[]); et_id_opts.update({s['id']:s['name'] for s in all_sk_base if not s.get('specialization_possible')})
            et_id_opts.update({sk_id: sk_id.replace(bs['id']+"_","").replace("_"," ").title()+f" ({bs['name']})" for bs in all_sk_base if bs.get('specialization_possible') for sk_id in char_state_context.get('skills',{}).keys() if sk_id.startswith(bs['id']+"_")})
        elif trait_builder_state['enhanced_trait_category'] == "Defense": et_id_opts.update({d:d for d in ["Dodge","Parry","Toughness","Fortitude","Will"]})
        elif trait_builder_state['enhanced_trait_category'] == "Advantage": et_id_opts.update({adv['id']:adv['name'] for adv in rule_data.get('advantages_v1',[])})

        cur_et_id = trait_builder_state.get('enhanced_trait_id')
        idx_et_id = list(et_id_opts.keys()).index(cur_et_id) if cur_et_id in et_id_opts else 0
        trait_builder_state['enhanced_trait_id'] = st_obj.selectbox(f"{trait_builder_state['enhanced_trait_category']} to Enhance:", options=list(et_id_opts.keys()), format_func=lambda x: et_id_opts.get(x,"Choose..."), key=_uk_pb(form_key_prefix,"var_trait_enh_id"), index=idx_et_id)
        trait_builder_state['enhancementAmount'] = st_obj.number_input("Enhancement Amount (+ ranks):", min_value=1, value=trait_builder_state.get('enhancementAmount',1), key=_uk_pb(form_key_prefix, "var_trait_enh_amt"))
        
        # Auto-calculate cost for Enhanced Traits
        cost_per_rank_et = CoreEngine().get_trait_cost_per_rank(trait_builder_state['enhanced_trait_category'], trait_builder_state.get('enhanced_trait_id')) # Use a temp engine instance or pass main one
        trait_builder_state['pp_cost_in_variable'] = math.ceil(trait_builder_state['enhancementAmount'] * cost_per_rank_et)
        st_obj.caption(f"Calculated Cost: {trait_builder_state['pp_cost_in_variable']} PP (based on {cost_per_rank_et} PP/rank)")

    elif trait_builder_state['trait_type'] == "CustomText":
        # Name/Description is already captured. Primarily for user to assert cost.
        trait_builder_state['pp_cost_in_variable'] = st_obj.number_input("Asserted PP Cost for this Custom Trait:", min_value=0, value=trait_builder_state.get('pp_cost_in_variable',0), key=_uk_pb(form_key_prefix, "var_trait_cust_asserted_cost"))


# --- Variable Power: Main Configuration UI ---
def _render_variable_configurations_ui(st_obj: Any, power_form_state: Dict[str, Any], char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, generate_id_func: Callable):
    st_obj.subheader("⚙️ Define Variable Configurations")
    power_rank_var = power_form_state.get('rank', 1); variable_pool_pp_var = power_rank_var * 5
    st_obj.info(f"Available Variable Pool for each configuration: **{variable_pool_pp_var} PP**")
    power_form_state['variableDescriptors'] = st_obj.text_area("Variable Descriptors (e.g., 'Skills and Advantages', 'Fire Powers'):", value=power_form_state.get('variableDescriptors', ''), key=_uk_pb(power_form_state.get('editing_power_id','new'), "var_descriptors"))
    
    if 'variableConfigurations' not in power_form_state: power_form_state['variableConfigurations'] = []
    
    configs_to_keep_var = []
    for i_cfg, config_entry_var in enumerate(power_form_state['variableConfigurations']):
        config_id_var = config_entry_var.get('instance_id', generate_id_func("var_cfg_")); config_entry_var['instance_id'] = config_id_var # Ensure ID
        
        with st_obj.expander(f"Configuration #{i_cfg+1}: {config_entry_var.get('configName', 'Unnamed Config')}", expanded=True):
            cols_cfg_header_var = st_obj.columns([0.8, 0.2])
            config_entry_var['configName'] = cols_cfg_header_var[0].text_input("Config Name:", value=config_entry_var.get('configName', f'Form {i_cfg+1}'), key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_name", config_id_var))
            
            st_obj.markdown("**Traits in this Configuration:**"); config_total_cost_var = 0
            current_config_traits = config_entry_var.get('configTraits', [])
            if not current_config_traits: st_obj.caption("No traits added yet.")
            
            traits_to_keep_in_config_var = []
            for t_idx_var, trait_var in enumerate(current_config_traits):
                trait_id_inst_var = trait_var.get('instance_id', generate_id_func("var_trait_")); trait_var['instance_id'] = trait_id_inst_var # Ensure ID
                t_cost_var = trait_var.get('pp_cost_in_variable', 0); config_total_cost_var += t_cost_var
                
                t_cols_var = st_obj.columns([0.8,0.2])
                trait_display_name = trait_var.get('name','Trait')
                trait_type_disp = trait_var.get('trait_type','N/A')
                trait_rank_disp_parts = []
                if 'rank' in trait_var: trait_rank_disp_parts.append(f"R{trait_var['rank']}")
                if 'enhancementAmount' in trait_var: trait_rank_disp_parts.append(f"+{trait_var['enhancementAmount']}")
                trait_rank_str = ", ".join(trait_rank_disp_parts)
                
                t_cols_var[0].markdown(f"- **{trait_display_name}** ({trait_type_disp}{f', {trait_rank_str}' if trait_rank_str else ''}) - *Cost: {t_cost_var} PP*", key=_uk_pb(power_form_state.get('editing_power_id','new'),"var_trait_disp",config_id_var,trait_id_inst_var))
                if t_cols_var[1].button("➖", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_rem_trait", config_id_var, trait_id_inst_var), help="Remove Trait"): pass
                else: traits_to_keep_in_config_var.append(trait_var)
            
            if len(traits_to_keep_in_config_var) != len(current_config_traits): 
                config_entry_var['configTraits'] = traits_to_keep_in_config_var; st.rerun()

            # Trait Builder UI for this specific configuration
            current_trait_builder_state = power_form_state['ui_state']['variable_config_trait_builder']
            _render_variable_config_trait_builder_ui(st_obj, current_trait_builder_state, rule_data, _uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_traitbuild", config_id_var), char_state)
            
            if st_obj.button("➕ Add Trait to This Configuration", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_add_trait_btn", config_id_var)):
                new_trait_to_add_var = copy.deepcopy(current_trait_builder_state)
                new_trait_to_add_var['instance_id'] = generate_id_func("var_trait_") # New instance ID for the trait
                
                if 'configTraits' not in config_entry_var: config_entry_var['configTraits'] = []
                config_entry_var['configTraits'].append(new_trait_to_add_var)
                # Reset builder for next trait
                power_form_state['ui_state']['variable_config_trait_builder'] = copy.deepcopy(get_default_power_form_state(rule_data)['ui_state']['variable_config_trait_builder'])
                st.rerun()

            st_obj.metric(f"Config Total Cost:", f"{config_total_cost_var} / {variable_pool_pp_var} PP", delta_color="normal" if config_total_cost_var <= variable_pool_pp_var else "inverse", key=_uk_pb(power_form_state.get('editing_power_id','new'),"var_cfg_cost_metric",config_id_var))
            if config_total_cost_var > variable_pool_pp_var: st_obj.error("Configuration cost exceeds Variable Pool for this power rank!", icon="⚠️")
            
            if cols_cfg_header_var[1].button("🗑️ Remove This Configuration", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_remove_btn", config_id_var), type="secondary"): pass
            else: configs_to_keep_var.append(config_entry_var)
    
    if len(configs_to_keep_var) != len(power_form_state['variableConfigurations']): 
        power_form_state['variableConfigurations'] = configs_to_keep_var; st.rerun()
    
    if st_obj.button("➕ Add New Variable Configuration Slot", key=_uk_pb(power_form_state.get('editing_power_id','new'), "varcfg_add_slot_btn")):
        new_config_id_var = generate_id_func("var_cfg_")
        power_form_state['variableConfigurations'].append({'instance_id': new_config_id_var, 'configName': f'Config Slot {len(power_form_state["variableConfigurations"])+1}', 'configTraits': [], 'assertedConfigCost': 0})
        st.rerun()

# --- Ally (Summon/Duplication) Stat Block UI ---
def _render_ally_creation_stat_block_ui(st_obj: Any, power_form_state: Dict[str, Any], char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, base_effect_rule: Dict[str, Any]):
    st_obj.subheader(f"🐾 Define {base_effect_rule.get('name','Creation')} Details")
    # Ensure structure exists and has defaults
    if 'ally_notes_and_stats_structured' not in power_form_state or not isinstance(power_form_state['ally_notes_and_stats_structured'], dict):
        power_form_state['ally_notes_and_stats_structured'] = copy.deepcopy(get_default_power_form_state(rule_data)['ally_notes_and_stats_structured'])
    
    ally_data = power_form_state['ally_notes_and_stats_structured']
    default_ally_block = get_default_power_form_state(rule_data)['ally_notes_and_stats_structured']
    for key, default_val in default_ally_block.items():
        ally_data.setdefault(key, default_val) # Ensure all keys from default are present

    allotted_pp_ally = power_form_state.get('rank',0) * base_effect_rule.get('grantsAllyPointsFactor',15)
    st_obj.info(f"This {base_effect_rule.get('name','Creation')} is built on **{allotted_pp_ally} Power Points** (derived from the main power's rank: {power_form_state.get('rank',0)}).")
    
    form_key_prefix_ally = _uk_pb(power_form_state.get('editing_power_id','new'), base_effect_rule.get('id','ally_creation'))
    
    ally_data['name'] = st_obj.text_input(f"{base_effect_rule.get('name','Creation')} Name/Type:", value=ally_data.get('name', f"My {base_effect_rule.get('name','Creation')}"), key=_uk_pb(form_key_prefix_ally, "name"))
    ally_data['pl_for_ally'] = st_obj.number_input(f"{base_effect_rule.get('name','Creation')}'s Power Level:", min_value=0, value=int(ally_data.get('pl_for_ally', char_state.get('powerLevel',10) - 2)), step=1, key=_uk_pb(form_key_prefix_ally, "pl"))
    ally_data['cost_pp_asserted_by_user'] = st_obj.number_input(f"Asserted PP Cost for {base_effect_rule.get('name','Creation')}'s Build:", min_value=0, value=int(ally_data.get('cost_pp_asserted_by_user',0)), step=1, key=_uk_pb(form_key_prefix_ally, "asserted_cost"), help=f"This must be less than or equal to the allotted {allotted_pp_ally} PP.")
    if ally_data['cost_pp_asserted_by_user'] > allotted_pp_ally:
        st_obj.error(f"Asserted cost ({ally_data['cost_pp_asserted_by_user']}) exceeds the allotted pool of {allotted_pp_ally} PP for this creation!", icon="⚠️")

    st_obj.markdown("**Simplified Stat Block Summary:** (Describe key traits. Detailed build occurs offline.)")
    ally_data['abilities_summary_text'] = st_obj.text_area("Key Abilities (e.g., STR 2, AGL 4):", value=ally_data.get("abilities_summary_text",""), height=50, key=_uk_pb(form_key_prefix_ally,"abil_sum_text"))
    ally_data['defenses_summary_text'] = st_obj.text_area("Key Defenses (e.g., Dodge 6, Toughness 4):", value=ally_data.get("defenses_summary_text",""), height=50, key=_uk_pb(form_key_prefix_ally,"def_sum_text"))
    ally_data['skills_summary_text'] = st_obj.text_area("Key Skills (e.g., Stealth +8, Perception +5):", value=ally_data.get("skills_summary_text",""), height=75, key=_uk_pb(form_key_prefix_ally,"skills_sum_text"))
    ally_data['powers_advantages_summary_text'] = st_obj.text_area("Key Powers & Advantages (briefly):", value=ally_data.get("powers_advantages_summary_text",""), height=100, key=_uk_pb(form_key_prefix_ally,"pwr_adv_sum_text"))
    ally_data['notes'] = st_obj.text_area("Notes (behavior, appearance, etc.):", value=ally_data.get("notes",""), height=75, key=_uk_pb(form_key_prefix_ally,"notes_text"))


# --- Affliction Parameters UI ---
def _render_affliction_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🤢 Configure Affliction Parameters")
    if 'affliction_params' not in power_form_state: power_form_state['affliction_params'] = copy.deepcopy(get_default_power_form_state(rule_data)['affliction_params'])
    aff_params = power_form_state['affliction_params']
    form_key_prefix_aff = _uk_pb(power_form_state.get('editing_power_id','new'), "affliction")

    aff_params['degree1'] = st_obj.text_input("1st Degree Condition(s):", value=aff_params.get('degree1', 'Dazed'), key=_uk_pb(form_key_prefix_aff,"deg1"))
    aff_params['degree2'] = st_obj.text_input("2nd Degree Condition(s):", value=aff_params.get('degree2', 'Stunned'), key=_uk_pb(form_key_prefix_aff,"deg2"))
    aff_params['degree3'] = st_obj.text_input("3rd Degree Condition(s):", value=aff_params.get('degree3', 'Incapacitated'), key=_uk_pb(form_key_prefix_aff,"deg3"))
    
    resistance_options_aff = ["Fortitude", "Will", "Dodge"]; current_res_aff = aff_params.get('resistance_type', 'Fortitude')
    res_idx_aff = resistance_options_aff.index(current_res_aff) if current_res_aff in resistance_options_aff else 0
    aff_params['resistance_type'] = st_obj.selectbox("Resisted By:", options=resistance_options_aff, index=res_idx_aff, key=_uk_pb(form_key_prefix_aff,"res_type"))
    
    # Cumulative and Progressive are standard Extras, added via modifier system.
    # This section is for core Affliction parameters only.

# --- Enhanced Trait UI ---
def _render_enhanced_trait_params_ui(st_obj: Any, power_form_state: Dict[str, Any], char_state: CharacterState, rule_data: RuleData, engine: CoreEngine):
    st_obj.subheader("➕ Configure Enhanced Trait")
    if 'enhanced_trait_params' not in power_form_state: power_form_state['enhanced_trait_params'] = copy.deepcopy(get_default_power_form_state(rule_data)['enhanced_trait_params'])
    et_params = power_form_state['enhanced_trait_params']
    form_key_prefix_et = _uk_pb(power_form_state.get('editing_power_id','new'), "enhanced_trait")
    
    base_effect_rule_et = next((eff for eff in rule_data.get('power_effects', []) if eff['id'] == 'eff_enhanced_trait'), {})
    trait_categories_et = base_effect_rule_et.get('enhancementTargetCategories', ["Ability", "Skill", "Advantage", "Defense", "PowerRank"])
    
    current_cat_et = et_params.get('category', trait_categories_et[0]); 
    cat_idx_et = trait_categories_et.index(current_cat_et) if current_cat_et in trait_categories_et else 0
    
    new_cat_et = st_obj.selectbox("Trait Category to Enhance:", options=trait_categories_et, index=cat_idx_et, key=_uk_pb(form_key_prefix_et,"category"))
    if new_cat_et != et_params.get('category'):
        et_params['category'] = new_cat_et
        et_params['trait_id'] = None # Reset trait ID on category change
        st.rerun()

    trait_options_et = {"": f"Select {et_params['category']}..."}
    if et_params['category'] == "Ability": trait_options_et.update({ab['id']: ab['name'] for ab in rule_data.get('abilities',{}).get('list',[])})
    elif et_params['category'] == "Skill":
        all_skills_base_et = rule_data.get('skills', {}).get('list', [])
        char_spec_skills_et = { sk_id: engine.get_skill_name_by_id(sk_id, all_skills_base_et) for sk_id in char_state.get('skills', {}).keys() if "_" in sk_id}
        trait_options_et.update({s['id']: s['name'] for s in all_skills_base_et}); trait_options_et.update(char_spec_skills_et)
    elif et_params['category'] == "Advantage": trait_options_et.update({adv['id']: adv['name'] for adv in rule_data.get('advantages_v1',[])})
    elif et_params['category'] == "Defense": trait_options_et.update({d_id: d_id for d_id in ["Dodge", "Parry", "Toughness", "Fortitude", "Will"]})
    elif et_params['category'] == "PowerRank": 
        trait_options_et.update({pwr['id']: pwr.get('name','Unnamed Power') for pwr in char_state.get('powers',[]) if pwr.get('id') != power_form_state.get('editing_power_id')}) # Exclude self
    
    current_trait_id_et = et_params.get('trait_id')
    if current_trait_id_et not in trait_options_et and len(trait_options_et) > 1:
        current_trait_id_et = list(trait_options_et.keys())[1] 
        et_params['trait_id'] = current_trait_id_et
    trait_idx_et = list(trait_options_et.keys()).index(current_trait_id_et) if current_trait_id_et in trait_options_et else 0
    et_params['trait_id'] = st_obj.selectbox(f"Specific {et_params['category']} to Enhance:", options=list(trait_options_et.keys()), format_func=lambda x: trait_options_et.get(x, "Choose..."), index=trait_idx_et, key=_uk_pb(form_key_prefix_et,"trait_id_select"))
    
    # Rank of Enhanced Trait power IS the enhancementAmount
    current_enh_amount = power_form_state.get('rank',1) # Use power_form_state.rank as the source of truth
    new_enh_amount_et = st_obj.number_input("Enhancement Amount (+ Ranks for Trait):", min_value=1, value=current_enh_amount, step=1, key=_uk_pb(form_key_prefix_et,"enhancement_amount_input"))
    if new_enh_amount_et != current_enh_amount:
        power_form_state['rank'] = new_enh_amount_et # Update main power rank
        et_params['enhancementAmount'] = new_enh_amount_et # Sync with params too
        st.rerun()
    else: # Ensure param is synced if rank was changed elsewhere
        et_params['enhancementAmount'] = current_enh_amount


# --- Create Effect Parameters UI ---
def _render_create_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🛠️ Configure Create Effect")
    if 'create_params' not in power_form_state: power_form_state['create_params'] = copy.deepcopy(get_default_power_form_state(rule_data)['create_params'])
    create_params = power_form_state['create_params']
    form_key_prefix_create = _uk_pb(power_form_state.get('editing_power_id','new'), "create_effect")

    create_params['movable'] = st_obj.checkbox("Movable Extra?", value=create_params.get('movable', False), key=_uk_pb(form_key_prefix_create,"movable"), help="Created object can be moved. (+1 PP/rank)")
    create_params['stationary'] = st_obj.checkbox("Stationary Extra? (Immobile, Tethered)", value=create_params.get('stationary', False), key=_uk_pb(form_key_prefix_create,"stationary"), help="Object cannot be moved once created. (+0 PP/rank)")
    create_params['innate_object'] = st_obj.checkbox("Innate Object? (Nullify doesn't affect)", value=create_params.get('innate_object', False), key=_uk_pb(form_key_prefix_create,"innate_obj"), help="Like Innate Extra for created objects. (+1 flat PP)")
    create_params['selective_create'] = st_obj.checkbox("Selective Create? (Exclude targets in area)", value=create_params.get('selective_create', False), key=_uk_pb(form_key_prefix_create,"selective_obj"), help="If Area effect, can choose not to affect specific targets. (+1 PP/rank)")
    
    create_params['toughness_override'] = st_obj.number_input(
        "Override Object Toughness (Optional, 0 to use Create Rank):", 
        min_value=0, value=int(create_params.get('toughness_override', power_form_state.get('rank',1)) or power_form_state.get('rank',1)), 
        step=1, format="%d", key=_uk_pb(form_key_prefix_create,"tough_override"), 
        help="Default is Create Power Rank. Set to 0 to explicitly use power rank. Overriding might have PP cost implications handled by GM or Feature extras."
    )
    if create_params['toughness_override'] == 0: create_params['toughness_override'] = None 
    st_obj.caption(f"Object Volume Rank will typically be equal to Create Power Rank ({power_form_state.get('rank',1)}).")

# --- Movement Effect Parameters UI ---
def _render_movement_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData, engine: CoreEngine, generate_id_func: Callable): # Added engine and generate_id_func
    st_obj.subheader("🏃 Configure Movement Effect")
    if 'movement_params' not in power_form_state: power_form_state['movement_params'] = {'defined_movements': []}
    mov_params = power_form_state['movement_params']
    if 'defined_movements' not in mov_params: mov_params['defined_movements'] = []
    
    form_key_prefix_mov = _uk_pb(power_form_state.get('editing_power_id','new'), "move_effect_params")
    power_rank_mov = power_form_state.get('rank', 1)
    total_maps_avail = power_rank_mov * 2 # Each rank of Movement power (2PP) gives 2 "Movement Allocation Points" (MAPs)
    st_obj.info(f"Movement Power Rank {power_rank_mov} provides **{total_maps_avail} Movement Allocation Points (MAPs)** for specific movement modes.")

    current_def_mov = list(mov_params.get('defined_movements', []))
    mov_to_keep = []; total_maps_used = 0
    if current_def_mov: st_obj.markdown("**Configured Movement Modes:**")
    for idx_mov, move_e in enumerate(current_def_mov):
        move_e_id = move_e.get('instance_id', generate_id_func("move_mode_")); move_e['instance_id'] = move_e_id
        cols_mov_edit = st_obj.columns([0.5, 0.2, 0.2, 0.1]);
        new_desc_mov = cols_mov_edit[0].text_input(f"Mode #{idx_mov+1} Desc:", value=move_e.get('description', ''), key=_uk_pb(form_key_prefix_mov, "desc", move_e_id))
        new_ranks_mode_mov = cols_mov_edit[1].number_input("Ranks of Mode:", min_value=1, value=int(move_e.get('ranks_of_mode', 1)), step=1, key=_uk_pb(form_key_prefix_mov, "mode_ranks", move_e_id))
        new_maps_per_rank_mode_mov = cols_mov_edit[2].selectbox("MAPs/Rank of Mode:", options=[1,2], index=[1,2].index(int(move_e.get('maps_per_rank_of_mode',1))), help="1 MAP for 1PP/rank types (e.g. Wall-Crawling), 2 MAPs for 2PP/rank types (e.g. Dimensional).", key=_uk_pb(form_key_prefix_mov, "map_cost", move_e_id))
        mode_cost_maps_mov = new_ranks_mode_mov * new_maps_per_rank_mode_mov; total_maps_used += mode_cost_maps_mov
        st_obj.caption(f"Cost: {mode_cost_maps_mov} MAPs", key=_uk_pb(form_key_prefix_mov,"mode_cost_disp_item", move_e_id))
        if new_desc_mov!=move_e.get('description') or new_ranks_mode_mov!=move_e.get('ranks_of_mode') or new_maps_per_rank_mode_mov!=move_e.get('maps_per_rank_of_mode'):
            move_e['description']=new_desc_mov; move_e['ranks_of_mode']=new_ranks_mode_mov; move_e['maps_per_rank_of_mode']=new_maps_per_rank_mode_mov
        if cols_mov_edit[3].button("➖", key=_uk_pb(form_key_prefix_mov, "del_mode", move_e_id), help="Remove mode"): pass
        else: mov_to_keep.append(move_e)
    if len(mov_to_keep)!=len(current_def_mov): mov_params['defined_movements']=mov_to_keep; st.rerun()
    st_obj.metric("Total MAPs Consumed:",f"{total_maps_used}/{total_maps_avail} MAPs",delta_color="inverse" if total_maps_used>total_maps_avail else "normal", key=_uk_pb(form_key_prefix_mov,"total_maps_metric"))
    if total_maps_used>total_maps_avail:st_obj.error("Consumed MAPs exceed available MAPs!", icon="⚠️")
    with st_obj.form(key=_uk_pb(form_key_prefix_mov, "add_mode_form"), clear_on_submit=True):
        st_obj.markdown("*Add New Movement Mode:*"); new_mode_desc_form = st.text_input("Desc (e.g., Wall-Crawling, Sure-Footed):", key=_uk_pb(form_key_prefix_mov,"new_desc_form"))
        new_mode_ranks_form = st.number_input("Ranks in this mode:", min_value=1, value=1, step=1, key=_uk_pb(form_key_prefix_mov,"new_ranks_form"))
        new_mode_maps_per_rank_form = st.selectbox("MAPs cost per rank of this mode:",options=[1,2],index=0,format_func=lambda x:f"{x} MAP(s) ({x}PP type)",key=_uk_pb(form_key_prefix_mov,"new_map_cost_form"))
        if st.form_submit_button("➕ Add Movement Mode"):
            if new_mode_desc_form.strip():
                mov_params.get('defined_movements',[]).append({'instance_id':generate_id_func("move_mode_"),'description':new_mode_desc_form.strip(),'ranks_of_mode':new_mode_ranks_form,'maps_per_rank_of_mode':new_mode_maps_per_rank_form})
                st.rerun()

# --- Morph/Transform Parameters UI ---
def _render_morph_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🎭 Configure Morph/Transform")
    if 'morph_params' not in power_form_state: power_form_state['morph_params'] = copy.deepcopy(get_default_power_form_state(rule_data)['morph_params'])
    morph_params = power_form_state['morph_params']
    form_key_prefix_morph = _uk_pb(power_form_state.get('editing_power_id','new'), "morph_transform")
    base_effect_id_morph = power_form_state.get('baseEffectId')
    base_effect_rule_morph = next((eff for eff in rule_data.get('power_effects', []) if eff['id'] == base_effect_id_morph), None)

    morph_params['description_of_forms'] = st_obj.text_area("Description of Forms Assumed or Transformation Effect:",value=morph_params.get('description_of_forms', ""),height=75,key=_uk_pb(form_key_prefix_morph, "forms_description"),help="For Morph, describe the range of forms (e.g., 'Humanoids of similar mass', 'Specific Person', 'Any Animal'). For Transform, describe what it turns subjects into (e.g., 'Inanimate objects', 'Small animals').")
    
    if base_effect_id_morph == 'eff_transform' and base_effect_rule_morph and base_effect_rule_morph.get('isTransformContainer') and base_effect_rule_morph.get('costOptions'):
        st_obj.markdown("**Transformation Scope (determines cost per rank for Transform):**")
        cost_opts_map_labels_morph = {opt['choice_id']: opt['label'] for opt in base_effect_rule_morph['costOptions']}
        cost_opts_map_vals_morph = [opt['choice_id'] for opt in base_effect_rule_morph['costOptions']]
        current_scope_id_morph = morph_params.get('transform_scope_choice_id', cost_opts_map_vals_morph[0] if cost_opts_map_vals_morph else None)
        sel_idx_scope_morph = cost_opts_map_vals_morph.index(current_scope_id_morph) if current_scope_id_morph in cost_opts_map_vals_morph else 0
        new_scope_id_morph = st_obj.selectbox("Select Transformation Scope:",options=cost_opts_map_vals_morph,format_func=lambda x: cost_opts_map_labels_morph.get(x,"Scope..."),index=sel_idx_scope_morph,key=_uk_pb(form_key_prefix_morph, "transform_scope_select"))
        if new_scope_id_morph != current_scope_id_morph: morph_params['transform_scope_choice_id'] = new_scope_id_morph; # Engine uses this for cost
    
    # Metamorph Extra (if added via modifier system) can grant ranks here.
    # This is primarily for the base Morph/Transform effect description.
    # For Morph, ranks determine variety; for Transform, rank determines DC.

# --- Nullify Parameters UI ---
def _render_nullify_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    st_obj.subheader("🚫 Configure Nullify")
    if 'nullify_params' not in power_form_state: power_form_state['nullify_params'] = copy.deepcopy(get_default_power_form_state(rule_data)['nullify_params'])
    null_params = power_form_state['nullify_params']
    form_key_prefix_null = _uk_pb(power_form_state.get('editing_power_id','new'), "nullify_effect")
    null_params['descriptor_to_nullify'] = st_obj.text_input("Descriptor(s) or Specific Power Name to Nullify:",value=null_params.get('descriptor_to_nullify', ""),key=_uk_pb(form_key_prefix_null, "nullify_descriptor"),help="E.g., 'Fire powers', 'Magic', 'Flight power of Target X'. For broader categories, use the Broad extra.")
    # Broad and Simultaneous are standard Extras, should be added via the modifier system.

# --- Illusion Parameters UI ---
def _render_illusion_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    # (Implementation from previous response, assumed complete)
    st_obj.subheader("✨ Configure Illusion Effect")
    ill_params = power_form_state.get('illusion_params', {'scope_id': None, 'affected_senses': []})
    base_effect_rule = next((eff for eff in rule_data.get('power_effects', []) if eff['id'] == 'eff_illusion'), {})
    cost_options = base_effect_rule.get('costOptions', []); scope_options_map = {opt['choice_id']: opt['label'] for opt in cost_options}; scope_vals = [opt['choice_id'] for opt in cost_options]
    current_scope = ill_params.get('scope_id', scope_vals[0] if scope_vals else None); sel_idx_scope = scope_vals.index(current_scope) if current_scope in scope_vals else 0
    new_scope = st_obj.selectbox("Illusion Scope:",options=scope_vals,format_func=lambda x:scope_options_map.get(x,"Scope..."),index=sel_idx_scope,key=_uk_pb("ill_scope_sel"))
    if new_scope!=current_scope: ill_params['scope_id']=new_scope;ill_params['affected_senses']=[];st.rerun()
    available_senses_ill = ["Visual", "Auditory", "Mental", "Olfactory", "Tactile"]
    if new_scope and "all_senses" in new_scope.lower(): ill_params['affected_senses']=list(available_senses_ill); st_obj.caption("Scope covers all senses.")
    elif new_scope and any(s_num in new_scope.lower() for s_num in ["one_sense","two_senses","three_senses","four_senses"]):
        max_sel=1; [max_sel:=v for k,v in {"two":2,"three":3,"four":4}.items() if k in new_scope.lower()]
        sel_senses=st_obj.multiselect(f"Affected Sense(s) (Max {max_sel}):",options=available_senses_ill,default=ill_params.get('affected_senses',[]),key=_uk_pb("ill_aff_senses_ms"))
        if len(sel_senses)>max_sel: st_obj.warning(f"Max {max_sel} sense(s) for this scope.",icon="⚠️"); ill_params['affected_senses']=sel_senses[:max_sel]
        else: ill_params['affected_senses']=sel_senses
    else: ill_params['affected_senses']=[]
    ill_params['visual_elements']=st_obj.text_area("Visual Elements:",value=ill_params.get('visual_elements',''),height=50,key=_uk_pb("ill_vis_txt"))
    ill_params['auditory_elements']=st_obj.text_area("Auditory Elements:",value=ill_params.get('auditory_elements',''),height=50,key=_uk_pb("ill_aud_txt"))
    ill_params['other_elements']=st_obj.text_area("Other Sensory Elements (Tactile, Olfactory, Mental):",value=ill_params.get('other_elements',''),height=50,key=_uk_pb("ill_oth_txt"))
    power_form_state['illusion_params'] = ill_params

# --- Remote Sensing Parameters UI ---
def _render_remote_sensing_params_ui(st_obj: Any, power_form_state: Dict[str, Any], rule_data: RuleData):
    # (Implementation from previous response, assumed complete)
    st_obj.subheader("📡 Configure Remote Sensing")
    rs_params = power_form_state.get('remote_sensing_params', {'projected_senses': ['Visual', 'Auditory']})
    all_poss_senses_rs = ["Visual", "Auditory", "Mental", "Olfactory", "Tactile", "Radio", "Special (e.g. Detect X)"]
    rs_params['projected_senses'] = st_obj.multiselect("Senses to Project:",options=all_poss_senses_rs,default=rs_params.get('projected_senses',['Visual','Auditory']),key=_uk_pb("rs_proj_senses_ms"))
    cost_notes_rs=[]; 
    if "Visual" in rs_params['projected_senses']: cost_notes_rs.append("Visual (+2/rank)")
    if "Auditory" in rs_params['projected_senses']: cost_notes_rs.append("Auditory (+1/rank)")
    other_s_sel_rs=[s for s in rs_params['projected_senses'] if s not in ["Visual","Auditory"]]; 
    if other_s_sel_rs: cost_notes_rs.append(f"{len(other_s_sel_rs)} Other (+{len(other_s_sel_rs)}/rank)")
    if cost_notes_rs: st_obj.caption(f"Cost Implication: {', '.join(cost_notes_rs)} of Remote Sensing Rank.")
    rs_params['medium_flaw_desc']=st_obj.text_input("Medium Flaw Description (Optional):",value=rs_params.get('medium_flaw_desc',''),key=_uk_pb("rs_med_flaw_txt"),help="E.g., 'Only through reflective surfaces'")
    power_form_state['remote_sensing_params'] = rs_params


# --- Main Power Builder Form ---
# (The rest of render_power_builder_form from previous responses, calling the fully implemented helpers above)
def render_power_builder_form(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    power_form_state: Dict[str, Any], 
    generate_id_func: Callable[[str], str]
):
    """
    Renders the main form for adding or editing a power.
    Manages the power_form_state directly (which is expected to be st.session_state.power_form_state).
    """
    form_key_prefix = power_form_state.get('editing_power_id') or "new_power_form" 
    
    # Use a single form for the whole power builder to manage state and updates better
    with st_obj.form(key=_uk_pb("power_form_main", form_key_prefix), clear_on_submit=False):
        editing_id = power_form_state.get('editing_power_id')
        if editing_id:
            st_obj.subheader(f"Edit Power: {power_form_state.get('name', '')} (ID: {editing_id})")
        else:
            st_obj.subheader("✨ Add New Power ✨")

        # --- Basic Info ---
        col1_basic, col2_basic = st_obj.columns([3,1])
        power_form_state['name'] = col1_basic.text_input("Power Name:", value=power_form_state.get('name', 'New Power'), key=_uk_pb(form_key_prefix, "name"))
        
        effect_options = {"": "Select Base Effect..."}
        power_effects_list = rule_data.get('power_effects', [])
        effect_options.update({eff['id']: eff['name'] for eff in power_effects_list})
        
        current_effect_id = power_form_state.get('baseEffectId', list(effect_options.keys())[1] if len(effect_options)>1 else "")
        if current_effect_id not in effect_options and effect_options: 
            current_effect_id = list(effect_options.keys())[1] if len(effect_options) > 1 else list(effect_options.keys())[0]
            power_form_state['baseEffectId'] = current_effect_id

        effect_idx = list(effect_options.keys()).index(current_effect_id) if current_effect_id in effect_options else 0
        
        new_base_effect_id = col2_basic.selectbox(
            "Base Effect:", options=list(effect_options.keys()), 
            format_func=lambda x: effect_options.get(x, "Choose..."),
            index=effect_idx, key=_uk_pb(form_key_prefix, "base_effect_select")
        )
        
        if new_base_effect_id != current_effect_id:
            power_form_state['baseEffectId'] = new_base_effect_id
            # Reset effect-specific params when base effect changes
            default_state_for_reset = get_default_power_form_state(rule_data)
            for param_key in ['sensesConfig', 'immunityConfig', 'variableConfigurations', 
                              'affliction_params', 'enhanced_trait_params', 'create_params', 
                              'movement_params', 'morph_params', 'nullify_params', 
                              'illusion_params', 'remote_sensing_params',
                              'ally_notes_and_stats_structured']:
                if param_key in power_form_state: # Reset to default
                    power_form_state[param_key] = copy.deepcopy(default_state_for_reset.get(param_key))
            st.rerun() 

        selected_base_effect_rule = next((e for e in power_effects_list if e['id'] == power_form_state.get('baseEffectId')), None)

        # --- Rank Input & Descriptors ---
        col_rank_desc, col_desc_input = st_obj.columns(2)
        with col_rank_desc:
            if selected_base_effect_rule and not (selected_base_effect_rule.get('isSenseContainer') or selected_base_effect_rule.get('isImmunityContainer')):
                # Enhanced Trait rank is its enhancementAmount, handled in its specific UI
                if not selected_base_effect_rule.get('isEnhancementEffect'): 
                     current_rank_val = power_form_state.get('rank',1)
                     new_rank_val = st.number_input(
                        "Power Rank:", min_value=0, 
                        max_value=char_state.get('powerLevel', 10) * 2, # General practical max
                        value=current_rank_val, step=1, 
                        key=_uk_pb(form_key_prefix, "rank_input"), 
                        help=selected_base_effect_rule.get('description','') if selected_base_effect_rule else ""
                    )
                     if new_rank_val != current_rank_val: 
                         power_form_state['rank'] = new_rank_val
                         # If rank changes, Enhanced Trait amount should also sync if that's the effect
                         if selected_base_effect_rule.get('isEnhancementEffect'):
                             power_form_state.setdefault('enhanced_trait_params', {})['enhancementAmount'] = new_rank_val
                         st.rerun() 
            elif selected_base_effect_rule and (selected_base_effect_rule.get('isSenseContainer') or selected_base_effect_rule.get('isImmunityContainer')):
                power_form_state['rank'] = 0 # These are costed by selections, not rank
        
        with col_desc_input:
            power_form_state['descriptors'] = st.text_input("Descriptors (comma-separated, e.g., Fire, Magical):", value=power_form_state.get('descriptors',''), key=_uk_pb(form_key_prefix, "descriptors"))

        if selected_base_effect_rule: 
            st.caption(f"Base: {selected_base_effect_rule.get('name', 'N/A')} - {selected_base_effect_rule.get('description', '')}", key=_uk_pb(form_key_prefix,"eff_desc_cap"))
        
        # Display measurement details if applicable
        if selected_base_effect_rule and power_form_state.get('rank',0) >= 0 : 
            temp_power_def_for_measure = {k:v for k,v in power_form_state.items() if k != 'ui_state'}
            measurement_str = engine.get_power_measurement_details(temp_power_def_for_measure, rule_data) 
            if measurement_str: 
                st.info(f"ℹ️ Effect Details: {measurement_str}", icon="📏", key=_uk_pb(form_key_prefix,"measure_info"))

        # --- Effect-Specific Configuration UIs ---
        st.markdown("---", key=_uk_pb(form_key_prefix,"eff_spec_sep_start"))
        if selected_base_effect_rule:
            st.markdown(f"**Configuration for: {selected_base_effect_rule.get('name')}**", key=_uk_pb(form_key_prefix,"eff_spec_header_main"))
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
                _render_movement_params_ui(st, power_form_state, rule_data, engine, generate_id_func)
            elif selected_base_effect_rule.get('id') in ['eff_morph', 'eff_transform']:
                _render_morph_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('id') == 'eff_nullify':
                _render_nullify_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('id') == 'eff_illusion':
                 _render_illusion_params_ui(st, power_form_state, rule_data)
            elif selected_base_effect_rule.get('id') == 'eff_remote_sensing':
                 _render_remote_sensing_params_ui(st, power_form_state, rule_data)
            else:
                st.caption("This effect has no special parameters beyond standard modifiers.", key=_uk_pb(form_key_prefix,"no_spec_param_cap_main"))
        
        st.markdown("---", key=_uk_pb(form_key_prefix,"mod_sep_start"))
        # --- Modifier Management UI ---
        st.subheader("✨ Modifiers (Extras & Flaws)")
        
        current_modifiers = power_form_state.get('modifiersConfig', [])
        if current_modifiers:
            st.markdown("**Applied Modifiers:**", key=_uk_pb(form_key_prefix,"applied_mod_header_main"))
            modifiers_to_keep_in_form = []
            for idx, mod_conf_instance in enumerate(current_modifiers):
                mod_rule_id = mod_conf_instance.get('id')
                mod_instance_id = mod_conf_instance.get('instance_id') 
                if not mod_instance_id: # Should have been set when added
                    mod_instance_id = generate_id_func(f"mod_inst_{mod_rule_id}_{idx}_")
                    mod_conf_instance['instance_id'] = mod_instance_id

                mod_rule_def = next((m for m in rule_data.get('power_modifiers',[]) if m['id'] == mod_rule_id), None)
                if not mod_rule_def: 
                    st.warning(f"Modifier rule for ID '{mod_rule_id}' not found. Skipping display.", icon="⚠️")
                    modifiers_to_keep_in_form.append(mod_conf_instance) # Keep it to avoid data loss, but warn
                    continue

                mod_disp_name = mod_rule_def.get('name', mod_rule_id)
                mod_rank_val = mod_conf_instance.get('rank',1) if mod_rule_def.get('ranked') else None
                mod_rank_disp = f" (Rank {mod_rank_val})" if mod_rank_val is not None and mod_rule_def.get('ranked') else "" # Only show rank if modifier is ranked
                
                exp_key = _uk_pb(form_key_prefix,"mod_exp",mod_instance_id)
                with st.expander(f"{mod_disp_name}{mod_rank_disp} [{mod_rule_def.get('type', '')}]", expanded=False, key=exp_key):
                    if mod_rule_def.get('parameter_needed'):
                        _render_modifier_parameter_input(st, mod_rule_def, mod_conf_instance, _uk_pb(form_key_prefix,"mod_edit_params", mod_instance_id), char_state, rule_data, engine, power_form_state)
                    else:
                        st.caption("No parameters for this modifier.", key=_uk_pb(form_key_prefix,"no_mod_param_cap_instance",mod_instance_id))
                    
                    remove_mod_key = _uk_pb(form_key_prefix, "mod_remove_btn_instance", mod_instance_id)
                    if st.button("➖ Remove this Modifier", key=remove_mod_key, type="secondary"):
                        # This modifier will be omitted when rebuilding modifiers_to_keep_in_form
                        pass 
                    else:
                        modifiers_to_keep_in_form.append(mod_conf_instance)
            
            if len(modifiers_to_keep_in_form) != len(current_modifiers):
                power_form_state['modifiersConfig'] = modifiers_to_keep_in_form
                st.rerun() 

        st.markdown("*Add New Modifier:*", key=_uk_pb(form_key_prefix,"add_mod_header_main"))
        mod_options_select = {"": "Select Modifier..."}
        mod_options_select.update({m['id']: f"{m['name']} ({m.get('type','')}, Cost: {m.get('costChangePerRank', m.get('flatCost', m.get('flatCostChange', '?')))}{'/r' if m.get('costType')=='perRank' or m.get('costType')=='flatPerRankOfModifier' else ' flat'})" 
                            for m in rule_data.get('power_modifiers',[])})
        
        # Use ui_state to manage the selection for the "add modifier" part
        current_mod_add_id_ui = power_form_state.get('ui_state',{}).get('modifier_to_add_id')
        select_mod_key = _uk_pb(form_key_prefix,"mod_select_to_add_key_main")
        
        selected_mod_id_from_ui = st.selectbox(
            "Available Modifiers:", options=list(mod_options_select.keys()),
            format_func=lambda x_id: mod_options_select.get(x_id,"Choose..."),
            index = list(mod_options_select.keys()).index(current_mod_add_id_ui) if current_mod_add_id_ui in mod_options_select else 0,
            key=select_mod_key
        )
        
        if selected_mod_id_from_ui != current_mod_add_id_ui:
            power_form_state['ui_state']['modifier_to_add_id'] = selected_mod_id_from_ui
            # Reset temp config when selection changes
            power_form_state['ui_state']['temp_new_mod_config'] = {'id': selected_mod_id_from_ui, 'rank': 1, 'params': {}} if selected_mod_id_from_ui else {}
            st.rerun() # Rerun to update the parameter section for the new selection

        # Parameter configuration for the modifier being added
        if power_form_state.get('ui_state',{}).get('modifier_to_add_id'):
            mod_id_to_configure = power_form_state['ui_state']['modifier_to_add_id']
            mod_rule_to_configure = next((m_rule for m_rule in rule_data.get('power_modifiers',[]) if m_rule['id'] == mod_id_to_configure), None)
            
            if mod_rule_to_configure:
                # Ensure temp_new_mod_config exists and matches the selected ID
                if 'temp_new_mod_config' not in power_form_state['ui_state'] or power_form_state['ui_state']['temp_new_mod_config'].get('id') != mod_id_to_configure:
                    power_form_state['ui_state']['temp_new_mod_config'] = {'id': mod_id_to_configure, 'rank': 1, 'params': {}}
                
                temp_mod_config_for_add = power_form_state['ui_state']['temp_new_mod_config']

                if mod_rule_to_configure.get('ranked'):
                    temp_mod_config_for_add['rank'] = st.number_input(
                        "Modifier Rank:",min_value=1, 
                        max_value=mod_rule_to_configure.get('maxRanks',20), # Simplified max
                        value=temp_mod_config_for_add.get('rank',1),
                        key=_uk_pb(form_key_prefix, "mod_add_rank_input", mod_id_to_configure)
                    )
                if mod_rule_to_configure.get('parameter_needed'):
                    st.caption(f"Configure parameters for: {mod_rule_to_configure['name']}", key=_uk_pb(form_key_prefix,"mod_add_param_header_text",mod_id_to_configure))
                    _render_modifier_parameter_input(st, mod_rule_to_configure, temp_mod_config_for_add, _uk_pb(form_key_prefix,"mod_add_new_param_inputs",mod_id_to_configure), char_state, rule_data, engine, power_form_state)
                
                add_mod_button_key = _uk_pb(form_key_prefix, "mod_add_confirm_button", mod_id_to_configure)
                if st.button(f"➕ Add Modifier: {mod_rule_to_configure['name']}", key=add_mod_button_key):
                    final_mod_to_add_to_list = copy.deepcopy(temp_mod_config_for_add)
                    final_mod_to_add_to_list['instance_id'] = generate_id_func("mod_inst_") 
                    
                    if 'modifiersConfig' not in power_form_state: power_form_state['modifiersConfig'] = []
                    power_form_state['modifiersConfig'].append(final_mod_to_add_to_list)
                    
                    # Reset selection and temp config
                    power_form_state['ui_state']['modifier_to_add_id'] = None 
                    power_form_state['ui_state']['temp_new_mod_config'] = {}
                    st.rerun()
        
        # --- Array Configuration UI ---
        st.markdown("---", key=_uk_pb(form_key_prefix,"arr_sep_start"))
        st.subheader("🔗 Array Configuration")
        is_base_val = power_form_state.get('isArrayBase',False)
        new_is_base_val = st.checkbox("Is this power the Base of a new Array?", value=is_base_val, key=_uk_pb(form_key_prefix, "is_array_base_cb"))
        if new_is_base_val != is_base_val:
            power_form_state['isArrayBase'] = new_is_base_val
            if new_is_base_val: power_form_state['isAlternateEffectOf'] = None # Cannot be base and AE
            st.rerun()

        if power_form_state.get('isArrayBase'):
            power_form_state['arrayId'] = st.text_input("Array ID (e.g., 'energy_effects', must be unique for this array):", value=power_form_state.get('arrayId',''), key=_uk_pb(form_key_prefix, "array_id_input"))
            
            is_dyn_val = power_form_state.get('isDynamicArray',False)
            new_is_dyn_val = st.checkbox("Make this Array Dynamic?", value=is_dyn_val, key=_uk_pb(form_key_prefix, "is_dynamic_array_cb"))
            if new_is_dyn_val != is_dyn_val:
                power_form_state['isDynamicArray'] = new_is_dyn_val; st.rerun()

            if power_form_state.get('isDynamicArray'):
                st.caption("Note: Dynamic Array Alternate Effects cost 2 PP each (flat) instead of 1 PP.", key=_uk_pb(form_key_prefix,"dyn_array_note_text"))
        else: # Not a base, could be an AE
            is_ae_current_val = power_form_state.get('isAlternateEffectOf') is not None
            new_is_ae_val = st.checkbox("Is this an Alternate Effect (AE) of an existing Array Base?", value=is_ae_current_val, key=_uk_pb(form_key_prefix, "is_ae_cb"))
            
            if new_is_ae_val: # If checkbox is checked for AE
                array_base_options_ae = {"": "Select Array Base Power..."}
                editing_power_id_for_ae_check = power_form_state.get('editing_power_id')
                for p_other_for_ae in char_state.get('powers', []):
                    # An AE can only be linked to a power that is an array base OR already part of an array (has an arrayId)
                    if (p_other_for_ae.get('isArrayBase') or p_other_for_ae.get('arrayId')) and p_other_for_ae.get('id') != editing_power_id_for_ae_check:
                        array_base_options_ae[p_other_for_ae.get('id')] = f"{p_other_for_ae.get('name')} (Array ID: {p_other_for_ae.get('arrayId', 'Default Array')})"
                
                current_ae_base_id_form = power_form_state.get('isAlternateEffectOf')
                sel_idx_ae_form = list(array_base_options_ae.keys()).index(current_ae_base_id_form) if current_ae_base_id_form in array_base_options_ae else 0
                
                new_ae_base_id_form = st.selectbox(
                    "Select Base Power for this AE:", 
                    options=list(array_base_options_ae.keys()), 
                    format_func=lambda x_ae_id: array_base_options_ae.get(x_ae_id,"Choose..."), 
                    index=sel_idx_ae_form, 
                    key=_uk_pb(form_key_prefix, "ae_of_select_input")
                )
                if new_ae_base_id_form != current_ae_base_id_form:
                    power_form_state['isAlternateEffectOf'] = new_ae_base_id_form if new_ae_base_id_form else None
                    if new_ae_base_id_form: 
                        base_pwr_for_ae_link = next((p_link for p_link in char_state.get('powers',[]) if p_link.get('id') == new_ae_base_id_form), None)
                        power_form_state['arrayId'] = base_pwr_for_ae_link.get('arrayId') if base_pwr_for_ae_link else None
                    else: 
                        power_form_state['arrayId'] = None
                    st.rerun()
            elif not new_is_ae_val and is_ae_current_val : # If AE was just unchecked
                power_form_state['isAlternateEffectOf'] = None
                power_form_state['arrayId'] = None 
                st.rerun()

        # --- Linked Combat Skill ---
        st.markdown("---", key=_uk_pb(form_key_prefix,"combat_skill_sep_start"))
        st.subheader("⚔️ Linked Combat Skill")
        skills_list_cs = rule_data.get('skills',{}).get('list',[]); combat_skill_options_cs = {"": "None"}
        for sk_rule_cs in skills_list_cs:
            if sk_rule_cs.get('isCombatSkill'):
                combat_skill_options_cs[sk_rule_cs['id']] = sk_rule_cs['name'] + " (General)"
                # Add character's specialized versions of this combat skill
                for sk_id_char_cs, sk_rank_char_cs in char_state.get('skills',{}).items():
                    if sk_id_char_cs.startswith(sk_rule_cs['id'] + "_"): 
                         spec_name_cs = sk_id_char_cs.replace(sk_rule_cs['id'] + "_", "").replace("_"," ").title()
                         combat_skill_options_cs[sk_id_char_cs] = f"{sk_rule_cs['name']}: {spec_name_cs}"
        
        current_linked_skill_form = power_form_state.get('linkedCombatSkill')
        sel_idx_lcs_form = list(combat_skill_options_cs.keys()).index(current_linked_skill_form) if current_linked_skill_form in combat_skill_options_cs else 0
        power_form_state['linkedCombatSkill'] = st.selectbox(
            "Link to Combat Skill (for Attack Bonus if this power makes an attack roll):", 
            options=list(combat_skill_options_cs.keys()), 
            format_func=lambda x_lcs: combat_skill_options_cs.get(x_lcs, "None"), 
            index=sel_idx_lcs_form, 
            key=_uk_pb(form_key_prefix, "linked_skill_select_input")
        )

        # --- Live Cost Preview ---
        st.markdown("---", key=_uk_pb(form_key_prefix,"cost_sep_start"))
        st.subheader("💰 Estimated Power Cost")
        # Create a temporary power definition from the form state for cost calculation
        preview_power_def_for_cost = {k:v for k,v in power_form_state.items() if k != 'ui_state'} 
        
        cost_details_preview_form = engine.calculate_individual_power_cost(preview_power_def_for_cost, char_state.get('powers',[]))
        st.metric("Total Cost:", f"{cost_details_preview_form.get('totalCost',0)} PP", key=_uk_pb(form_key_prefix,"cost_metric_form"))
        
        cost_bd_form = cost_details_preview_form.get('costBreakdown',{})
        cost_per_rank_disp_form = cost_details_preview_form.get('costPerRankFinal','N/A')
        if isinstance(cost_per_rank_disp_form, float): cost_per_rank_disp_form = f"{cost_per_rank_disp_form:.1f}" 
        
        st.caption(f"Cost/Rank: {cost_per_rank_disp_form} | Breakdown: Base Effect {cost_bd_form.get('base_effect_cpr', cost_bd_form.get('base',0)) * power_form_state.get('rank',1):.1f}, Extras {cost_bd_form.get('extras_cpr',0) * power_form_state.get('rank',1):.1f}, Flaws {cost_bd_form.get('flaws_cpr',0) * power_form_state.get('rank',1):.1f}, Flat {cost_bd_form.get('flat_total',0):.1f}", key=_uk_pb(form_key_prefix,"cost_breakdown_cap_form"))
        if cost_bd_form.get('senses_total',0) > 0: st.caption(f"Senses Cost: {cost_bd_form['senses_total']:.1f}", key=_uk_pb(form_key_prefix,"senses_cost_cap_form"))
        if cost_bd_form.get('immunities_total',0) > 0: st.caption(f"Immunities Cost: {cost_bd_form['immunities_total']:.1f}", key=_uk_pb(form_key_prefix,"imm_cost_cap_form"))

        # --- Form Actions ---
        submit_col_main_form, cancel_col_main_form = st.columns(2)
        with submit_col_main_form:
            if st.form_submit_button("💾 Save Power to Character", use_container_width=True, type="primary"):
                final_power_data_to_save = {k:v for k,v in power_form_state.items() if k != 'ui_state'}
                final_power_data_to_save['id'] = power_form_state.get('editing_power_id') or generate_id_func("pwr_")
                
                current_char_powers_list_save = list(char_state.get('powers', [])) 
                if power_form_state.get('editing_power_id'): 
                    power_edited_successfully = False
                    for i_save, p_char_save in enumerate(current_char_powers_list_save):
                        if p_char_save.get('id') == power_form_state.get('editing_power_id'):
                            current_char_powers_list_save[i_save] = final_power_data_to_save
                            power_edited_successfully = True; break
                    if not power_edited_successfully: # Should not happen if ID is correct
                        st.warning("Could not find original power to edit by ID, appending as new instead.", icon="⚠️")
                        current_char_powers_list_save.append(final_power_data_to_save) 
                else: # Adding new power
                    current_char_powers_list_save.append(final_power_data_to_save)
                
                update_char_value(['powers'], current_char_powers_list_save) 
                
                # Reset power_form_state to default and hide form
                default_pfs_after_save = get_default_power_form_state(rule_data) # Get fresh default
                power_form_state.clear(); power_form_state.update(default_pfs_after_save)
                st.session_state.show_power_builder_form = False # Signal to hide the form in advanced_mode_ui
                
                st.success(f"Power '{final_power_data_to_save['name']}' saved!")
                st.rerun() 
        with cancel_col_main_form:
            if st.form_submit_button("❌ Cancel Edit", use_container_width=True):
                default_pfs_on_cancel = get_default_power_form_state(rule_data) # Get fresh default
                power_form_state.clear(); power_form_state.update(default_pfs_on_cancel)
                st.session_state.show_power_builder_form = False
                st.rerun()
