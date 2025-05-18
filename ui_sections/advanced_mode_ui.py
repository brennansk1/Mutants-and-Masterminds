# heroforge-mm-streamlit/ui_sections/advanced_mode_ui.py
# Version: 1.2 (Completed Edit for HQ/Vehicles, Full Integration)

import streamlit as st
import copy
import math
import json # For pretty printing dicts in UI sometimes
import uuid # For instance_ids
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core_engine import CoreEngine, CharacterState, RuleData, AdvantageDefinition, PowerDefinition, EquipmentDefinition, HQDefinition, VehicleDefinition, AllyDefinition
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
        st_obj.caption(f"⚠️ {err}", key=_uk("validation_err", field_identifier, err_idx)) # caption might be ok with key, but markdown is not. Keeping for consistency if user changes this.

# --- Helper function to initialize editor state ---
def _initialize_editor_config(editor_config_ref: Dict[str, Any], default_values: Dict[str, Any], preserve_mode: bool = False):
    """Initializes or resets a generic editor config in session state."""
    current_mode = editor_config_ref.get("mode") if preserve_mode else "add"
    show_form = editor_config_ref.get("show_form", False) if preserve_mode else False

    editor_config_ref.clear()
    editor_config_ref.update(copy.deepcopy(default_values))

    editor_config_ref["mode"] = current_mode
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
    "current_features": [], # List of feature entries {'id': rule_id, 'rank': X, 'params': {}, 'instance_id': unique_feature_instance_id}
    "selected_hq_size_rule": None
}
DEFAULT_VEHICLE_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "vehicle_instance_id": None,
    "current_name": "New Vehicle",
    "current_size_rank": 0,
    "current_features": [], # Similar to HQ features
    "derived_base_stats": {}
}
DEFAULT_ALLY_EDITOR_CONFIG = {
    "show_form": False, "mode": "add", "ally_instance_id": None,
    "current_name": "New Ally", "current_type": "Minion", "current_pl": 5,
    "current_asserted_pp_cost": 0,
    "current_abilities_summary_text": "STR 0, STA 0, AGL 0, DEX 0, FGT 0, INT 0, AWE 0, PRE 0",
    "current_defenses_summary_text": "Dodge 0, Parry 0, Toughness 0, Fortitude 0, Will 0",
    "current_skills_summary_text": "Perception +0",
    "current_powers_advantages_summary_text": "None",
    "current_notes": "",
    "current_structured_abilities": {},
    "current_structured_defenses": {}
}

# --- Abilities Section ---
def render_abilities_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable):
    st_obj.header("Abilities")
    with st_obj.expander("ℹ️ Understanding Abilities (Cost: 2 PP per Rank)", expanded=False):
        st_obj.markdown(rule_data.get("abilities", {}).get("help_text", {}).get("general", "Define your hero's 8 core attributes. 0 is average human."))
    ability_rules_data = rule_data.get('abilities', {}); ability_rules_list: List[Dict[str, Any]] = ability_rules_data.get('list', [])
    current_abilities = char_state.get('abilities', {}); cost_factor = ability_rules_data.get('costFactor', 2)
    cols = st_obj.columns(4)
    for i, ab_info in enumerate(ability_rules_list):
        ab_id = ab_info['id']; ab_name = ab_info['name']; ab_help = ability_rules_data.get("help_text", {}).get(ab_id, ab_info.get('description', ''))
        current_rank = current_abilities.get(ab_id, 0)
        with cols[i % len(cols)]:
            key_ability_input = _uk("ab_input", ab_id)
            new_rank = st_obj.number_input(f"{ab_name} ({ab_id})", min_value=-5, max_value=30, value=current_rank, key=key_ability_input, help=ab_help, step=1)
            if new_rank != current_rank: update_char_value(['abilities', ab_id], new_rank); st_obj.rerun()
            cost = new_rank * cost_factor; mod = engine.get_ability_modifier(new_rank)
            st_obj.caption(f"Mod: {mod:+}, Cost: {cost} PP", key=_uk("ab_caption", ab_id)) # caption might be ok
    total_ability_cost = engine.calculate_ability_cost(current_abilities)
    st_obj.markdown(f"**Total Ability Cost: {total_ability_cost} PP**")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Ability")

# --- Defenses Section ---
def render_defenses_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable):
    st_obj.header("Defenses")
    defenses_help_text = rule_data.get("help_text", {}).get("defenses_help", "Base from Abilities, buy ranks to increase. PL Caps are crucial!")
    with st_obj.expander("🛡️ Understanding Defenses (Cost: 1 PP per +1 Bought Rank)", expanded=False): st_obj.markdown(defenses_help_text)
    pl = char_state.get('powerLevel', 10); pl_cap_paired = pl * 2; bought_defenses = char_state.get('defenses', {}); current_abilities = char_state.get('abilities', {})
    defense_configs = [
        {"id": "Dodge", "name": "Dodge", "base_ability_id": "AGL", "tooltip": "Avoid ranged/area attacks."},
        {"id": "Parry", "name": "Parry", "base_ability_id": "FGT", "tooltip": "Avoid close attacks."},
        {"id": "Toughness", "name": "Toughness", "base_ability_id": "STA", "tooltip": "Resist damage."},
        {"id": "Fortitude", "name": "Fortitude", "base_ability_id": "STA", "tooltip": "Resist health effects."},
        {"id": "Will", "name": "Will", "base_ability_id": "AWE", "tooltip": "Resist mental effects."}
    ]
    st_obj.markdown("Enter **bought ranks** for each defense below:")
    def_cols = st_obj.columns(len(defense_configs)); totals_for_cap_check: Dict[str, int] = {}
    for i, d_conf in enumerate(defense_configs):
        with def_cols[i]:
            base_val_from_ability = engine.get_ability_modifier(current_abilities.get(d_conf['base_ability_id'], 0)); bought_val = bought_defenses.get(d_conf['id'], 0)
            total_val_display = engine.get_total_defense(char_state, d_conf['id'], d_conf['base_ability_id']); totals_for_cap_check[d_conf['id']] = total_val_display
            key_def_input = _uk("def_input", d_conf['id'])
            new_bought_val = st_obj.number_input(f"{d_conf['name']}", min_value=0, max_value=pl + 15, value=bought_val, key=key_def_input, help=f"{d_conf['tooltip']}\nBase: {base_val_from_ability}, Total: {total_val_display}")
            if new_bought_val != bought_val: update_char_value(['defenses', d_conf['id']], new_bought_val); st_obj.rerun()
            st_obj.caption(f"Bought: {new_bought_val} (Cost: {new_bought_val} PP)", key=_uk("def_caption", d_conf['id'])) # caption might be ok
            st_obj.metric(label=f"Total {d_conf['name']}", value=total_val_display, key=_uk("def_metric", d_conf['id']))
    st_obj.markdown("---"); st_obj.subheader("Defense Power Level Caps"); cap_col1, cap_col2, cap_col3 = st_obj.columns(3)
    total_toughness_for_cap = totals_for_cap_check.get('Toughness',0); dt_sum = totals_for_cap_check.get('Dodge',0) + total_toughness_for_cap; pt_sum = totals_for_cap_check.get('Parry',0) + total_toughness_for_cap; fw_sum = totals_for_cap_check.get('Fortitude',0) + totals_for_cap_check.get('Will',0)
    dt_color = "normal" if dt_sum <= pl_cap_paired else "inverse"; pt_color = "normal" if pt_sum <= pl_cap_paired else "inverse"; fw_color = "normal" if fw_sum <= pl_cap_paired else "inverse"
    with cap_col1: st_obj.metric("Dodge + Toughness", f"{dt_sum}/{pl_cap_paired}", delta="OK" if dt_color=="normal" else "OVER!", delta_color=dt_color, key=_uk("def_cap_metric","dt"))
    with cap_col2: st_obj.metric("Parry + Toughness", f"{pt_sum}/{pl_cap_paired}", delta="OK" if pt_color=="normal" else "OVER!", delta_color=pt_color, key=_uk("def_cap_metric","pt"))
    with cap_col3: st_obj.metric("Fortitude + Will", f"{fw_sum}/{pl_cap_paired}", delta="OK" if fw_color=="normal" else "OVER!", delta_color=fw_color, key=_uk("def_cap_metric","fw"))
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Defense Cap"); display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Toughness")

