# heroforge-mm-streamlit/ui_sections/advanced_mode_ui.py

import streamlit as st
import copy
import math
import json # For pretty printing dicts in UI sometimes
import uuid # For instance_ids
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core_engine import CoreEngine, CharacterState, RuleData, AdvantageDefinition, PowerDefinition, EquipmentDefinition, HQDefinition, VehicleDefinition, AllyDefinition
    from ..pdf_utils import generate_pdf_html_content
    from .power_builder_ui import render_power_builder_form, get_default_power_form_state 
else:
    CoreEngine = Any
    CharacterState = Dict[str, Any]
    RuleData = Dict[str, Any]
    AdvantageDefinition = Dict[str, Any] 
    PowerDefinition = Dict[str, Any]
    EquipmentDefinition = Dict[str, Any]
    HQDefinition = Dict[str, Any]
    VehicleDefinition = Dict[str, Any]
    AllyDefinition = Dict[str, Any]
    generate_pdf_html_content = Any
    render_power_builder_form = Any 
    get_default_power_form_state = Any 


# --- Helper for unique keys in loops ---
def _uk(base: str, *args: Any) -> str:
    """Creates a unique key for Streamlit widgets."""
    str_args = [str(a).replace(":", "_").replace(" ", "_").replace("[", "_").replace("]", "_").replace("(", "_").replace(")", "_").replace("/", "_") for a in args if a is not None]
    return f"adv_{base}_{'_'.join(str_args)}"

# --- Helper for displaying validation errors for a field ---
def display_field_validation_errors(st_obj: Any, validation_errors: List[str], field_identifier: str):
    """Displays validation errors relevant to a specific field identifier."""
    field_errors = [err for err in validation_errors if field_identifier.lower() in err.lower()]
    for err_idx, err in enumerate(field_errors):
        st_obj.caption(f"⚠️ {err}", key=_uk("validation_err", field_identifier, err_idx))

# --- Helper function to initialize editor state ---
def _initialize_editor_config(editor_config_ref: Dict[str, Any], default_values: Dict[str, Any]):
    """Initializes or resets a generic editor config in session state."""
    current_mode = editor_config_ref.get("mode") # Preserve mode if resetting for same mode
    show_form = editor_config_ref.get("show_form", False)

    editor_config_ref.clear() # Clear it first
    editor_config_ref.update(copy.deepcopy(default_values)) # Apply defaults
    
    # Restore mode and show_form if they were meant to persist (e.g. after a sub-action within the form)
    if current_mode: editor_config_ref["mode"] = current_mode 
    editor_config_ref["show_form"] = show_form


DEFAULT_ADVANTAGE_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "advantage_id_rule": None, 
    "instance_id": None, "current_rank": 1, "current_params": {},
    "selected_adv_rule": None
}
DEFAULT_EQUIPMENT_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "item_instance_id": None,
    "is_custom": False, "selected_item_rule_id": None,
    "current_name": "Custom Item", "current_ep_cost": 1, "current_description": "",
    "current_params": {}, "selected_item_rule": None
}
DEFAULT_HQ_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "hq_instance_id": None,
    "current_name": "New HQ", 
    "current_size_id": None, 
    "current_bought_toughness": 0,
    "current_features": [], 
    "selected_hq_size_rule": None 
}
DEFAULT_VEHICLE_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "vehicle_instance_id": None,
    "current_name": "New Vehicle",
    "current_size_rank": 0, 
    "current_features": [],
    "derived_base_stats": {} 
}
DEFAULT_ALLY_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "ally_instance_id": None,
    "current_name": "New Ally", "current_type": "Minion", "current_pl": 5,
    "current_asserted_pp_cost": 0,
    "current_abilities_summary_text": "", "current_defenses_summary_text": "",
    "current_skills_summary_text": "", "current_powers_advantages_summary_text": "",
    "current_notes": ""
}

# --- Abilities Section ---
def render_abilities_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable
):
    st_obj.header("Abilities")
    with st_obj.expander("ℹ️ Understanding Abilities (Cost: 2 PP per Rank)", expanded=False):
        st_obj.markdown(rule_data.get("abilities", {}).get("help_text", {}).get("general", "Define your hero's 8 core attributes. 0 is average human."))

    ability_rules_data = rule_data.get('abilities', {}) 
    ability_rules_list: List[Dict[str, Any]] = ability_rules_data.get('list', [])

    current_abilities = char_state.get('abilities', {})
    cost_factor = ability_rules_data.get('costFactor', 2)

    cols = st_obj.columns(4)
    for i, ab_info in enumerate(ability_rules_list):
        ab_id = ab_info['id']
        ab_name = ab_info['name']
        ab_help = ability_rules_data.get("help_text", {}).get(ab_id, ab_info.get('description', ''))
        current_rank = current_abilities.get(ab_id, 0)
        
        with cols[i % len(cols)]:
            key_ability_input = _uk("ab_input", ab_id)
            new_rank = st_obj.number_input(
                f"{ab_name} ({ab_id})", min_value=-5, max_value=30, 
                value=current_rank, 
                key=key_ability_input,
                help=ab_help,
                step=1
            )
            if new_rank != current_rank:
                update_char_value(['abilities', ab_id], new_rank)
                st_obj.rerun() 
            
            cost = new_rank * cost_factor
            mod = engine.get_ability_modifier(new_rank) 
            st_obj.caption(f"Mod: {mod:+}, Cost: {cost} PP", key=_uk("ab_caption", ab_id))
    
    total_ability_cost = engine.calculate_ability_cost(current_abilities)
    st_obj.markdown(f"**Total Ability Cost: {total_ability_cost} PP**")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Ability")

# --- Defenses Section ---
def render_defenses_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable
):
    st_obj.header("Defenses")
    defenses_help_text = "Base from Abilities, buy ranks to increase. PL Caps are crucial!"
    rule_help_text_section = rule_data.get("help_text", {})
    if isinstance(rule_help_text_section, dict):
        defenses_help_text = rule_help_text_section.get("defenses_help", defenses_help_text)
    
    with st_obj.expander("🛡️ Understanding Defenses (Cost: 1 PP per +1 Bought Rank)", expanded=False):
        st_obj.markdown(defenses_help_text)

    pl = char_state.get('powerLevel', 10)
    pl_cap_paired = pl * 2
    bought_defenses = char_state.get('defenses', {})
    current_abilities = char_state.get('abilities', {})

    defense_configs = [
        {"id": "Dodge", "name": "Dodge", "base_ability_id": "AGL", "tooltip": "Avoid ranged/area attacks."},
        {"id": "Parry", "name": "Parry", "base_ability_id": "FGT", "tooltip": "Avoid close attacks."},
        {"id": "Toughness", "name": "Toughness", "base_ability_id": "STA", "tooltip": "Resist damage. (Base from STA, also from Protection power, Defensive Roll advantage)."},
        {"id": "Fortitude", "name": "Fortitude", "base_ability_id": "STA", "tooltip": "Resist health effects (poison, disease)."},
        {"id": "Will", "name": "Will", "base_ability_id": "AWE", "tooltip": "Resist mental effects."}
    ]
    
    st_obj.markdown("Enter **bought ranks** for each defense below:")
    def_cols = st_obj.columns(len(defense_configs))
    totals_for_cap_check: Dict[str, int] = {}

    for i, d_conf in enumerate(defense_configs):
        with def_cols[i]:
            base_val_from_ability = engine.get_ability_modifier(current_abilities.get(d_conf['base_ability_id'], 0))
            bought_val = bought_defenses.get(d_conf['id'], 0)
            
            total_val_display = engine.get_total_defense(char_state, d_conf['id'], d_conf['base_ability_id'])
            totals_for_cap_check[d_conf['id']] = total_val_display
            
            key_def_input = _uk("def_input", d_conf['id'])
            new_bought_val = st_obj.number_input(
                f"{d_conf['name']}", min_value=0, max_value=pl + 15, 
                value=bought_val, 
                key=key_def_input,
                help=f"{d_conf['tooltip']}\nBase from {d_conf['base_ability_id']}: {base_val_from_ability}\nCurrent Total (all sources): {total_val_display}"
            )
            if new_bought_val != bought_val:
                update_char_value(['defenses', d_conf['id']], new_bought_val)
                st_obj.rerun()
            st_obj.caption(f"Bought: {new_bought_val} (Cost: {new_bought_val} PP)", key=_uk("def_caption", d_conf['id']))
            st_obj.metric(label=f"Total {d_conf['name']}", value=total_val_display, key=_uk("def_metric", d_conf['id']))

    st_obj.markdown("---")
    st_obj.subheader("Defense Power Level Caps")
    cap_col1, cap_col2, cap_col3 = st_obj.columns(3)
    
    total_toughness_for_cap = totals_for_cap_check.get('Toughness',0)
    dt_sum = totals_for_cap_check.get('Dodge',0) + total_toughness_for_cap
    pt_sum = totals_for_cap_check.get('Parry',0) + total_toughness_for_cap
    fw_sum = totals_for_cap_check.get('Fortitude',0) + totals_for_cap_check.get('Will',0)
    
    dt_color = "normal" if dt_sum <= pl_cap_paired else "inverse"
    pt_color = "normal" if pt_sum <= pl_cap_paired else "inverse"
    fw_color = "normal" if fw_sum <= pl_cap_paired else "inverse"

    with cap_col1: st_obj.metric("Dodge + Toughness", f"{dt_sum} / {pl_cap_paired}", delta="OK" if dt_color=="normal" else "OVER LIMIT!", delta_color=dt_color, key=_uk("def_cap_metric", "dt"))
    with cap_col2: st_obj.metric("Parry + Toughness", f"{pt_sum} / {pl_cap_paired}", delta="OK" if pt_color=="normal" else "OVER LIMIT!", delta_color=pt_color, key=_uk("def_cap_metric", "pt"))
    with cap_col3: st_obj.metric("Fortitude + Will", f"{fw_sum} / {pl_cap_paired}", delta="OK" if fw_color=="normal" else "OVER LIMIT!", delta_color=fw_color, key=_uk("def_cap_metric", "fw"))
    
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Defense Cap")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Toughness")