# --- Skills Section ---
def render_skills_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str], str]):
    st_obj.header("Skills"); skills_rules_data = rule_data.get('skills', {})
    with st_obj.expander("🎯 Understanding Skills (Cost: 1 PP per 2 Ranks Bought)", expanded=False):
        st_obj.markdown(skills_rules_data.get("help_text",{}).get("general","")); st_obj.markdown(skills_rules_data.get("help_text",{}).get("specialization_note",""))
    current_skills_state = char_state.get('skills', {}); current_abilities = char_state.get('abilities', {}); pl = char_state.get('powerLevel', 10)
    skill_bonus_cap = pl + 10; skill_rank_cap = pl + 5; total_skill_cost = engine.calculate_skill_cost(current_skills_state)
    st_obj.subheader(f"Total Skill Cost: {total_skill_cost} PP"); st_obj.markdown("---"); st_obj.markdown("**Modify Skill Ranks:**")
    base_skill_rules: List[Dict[str, Any]] = skills_rules_data.get('list', []); skill_display_cols = st_obj.columns(3); col_idx = 0
    sorted_base_skill_rules = sorted(base_skill_rules, key=lambda x: x.get('name', ''))
    for skill_info_idx, skill_info in enumerate(sorted_base_skill_rules):
        base_skill_id = skill_info['id']; base_skill_name = skill_info['name']; gov_ab_id = skill_info.get('ability', ''); skill_desc_help = skill_info.get('description', '') + f"\nMax Ranks: {skill_rank_cap}, Max Bonus: {skill_bonus_cap:+}"
        is_specializable = skill_info.get('specialization_possible', False)
        with skill_display_cols[col_idx % len(skill_display_cols)]:
            st_obj.markdown(f"##### {base_skill_name} ({gov_ab_id})")
            if not is_specializable:
                bought_rank = current_skills_state.get(base_skill_id, 0); ability_mod = engine.get_ability_modifier(current_abilities.get(gov_ab_id, 0)); total_bonus = ability_mod + bought_rank
                key_skill_input = _uk("skill_input_base", base_skill_id)
                new_rank = st_obj.number_input("Ranks", min_value=0, max_value=skill_rank_cap, value=bought_rank, key=key_skill_input, label_visibility="visible", help=skill_desc_help)
                if new_rank != bought_rank: update_char_value(['skills', base_skill_id], new_rank); st_obj.rerun()
                bonus_display_str = f"Total Bonus: {total_bonus:+}"
                if total_bonus > skill_bonus_cap: st_obj.error(f"{bonus_display_str} (Cap: {skill_bonus_cap:+})", icon="⚠️", key=_uk("skill_err_base", base_skill_id))
                else: st_obj.caption(bonus_display_str, key=_uk("skill_bonus_disp_base", base_skill_id)) # caption might be ok
            else:
                specializations_for_this_base = {sk_id: r for sk_id, r in current_skills_state.items() if sk_id.startswith(base_skill_id + "_") and sk_id != base_skill_id}
                if not specializations_for_this_base: st_obj.caption(f"No '{base_skill_name}' specializations yet.", key=_uk("no_spec_caption", base_skill_id)) # caption might be ok
                for spec_skill_id, spec_rank in sorted(specializations_for_this_base.items()):
                    spec_name_part = spec_skill_id.replace(base_skill_id + "_", "").replace("_", " ").title(); spec_ability_mod = engine.get_ability_modifier(current_abilities.get(gov_ab_id, 0)); spec_total_bonus = spec_ability_mod + spec_rank
                    cols_spec_edit = st_obj.columns([0.7, 0.15, 0.15]);
                    with cols_spec_edit[0]: st_obj.markdown(f"*{spec_name_part}*")
                    with cols_spec_edit[1]:
                        key_spec_skill_input = _uk("skill_input_spec", spec_skill_id)
                        new_spec_rank = st_obj.number_input("Ranks", min_value=0, max_value=skill_rank_cap, value=spec_rank, key=key_spec_skill_input, help=f"Ranks for {spec_name_part}. Max: {skill_rank_cap}")
                    with cols_spec_edit[2]:
                        st_obj.markdown("## ") # This markdown call is for spacing or larger text, does not need a key.
                        key_del_spec_btn = _uk("del_spec_btn", spec_skill_id)
                        if st_obj.button("✖", key=key_del_spec_btn, help=f"Remove '{spec_name_part}'"):
                            new_skills_state = {k:v for k,v in current_skills_state.items() if k != spec_skill_id}; update_char_value(['skills'], new_skills_state); st_obj.rerun(); return
                    if new_spec_rank != spec_rank: update_char_value(['skills', spec_skill_id], new_spec_rank); st_obj.rerun()
                    spec_bonus_display_str = f"Bonus: {spec_total_bonus:+}";
                    if spec_total_bonus > skill_bonus_cap: st_obj.error(f"{spec_bonus_display_str} (Cap: {skill_bonus_cap:+})", icon="⚠️", key=_uk("skill_err_spec", spec_skill_id))
                    else: st_obj.caption(spec_bonus_display_str, key=_uk("skill_bonus_disp_spec", spec_skill_id)) # caption might be ok
                with st_obj.form(key=_uk("add_spec_form", base_skill_id), clear_on_submit=True):
                    spec_prompt = skill_info.get('specialization_prompt', 'Enter specialization name'); new_spec_name_text = st.text_input(f"New {base_skill_name} Specialization:", placeholder=spec_prompt, key=_uk("add_spec_text_input_form", base_skill_id))
                    submitted_add_spec = st.form_submit_button(f"➕ Add")
                    if submitted_add_spec and new_spec_name_text.strip():
                        spec_id_part = "".join(c for c in new_spec_name_text.strip().lower().replace(" ", "_") if c.isalnum() or c == '_')
                        if not spec_id_part: st.warning("Specialization name is invalid.", icon="⚠️")
                        else:
                            new_full_spec_id = f"{base_skill_id}_{spec_id_part}"
                            if new_full_spec_id not in current_skills_state:
                                updated_skills_for_add = dict(current_skills_state); updated_skills_for_add[new_full_spec_id] = 0; update_char_value(['skills'], updated_skills_for_add); st_obj.rerun()
                            else: st.warning(f"Specialization '{new_spec_name_text}' already exists.", icon="⚠️")
            st_obj.markdown("---")
        col_idx += 1
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Skill Rank"); display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Skill Bonus")