# --- Skills Section ---
def render_skills_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable,
    generate_id_func: Callable[[str], str] 
):
    st_obj.header("Skills")
    skills_rules_data = rule_data.get('skills', {}) 
    
    with st_obj.expander("🎯 Understanding Skills (Cost: 1 PP per 2 Ranks Bought)", expanded=False):
        st_obj.markdown(skills_rules_data.get("help_text",{}).get("general","Skill rules..."))
        st_obj.markdown(skills_rules_data.get("help_text",{}).get("specialization_note","Specialization rules..."))

    current_skills_state = char_state.get('skills', {})
    current_abilities = char_state.get('abilities', {})
    pl = char_state.get('powerLevel', 10)
    skill_bonus_cap = pl + 10
    skill_rank_cap = pl + 5 

    total_skill_cost = engine.calculate_skill_cost(current_skills_state)
    st_obj.subheader(f"Total Skill Cost: {total_skill_cost} PP")
    st_obj.markdown("---")
    st_obj.markdown("**Modify Skill Ranks:**")
    
    base_skill_rules: List[Dict[str, Any]] = skills_rules_data.get('list', [])
    skill_display_cols = st_obj.columns(3)
    col_idx = 0
    sorted_base_skill_rules = sorted(base_skill_rules, key=lambda x: x.get('name', ''))

    for skill_info in sorted_base_skill_rules:
        base_skill_id = skill_info['id']
        base_skill_name = skill_info['name']
        gov_ab_id = skill_info.get('ability', '')
        skill_desc_help = skill_info.get('description', '') + f"\nMax Ranks: {skill_rank_cap}, Max Bonus: {skill_bonus_cap:+}"
        is_specializable = skill_info.get('specialization_possible', False)

        with skill_display_cols[col_idx % len(skill_display_cols)]:
            st_obj.markdown(f"##### {base_skill_name} ({gov_ab_id})")
            
            if not is_specializable:
                bought_rank = current_skills_state.get(base_skill_id, 0)
                ability_mod = engine.get_ability_modifier(current_abilities.get(gov_ab_id, 0))
                total_bonus = ability_mod + bought_rank
                
                key_skill_input = _uk("skill_input", base_skill_id)
                new_rank = st_obj.number_input(
                    "Ranks", 
                    min_value=0, max_value=skill_rank_cap,
                    value=bought_rank, 
                    key=key_skill_input, 
                    label_visibility="visible",
                    help=skill_desc_help
                )
                if new_rank != bought_rank:
                    update_char_value(['skills', base_skill_id], new_rank)
                    st_obj.rerun()
                
                bonus_display_str = f"Total Bonus: {total_bonus:+}"
                if total_bonus > skill_bonus_cap:
                    st_obj.error(f"{bonus_display_str} (Cap: {skill_bonus_cap:+})", icon="⚠️", key=_uk("skill_err", base_skill_id))
                else:
                    st_obj.caption(bonus_display_str, key=_uk("skill_bonus_disp", base_skill_id))
            else: 
                specializations_for_this_base = {
                    sk_id: r for sk_id, r in current_skills_state.items() 
                    if sk_id.startswith(base_skill_id + "_") 
                }
                if not specializations_for_this_base:
                    st_obj.caption(f"No '{base_skill_name}' specializations yet.", key=_uk("no_spec_caption", base_skill_id))

                for spec_skill_id, spec_rank in sorted(specializations_for_this_base.items()):
                    spec_name_part = spec_skill_id.replace(base_skill_id + "_", "").replace("_", " ").title()
                    spec_ability_mod = engine.get_ability_modifier(current_abilities.get(gov_ab_id, 0))
                    spec_total_bonus = spec_ability_mod + spec_rank

                    cols_spec_edit = st_obj.columns([0.8, 0.2])
                    with cols_spec_edit[0]:
                        key_spec_skill_input = _uk("skill_input_spec", spec_skill_id)
                        new_spec_rank = st_obj.number_input(
                            f"{spec_name_part}", 
                            min_value=0, max_value=skill_rank_cap,
                            value=spec_rank, 
                            key=key_spec_skill_input,
                            help=f"Specialization of {base_skill_name}. Max Ranks: {skill_rank_cap}, Max Bonus: {skill_bonus_cap:+}"
                        )
                    with cols_spec_edit[1]:
                        st_obj.markdown("## ") 
                        key_del_spec_btn = _uk("del_spec_btn", spec_skill_id)
                        if st_obj.button("✖", key=key_del_spec_btn, help=f"Remove '{spec_name_part}' specialization"):
                            new_skills_state = {k:v for k,v in current_skills_state.items() if k != spec_skill_id}
                            update_char_value(['skills'], new_skills_state)
                            st_obj.rerun()
                            return 

                    if new_spec_rank != spec_rank:
                        update_char_value(['skills', spec_skill_id], new_spec_rank)
                        st_obj.rerun()
                    
                    spec_bonus_display_str = f"Bonus: {spec_total_bonus:+}"
                    if spec_total_bonus > skill_bonus_cap:
                        st_obj.error(f"{spec_bonus_display_str} (Cap: {skill_bonus_cap:+})", icon="⚠️", key=_uk("skill_err_spec", spec_skill_id))
                    else:
                        st_obj.caption(spec_bonus_display_str, key=_uk("skill_bonus_disp_spec", spec_skill_id))
                
                with st_obj.form(key=_uk("add_spec_form", base_skill_id), clear_on_submit=True):
                    spec_prompt = skill_info.get('specialization_prompt', 'Enter specialization name')
                    new_spec_name_text = st.text_input(f"New {base_skill_name} Specialization Name:", placeholder=spec_prompt, key=_uk("add_spec_text_input_form", base_skill_id))
                    submitted_add_spec = st.form_submit_button(f"➕ Add {base_skill_name} Specialization")
                    if submitted_add_spec and new_spec_name_text.strip():
                        spec_id_part = "".join(c for c in new_spec_name_text.strip().lower().replace(" ", "_") if c.isalnum() or c == '_')
                        new_full_spec_id = f"{base_skill_id}_{spec_id_part}"
                        
                        if new_full_spec_id not in current_skills_state:
                            updated_skills = dict(current_skills_state)
                            updated_skills[new_full_spec_id] = 0 
                            update_char_value(['skills'], updated_skills)
                            st.rerun()
                        else:
                            st.warning(f"Specialization '{new_spec_name_text}' already exists or ID conflicts.", icon="⚠️")
            st_obj.markdown("---", key=_uk("skill_sep", base_skill_id))
        col_idx += 1
    
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Skill Rank")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Skill Bonus")