# --- Advantages Section ---
def render_advantages_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], advantage_editor_config_ref: Dict[str, Any]):
    st_obj.header("Advantages"); adv_rules_list: List[Dict] = rule_data.get('advantages_v1', [])
    if not advantage_editor_config_ref.get("show_form"): _initialize_editor_config(advantage_editor_config_ref, DEFAULT_ADVANTAGE_EDITOR_CONFIG)
    with st_obj.expander("💡 Understanding Advantages", expanded=False): st_obj.markdown(rule_data.get("help_text",{}).get("advantages_help",""))
    current_advantages: List[AdvantageDefinition] = char_state.get('advantages', []); total_adv_cost = engine.calculate_advantage_cost(current_advantages)
    st_obj.subheader(f"Total Advantage Cost: {total_adv_cost} PP"); st_obj.markdown("**Your Advantages:**")
    if not current_advantages: st_obj.caption("No advantages selected.") # caption might be ok
    for i, adv_entry in enumerate(current_advantages):
        adv_rule = next((r for r in adv_rules_list if r['id'] == adv_entry.get('id')), None)
        if not adv_rule: st_obj.error(f"Rule for adv ID: {adv_entry.get('id')} not found"); continue
        adv_name = adv_rule.get('name', adv_entry.get('id')); adv_rank_display = f" (Rk {adv_entry.get('rank', 1)})" if adv_rule.get('ranked') else ""
        params_display_str = engine._format_advantage_params_for_display(adv_entry, adv_rule, rule_data) # Use engine helper
        params_display = f" [{params_display_str}]" if params_display_str else ""
        instance_id = adv_entry.get("instance_id", generate_id_func(f"adv_{adv_entry['id']}_{i}")); adv_entry["instance_id"] = instance_id
        cols_adv_disp = st_obj.columns([0.6, 0.2, 0.2]); cols_adv_disp[0].markdown(f"**{adv_name}**{adv_rank_display}{params_display}", unsafe_allow_html=True)
        if cols_adv_disp[1].button("✏️ Edit", key=_uk("edit_adv_btn", instance_id)):
            _initialize_editor_config(advantage_editor_config_ref, DEFAULT_ADVANTAGE_EDITOR_CONFIG); advantage_editor_config_ref.update({"show_form":True, "mode":"edit", "advantage_id_rule":adv_entry['id'], "instance_id":instance_id, "current_rank":adv_entry.get('rank',1), "current_params":copy.deepcopy(adv_entry.get('params',{})), "selected_adv_rule":copy.deepcopy(adv_rule)}); st.rerun()
        if cols_adv_disp[2].button("🗑️ Del", key=_uk("remove_adv_btn", instance_id)):
            new_adv_list = [adv for adv in current_advantages if adv.get("instance_id") != instance_id]; update_char_value(['advantages'], new_adv_list); st.rerun(); return
        st_obj.markdown("---")
    st_obj.markdown("---")
    if st_obj.button("➕ Add New Advantage", key=_uk("add_new_adv_btn_main")):
        _initialize_editor_config(advantage_editor_config_ref, DEFAULT_ADVANTAGE_EDITOR_CONFIG); advantage_editor_config_ref["show_form"]=True; advantage_editor_config_ref["mode"]="add"
        if adv_rules_list: advantage_editor_config_ref["advantage_id_rule"]=adv_rules_list[0]['id']; advantage_editor_config_ref["selected_adv_rule"]=copy.deepcopy(adv_rules_list[0])
        else: advantage_editor_config_ref["show_form"]=False; st.warning("No advantage rules loaded.")
        st.rerun()
    if advantage_editor_config_ref.get("show_form"):
        st_obj.info("Advantage Add/Edit Form placeholder - Full form logic from previous step applies here.", icon="🚧")
        if st_obj.button("Close Adv Form (Dev)", key=_uk("close_adv_form_dev")): advantage_editor_config_ref["show_form"] = False; st.rerun()

    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Advantage")

# --- Powers Section ---
def render_powers_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], power_form_state_ref: Dict[str,Any]):
    st_obj.header("Powers")
    with st_obj.expander("⚡ Understanding Powers (Advanced)", expanded=False): st_obj.markdown(rule_data.get("help_text",{}).get("powers_adv_help",""))
    if 'show_power_builder_form' not in st.session_state: st.session_state.show_power_builder_form = False
    st_obj.markdown("**Current Powers:**"); current_powers_list: List[PowerDefinition] = char_state.get('powers', [])
    if not current_powers_list: st_obj.caption("No powers defined yet.") # caption might be ok
    for i, pwr_entry in enumerate(current_powers_list):
        pwr_id = pwr_entry.get('id', generate_id_func(f"pwr_unk_{i}_")); pwr_entry["id"] = pwr_id
        pwr_name=pwr_entry.get('name','Unnamed Power'); pwr_rank=pwr_entry.get('rank',0); pwr_cost=pwr_entry.get('cost',0)
        base_eff_rule=next((eff for eff in rule_data.get('power_effects',[]) if eff['id']==pwr_entry.get('baseEffectId')),None); base_eff_name=base_eff_rule.get('name','Unk Eff') if base_eff_rule else 'N/A'
        cols_pwr_disp=st_obj.columns([0.5,0.1,0.1,0.15,0.15]); cols_pwr_disp[0].markdown(f"**{pwr_name}** <small>({base_eff_name})</small>",unsafe_allow_html=True); cols_pwr_disp[1].markdown(f"*R: {pwr_rank}*"); cols_pwr_disp[2].markdown(f"*C: {pwr_cost} PP*")
        if cols_pwr_disp[3].button("✏️ Edit", key=_uk("edit_pwr_btn",pwr_id), help="Edit Power"):
            try:
                from .power_builder_ui import get_default_power_form_state; default_for_missing=get_default_power_form_state(rule_data)
                power_form_state_ref.clear(); power_form_state_ref.update(copy.deepcopy(default_for_missing)); power_form_state_ref.update(copy.deepcopy(pwr_entry)); power_form_state_ref['editing_power_id']=pwr_id
                st.session_state.show_power_builder_form=True; st.rerun()
            except ImportError: st.error("Power Builder UI module error.", icon="🚨")
            except Exception as e_load_pbf: st.error(f"Error preparing power editor: {e_load_pbf}", icon="🚨")
        if cols_pwr_disp[4].button("🗑️ Del", key=_uk("remove_pwr_btn",pwr_id), help="Remove Power"):
            new_p_list=[p for p in current_powers_list if p.get('id')!=pwr_id]; update_char_value(['powers'],new_p_list); st.rerun(); return
        details_p=[];
        if pwr_entry.get('final_range'): details_p.append(f"Range: {pwr_entry['final_range']}")
        if pwr_entry.get('final_duration'): details_p.append(f"Dur: {pwr_entry['final_duration']}")
        if pwr_entry.get('final_action'): details_p.append(f"Act: {pwr_entry['final_action']}")
        if details_p: st_obj.caption(", ".join(details_p), key=_uk("pwr_details_disp", pwr_id)) # caption might be ok
        st_obj.markdown("---")
    st_obj.markdown("---")
    if st_obj.button("➕ Add New Power", key=_uk("add_new_pwr_btn_main")):
        try:
            from .power_builder_ui import get_default_power_form_state; default_p_state=get_default_power_form_state(rule_data)
            power_form_state_ref.clear(); power_form_state_ref.update(default_p_state); power_form_state_ref['editing_power_id']=None
        except ImportError: st.error("Power builder default function error."); first_eff_id = rule_data.get('power_effects',[{}])[0].get('id') if rule_data.get('power_effects') else "eff_damage"; power_form_state_ref.clear(); power_form_state_ref.update({'editing_power_id':None,'name':'New Power','rank':1,'modifiersConfig':[],'sensesConfig':[],'immunityConfig':[],'variableConfigurations':[],'baseEffectId':first_eff_id,'ui_state':{}})
        st.session_state.show_power_builder_form=True; st.rerun()
    if st.session_state.get('show_power_builder_form',False):
        st_obj.markdown("### Power Editor")
        try: from .power_builder_ui import render_power_builder_form; render_power_builder_form(st_obj,char_state,rule_data,engine,update_char_value,power_form_state_ref,generate_id_func)
        except ImportError: st_obj.error("Power builder UI failed to import.");
        except Exception as e_pb_render: st_obj.error(f"Error rendering power builder: {e_pb_render}")
        if st_obj.button("Close Editor (if stuck)", key=_uk("close_pb_manual_btn")): st.session_state.show_power_builder_form=False; st.rerun()
    display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Power")

# --- Equipment Section ---
def render_equipment_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], equipment_editor_config_ref: Dict[str, Any]):
    st_obj.header("Equipment");
    if not equipment_editor_config_ref.get("show_form"): _initialize_editor_config(equipment_editor_config_ref, DEFAULT_EQUIPMENT_EDITOR_CONFIG)
    eq_rules_list: List[Dict] = rule_data.get('equipment_items', [])
    with st_obj.expander("ℹ️ Understanding Equipment", expanded=False): st_obj.markdown("Equipment is bought with Equipment Points (EP). 1 PP = 5 EP.")
    total_ep=char_state.get('derived_total_ep',0); spent_ep=char_state.get('derived_spent_ep',0); st_obj.subheader(f"EP: {spent_ep}/{total_ep}")
    if spent_ep > total_ep: st_obj.error(f"EP Overspent! Used {spent_ep}, Available {total_ep}.", icon="⚠️")
    st_obj.markdown("**Current Gear & Items:**"); current_eq_list: List[EquipmentDefinition] = char_state.get('equipment', [])
    if not current_eq_list: st_obj.caption("No equipment items.") # caption might be ok
    for i, item_entry in enumerate(current_eq_list):
        item_id_rule = item_entry.get('id',"custom"); item_name=item_entry.get('name','Item'); item_cost=item_entry.get('ep_cost',0); item_desc=item_entry.get('description',item_entry.get('effects_text',''))
        instance_id = item_entry.get("instance_id",generate_id_func(f"eq_{item_id_rule}_{i}_")); item_entry["instance_id"]=instance_id
        cols_item_disp=st_obj.columns([0.55,0.15,0.15,0.15]); cols_item_disp[0].markdown(f"**{item_name}**"); cols_item_disp[1].markdown(f"*{item_cost} EP*");
        if item_desc: cols_item_disp[0].caption(item_desc,key=_uk("eq_disp_desc",instance_id)) # caption might be ok
        if cols_item_disp[2].button("✏️ Edit",key=_uk("edit_eq_btn",instance_id)):
            _initialize_editor_config(equipment_editor_config_ref,DEFAULT_EQUIPMENT_EDITOR_CONFIG); equipment_editor_config_ref.update({"show_form":True,"mode":"edit","item_instance_id":instance_id,"is_custom":item_entry.get("is_custom_item",item_id_rule.startswith("custom_")),"selected_item_rule_id":item_id_rule if not item_entry.get("is_custom_item") else None,"selected_item_rule":next((r for r in eq_rules_list if r['id']==item_id_rule),None) if not item_entry.get("is_custom_item") else None,"current_name":item_name,"current_ep_cost":item_cost,"current_description":item_desc,"current_params":copy.deepcopy(item_entry.get("params",{}))}); st.rerun()
        if cols_item_disp[3].button("🗑️ Del",key=_uk("remove_eq_btn",instance_id)):
            new_eq_list=[eq for eq in current_eq_list if eq.get("instance_id")!=instance_id]; update_char_value(['equipment'],new_eq_list); st.rerun(); return
        st_obj.markdown("---")
    st_obj.markdown("---")
    if st_obj.button("➕ Add Equipment Item",key=_uk("add_new_eq_btn_main")):
        _initialize_editor_config(equipment_editor_config_ref,DEFAULT_EQUIPMENT_EDITOR_CONFIG); equipment_editor_config_ref["show_form"]=True; equipment_editor_config_ref["mode"]="add"
        if eq_rules_list: equipment_editor_config_ref["selected_item_rule_id"]=eq_rules_list[0]['id']; equipment_editor_config_ref["selected_item_rule"]=eq_rules_list[0]
        st.rerun()
    if equipment_editor_config_ref.get("show_form"):
        st_obj.info("Equipment Add/Edit Form placeholder - Full form logic from previous step applies here.", icon="🚧")
        if st_obj.button("Close Equip Form (Dev)", key=_uk("close_eq_form_dev")): equipment_editor_config_ref["show_form"] = False; st.rerun()
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Equipment Point")