# --- Advantages Section ---
def render_advantages_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    generate_id_func: Callable[[str],str],
    advantage_editor_config_ref: Dict[str, Any] 
):
    st_obj.header("Advantages")
    adv_rules_list: List[Dict] = rule_data.get('advantages_v1', []) 

    _initialize_editor_config(advantage_editor_config_ref, DEFAULT_ADVANTAGE_EDITOR_CONFIG)


    with st_obj.expander("💡 Understanding Advantages (Cost: Usually 1 PP per Rank)", expanded=False):
        st_obj.markdown(rule_data.get("help_text",{}).get("advantages_help","Special talents, contacts, or benefits. Many require specific parameters."))

    current_advantages: List[AdvantageDefinition] = char_state.get('advantages', [])
    total_adv_cost = engine.calculate_advantage_cost(current_advantages) 
    st_obj.subheader(f"Total Advantage Cost: {total_adv_cost} PP")
    
    st_obj.markdown("**Your Advantages:**")
    if not current_advantages:
        st_obj.caption("No advantages selected.")
    
    for i, adv_entry in enumerate(current_advantages):
        adv_rule = next((r for r in adv_rules_list if r['id'] == adv_entry.get('id')), None)
        if not adv_rule:
            st_obj.error(f"Rule definition not found for advantage ID: {adv_entry.get('id')}")
            continue

        adv_name = adv_rule.get('name', adv_entry.get('id'))
        adv_rank_display = f" (Rank {adv_entry.get('rank', 1)})" if adv_rule.get('ranked') else ""
        
        params_str_list = []
        if adv_entry.get('params'):
            for p_key, p_val in adv_entry.get('params', {}).items():
                if p_val: 
                    param_label = p_key.replace('_',' ').title()
                    if p_key == 'skill_id' and adv_rule.get('parameter_type') == 'select_skill':
                        skill_name_val = engine.get_skill_name_by_id(str(p_val), rule_data.get('skills',{}).get('list',[]))
                        params_str_list.append(f"{param_label}: {skill_name_val if skill_name_val else str(p_val)}")
                    elif isinstance(p_val, list): 
                         params_str_list.append(f"{param_label}: {', '.join(map(str,p_val))}")
                    elif p_key == 'selected_option' and adv_rule.get('parameter_type') == 'select_from_options':
                        option_label = str(p_val) 
                        for opt_item in adv_rule.get('parameter_options', []):
                            if opt_item.get('value') == p_val:
                                option_label = opt_item.get('label', str(p_val))
                                break
                        params_str_list.append(f"{option_label}") 
                    else:
                        params_str_list.append(f"{param_label}: {str(p_val)}")
        params_display = f" [{'; '.join(params_str_list)}]" if params_str_list else ""

        cols_adv_disp = st_obj.columns([0.7, 0.15, 0.15])
        cols_adv_disp[0].markdown(f"**{adv_name}**{adv_rank_display}{params_display}", unsafe_allow_html=True)
        
        instance_id = adv_entry.get("instance_id", generate_id_func(f"adv_{adv_entry['id']}_"))
        if "instance_id" not in adv_entry: adv_entry["instance_id"] = instance_id 

        key_edit_adv_btn = _uk("edit_adv_btn", instance_id)
        if cols_adv_disp[1].button("✏️ Edit", key=key_edit_adv_btn):
            advantage_editor_config_ref.update({
                "show_form": True, "mode": "edit",
                "advantage_id_rule": adv_entry['id'],
                "instance_id": instance_id,
                "current_rank": adv_entry.get('rank', 1),
                "current_params": copy.deepcopy(adv_entry.get('params', {})),
                "selected_adv_rule": copy.deepcopy(adv_rule)
            })
            st.rerun()

        key_remove_adv_btn = _uk("remove_adv_btn", instance_id)
        if cols_adv_disp[2].button("🗑️ Remove", key=key_remove_adv_btn):
            new_advantages_list = [adv for adv in current_advantages if adv.get("instance_id") != instance_id]
            update_char_value(['advantages'], new_advantages_list)
            st.rerun()
        st_obj.markdown("---", key=_uk("adv_sep_disp", instance_id))

    st_obj.markdown("---")
    key_add_new_adv_btn = _uk("add_new_adv_btn_main")
    if st_obj.button("➕ Add New Advantage", key=key_add_new_adv_btn):
        advantage_editor_config_ref.update({
            "show_form": True, "mode": "add",
            "advantage_id_rule": adv_rules_list[0]['id'] if adv_rules_list else None, 
            "instance_id": None, "current_rank": 1, "current_params": {},
            "selected_adv_rule": copy.deepcopy(adv_rules_list[0]) if adv_rules_list else None
        })
        st.rerun()

    if advantage_editor_config_ref.get("show_form"):
        form_title = "Add New Advantage" if advantage_editor_config_ref["mode"] == "add" else f"Edit Advantage: {advantage_editor_config_ref.get('selected_adv_rule',{}).get('name', '')}"
        st_obj.subheader(form_title)

        with st_obj.form(key=_uk("advantage_editor_form"), clear_on_submit=False):
            adv_config = advantage_editor_config_ref 
            adv_options = {rule['id']: rule['name'] for rule in adv_rules_list}

            if adv_config["mode"] == "add":
                selected_adv_id_rule = st.selectbox(
                    "Select Advantage Type:",
                    options=list(adv_options.keys()),
                    format_func=lambda x: adv_options.get(x, "Unknown"),
                    key=_uk("adv_form_select_id"),
                    index = list(adv_options.keys()).index(adv_config["advantage_id_rule"]) if adv_config["advantage_id_rule"] in adv_options else 0
                )
                if selected_adv_id_rule != adv_config["advantage_id_rule"]:
                    adv_config["advantage_id_rule"] = selected_adv_id_rule
                    adv_config["selected_adv_rule"] = copy.deepcopy(next((r for r in adv_rules_list if r['id'] == selected_adv_id_rule), None))
                    adv_config["current_params"] = {} 
                    adv_config["current_rank"] = 1 
                    st.rerun() 
            else: 
                st_obj.markdown(f"**Editing:** {adv_config.get('selected_adv_rule',{}).get('name')}")

            selected_rule = adv_config.get("selected_adv_rule")
            if selected_rule:
                st_obj.caption(selected_rule.get('description',''))
                if selected_rule.get('ranked'):
                    max_r = 20 
                    if isinstance(selected_rule.get('maxRanks'), int):
                        max_r = selected_rule['maxRanks']
                    elif selected_rule.get('maxRanks_source') == 'AGL': 
                        max_r = char_state.get('abilities',{}).get('AGL',0)
                        max_r = max(1, max_r) 
                    
                    adv_config["current_rank"] = st.number_input(
                        "Rank:", min_value=1, max_value=max_r, 
                        value=adv_config["current_rank"], 
                        key=_uk("adv_form_rank_input", selected_rule['id'])
                    )

                if selected_rule.get('parameter_needed'):
                    param_type = selected_rule.get('parameter_type')
                    param_prompt = selected_rule.get('parameter_prompt', "Parameter:")
                    param_key_base = selected_rule['id'] 

                    if param_type == "text":
                        adv_config["current_params"]["detail"] = st.text_input(param_prompt, value=adv_config["current_params"].get("detail", ""), key=_uk("adv_param_text", param_key_base))
                    elif param_type == "text_long":
                        adv_config["current_params"]["detail"] = st.text_area(param_prompt, value=adv_config["current_params"].get("detail", ""), height=100, key=_uk("adv_param_textarea", param_key_base))
                    elif param_type == "select_from_options":
                        param_options_list = selected_rule.get('parameter_options', [])
                        options_map_vals = [opt['value'] for opt in param_options_list]
                        options_map_labels = {opt['value']: opt['label'] for opt in param_options_list}
                        
                        current_selection = adv_config["current_params"].get("selected_option")
                        sel_idx = options_map_vals.index(current_selection) if current_selection in options_map_vals else 0
                        
                        adv_config["current_params"]["selected_option"] = st.selectbox(
                            param_prompt, options=options_map_vals,
                            format_func=lambda x: options_map_labels.get(x, str(x)),
                            index=sel_idx,
                            key=_uk("adv_param_select_options", param_key_base)
                        )
                    elif param_type == "select_skill":
                        all_skills_base_list = rule_data.get('skills', {}).get('list', [])
                        char_specialized_skills = {
                            sk_id: sk_id.replace(bs['id']+"_", "").replace("_"," ").title() + f" ({bs['name']})"
                            for bs in all_skills_base_list if bs.get('specialization_possible')
                            for sk_id in char_state.get('skills', {}).keys() if sk_id.startswith(bs['id']+"_")
                        }
                        skill_options = {"": "Select Skill..."}
                        skill_options.update({s['id']: s['name'] for s in all_skills_base_list if not s.get('specialization_possible')})
                        skill_options.update(char_specialized_skills)
                        
                        filter_hint = selected_rule.get('parameter_filter_hint', '').lower()
                        skill_options_to_display = skill_options
                        if filter_hint:
                            filtered_options_dict = {"": "Select Skill..."}
                            for s_id, s_name in skill_options.items():
                                if not s_id: continue
                                if any(hint_part in s_name.lower() or hint_part in s_id.lower() for hint_part in filter_hint.split(',')):
                                    filtered_options_dict[s_id] = s_name
                            skill_options_to_display = filtered_options_dict
                        
                        current_skill_id = adv_config["current_params"].get("skill_id")
                        sel_idx_skill = list(skill_options_to_display.keys()).index(current_skill_id) if current_skill_id in skill_options_to_display else 0
                        adv_config["current_params"]["skill_id"] = st.selectbox(
                            param_prompt, options=list(skill_options_to_display.keys()),
                            format_func=lambda x: skill_options_to_display.get(x, "Choose..."),
                            index=sel_idx_skill,
                            key=_uk("adv_param_select_skill", param_key_base)
                        )
                    elif param_type == "list_string":
                        num_entries = adv_config["current_rank"] if selected_rule.get('languages_per_rank') or selected_rule.get('parameter_name_singular') else 1
                        param_list_key = selected_rule.get("parameter_list_key", "details_list") 
                        current_list_val = adv_config["current_params"].get(param_list_key, [])
                        if not isinstance(current_list_val, list): current_list_val = [str(current_list_val)] if current_list_val else []
                        
                        new_list_val = [""] * num_entries
                        for i in range(num_entries):
                            if i < len(current_list_val): new_list_val[i] = current_list_val[i]
                        
                        st.markdown(f"**{param_prompt}**")
                        for i in range(num_entries):
                            singular_label = selected_rule.get('parameter_name_singular', 'Detail')
                            new_list_val[i] = st.text_input(f"{singular_label} #{i+1}", value=new_list_val[i], key=_uk("adv_param_list_str", param_key_base, i))
                        adv_config["current_params"][param_list_key] = [s for s in new_list_val if s.strip()] 

                    elif param_type == "complex_config_note":
                        st.info(selected_rule.get('parameter_prompt', 'Configuration handled in another section.'))
                    else:
                        st.warning(f"Unsupported parameter_type: {param_type} for {selected_rule['name']}")

            submit_col, cancel_col = st.columns(2)
            with submit_col:
                key_save_adv_btn = _uk("adv_form_save_btn", adv_config["mode"])
                if st.form_submit_button("💾 Save Advantage", use_container_width=True, type="primary"):
                    if not adv_config["selected_adv_rule"]:
                        st.error("No advantage type selected.")
                    else:
                        final_params = {}
                        for p_key, p_value in adv_config["current_params"].items():
                            if isinstance(p_value, list): 
                                cleaned_list = [item for item in p_value if isinstance(item, str) and item.strip()]
                                if cleaned_list: final_params[p_key] = cleaned_list
                            elif isinstance(p_value, str) and p_value.strip():
                                final_params[p_key] = p_value
                            elif not isinstance(p_value, str) and p_value is not None : 
                                final_params[p_key] = p_value
                        
                        new_adv_entry: AdvantageDefinition = {
                            "id": adv_config["selected_adv_rule"]['id'],
                            "instance_id": adv_config["instance_id"] or generate_id_func("adv_inst_"),
                            "rank": adv_config["current_rank"] if selected_rule.get('ranked') else 1,
                            "params": final_params
                        }
                        
                        current_char_advantages = list(char_state.get('advantages', [])) 
                        if adv_config["mode"] == "add":
                            current_char_advantages.append(new_adv_entry)
                        else: 
                            found = False
                            for idx, existing_adv in enumerate(current_char_advantages):
                                if existing_adv.get("instance_id") == new_adv_entry["instance_id"]:
                                    current_char_advantages[idx] = new_adv_entry
                                    found = True
                                    break
                            if not found: current_char_advantages.append(new_adv_entry) 
                        
                        update_char_value(['advantages'], current_char_advantages)
                        _initialize_editor_config(advantage_editor_config_ref, DEFAULT_ADVANTAGE_EDITOR_CONFIG) 
                        st.rerun()
            
            with cancel_col:
                key_cancel_adv_btn = _uk("adv_form_cancel_btn", adv_config["mode"])
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    _initialize_editor_config(advantage_editor_config_ref, DEFAULT_ADVANTAGE_EDITOR_CONFIG) 
                    st.rerun()
        
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Advantage")