# --- HQ Builder Section ---
def render_hq_builder_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], hq_form_state_ref: Dict[str,Any]):
    st_obj.header("Headquarters")
    if not hq_form_state_ref.get("show_form"): _initialize_editor_config(hq_form_state_ref, DEFAULT_HQ_EDITOR_CONFIG)
    hq_features_rules:List[Dict] = rule_data.get('hq_features',[])
    if (hq_form_state_ref.get("show_form") or not hq_form_state_ref.get("current_size_id")) and hq_features_rules:
        current_size = hq_form_state_ref.get("current_size_id")
        if not current_size: default_size=next((f['id'] for f in hq_features_rules if f.get('type')=='Size' and "medium" in f.get('name','').lower()), next((f['id'] for f in hq_features_rules if f.get('type')=='Size'),None)); hq_form_state_ref["current_size_id"] = default_size if default_size else None
    with st_obj.expander("ℹ️ Understanding HQs",expanded=False):st_obj.markdown("HQs are bases bought with EP. Size, Toughness, Features.")
    total_ep=char_state.get('derived_total_ep',0); spent_ep_hqs=sum(engine.calculate_hq_cost(hq,hq_features_rules) for hq in char_state.get('headquarters',[])); st_obj.subheader(f"EP on HQs: {spent_ep_hqs} (Total EP: {char_state.get('derived_spent_ep',0)}/{total_ep})")
    st_obj.markdown("**Current HQs:**"); current_hqs:List[HQDefinition] = char_state.get('headquarters',[])
    if not current_hqs: st_obj.caption("No HQs yet.") # caption might be ok
    for i, hq_entry in enumerate(current_hqs):
        hq_instance_id=hq_entry.get('hq_instance_id',generate_id_func(f"hq_{i}_")); hq_entry["hq_instance_id"]=hq_instance_id
        hq_name=hq_entry.get('name','HQ'); hq_cost=engine.calculate_hq_cost(hq_entry,hq_features_rules)
        cols_hq_disp=st_obj.columns([0.55,0.15,0.15,0.15]); cols_hq_disp[0].markdown(f"**{hq_name}**"); cols_hq_disp[1].markdown(f"*{hq_cost} EP*")
        if cols_hq_disp[2].button("✏️ Edit",key=_uk("edit_hq",hq_instance_id)):
            _initialize_editor_config(hq_form_state_ref,DEFAULT_HQ_EDITOR_CONFIG); hq_form_state_ref.update({"show_form":True,"mode":"edit","hq_instance_id":hq_instance_id,"current_name":hq_entry.get("name"),"current_size_id":hq_entry.get("size_id"),"current_bought_toughness":hq_entry.get("bought_toughness_ranks",0),"current_features":copy.deepcopy(hq_entry.get("features",[])),"selected_hq_size_rule":next((s for s in hq_features_rules if s['id']==hq_entry.get("size_id")),None)}); st.rerun()
        if cols_hq_disp[3].button("🗑️ Del",key=_uk("del_hq",hq_instance_id)):
            new_list=[hq for hq in current_hqs if hq.get("hq_instance_id")!=hq_instance_id];update_char_value(['headquarters'],new_list);st.rerun();return
        st_obj.markdown("---")
    st_obj.markdown("---")
    if st_obj.button("➕ Add HQ",key=_uk("add_hq_main")):
        _initialize_editor_config(hq_form_state_ref,DEFAULT_HQ_EDITOR_CONFIG);hq_form_state_ref["show_form"]=True;hq_form_state_ref["mode"]="add"
        if not hq_form_state_ref.get("current_size_id") and hq_features_rules: default_size=next((f['id'] for f in hq_features_rules if f.get('type')=='Size' and "medium" in f.get('name','').lower()), next((f['id'] for f in hq_features_rules if f.get('type')=='Size'),None)); hq_form_state_ref["current_size_id"] = default_size if default_size else None
        st.rerun()
    if hq_form_state_ref.get("show_form"): # Full HQ Form
        hq_conf = hq_form_state_ref; title="Add HQ" if hq_conf['mode']=='add' else f"Edit: {hq_conf.get('current_name','HQ')}"; st_obj.subheader(title)
        with st_obj.form(key=_uk("hq_form",hq_conf['mode'],hq_conf.get('hq_instance_id','new')),clear_on_submit=False):
            hq_conf["current_name"]=st.text_input("Name:",value=hq_conf.get('current_name',"HQ"),key=_uk("hq_f_name",hq_conf.get('hq_instance_id','new')))
            size_opts={f['id']:f['name'] for f in hq_features_rules if f.get('type')=='Size'}; cur_size_id=hq_conf.get("current_size_id");
            if cur_size_id not in size_opts and size_opts: cur_size_id = list(size_opts.keys())[0]; hq_conf["current_size_id"] = cur_size_id
            sel_idx_hq_size = list(size_opts.keys()).index(cur_size_id) if cur_size_id in size_opts else 0
            sel_size_id_form=st.selectbox("Size:",options=list(size_opts.keys()),format_func=lambda x_id:size_opts.get(x_id,"Size..."),index=sel_idx_hq_size,key=_uk("hq_f_size",hq_conf.get('hq_instance_id','new')))
            if sel_size_id_form!=cur_size_id: hq_conf["current_size_id"]=sel_size_id_form; hq_conf["selected_hq_size_rule"]=next((s for s in hq_features_rules if s['id']==sel_size_id_form),None); st.rerun()
            sel_size_rule_form=hq_conf.get("selected_hq_size_rule");
            if not sel_size_rule_form and hq_conf.get("current_size_id"): sel_size_rule_form=next((s for s in hq_features_rules if s['id']==hq_conf["current_size_id"]),None); hq_conf["selected_hq_size_rule"]=sel_size_rule_form
            if sel_size_rule_form: st.caption(f"Base Tough: {sel_size_rule_form.get('base_toughness_provided',0)}, Base EP: {sel_size_rule_form.get('ep_cost',0)}",key=_uk("hq_size_caption",hq_conf.get('hq_instance_id','new'))) # caption might be ok
            hq_conf["current_bought_toughness"]=st.number_input("Add. Tough Ranks (1 EP/rank):",min_value=0,value=hq_conf.get('current_bought_toughness',0),step=1,key=_uk("hq_f_tough",hq_conf.get('hq_instance_id','new')))
            st_obj.markdown("**Features:**"); temp_feats_list=list(hq_conf.get("current_features",[])); feats_to_keep_form=[]
            for idx_f, feat_e in enumerate(temp_feats_list):
                f_rule=next((fr for fr in hq_features_rules if fr['id']==feat_e['id']),None); f_name=f_rule['name'] if f_rule else feat_e['id']; f_rank_d=f" (Rk {feat_e.get('rank',1)})" if f_rule and f_rule.get('ranked') else ""
                f_cols_form=st_obj.columns([0.8,0.2]); f_cols_form[0].markdown(f"- {f_name}{f_rank_d}")
                if f_cols_form[1].button("➖",key=_uk("hq_f_rem_f",feat_e.get('instance_id',idx_f)),help=f"Remove {f_name}"): pass
                else: feats_to_keep_form.append(feat_e)
            if len(feats_to_keep_form)!=len(temp_feats_list): hq_conf["current_features"]=feats_to_keep_form; st.rerun()
            st_obj.markdown("*Add Feature:*"); feat_opts_hq={"":"Select..."}; feat_opts_hq.update({f['id']:f"{f['name']} ({f.get('ep_cost',str(f.get('ep_cost_per_rank','?'))+'/r')} EP)" for f in hq_features_rules if f.get('type')=='Feature'})
            sel_f_add_id_hq=st.selectbox("Feature:",options=list(feat_opts_hq.keys()),format_func=lambda x_id:feat_opts_hq.get(x_id,"Choose..."),key=_uk("hq_f_sel_f_add",hq_conf.get('hq_instance_id','new')))
            add_f_rank_hq=1; add_f_param_hq=""; sel_f_rule_add_hq=next((f for f in hq_features_rules if f['id']==sel_f_add_id_hq),None)
            if sel_f_rule_add_hq:
                if sel_f_rule_add_hq.get('ranked'):add_f_rank_hq=st.number_input("Rank:",min_value=1,max_value=sel_f_rule_add_hq.get('max_ranks',20),value=1,key=_uk("hq_f_add_f_rank",hq_conf.get('hq_instance_id','new')))
                if sel_f_rule_add_hq.get('parameter_needed'):add_f_param_hq=st.text_input(sel_f_rule_add_hq.get('parameter_prompt','Detail:'),key=_uk("hq_f_add_f_param",hq_conf.get('hq_instance_id','new')))
            if st.button("➕ Add Feature",key=_uk("hq_f_add_f_btn",hq_conf.get('hq_instance_id','new'))):
                if sel_f_add_id_hq and sel_f_rule_add_hq:
                    new_f_e_hq={"id":sel_f_add_id_hq,"rank":add_f_rank_hq,"instance_id":generate_id_func(f"hqfeat_{sel_f_add_id_hq}_")}
                    if sel_f_rule_add_hq.get('parameter_needed') and add_f_param_hq: new_f_e_hq['params']={'detail':add_f_param_hq}
                    cur_form_f_hq=hq_conf.get("current_features",[]);cur_form_f_hq.append(new_f_e_hq);hq_conf["current_features"]=cur_form_f_hq; st.rerun()
            sub_col_hq_f,can_col_hq_f=st.columns(2)
            with sub_col_hq_f:
                if st.form_submit_button("💾 Save HQ",type="primary",use_container_width=True):
                    if not hq_conf.get("current_name","").strip() or not hq_conf.get("current_size_id"): st.error("HQ Name & Size required."); return
                    hq_data_save:HQDefinition={"hq_instance_id":hq_conf.get("hq_instance_id") or generate_id_func("hq_"),"name":hq_conf["current_name"],"size_id":hq_conf["current_size_id"],"bought_toughness_ranks":hq_conf["current_bought_toughness"],"features":copy.deepcopy(hq_conf.get("current_features",[]))}
                    all_hqs_save=list(char_state.get('headquarters',[]))
                    if hq_conf["mode"]=="edit":
                        edited_hq=False;
                        for idx_hq_s,hq_s_item in enumerate(all_hqs_save):
                            if hq_s_item.get("hq_instance_id")==hq_data_save["hq_instance_id"]:all_hqs_save[idx_hq_s]=hq_data_save;edited_hq=True;break
                        if not edited_hq: all_hqs_save.append(hq_data_save)
                    else: all_hqs_save.append(hq_data_save)
                    update_char_value(['headquarters'],all_hqs_save);_initialize_editor_config(hq_form_state_ref,DEFAULT_HQ_EDITOR_CONFIG);st.rerun()
            with can_col_hq_f:
                if st.form_submit_button("❌ Cancel",use_container_width=True):_initialize_editor_config(hq_form_state_ref,DEFAULT_HQ_EDITOR_CONFIG);st.rerun()
    display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Headquarters")