# --- Powers Section ---
def render_powers_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    generate_id_func: Callable[[str],str],
    power_form_state_ref: Dict[str,Any] 
):
    st_obj.header("Powers")
    with st_obj.expander("⚡ Understanding Powers (Advanced)", expanded=False):
        st_obj.markdown(rule_data.get("help_text",{}).get("powers_adv_help","Build custom powers with Effects, Extras, and Flaws. Watch PL Caps!"))

    if 'show_power_builder_form' not in st.session_state: 
        st.session_state.show_power_builder_form = False
    
    st_obj.markdown("**Current Powers:**")
    current_powers_list: List[PowerDefinition] = char_state.get('powers', [])
    if not current_powers_list:
        st_obj.caption("No powers defined yet.")

    for i, pwr_entry in enumerate(current_powers_list):
        pwr_id = pwr_entry.get('id', f"unknown_pwr_{i}")
        pwr_name = pwr_entry.get('name', 'Unnamed Power')
        pwr_rank = pwr_entry.get('rank', 0)
        pwr_cost = pwr_entry.get('cost', 0) 
        base_effect_rule = next((eff for eff in rule_data.get('power_effects',[]) if eff['id'] == pwr_entry.get('baseEffectId')), None)
        base_effect_name = base_effect_rule.get('name', 'Unknown Effect') if base_effect_rule else 'N/A'

        cols_pwr_disp = st_obj.columns([0.5, 0.1, 0.1, 0.15, 0.15]) 
        cols_pwr_disp[0].markdown(f"**{pwr_name}** <small>({base_effect_name})</small>", unsafe_allow_html=True)
        cols_pwr_disp[1].markdown(f"*R: {pwr_rank}*")
        cols_pwr_disp[2].markdown(f"*C: {pwr_cost} PP*")

        key_edit_pwr_btn = _uk("edit_pwr_btn", pwr_id)
        if cols_pwr_disp[3].button("✏️ Edit", key=key_edit_pwr_btn, help="Edit Power"):
            power_form_state_ref.clear() 
            power_form_state_ref.update(copy.deepcopy(pwr_entry)) 
            power_form_state_ref['editing_power_id'] = pwr_id 
            try:
                from .power_builder_ui import get_default_power_form_state 
                default_for_missing_keys = get_default_power_form_state(rule_data)
                for k, v_default in default_for_missing_keys.items():
                    if k not in power_form_state_ref:
                        power_form_state_ref[k] = v_default
            except ImportError:
                st.warning("Could not load default power form state for editing.")

            st.session_state.show_power_builder_form = True
            st.rerun()

        key_remove_pwr_btn = _uk("remove_pwr_btn", pwr_id)
        if cols_pwr_disp[4].button("🗑️ Del", key=key_remove_pwr_btn, help="Remove Power"): 
            new_powers_list = [p for p in current_powers_list if p.get('id') != pwr_id]
            update_char_value(['powers'], new_powers_list)
            st.rerun()
        
        details_parts = []
        if pwr_entry.get('final_range'): details_parts.append(f"Range: {pwr_entry['final_range']}")
        if pwr_entry.get('final_duration'): details_parts.append(f"Dur: {pwr_entry['final_duration']}")
        if pwr_entry.get('final_action'): details_parts.append(f"Act: {pwr_entry['final_action']}")
        if details_parts:
            st_obj.caption(", ".join(details_parts), key=_uk("pwr_details_disp", pwr_id))
        
        st_obj.markdown("---", key=_uk("pwr_sep_disp", pwr_id))
        
    st_obj.markdown("---")
    key_add_new_pwr_btn = _uk("add_new_pwr_btn_main")
    if st_obj.button("➕ Add New Power", key=key_add_new_pwr_btn):
        try:
            from .power_builder_ui import get_default_power_form_state 
            default_power_state = get_default_power_form_state(rule_data) 
            power_form_state_ref.clear()
            power_form_state_ref.update(default_power_state)
            power_form_state_ref['editing_power_id'] = None 
        except ImportError:
            st.error("Power builder default state function not found. Cannot add new power.")
            power_form_state_ref.clear()
            power_form_state_ref.update({
                'editing_power_id': None, 'name': 'New Power', 'rank':1, 
                'modifiersConfig':[], 'sensesConfig':[], 'immunityConfig':[], 'variableConfigurations':[],
                'baseEffectId': rule_data.get('power_effects', [{}])[0].get('id') 
            })
        st.session_state.show_power_builder_form = True
        st.rerun()

    if st.session_state.get('show_power_builder_form', False):
        st_obj.markdown("### Power Editor")
        try:
            from .power_builder_ui import render_power_builder_form 
            render_power_builder_form(
                st_obj, char_state, rule_data, engine, 
                update_char_value, power_form_state_ref, generate_id_func
            )
        except ImportError:
            st_obj.error("`power_builder_ui.py` or `render_power_builder_form` not found or failed to import.")
            st_obj.markdown("*(Power Builder UI would be rendered here from `power_builder_ui.py`)*")
            if st_obj.button("Close Editor", key=_uk("close_pb_error_btn")):
                 st.session_state.show_power_builder_form = False
                 st.rerun()
        except Exception as e_pb:
            st_obj.error(f"Error rendering power builder form: {e_pb}")
            if st_obj.button("Close Editor", key=_uk("close_pb_exception_btn")):
                 st.session_state.show_power_builder_form = False
                 st.rerun()

    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Power")

# --- Equipment Section ---
def render_equipment_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    generate_id_func: Callable[[str],str],
    equipment_editor_config_ref: Dict[str, Any] 
):
    st_obj.header("Equipment")
    _initialize_editor_config(equipment_editor_config_ref, DEFAULT_EQUIPMENT_EDITOR_CONFIG)
    
    equipment_items_rules: List[Dict] = rule_data.get('equipment_items', [])

    with st_obj.expander("ℹ️ Understanding Equipment", expanded=False):
        st_obj.markdown("Equipment represents mundane gear, weapons, armor, vehicles, and headquarters bought with Equipment Points (EP). 1 Power Point buys 5 EP via the Equipment advantage.")

    total_ep = char_state.get('derived_total_ep', 0)
    spent_ep = char_state.get('derived_spent_ep', 0) 
    st_obj.subheader(f"Equipment Points (EP): {spent_ep} / {total_ep}")
    if spent_ep > total_ep:
        st_obj.error(f"EP Overspent! {spent_ep} EP used, but only {total_ep} EP available from Equipment advantage.", icon="⚠️")

    st_obj.markdown("**Current Gear & Items:**")
    current_equipment_list: List[EquipmentDefinition] = char_state.get('equipment', [])
    if not current_equipment_list:
        st_obj.caption("No equipment items added yet.")

    for i, item_entry in enumerate(current_equipment_list):
        item_id_rule = item_entry.get('id', "custom") # Rule ID or "custom"
        item_name = item_entry.get('name', 'Unnamed Item')
        item_cost = item_entry.get('ep_cost', 0)
        item_desc = item_entry.get('description', item_entry.get('effects_text', ''))
        instance_id = item_entry.get("instance_id", generate_id_func(f"eq_inst_{item_id_rule}_"))
        if "instance_id" not in item_entry: item_entry["instance_id"] = instance_id


        cols_item_disp = st_obj.columns([0.6, 0.15, 0.1, 0.15])
        cols_item_disp[0].markdown(f"**{item_name}**")
        cols_item_disp[1].markdown(f"*{item_cost} EP*")
        if item_desc:
             cols_item_disp[0].caption(item_desc) 
        
        # For now, no edit button for individual equipment items to keep it simpler. Remove and re-add.
        # key_edit_eq_btn = _uk("edit_eq_btn", instance_id)
        # if cols_item_disp[2].button("✏️", key=key_edit_eq_btn, help="Edit Equipment"):
        #     # Logic to populate equipment_editor_config_ref for editing this item_entry
        #     st.rerun()
        
        key_remove_eq_btn = _uk("remove_eq_btn", instance_id)
        if cols_item_disp[3].button("🗑️ Remove", key=key_remove_eq_btn, help="Remove Equipment"):
            new_eq_list = [eq for eq in current_equipment_list if eq.get("instance_id") != instance_id]
            update_char_value(['equipment'], new_eq_list)
            st.rerun()
            return # Avoid iterating over modified list
        st_obj.markdown("---", key=_uk("eq_sep_disp", instance_id))
    
    st_obj.markdown("---")
    st_obj.subheader("Add New Equipment Item")
    
    if st_obj.button("➕ Add Equipment Item", key=_uk("add_new_eq_btn_main_form_trigger")):
        _initialize_editor_config(equipment_editor_config_ref, DEFAULT_EQUIPMENT_EDITOR_CONFIG) 
        equipment_editor_config_ref["show_form"] = True
        equipment_editor_config_ref["mode"] = "add"
        if equipment_items_rules: 
            equipment_editor_config_ref["selected_item_rule_id"] = equipment_items_rules[0]['id']
            equipment_editor_config_ref["selected_item_rule"] = equipment_items_rules[0]
        st.rerun()

    if equipment_editor_config_ref.get("show_form"):
        eq_config = equipment_editor_config_ref
        with st_obj.form(key=_uk("equipment_editor_form"), clear_on_submit=False): # Keep form values on rerun
            
            # Radio button for item type selection
            current_is_custom = eq_config.get("is_custom", False)
            item_type_choice = st.radio("Item Type:", ["Standard Item", "Custom Item"], 
                                     index=1 if current_is_custom else 0, 
                                     key=_uk("eq_form_is_custom_radio_key"))
            
            new_is_custom = (item_type_choice == "Custom Item")
            if new_is_custom != current_is_custom: # If type changed
                eq_config["is_custom"] = new_is_custom
                eq_config["selected_item_rule_id"] = None
                eq_config["selected_item_rule"] = None
                eq_config["current_params"] = {}
                st.rerun() # Rerun to update the rest of the form based on new type

            if not eq_config["is_custom"]:
                std_item_options = {"": "Select Standard Item..."}
                std_item_options.update({item['id']: item['name'] for item in equipment_items_rules})
                
                current_selection_id = eq_config.get("selected_item_rule_id")
                sel_idx = list(std_item_options.keys()).index(current_selection_id) if current_selection_id in std_item_options else 0

                selected_id = st.selectbox("Standard Item:", 
                                           options=list(std_item_options.keys()),
                                           format_func=lambda x: std_item_options.get(x, "Choose..."),
                                           index=sel_idx,
                                           key=_uk("eq_form_select_std_item_key"))
                
                if selected_id != current_selection_id: # If selection changed
                    eq_config["selected_item_rule_id"] = selected_id
                    eq_config["selected_item_rule"] = next((item for item in equipment_items_rules if item['id'] == selected_id), None)
                    eq_config["current_params"] = {} 
                    st.rerun() 

                selected_rule = eq_config.get("selected_item_rule")
                if selected_rule:
                    st.caption(f"EP Cost: {selected_rule.get('ep_cost', 0)}")
                    st.caption(f"Description: {selected_rule.get('description', selected_rule.get('effects_text','N/A'))}")
                    if selected_rule.get('params_needed'):
                        param_type = selected_rule.get('parameter_type')
                        param_prompt = selected_rule.get('parameter_prompt', "Detail:")
                        if param_type == "text":
                             eq_config["current_params"]["detail"] = st.text_input(param_prompt, value=eq_config["current_params"].get("detail",""), key=_uk("eq_form_param_text", selected_rule['id']))
            else: 
                eq_config["current_name"] = st.text_input("Custom Item Name:", value=eq_config.get("current_name", "Custom Item"), key=_uk("eq_form_custom_name_key"))
                eq_config["current_ep_cost"] = st.number_input("EP Cost:", min_value=0, value=eq_config.get("current_ep_cost",1), step=1, key=_uk("eq_form_custom_cost_key"))
                eq_config["current_description"] = st.text_area("Description/Effects:", value=eq_config.get("current_description",""), height=100, key=_uk("eq_form_custom_desc_key"))

            submit_col, cancel_col = st.columns(2)
            with submit_col:
                if st.form_submit_button("💾 Save Equipment", use_container_width=True, type="primary"):
                    new_equipment_list = list(char_state.get('equipment', []))
                    item_to_save: EquipmentDefinition = {"instance_id": eq_config.get("item_instance_id") or generate_id_func("eq_inst_")}

                    if not eq_config["is_custom"] and eq_config.get("selected_item_rule"):
                        rule = eq_config["selected_item_rule"]
                        item_to_save.update({
                            "id": rule['id'], "name": rule['name'], "ep_cost": rule.get('ep_cost',0),
                            "description": rule.get('description', rule.get('effects_text','')),
                            "params": copy.deepcopy(eq_config.get("current_params", {}))
                        })
                    elif eq_config["is_custom"]:
                        if not eq_config.get("current_name","").strip():
                             st.error("Custom item name cannot be empty.")
                             return # Stop save
                        item_to_save.update({
                            "id": "custom_" + "".join(c for c in eq_config.get("current_name","").strip().lower().replace(" ", "_") if c.isalnum() or c == '_'), # Generate a pseudo-ID
                            "name": eq_config.get("current_name"), 
                            "ep_cost": eq_config.get("current_ep_cost",0),
                            "description": eq_config.get("current_description",""),
                            "is_custom_item": True # Flag it
                        })
                    else:
                        st.error("Please select a standard item or define a custom one.")
                        return 

                    if eq_config["mode"] == "add": # Simplified: always add for now
                        new_equipment_list.append(item_to_save)
                    
                    update_char_value(['equipment'], new_equipment_list)
                    _initialize_editor_config(equipment_editor_config_ref, DEFAULT_EQUIPMENT_EDITOR_CONFIG) # Reset and hide
                    equipment_editor_config_ref["show_form"] = False
                    st.rerun()

            with cancel_col:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    _initialize_editor_config(equipment_editor_config_ref, DEFAULT_EQUIPMENT_EDITOR_CONFIG)
                    equipment_editor_config_ref["show_form"] = False
                    st.rerun()
    
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Equipment Point")