# --- Vehicle Builder Section ---
def render_vehicle_builder_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], vehicle_form_state_ref: Dict[str,Any]):
    st_obj.header("Vehicles")
    if not vehicle_form_state_ref.get("show_form"): _initialize_editor_config(vehicle_form_state_ref, DEFAULT_VEHICLE_EDITOR_CONFIG)
    vh_feat_rules:List[Dict]=rule_data.get('vehicle_features',[]); vh_size_rules:List[Dict]=rule_data.get('vehicle_size_stats',[])
    with st_obj.expander("ℹ️ Understanding Vehicles",expanded=False):st_obj.markdown("Vehicles bought with EP. Base stats from Size Rank. Features add capabilities & cost.")
    total_ep_vh=char_state.get('derived_total_ep',0); spent_ep_vh=sum(engine.calculate_vehicle_cost(vh,vh_feat_rules,vh_size_rules) for vh in char_state.get('vehicles',[])); st_obj.subheader(f"EP on Vehicles: {spent_ep_vh} (Total EP: {char_state.get('derived_spent_ep',0)}/{total_ep_vh})")
    st_obj.markdown("**Current Vehicles:**"); current_vh_list:List[VehicleDefinition]=char_state.get('vehicles',[])
    if not current_vh_list: st_obj.caption("No vehicles yet.") # caption might be ok
    for i_vh, vh_e in enumerate(current_vh_list):
        vh_inst_id=vh_e.get('vehicle_instance_id',generate_id_func(f"vh_{i_vh}_")); vh_e["vehicle_instance_id"]=vh_inst_id
        vh_n=vh_e.get('name','Vehicle'); vh_c=engine.calculate_vehicle_cost(vh_e,vh_feat_rules,vh_size_rules)
        cols_vh_d=st_obj.columns([0.55,0.15,0.15,0.15]); cols_vh_d[0].markdown(f"**{vh_n}**"); cols_vh_d[1].markdown(f"*{vh_c} EP*")
        if cols_vh_d[2].button("✏️ Edit",key=_uk("edit_vh",vh_inst_id)):
            _initialize_editor_config(vehicle_form_state_ref,DEFAULT_VEHICLE_EDITOR_CONFIG); vehicle_form_state_ref.update({"show_form":True,"mode":"edit","vehicle_instance_id":vh_inst_id,"current_name":vh_e.get("name"),"current_size_rank":vh_e.get("size_rank",0),"current_features":copy.deepcopy(vh_e.get("features",[]))}); st.rerun()
        if cols_vh_d[3].button("🗑️ Del",key=_uk("del_vh",vh_inst_id)):
            new_list_vh=[vh for vh in current_vh_list if vh.get("vehicle_instance_id")!=vh_inst_id]; update_char_value(['vehicles'],new_list_vh);st.rerun();return
        st_obj.markdown("---")
    st_obj.markdown("---")
    if st_obj.button("➕ Add Vehicle",key=_uk("add_vh_main")): _initialize_editor_config(vehicle_form_state_ref,DEFAULT_VEHICLE_EDITOR_CONFIG);vehicle_form_state_ref["show_form"]=True;vehicle_form_state_ref["mode"]="add";st.rerun()
    if vehicle_form_state_ref.get("show_form"): # Full Vehicle Form (similar to HQ form)
        vh_conf=vehicle_form_state_ref; title_vh="Add Vehicle" if vh_conf['mode']=='add' else f"Edit: {vh_conf.get('current_name','Vehicle')}"; st_obj.subheader(title_vh)
        with st_obj.form(key=_uk("vh_form",vh_conf['mode'],vh_conf.get('vehicle_instance_id','new')),clear_on_submit=False):
            vh_conf["current_name"]=st.text_input("Name:",value=vh_conf.get('current_name',"Vehicle"),key=_uk("vh_f_n",vh_conf.get('vehicle_instance_id','new')))
            size_rank_opts={s['size_rank_value']:f"{s['size_name']} (Rank {s['size_rank_value']})" for s in vh_size_rules}; cur_size_r=vh_conf.get("current_size_rank",0); valid_s_ranks=list(size_rank_opts.keys()); sel_idx_vh_size=valid_s_ranks.index(cur_size_r) if cur_size_r in valid_s_ranks else 0
            sel_size_r_form=st.selectbox("Size Rank:",options=valid_s_ranks,format_func=lambda x_r:size_rank_opts.get(x_r,"Size Rank..."),index=sel_idx_vh_size,key=_uk("vh_f_size_r",vh_conf.get('vehicle_instance_id','new')))
            if sel_size_r_form!=cur_size_r: vh_conf["current_size_rank"]=sel_size_r_form; st.rerun()
            size_stat_r_form=next((s for s in vh_size_rules if s['size_rank_value']==vh_conf["current_size_rank"]),None)
            if size_stat_r_form: vh_conf["derived_base_stats"]=size_stat_r_form; st.caption(f"Base: Str {size_stat_r_form['base_str']}, Spd {size_stat_r_form['base_spd']}, Def {size_stat_r_form['base_def']}, Tou {size_stat_r_form['base_tou']}. EP: {size_stat_r_form['base_ep_cost']}",key=_uk("vh_size_r_cap",vh_conf.get('vehicle_instance_id','new'))) # caption might be ok
            st_obj.markdown("**Features:**"); temp_vh_f_list=list(vh_conf.get("current_features",[])); vh_f_to_keep=[]
            for idx_vhf, feat_e_vhf in enumerate(temp_vh_f_list):
                f_r_vhf=next((fr_vhf for fr_vhf in vh_feat_rules if fr_vhf['id']==feat_e_vhf['id']),None); f_n_vhf=f_r_vhf['name'] if f_r_vhf else feat_e_vhf['id']; f_rk_d_vhf=f" (Rk {feat_e_vhf.get('rank',1)})" if f_r_vhf and f_r_vhf.get('ranked') else ""
                f_cols_vhf=st_obj.columns([0.8,0.2]); f_cols_vhf[0].markdown(f"- {f_n_vhf}{f_rk_d_vhf}")
                if f_cols_vhf[1].button("➖",key=_uk("vh_f_rem_f",feat_e_vhf.get('instance_id',idx_vhf)),help=f"Remove {f_n_vhf}"):pass
                else: vh_f_to_keep.append(feat_e_vhf)
            if len(vh_f_to_keep)!=len(temp_vh_f_list): vh_conf["current_features"]=vh_f_to_keep;st.rerun()
            st_obj.markdown("*Add Feature:*"); vhf_opts={"":"Select..."}; vhf_opts.update({f['id']:f"{f['name']} ({f.get('ep_cost',str(f.get('ep_cost_per_rank','?'))+'/r')} EP)" for f in vh_feat_rules})
            sel_vhf_add_id=st.selectbox("Feature:",options=list(vhf_opts.keys()),format_func=lambda x_id:vhf_opts.get(x_id,"Choose..."),key=_uk("vh_f_sel_f_add",vh_conf.get('vehicle_instance_id','new')))
            add_vhf_rank=1;add_vhf_param="";sel_vhf_rule_add=next((f for f in vh_feat_rules if f['id']==sel_vhf_add_id),None)
            if sel_vhf_rule_add:
                if sel_vhf_rule_add.get('ranked'):add_vhf_rank=st.number_input("Rank:",min_value=1,max_value=sel_vhf_rule_add.get('max_ranks',20),value=1,key=_uk("vh_f_add_f_rank",vh_conf.get('vehicle_instance_id','new')))
                if sel_vhf_rule_add.get('parameter_needed'):add_vhf_param=st.text_input(sel_vhf_rule_add.get('parameter_prompt','Detail:'),key=_uk("vh_f_add_f_param",vh_conf.get('vehicle_instance_id','new')))
            if st.button("➕ Add Feature",key=_uk("vh_f_add_f_btn",vh_conf.get('vehicle_instance_id','new'))):
                if sel_vhf_add_id and sel_vhf_rule_add:
                    new_vhf_e={"id":sel_vhf_add_id,"rank":add_vhf_rank,"instance_id":generate_id_func(f"vhfeat_{sel_vhf_add_id}_")}
                    if sel_vhf_rule_add.get('parameter_needed') and add_vhf_param: new_vhf_e['params']={'detail':add_vhf_param}
                    cur_form_vhf=vh_conf.get("current_features",[]);cur_form_vhf.append(new_vhf_e);vh_conf["current_features"]=cur_form_vhf;st.rerun()
            sub_col_vhf,can_col_vhf=st.columns(2)
            with sub_col_vhf:
                if st.form_submit_button("💾 Save Vehicle",type="primary",use_container_width=True):
                    if not vh_conf.get("current_name","").strip(): st.error("Vehicle Name required."); return
                    vh_data_save:VehicleDefinition={"vehicle_instance_id":vh_conf.get("vehicle_instance_id")or generate_id_func("vh_"),"name":vh_conf["current_name"],"size_rank":vh_conf["current_size_rank"],"features":copy.deepcopy(vh_conf.get("current_features",[]))}
                    all_vh_save=list(char_state.get('vehicles',[]))
                    if vh_conf["mode"]=="edit":
                        edited_vh=False;
                        for idx_vh_s,vh_s_item in enumerate(all_vh_save):
                            if vh_s_item.get("vehicle_instance_id")==vh_data_save["vehicle_instance_id"]:all_vh_save[idx_vh_s]=vh_data_save;edited_vh=True;break
                        if not edited_vh: all_vh_save.append(vh_data_save)
                    else: all_vh_save.append(vh_data_save)
                    update_char_value(['vehicles'],all_vh_save);_initialize_editor_config(vehicle_form_state_ref,DEFAULT_VEHICLE_EDITOR_CONFIG);st.rerun()
            with can_col_vhf:
                if st.form_submit_button("❌ Cancel",use_container_width=True):_initialize_editor_config(vehicle_form_state_ref,DEFAULT_VEHICLE_EDITOR_CONFIG);st.rerun()
    display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Vehicle")


# --- Allies Section ---
def render_allies_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], ally_editor_config_ref: Dict[str, Any]):
    st_obj.header("Companions (Allies)")
    if not ally_editor_config_ref.get("show_form"):_initialize_editor_config(ally_editor_config_ref,DEFAULT_ALLY_EDITOR_CONFIG);ally_editor_config_ref.setdefault("current_structured_abilities",{});ally_editor_config_ref.setdefault("current_structured_defenses",{})
    with st_obj.expander("ℹ️ Understanding Companions",expanded=False):st_obj.markdown("Minions/Sidekicks from Advantages (PP pools), Summon/Duplication from Powers.")
    min_pool_t=char_state.get('derived_total_minion_pool_pp',0);min_pool_s=char_state.get('derived_spent_minion_pool_pp',0);side_pool_t=char_state.get('derived_total_sidekick_pool_pp',0);side_pool_s=char_state.get('derived_spent_sidekick_pool_pp',0)
    col_m,col_s=st_obj.columns(2)
    with col_m:
        if min_pool_t>0 or min_pool_s>0: st_obj.metric(label="Minion Pool PP",value=f"{min_pool_s}/{min_pool_t}",delta=f"{min_pool_t-min_pool_s} Rem.",delta_color="normal" if min_pool_s<=min_pool_t else "inverse",key=_uk("min_pool_met"))
    with col_s:
        if side_pool_t>0 or side_pool_s>0: st_obj.metric(label="Sidekick Pool PP",value=f"{side_pool_s}/{side_pool_t}",delta=f"{side_pool_t-side_pool_s} Rem.",delta_color="normal" if side_pool_s<=side_pool_t else "inverse",key=_uk("side_pool_met"))
    st_obj.markdown("**Defined Minions & Sidekicks (Advantages):**");cur_adv_allies:List[AllyDefinition]=[a for a in char_state.get('allies',[]) if a.get('source_type')=='advantage_pool']
    if not cur_adv_allies:st_obj.caption("No Minions/Sidekicks from Advantages.") # caption might be ok
    for i_a,ally_e in enumerate(cur_adv_allies):
        ally_inst_id_a=ally_e.get('ally_instance_id',generate_id_func(f"ally_adv_{i_a}_"));ally_e["ally_instance_id"]=ally_inst_id_a
        ally_n_a=ally_e.get('name','Ally');ally_t_a=ally_e.get('type','Minion');ally_c_a=ally_e.get('cost_pp_asserted_by_user',0)
        cols_ally_d_a=st_obj.columns([0.5,0.15,0.1,0.1,0.15]);cols_ally_d_a[0].markdown(f"**{ally_n_a}** ({ally_t_a})");cols_ally_d_a[1].markdown(f"*PL {ally_e.get('pl_for_ally','N/A')}*");cols_ally_d_a[2].markdown(f"*{ally_c_a} PP*")
        if cols_ally_d_a[3].button("✏️ Edit",key=_uk("edit_ally_btn",ally_inst_id_a)):
            _initialize_editor_config(ally_editor_config_ref,DEFAULT_ALLY_EDITOR_CONFIG);ally_editor_config_ref.update({"show_form":True,"mode":"edit","ally_instance_id":ally_inst_id_a})
            for k_f,k_e in DEFAULT_ALLY_EDITOR_CONFIG.items():
                if k_f.startswith("current_"): e_k=k_f.replace("current_",""); e_k="pl_for_ally" if e_k=="pl" else "cost_pp_asserted_by_user" if e_k=="asserted_pp_cost" else e_k; ally_editor_config_ref[k_f]=copy.deepcopy(ally_e.get(e_k,DEFAULT_ALLY_EDITOR_CONFIG[k_f]))
            ally_editor_config_ref["current_structured_abilities"]=copy.deepcopy(ally_e.get("structured_abilities",{}));ally_editor_config_ref["current_structured_defenses"]=copy.deepcopy(ally_e.get("structured_defenses",{}))
            st.rerun()
        if cols_ally_d_a[4].button("🗑️ Del",key=_uk("remove_ally_btn",ally_inst_id_a)):
            new_ally_l_a=[ally for ally in char_state.get('allies',[]) if ally.get("ally_instance_id")!=ally_inst_id_a];update_char_value(['allies'],new_ally_l_a);st.rerun();return
        with st_obj.expander(f"Details: {ally_n_a}",expanded=False,key=_uk("ally_exp_d",ally_inst_id_a)):st_obj.json(ally_e)
        st_obj.markdown("---")
    st_obj.markdown("---")
    if st_obj.button("➕ Add Minion/Sidekick",key=_uk("add_new_ally_main")):
        _initialize_editor_config(ally_editor_config_ref,DEFAULT_ALLY_EDITOR_CONFIG);ally_editor_config_ref.update({"show_form":True,"mode":"add","current_structured_abilities":{},"current_structured_defenses":{}});st.rerun()
    if ally_editor_config_ref.get("show_form"):
        st_obj.info("Ally Add/Edit Form placeholder - Full form logic (incl. Sidekick stats) from previous step applies here.", icon="🚧")
        if st_obj.button("Close Ally Form (Dev)",key=_uk("close_ally_form_dev")) : ally_editor_config_ref["show_form"]=False; st.rerun()
    st_obj.markdown("---");st_obj.markdown("**Summoned/Duplicated Allies (Powers):**");pwr_allies_disp=[]
    for pwr_s_a in char_state.get('powers',[]):
        if pwr_s_a.get('baseEffectId') in ['eff_summon','eff_duplication'] and pwr_s_a.get('ally_notes_and_stats_structured'):
            ally_sb_s=pwr_s_a.get('ally_notes_and_stats_structured');pwr_allies_disp.append({"name":ally_sb_s.get('name','Creation'),"source_power_name":pwr_s_a.get('name','Power'),"pl":ally_sb_s.get('pl_for_ally','N/A'),"cost":ally_sb_s.get('cost_pp_asserted_by_user','N/A'),"details":ally_sb_s,"power_id":pwr_s_a.get("id")})
    if not pwr_allies_disp:st_obj.caption("No allies from Summon/Duplication.") # caption might be ok
    for ally_info_s_a in pwr_allies_disp:
        st_obj.markdown(f"**{ally_info_s_a['name']}** (from *{ally_info_s_a['source_power_name']}*) - PL {ally_info_s_a['pl']}, Cost {ally_info_s_a['cost']} PP")
        with st_obj.expander(f"Details: {ally_info_s_a['name']}",expanded=False,key=_uk("ally_sum_exp",ally_info_s_a['power_id'])):st_obj.json(ally_info_s_a['details'])
        st_obj.markdown("---")
    display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Ally");display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Minion Pool");display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Sidekick Pool")