# --- HQ Builder Section ---
def render_hq_builder_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    generate_id_func: Callable[[str],str], 
    hq_form_state_ref: Dict[str,Any] 
):
    st_obj.header("Headquarters")
    _initialize_editor_config(hq_form_state_ref, DEFAULT_HQ_EDITOR_CONFIG)
    hq_features_rules: List[Dict] = rule_data.get('hq_features', [])
    
    if not hq_form_state_ref.get("current_size_id") and hq_features_rules: 
        default_size = next((f['id'] for f in hq_features_rules if f.get('type') == 'Size' and "medium" in f.get('name','').lower()), None)
        if not default_size: default_size = next((f['id'] for f in hq_features_rules if f.get('type') == 'Size'), None) # Fallback to first size
        if default_size: hq_form_state_ref["current_size_id"] = default_size


    with st_obj.expander("ℹ️ Understanding Headquarters", expanded=False):
        st_obj.markdown("Headquarters (HQs) are bases of operation bought with Equipment Points. They have Size, Toughness, and various Features.")

    total_ep = char_state.get('derived_total_ep', 0)
    spent_ep_on_hqs = sum(engine.calculate_hq_cost(hq, hq_features_rules) for hq in char_state.get('headquarters', []))
    st_obj.subheader(f"EP Spent on HQs: {spent_ep_on_hqs} (Total EP: {char_state.get('derived_spent_ep',0)} / {total_ep})")


    st_obj.markdown("**Current Headquarters:**")
    current_hqs: List[HQDefinition] = char_state.get('headquarters', [])
    if not current_hqs:
        st_obj.caption("No HQs defined yet.")

    for i, hq_entry in enumerate(current_hqs):
        hq_instance_id = hq_entry.get('id', generate_id_func(f"hq_inst_{i}_")) # Ensure instance ID
        if "id" not in hq_entry: hq_entry["id"] = hq_instance_id
        
        hq_name = hq_entry.get('name', 'Unnamed HQ')
        hq_cost = engine.calculate_hq_cost(hq_entry, hq_features_rules) 

        cols_hq_disp = st_obj.columns([0.7, 0.15, 0.15])
        cols_hq_disp[0].markdown(f"**{hq_name}** ({hq_cost} EP)")
        
        # Edit for HQ - Complex, for now remove and re-add
        # if cols_hq_disp[1].button("✏️ Edit", key=_uk("edit_hq_btn", hq_instance_id)):
            # _initialize_editor_config(hq_form_state_ref, DEFAULT_HQ_EDITOR_CONFIG)
            # hq_form_state_ref.update(copy.deepcopy(hq_entry)) # Load data
            # hq_form_state_ref["hq_instance_id"] = hq_instance_id
            # hq_form_state_ref["mode"] = "edit"
            # hq_form_state_ref["show_form"] = True
            # st.rerun()

        if cols_hq_disp[2].button("🗑️ Remove", key=_uk("remove_hq_btn", hq_instance_id), help="Remove HQ"):
            new_hq_list = [hq for hq in current_hqs if hq.get("id") != hq_instance_id]
            update_char_value(['headquarters'], new_hq_list)
            st.rerun()
            return
        st_obj.markdown("---", key=_uk("hq_sep_disp", hq_instance_id))

    st_obj.markdown("---")
    if st_obj.button("➕ Add New Headquarters", key=_uk("add_new_hq_btn_main_formtrigger")):
        _initialize_editor_config(hq_form_state_ref, DEFAULT_HQ_EDITOR_CONFIG)
        hq_form_state_ref["show_form"] = True
        hq_form_state_ref["mode"] = "add"
        if not hq_form_state_ref.get("current_size_id") and hq_features_rules: # Re-check default
            default_size = next((f['id'] for f in hq_features_rules if f.get('type') == 'Size' and "medium" in f.get('name','').lower()), 
                                next((f['id'] for f in hq_features_rules if f.get('type') == 'Size'), None))
            if default_size: hq_form_state_ref["current_size_id"] = default_size
        st.rerun()

    if hq_form_state_ref.get("show_form"):
        hq_config = hq_form_state_ref
        form_title = "Add New HQ" if hq_config['mode'] == 'add' else f"Edit HQ: {hq_config.get('current_name')}"
        st_obj.subheader(form_title)

        with st_obj.form(key=_uk("hq_editor_form"), clear_on_submit=False):
            hq_config["current_name"] = st.text_input("HQ Name:", value=hq_config.get("current_name", "New HQ"), key=_uk("hq_form_name_key"))

            size_options = {f['id']: f['name'] for f in hq_features_rules if f.get('type') == 'Size'}
            current_size_selection = hq_config.get("current_size_id")
            
            # Ensure current_size_selection is valid or default
            if current_size_selection not in size_options and size_options:
                current_size_selection = list(size_options.keys())[0]
                hq_config["current_size_id"] = current_size_selection

            sel_idx_size = list(size_options.keys()).index(current_size_selection) if current_size_selection in size_options else 0
            
            selected_size_id = st.selectbox("HQ Size:", options=list(size_options.keys()),
                                            format_func=lambda x: size_options.get(x, "Select Size..."),
                                            index=sel_idx_size, key=_uk("hq_form_size_key"))
            if selected_size_id != current_size_selection:
                hq_config["current_size_id"] = selected_size_id
                hq_config["selected_hq_size_rule"] = next((s for s in hq_features_rules if s['id'] == selected_size_id), None)
                st.rerun()
            
            selected_size_rule = hq_config.get("selected_hq_size_rule")
            if not selected_size_rule and hq_config.get("current_size_id"): 
                 selected_size_rule = next((s for s in hq_features_rules if s['id'] == hq_config["current_size_id"]), None)
                 hq_config["selected_hq_size_rule"] = selected_size_rule

            if selected_size_rule:
                st.caption(f"Base Toughness: {selected_size_rule.get('base_toughness_provided',0)}, Base EP Cost (Size): {selected_size_rule.get('ep_cost',0)}")
            
            hq_config["current_bought_toughness"] = st.number_input("Additional Bought Toughness Ranks (1 EP per rank):", 
                                                                  min_value=0, value=hq_config.get("current_bought_toughness",0), step=1, key=_uk("hq_form_bought_tough_key"))

            st.markdown("**HQ Features:**")
            temp_features_list = list(hq_config.get("current_features", []))
            features_to_keep_in_form = []
            for idx, feat_entry in enumerate(temp_features_list):
                feat_rule = next((f_rule for f_rule in hq_features_rules if f_rule['id'] == feat_entry['id']), None)
                feat_name = feat_rule['name'] if feat_rule else feat_entry['id']
                feat_rank_disp = f" (Rank {feat_entry.get('rank',1)})" if feat_rule and feat_rule.get('ranked') else ""
                
                f_cols = st.columns([0.8,0.2])
                f_cols[0].markdown(f"- {feat_name}{feat_rank_disp}")
                if f_cols[1].button("➖", key=_uk("hq_form_remove_feat_key", feat_entry['id'], idx), help=f"Remove {feat_name}"):
                    pass
                else:
                    features_to_keep_in_form.append(feat_entry)
            
            if len(features_to_keep_in_form) != len(temp_features_list):
                hq_config["current_features"] = features_to_keep_in_form
                st.rerun()

            st.markdown("*Add New Feature:*")
            feature_options_hq = {"": "Select Feature..."}
            feature_options_hq.update({f['id']: f"{f['name']} ({f.get('ep_cost', str(f.get('ep_cost_per_rank','?')) + '/r') } EP)" 
                                   for f in hq_features_rules if f.get('type') == 'Feature'})
            
            selected_feature_to_add_id_hq = st.selectbox("Feature:", options=list(feature_options_hq.keys()),
                                                      format_func=lambda x: feature_options_hq.get(x, "Choose..."),
                                                      key=_uk("hq_form_select_feat_to_add_key"))
            
            add_feat_rank_hq = 1
            add_feat_param_text_hq = ""
            selected_feature_rule_to_add_hq = next((f for f in hq_features_rules if f['id'] == selected_feature_to_add_id_hq), None)
            if selected_feature_rule_to_add_hq:
                if selected_feature_rule_to_add_hq.get('ranked'):
                    add_feat_rank_hq = st.number_input("Rank for new feature:", min_value=1, 
                                                    max_value=selected_feature_rule_to_add_hq.get('max_ranks', 20), 
                                                    value=1, key=_uk("hq_form_add_feat_rank_key"))
                if selected_feature_rule_to_add_hq.get('parameter_needed'):
                    add_feat_param_text_hq = st.text_input(selected_feature_rule_to_add_hq.get('parameter_prompt', 'Detail:'), 
                                                        key=_uk("hq_form_add_feat_param_key"))

            if st.button("➕ Add Selected Feature to HQ", key=_uk("hq_form_add_feat_btn_key")):
                if selected_feature_to_add_id_hq and selected_feature_rule_to_add_hq:
                    new_feature_entry_hq = {"id": selected_feature_to_add_id_hq, "rank": add_feat_rank_hq}
                    if selected_feature_rule_to_add_hq.get('parameter_needed') and add_feat_param_text_hq:
                        new_feature_entry_hq['params'] = {'detail': add_feat_param_text_hq}
                    
                    current_form_features_hq = hq_config.get("current_features", [])
                    current_form_features_hq.append(new_feature_entry_hq)
                    hq_config["current_features"] = current_form_features_hq
                    st.rerun()

            submit_col_hq, cancel_col_hq = st.columns(2)
            with submit_col_hq:
                if st.form_submit_button("💾 Save Headquarters", use_container_width=True, type="primary"):
                    if not hq_config.get("current_name").strip() or not hq_config.get("current_size_id"):
                        st.error("HQ Name and Size are required.")
                    else:
                        new_hq_data: HQDefinition = {
                            "id": hq_config.get("hq_instance_id") or generate_id_func("hq_inst_"),
                            "name": hq_config["current_name"],
                            "size_id": hq_config["current_size_id"],
                            "bought_toughness_ranks": hq_config["current_bought_toughness"],
                            "features": copy.deepcopy(hq_config.get("current_features", []))
                        }
                        current_char_hqs = list(char_state.get('headquarters', []))
                        # Replace if editing, else append
                        if hq_config['mode'] == 'edit' and hq_config.get('hq_instance_id'):
                            found_hq = False
                            for idx, h in enumerate(current_char_hqs):
                                if h.get('id') == hq_config['hq_instance_id']:
                                    current_char_hqs[idx] = new_hq_data
                                    found_hq = True
                                    break
                            if not found_hq: current_char_hqs.append(new_hq_data) # Should not happen
                        else:
                            current_char_hqs.append(new_hq_data)
                        
                        update_char_value(['headquarters'], current_char_hqs)
                        _initialize_editor_config(hq_form_state_ref, DEFAULT_HQ_EDITOR_CONFIG)
                        hq_form_state_ref["show_form"] = False
                        st.rerun()
            with cancel_col_hq:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    _initialize_editor_config(hq_form_state_ref, DEFAULT_HQ_EDITOR_CONFIG)
                    hq_form_state_ref["show_form"] = False
                    st.rerun()
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Headquarters")


# --- Vehicle Builder Section ---
def render_vehicle_builder_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    generate_id_func: Callable[[str],str], 
    vehicle_form_state_ref: Dict[str,Any] 
):
    st_obj.header("Vehicles")
    _initialize_editor_config(vehicle_form_state_ref, DEFAULT_VEHICLE_EDITOR_CONFIG)
    vehicle_features_rules: List[Dict] = rule_data.get('vehicle_features', [])
    vehicle_size_stats_rules: List[Dict] = rule_data.get('vehicle_size_stats', [])

    with st_obj.expander("ℹ️ Understanding Vehicles", expanded=False):
        st_obj.markdown("Vehicles are bought with Equipment Points. Their base stats (Strength, Speed, Defense, Toughness, EP Cost) are determined by Size Rank. Features add capabilities and cost more EP.")

    total_ep = char_state.get('derived_total_ep', 0)
    spent_ep_on_vehicles = sum(engine.calculate_vehicle_cost(vh, vehicle_features_rules, vehicle_size_stats_rules) for vh in char_state.get('vehicles', []))
    st_obj.subheader(f"EP Spent on Vehicles: {spent_ep_on_vehicles} (Total EP: {char_state.get('derived_spent_ep',0)} / {total_ep})")

    st_obj.markdown("**Current Vehicles:**")
    current_vehicles: List[VehicleDefinition] = char_state.get('vehicles', [])
    if not current_vehicles:
        st_obj.caption("No vehicles defined yet.")

    for i, v_entry in enumerate(current_vehicles):
        v_instance_id = v_entry.get('id', generate_id_func(f"vh_inst_{i}_"))
        if "id" not in v_entry: v_entry["id"] = v_instance_id
        
        v_name = v_entry.get('name', 'Unnamed Vehicle')
        v_cost = engine.calculate_vehicle_cost(v_entry, vehicle_features_rules, vehicle_size_stats_rules)

        cols_vh_disp = st_obj.columns([0.7, 0.15, 0.15])
        cols_vh_disp[0].markdown(f"**{v_name}** ({v_cost} EP)")
        
        key_remove_vh_btn = _uk("remove_vh_btn", v_instance_id)
        if cols_vh_disp[2].button("🗑️ Remove", key=key_remove_vh_btn, help="Remove Vehicle"):
            new_vh_list = [vh for vh in current_vehicles if vh.get("id") != v_instance_id]
            update_char_value(['vehicles'], new_vh_list)
            st.rerun()
            return
        st_obj.markdown("---", key=_uk("vh_sep_disp", v_instance_id))

    st_obj.markdown("---")
    if st_obj.button("➕ Add New Vehicle", key=_uk("add_new_vh_btn_main_formtrigger")):
        _initialize_editor_config(vehicle_form_state_ref, DEFAULT_VEHICLE_EDITOR_CONFIG)
        vehicle_form_state_ref["show_form"] = True
        vehicle_form_state_ref["mode"] = "add"
        st.rerun()

    if vehicle_form_state_ref.get("show_form"):
        vh_config = vehicle_form_state_ref
        form_title = "Add New Vehicle" # Simplified: edit is remove/re-add
        st_obj.subheader(form_title)

        with st_obj.form(key=_uk("vehicle_editor_form"), clear_on_submit=False):
            vh_config["current_name"] = st.text_input("Vehicle Name:", value=vh_config.get("current_name", "New Vehicle"), key=_uk("vh_form_name_key"))
            
            size_rank_options = {s['size_rank_value']: f"{s['size_name']} (Rank {s['size_rank_value']})" for s in vehicle_size_stats_rules}
            current_size_rank_val = vh_config.get("current_size_rank", 0)
            valid_size_ranks = list(size_rank_options.keys())
            sel_idx_size_rank = valid_size_ranks.index(current_size_rank_val) if current_size_rank_val in valid_size_ranks else 0

            selected_size_rank = st.selectbox("Vehicle Size Rank:", options=valid_size_ranks,
                                              format_func=lambda x: size_rank_options.get(x, "Select Size Rank..."),
                                              index=sel_idx_size_rank, key=_uk("vh_form_size_rank_key"))
            if selected_size_rank != current_size_rank_val:
                vh_config["current_size_rank"] = selected_size_rank
                st.rerun()
            
            size_stat_rule = next((s for s in vehicle_size_stats_rules if s['size_rank_value'] == vh_config["current_size_rank"]), None)
            if size_stat_rule:
                vh_config["derived_base_stats"] = size_stat_rule
                st.caption(f"Base Stats from Size {size_stat_rule['size_name']}: Str {size_stat_rule['base_str']}, Spd {size_stat_rule['base_spd']}, Def {size_stat_rule['base_def']}, Tou {size_stat_rule['base_tou']}. Base EP: {size_stat_rule['base_ep_cost']}")
            
            st.markdown("**Vehicle Features:**")
            temp_vh_features_list = list(vh_config.get("current_features", []))
            vh_features_to_keep = []
            for idx, feat_entry in enumerate(temp_vh_features_list):
                feat_rule = next((f_rule for f_rule in vehicle_features_rules if f_rule['id'] == feat_entry['id']), None)
                feat_name = feat_rule['name'] if feat_rule else feat_entry['id']
                feat_rank_disp = f" (Rank {feat_entry.get('rank',1)})" if feat_rule and feat_rule.get('ranked') else ""
                
                f_cols_vh = st.columns([0.8,0.2])
                f_cols_vh[0].markdown(f"- {feat_name}{feat_rank_disp}")
                if f_cols_vh[1].button("➖", key=_uk("vh_form_remove_feat_key", feat_entry['id'], idx), help=f"Remove {feat_name}"):
                    pass
                else:
                    vh_features_to_keep.append(feat_entry)
            
            if len(vh_features_to_keep) != len(temp_vh_features_list):
                vh_config["current_features"] = vh_features_to_keep
                st.rerun()

            st.markdown("*Add New Feature:*")
            vh_feature_options = {"": "Select Feature..."}
            vh_feature_options.update({f['id']: f"{f['name']} ({f.get('ep_cost', str(f.get('ep_cost_per_rank','?')) + '/r')} EP)" 
                                     for f in vehicle_features_rules})
            
            selected_vh_feature_to_add_id = st.selectbox("Feature:", options=list(vh_feature_options.keys()),
                                                        format_func=lambda x: vh_feature_options.get(x, "Choose..."),
                                                        key=_uk("vh_form_select_feat_to_add_key"))
            
            add_vh_feat_rank = 1
            add_vh_feat_param_text = ""
            selected_vh_feature_rule_to_add = next((f for f in vehicle_features_rules if f['id'] == selected_vh_feature_to_add_id), None)
            if selected_vh_feature_rule_to_add:
                if selected_vh_feature_rule_to_add.get('ranked'):
                    add_vh_feat_rank = st.number_input("Rank for new feature:", min_value=1, 
                                                        max_value=selected_vh_feature_rule_to_add.get('max_ranks', 20), 
                                                        value=1, key=_uk("vh_form_add_feat_rank_key"))
                if selected_vh_feature_rule_to_add.get('parameter_needed'):
                    add_vh_feat_param_text = st.text_input(selected_vh_feature_rule_to_add.get('parameter_prompt', 'Detail:'), 
                                                            key=_uk("vh_form_add_feat_param_key"))

            if st.button("➕ Add Selected Feature to Vehicle", key=_uk("vh_form_add_feat_btn_key")):
                if selected_vh_feature_to_add_id and selected_vh_feature_rule_to_add:
                    new_vh_feature_entry = {"id": selected_vh_feature_to_add_id, "rank": add_vh_feat_rank}
                    if selected_vh_feature_rule_to_add.get('parameter_needed') and add_vh_feat_param_text:
                        new_vh_feature_entry['params'] = {'detail': add_vh_feat_param_text}
                    
                    current_form_vh_features = vh_config.get("current_features", [])
                    current_form_vh_features.append(new_vh_feature_entry)
                    vh_config["current_features"] = current_form_vh_features
                    st.rerun()

            submit_col_vh, cancel_col_vh = st.columns(2)
            with submit_col_vh:
                if st.form_submit_button("💾 Save Vehicle", use_container_width=True, type="primary"):
                    if not vh_config.get("current_name").strip():
                        st.error("Vehicle Name is required.")
                    else:
                        new_vehicle_data: VehicleDefinition = {
                            "id": vh_config.get("vehicle_instance_id") or generate_id_func("vh_inst_"),
                            "name": vh_config["current_name"],
                            "size_rank": vh_config["current_size_rank"],
                            "features": copy.deepcopy(vh_config.get("current_features", []))
                        }
                        current_char_vehicles = list(char_state.get('vehicles', []))
                        # Simplified add for now
                        current_char_vehicles.append(new_vehicle_data)
                        update_char_value(['vehicles'], current_char_vehicles)
                        _initialize_editor_config(vehicle_form_state_ref, DEFAULT_VEHICLE_EDITOR_CONFIG)
                        vehicle_form_state_ref["show_form"] = False
                        st.rerun()
            with cancel_col_vh:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    _initialize_editor_config(vehicle_form_state_ref, DEFAULT_VEHICLE_EDITOR_CONFIG)
                    vehicle_form_state_ref["show_form"] = False
                    st.rerun()
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Vehicle")