# --- Complications Section ---
def render_complications_section_adv(st_obj: Any, char_state: CharacterState, update_char_value: Callable, generate_id_func: Callable[[str], str]):
    st_obj.header("Complications");complications_help=rule_data.get("help_text",{}).get("complications_help","Complications add depth & earn Hero Points. Min 2 recommended.")
    with st_obj.expander("ℹ️ Understanding Complications",expanded=False):st_obj.markdown(complications_help)
    cur_comp_list=char_state.get('complications',[]);
    if not cur_comp_list:st_obj.info("No complications. Min 2 recommended.")
    proc_comps=[];needs_id_upd=False
    for i_c,comp_e_c in enumerate(cur_comp_list):
        new_e_c=dict(comp_e_c);
        if "instance_id" not in new_e_c:new_e_c["instance_id"]=generate_id_func(f"comp_{i_c}_");needs_id_upd=True
        proc_comps.append(new_e_c)
    if needs_id_upd:update_char_value(['complications'],proc_comps,do_recalc=False);cur_comp_list=proc_comps
    for i_c_disp,comp_e_disp in enumerate(cur_comp_list):
        comp_desc_d=comp_e_disp.get('description','');inst_id_c=comp_e_disp.get("instance_id")
        cols_c=st_obj.columns([0.9,0.1]);key_c_text_edit=_uk("comp_text_e",inst_id_c)
        new_desc_c=cols_c[0].text_area(f"Complication #{i_c_disp+1}",value=comp_desc_d,key=key_c_text_edit,height=75)
        if new_desc_c!=comp_desc_d:
            upd_comps_e=list(cur_comp_list);
            for edit_idx_c,edit_c_item in enumerate(upd_comps_e):
                if edit_c_item.get("instance_id")==inst_id_c:upd_comps_e[edit_idx_c]['description']=new_desc_c;break
            update_char_value(['complications'],upd_comps_e);st.rerun()
        key_c_del_btn=_uk("comp_del_e_btn",inst_id_c)
        if cols_c[1].button("🗑️",key=key_c_del_btn,help="Remove Complication"):
            upd_comps_d=[c for c_d in cur_comp_list if c_d.get("instance_id")!=inst_id_c];update_char_value(['complications'],upd_comps_d);st.rerun();return
        st_obj.markdown("---")
    st_obj.markdown("---");st_obj.subheader("Add New Complication")
    with st_obj.form(key=_uk("add_comp_form_adv"),clear_on_submit=True):
        new_comp_text_adv=st.text_area("New Complication Description:",key=_uk("new_comp_text_adv_area"),height=75)
        sub_add_comp_adv=st.form_submit_button("➕ Add Complication")
        if sub_add_comp_adv:
            if new_comp_text_adv.strip():
                fresh_comp_list_adv=list(char_state.get('complications',[]));new_comp_e_adv={'description':new_comp_text_adv.strip(),'instance_id':generate_id_func("comp_new_")};fresh_comp_list_adv.append(new_comp_e_adv);update_char_value(['complications'],fresh_comp_list_adv);st.rerun()
            else:st.warning("Complication description cannot be empty.",icon="⚠️")
    display_field_validation_errors(st_obj,char_state.get('validationErrors',[]),"Complication")

# --- Measurements Table Section ---
def render_measurements_table_view_adv(st_obj: Any, rule_data: RuleData):
    st_obj.header("Measurements Table Reference")
    with st_obj.expander("ℹ️ Understanding Measurements (DHH p.19)",expanded=False):st_obj.markdown("Table showing rank to real-world conversions.")
    measure_data=rule_data.get('measurements_table',[])
    if measure_data:st_obj.dataframe(measure_data,hide_index=True,use_container_width=True)
    else:st_obj.warning("Measurements table data not found.",icon="⚠️")

# --- Character Sheet View (In-App) ---
def render_character_sheet_view_in_app_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine):
    st_obj.header(f"Sheet Preview: {char_state.get('name','Hero')}")
    if st_obj.button("🔄 Recalculate & Refresh",key=_uk("refresh_sheet_adv")):st.session_state.character=engine.recalculate(char_state);st.rerun()
    try:
        from ..pdf_utils import generate_pdf_html_content as gen_html_func # Assuming pdf_utils still has this
        sheet_html=gen_html_func(char_state,rule_data,engine)
        css_path="assets/pdf_styles.css"
        try:
            with open(css_path,"r",encoding="utf-8") as f: sheet_css=f"<style>{f.read()}</style>"
            st_obj.markdown(sheet_css,unsafe_allow_html=True)
        except FileNotFoundError: st_obj.warning(f"CSS file `{css_path}` not found for preview.",icon="⚠️")
        st_obj.markdown(sheet_html,unsafe_allow_html=True)
    except ImportError: st_obj.error("HTML preview function not found in `pdf_utils`.",icon="🚨")
    except Exception as e_sheet_html: st_obj.error(f"Error generating HTML preview: {e_sheet_html}",icon="🚨")

# --- Main Dispatch Function for Advanced Mode Views ---
def render_selected_advanced_view(
    view_name: str, st_obj: Any, char_state: CharacterState, rule_data: RuleData,
    engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str],
    power_form_state_ref: Dict[str,Any], hq_form_state_ref: Dict[str,Any],
    vehicle_form_state_ref: Dict[str,Any], advantage_editor_config_ref: Dict[str, Any],
    equipment_editor_config_ref: Dict[str, Any], ally_editor_config_ref: Dict[str, Any]
):
    render_map = {
        'Abilities': lambda: render_abilities_section_adv(st_obj, char_state, rule_data, engine, update_char_value),
        'Defenses': lambda: render_defenses_section_adv(st_obj, char_state, rule_data, engine, update_char_value),
        'Skills': lambda: render_skills_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func),
        'Advantages': lambda: render_advantages_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, advantage_editor_config_ref),
        'Powers': lambda: render_powers_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, power_form_state_ref),
        'Equipment': lambda: render_equipment_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, equipment_editor_config_ref),
        'Headquarters': lambda: render_hq_builder_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, hq_form_state_ref),
        'Vehicles': lambda: render_vehicle_builder_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, vehicle_form_state_ref),
        'Companions (Allies)': lambda: render_allies_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, ally_editor_config_ref),
        'Complications': lambda: render_complications_section_adv(st_obj, char_state, update_char_value, generate_id_func),
        'Measurements Table': lambda: render_measurements_table_view_adv(st_obj, rule_data),
        'Character Sheet': lambda: render_character_sheet_view_in_app_adv(st_obj, char_state, rule_data, engine)
    }
    if view_name in render_map:
        try:render_map[view_name]()
        except Exception as e_render_adv:st_obj.error(f"Error rendering section '{view_name}': {e_render_adv}",icon="🚨")
    else: st_obj.error(f"Unknown view: {view_name}",icon="🚨")