# --- Allies Section ---
def render_allies_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable, 
    generate_id_func: Callable[[str],str],
    ally_editor_config_ref: Dict[str, Any] 
):
    st_obj.header("Companions (Allies)")
    _initialize_editor_config(ally_editor_config_ref, DEFAULT_ALLY_EDITOR_CONFIG)

    with st_obj.expander("ℹ️ Understanding Companions", expanded=False):
        st_obj.markdown("Companions include Minions and Sidekicks (bought with Advantage ranks, providing PP pools), and creatures from Summon/Duplication powers (built on PP from power rank).")

    minion_pool_total = char_state.get('derived_total_minion_pool_pp', 0)
    minion_pool_spent = char_state.get('derived_spent_minion_pool_pp', 0) 
    sidekick_pool_total = char_state.get('derived_total_sidekick_pool_pp', 0)
    sidekick_pool_spent = char_state.get('derived_spent_sidekick_pool_pp', 0)

    col_min, col_side = st_obj.columns(2)
    with col_min:
        if minion_pool_total > 0 or minion_pool_spent > 0 : # Show even if pool is 0 but points spent (error case)
            st_obj.metric(label="Minion Pool PP", value=f"{minion_pool_spent} / {minion_pool_total}", delta=f"{minion_pool_total - minion_pool_spent} Remaining", delta_color="normal" if minion_pool_spent <= minion_pool_total else "inverse")
    with col_side:
        if sidekick_pool_total > 0 or sidekick_pool_spent > 0:
            st_obj.metric(label="Sidekick Pool PP", value=f"{sidekick_pool_spent} / {sidekick_pool_total}", delta=f"{sidekick_pool_total - sidekick_pool_spent} Remaining", delta_color="normal" if sidekick_pool_spent <= sidekick_pool_total else "inverse")
    
    st_obj.markdown("**Defined Minions & Sidekicks (from Advantages):**")
    # Filter for allies sourced from advantages, not powers
    current_advantage_allies: List[AllyDefinition] = [
        ally for ally in char_state.get('allies', []) 
        if ally.get('source_type') == 'advantage_pool'
    ]

    if not current_advantage_allies:
        st_obj.caption("No Minions or Sidekicks defined from Advantages yet.")

    for i, ally_entry in enumerate(current_advantage_allies):
        ally_instance_id = ally_entry.get('id', generate_id_func(f"ally_adv_{i}_"))
        if "id" not in ally_entry: ally_entry["id"] = ally_instance_id

        ally_name = ally_entry.get('name', 'Unnamed Ally')
        ally_type = ally_entry.get('type', 'Minion')
        ally_cost = ally_entry.get('cost_pp_asserted_by_user', 0)

        cols_ally_disp = st_obj.columns([0.5, 0.15, 0.1, 0.1, 0.15])
        cols_ally_disp[0].markdown(f"**{ally_name}** ({ally_type})")
        cols_ally_disp[1].markdown(f"*PL {ally_entry.get('pl_for_ally','N/A')}*")
        cols_ally_disp[2].markdown(f"*{ally_cost} PP*")
        
        key_edit_ally_btn = _uk("edit_ally_btn", ally_instance_id)
        if cols_ally_disp[3].button("✏️", key=key_edit_ally_btn, help="Edit Ally"):
            _initialize_editor_config(ally_editor_config_ref, DEFAULT_ALLY_EDITOR_CONFIG) 
            ally_editor_config_ref["show_form"] = True
            ally_editor_config_ref["mode"] = "edit"
            ally_editor_config_ref["ally_instance_id"] = ally_instance_id
            # Populate form state from ally_entry
            for k_form, k_entry in { # Map form keys to entry keys
                "current_name": "name", "current_type": "type", "current_pl": "pl_for_ally",
                "current_asserted_pp_cost": "cost_pp_asserted_by_user",
                "current_abilities_summary_text": "abilities_summary_text",
                "current_defenses_summary_text": "defenses_summary_text",
                "current_skills_summary_text": "skills_summary_text",
                "current_powers_advantages_summary_text": "powers_advantages_summary_text",
                "current_notes": "notes"
            }.items():
                ally_editor_config_ref[k_form] = ally_entry.get(k_entry, DEFAULT_ALLY_EDITOR_CONFIG[k_form])
            st.rerun()

        key_remove_ally_btn = _uk("remove_ally_btn", ally_instance_id)
        if cols_ally_disp[4].button("🗑️", key=key_remove_ally_btn, help="Remove Ally"):
            new_ally_list = [ally for ally in char_state.get('allies', []) if ally.get("id") != ally_instance_id]
            update_char_value(['allies'], new_ally_list)
            st.rerun()
            return
        with st_obj.expander("Show Details", expanded=False):
            st_obj.json(ally_entry) 
        st_obj.markdown("---", key=_uk("ally_sep_disp", ally_instance_id))

    st_obj.markdown("---")
    if st_obj.button("➕ Add Minion/Sidekick", key=_uk("add_new_ally_btn_main_formtrigger")):
        _initialize_editor_config(ally_editor_config_ref, DEFAULT_ALLY_EDITOR_CONFIG)
        ally_editor_config_ref["show_form"] = True
        ally_editor_config_ref["mode"] = "add"
        st.rerun()

    if ally_editor_config_ref.get("show_form"):
        ally_config = ally_editor_config_ref
        form_title = "Add New Minion/Sidekick" if ally_config['mode'] == 'add' else f"Edit {ally_config.get('current_name', 'Ally')}"
        st_obj.subheader(form_title)

        with st_obj.form(key=_uk("ally_editor_form"), clear_on_submit=False): # Keep values on internal reruns
            ally_config["current_name"] = st.text_input("Ally Name:", value=ally_config.get("current_name", ""), key=_uk("ally_form_name_key"))
            ally_config["current_type"] = st.selectbox("Ally Type:", ["Minion", "Sidekick"], 
                                                     index=["Minion", "Sidekick"].index(ally_config.get("current_type","Minion")), 
                                                     key=_uk("ally_form_type_key"))
            ally_config["current_pl"] = st.number_input("Ally Power Level (PL):", min_value=1, max_value=char_state.get('powerLevel',10), 
                                                      value=ally_config.get("current_pl",5), step=1, key=_uk("ally_form_pl_key"))
            ally_config["current_asserted_pp_cost"] = st.number_input("Asserted PP Cost for this Ally's Build:", min_value=0, 
                                                                     value=ally_config.get("current_asserted_pp_cost",0), step=1, key=_uk("ally_form_asserted_cost_key"),
                                                                     help="This is how many PP from your Minion/Sidekick pool this ally uses.")
            
            st.markdown("**Simplified Stat Block:** (Describe key traits; detailed build is outside scope of this helper)")
            ally_config["current_abilities_summary_text"] = st.text_area("Key Abilities (e.g., STR 5, AGL 2):", value=ally_config.get("current_abilities_summary_text",""), height=50, key=_uk("ally_form_abil_key"))
            ally_config["current_defenses_summary_text"] = st.text_area("Key Defenses (e.g., Dodge 8, Tou 6):", value=ally_config.get("current_defenses_summary_text",""), height=50, key=_uk("ally_form_def_key"))
            ally_config["current_skills_summary_text"] = st.text_area("Key Skills (e.g., Stealth +10):", value=ally_config.get("current_skills_summary_text",""), height=75, key=_uk("ally_form_skills_key"))
            ally_config["current_powers_advantages_summary_text"] = st.text_area("Key Powers/Advantages:", value=ally_config.get("current_powers_advantages_summary_text",""), height=100, key=_uk("ally_form_pwr_adv_key"))
            ally_config["current_notes"] = st.text_area("Notes:", value=ally_config.get("current_notes",""), height=75, key=_uk("ally_form_notes_key"))

            submit_col_ally, cancel_col_ally = st.columns(2)
            with submit_col_ally:
                if st.form_submit_button("💾 Save Ally", use_container_width=True, type="primary"):
                    if not ally_config.get("current_name","").strip():
                        st.error("Ally Name is required.")
                    else:
                        new_ally_data: AllyDefinition = {
                            "id": ally_config.get("ally_instance_id") or generate_id_func("ally_inst_"),
                            "source_type": "advantage_pool", 
                            "name": ally_config["current_name"],
                            "type": ally_config["current_type"],
                            "pl_for_ally": ally_config["current_pl"],
                            "cost_pp_asserted_by_user": ally_config["current_asserted_pp_cost"],
                            "abilities_summary_text": ally_config["current_abilities_summary_text"],
                            "defenses_summary_text": ally_config["current_defenses_summary_text"],
                            "skills_summary_text": ally_config["current_skills_summary_text"],
                            "powers_advantages_summary_text": ally_config["current_powers_advantages_summary_text"],
                            "notes": ally_config["current_notes"]
                        }
                        current_char_allies_list = list(char_state.get('allies', []))
                        if ally_config["mode"] == "add":
                            current_char_allies_list.append(new_ally_data)
                        else: # Edit
                            found = False
                            for idx, existing_ally in enumerate(current_char_allies_list):
                                if existing_ally.get("id") == new_ally_data["id"]:
                                    current_char_allies_list[idx] = new_ally_data
                                    found = True
                                    break
                            if not found: current_char_allies_list.append(new_ally_data) # Should only happen if ID changed, safety
                        
                        update_char_value(['allies'], current_char_allies_list)
                        _initialize_editor_config(ally_editor_config_ref, DEFAULT_ALLY_EDITOR_CONFIG)
                        ally_editor_config_ref["show_form"] = False
                        st.rerun()
            with cancel_col_ally:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    _initialize_editor_config(ally_editor_config_ref, DEFAULT_ALLY_EDITOR_CONFIG)
                    ally_editor_config_ref["show_form"] = False
                    st.rerun()

    st_obj.markdown("---")
    st_obj.markdown("**Summoned/Duplicated Allies (from Powers):**")
    # Allies created by powers (Summon, Duplication) are stored in char_state.allies with source_type: 'power_creation'
    # The actual stat blocks are stored within the power definition itself (e.g., power_entry['ally_notes_and_stats_structured'])
    # This section should *display* them.
    
    power_created_allies_display = []
    for pwr in char_state.get('powers', []):
        if pwr.get('baseEffectId') in ['eff_summon', 'eff_duplication'] and pwr.get('ally_notes_and_stats_structured'):
            ally_stat_block = pwr.get('ally_notes_and_stats_structured')
            power_created_allies_display.append({
                "name": ally_stat_block.get('name', 'Unnamed Creation'),
                "source_power_name": pwr.get('name', 'Unknown Power'),
                "pl": ally_stat_block.get('pl_for_ally', 'N/A'),
                "cost": ally_stat_block.get('cost_pp_asserted_by_user', 'N/A'),
                "details": ally_stat_block
            })

    if not power_created_allies_display:
        st_obj.caption("No allies currently defined via Summon/Duplication powers.")
    for ally_info in power_created_allies_display:
        st_obj.markdown(f"**{ally_info['name']}** (from Power: *{ally_info['source_power_name']}*) - PL {ally_info['pl']}, Cost {ally_info['cost']} PP")
        with st_obj.expander("Show Details", expanded=False):
            st_obj.json(ally_info['details'])
        st_obj.markdown("---", key=_uk("ally_power_sep", ally_info['name'], ally_info['source_power_name']))


    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Ally")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Minion Pool")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Sidekick Pool")


# --- Complications Section ---
def render_complications_section_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    update_char_value: Callable
):
    st_obj.header("Complications")
    complications_help = "Complications are problems, weaknesses, or responsibilities that make your hero's life interesting. They don't cost Power Points. Instead, when your Complications cause trouble during the game, your Gamemaster (GM) awards you Hero Points! You need at least two Complications for a complete character."
    rule_help_text_section = rule_data.get("help_text", {})
    if isinstance(rule_help_text_section, dict): 
        complications_help = rule_help_text_section.get("complications_help", complications_help)
        
    with st_obj.expander("ℹ️ Understanding Complications", expanded=False):
        st_obj.markdown(complications_help)

    current_complications_list = char_state.get('complications', [])
    
    if not current_complications_list:
        st_obj.info("No complications added yet. A minimum of two is recommended for a complete character.")

    for i, comp_entry in enumerate(current_complications_list):
        comp_desc = comp_entry.get('description', '')
        cols_comp = st_obj.columns([0.9, 0.1])
        
        key_comp_text_edit = _uk("comp_text_edit", i)
        new_desc = cols_comp[0].text_area(
            f"Complication #{i+1}", 
            value=comp_desc, 
            key=key_comp_text_edit,
            height=75
        )
        
        if new_desc != comp_desc:
            updated_complications = list(current_complications_list)
            updated_complications[i] = {'description': new_desc}
            update_char_value(['complications'], updated_complications) 
            st_obj.rerun()

        key_comp_del_btn_edit = _uk("comp_del_btn_edit", i)
        if cols_comp[1].button("🗑️", key=key_comp_del_btn_edit, help="Remove Complication"):
            updated_complications = [c for idx, c in enumerate(current_complications_list) if idx != i]
            update_char_value(['complications'], updated_complications)
            st_obj.rerun()
            return 

    st_obj.markdown("---")
    st_obj.subheader("Add New Complication")
    with st_obj.form(key=_uk("add_complication_form"), clear_on_submit=True):
        new_comp_text_input = st.text_area("New Complication Description:", key=_uk("new_comp_text_input_form_adv"), height=75) 
        submitted_add_comp = st.form_submit_button("➕ Add Complication")
        
        if submitted_add_comp:
            if new_comp_text_input.strip():
                fresh_complications_list = list(char_state.get('complications', []))
                fresh_complications_list.append({'description': new_comp_text_input.strip()})
                update_char_value(['complications'], fresh_complications_list)
                st.rerun() 
            else:
                st.warning("Complication description cannot be empty.", icon="⚠️")
            
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Complication")

# --- Measurements Table Section ---
def render_measurements_table_view_adv(st_obj: Any, rule_data: RuleData):
    st_obj.header("Measurements Table Reference")
    with st_obj.expander("ℹ️ Understanding Measurements (DHH p.19)", expanded=False):
        st_obj.markdown("This table shows how ranks correspond to real-world distances, time, mass, and volume. Useful for determining power effect ranges, carrying capacity, etc.")
    
    measurements_data = rule_data.get('measurements_table', []) 

    if measurements_data:
        st_obj.dataframe(measurements_data, hide_index=True, use_container_width=True)
    else:
        st_obj.warning("Measurements table data not found in rule_data.")

# --- Character Sheet View (In-App) ---
def render_character_sheet_view_in_app_adv(
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine
):
    st_obj.header(f"Character Sheet Preview: {char_state.get('name', 'Unnamed Hero')}")
    
    key_refresh_sheet_btn = _uk("refresh_sheet_btn_adv_preview_main")
    if st_obj.button("🔄 Recalculate & Refresh Sheet Data", key=key_refresh_sheet_btn):
         st.session_state.character = engine.recalculate(char_state) 
         st_obj.rerun()

    try:
        from pdf_utils import generate_pdf_html_content as gen_html_func 
        
        sheet_html = gen_html_func(char_state, rule_data, engine)
    except ImportError:
        st_obj.error("Could not import `generate_pdf_html_content` from `pdf_utils`. Ensure it's correctly placed and importable.")
        return
    except Exception as e:
        st_obj.error(f"Error generating sheet HTML: {e}")
        return

    css_path = "assets/pdf_styles.css" 
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            sheet_css = f"<style>{f.read()}</style>"
        st_obj.markdown(sheet_css, unsafe_allow_html=True)
    except FileNotFoundError:
        st_obj.warning(f"CSS file `{css_path}` not found. Sheet preview will be unstyled.")
    
    st_obj.markdown(sheet_html, unsafe_allow_html=True)

# --- Main Dispatch Function for Advanced Mode Views ---
def render_selected_advanced_view(
    view_name: str, 
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable,
    generate_id_func: Callable[[str],str], 
    power_form_state_ref: Dict[str,Any], 
    hq_form_state_ref: Dict[str,Any],
    vehicle_form_state_ref: Dict[str,Any],
    advantage_editor_config_ref: Dict[str, Any], 
    equipment_editor_config_ref: Dict[str, Any], 
    ally_editor_config_ref: Dict[str, Any]
):
    if view_name == 'Abilities': 
        render_abilities_section_adv(st_obj, char_state, rule_data, engine, update_char_value)
    elif view_name == 'Defenses': 
        render_defenses_section_adv(st_obj, char_state, rule_data, engine, update_char_value)
    elif view_name == 'Skills': 
        render_skills_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func)
    elif view_name == 'Advantages': 
        render_advantages_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, advantage_editor_config_ref)
    elif view_name == 'Powers': 
        render_powers_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, power_form_state_ref)
    elif view_name == 'Equipment': 
        render_equipment_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, equipment_editor_config_ref)
    elif view_name == 'Headquarters': 
        render_hq_builder_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, hq_form_state_ref)
    elif view_name == 'Vehicles': 
        render_vehicle_builder_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, vehicle_form_state_ref)
    elif view_name == 'Companions (Allies)': 
        render_allies_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, ally_editor_config_ref)
    elif view_name == 'Complications': 
        render_complications_section_adv(st_obj, char_state, update_char_value)
    elif view_name == 'Measurements Table': 
        render_measurements_table_view_adv(st_obj, rule_data)
    elif view_name == 'Character Sheet': 
        render_character_sheet_view_in_app_adv(st_obj, char_state, rule_data, engine)
    else: 
        st_obj.error(f"Unknown advanced view selected: {view_name}")

