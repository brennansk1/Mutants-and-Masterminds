# heroforge-mm-streamlit/ui_sections/advanced_mode_ui.py

import streamlit as st
import copy
import math
from typing import Dict, List, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core_engine import CoreEngine, CharacterState, RuleData, PowerDefinition, AdvantageDefinition, SkillDefinition, AbilityDefinition, EquipmentDefinition, HQDefinition, VehicleDefinition, AllyDefinition # type: ignore
    from ..pdf_utils import generate_pdf_html_content # type: ignore
else:
    CoreEngine = Any
    CharacterState = Dict[str, Any]
    RuleData = Dict[str, Any]
    # Define other types as Dict[str,Any] for runtime if not fully typed in core_engine
    PowerDefinition = Dict[str, Any]
    AdvantageDefinition = Dict[str,Any]


# --- Helper for unique keys in loops ---
def _uk(base: str, *args):
    return f"{base}_{'_'.join(map(str, args))}"

# --- Helper for displaying validation errors for a field ---
def display_field_validation_errors(st_obj: Any, validation_errors: List[str], field_identifier: str):
    field_errors = [err for err in validation_errors if field_identifier.lower() in err.lower()]
    for err in field_errors:
        st_obj.caption(f"⚠️ {err}")


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
        st_obj.markdown(rule_data.get("help_text",{}).get("abilities_help", "Define your hero's 8 core attributes. Rank is also modifier. 0 is average human."))

    ability_rules: List[Dict[str, Any]] = rule_data.get('abilities', [])
    current_abilities = char_state.get('abilities', {})
    cost_factor = engine.rule_data.get('abilities', {}).get('costFactor', 2)

    cols = st_obj.columns(4)
    for i, ab_info in enumerate(ability_rules):
        ab_id = ab_info['id']
        ab_name = ab_info['name']
        ab_desc = ab_info.get('description', '')
        current_rank = current_abilities.get(ab_id, 0)
        
        with cols[i % len(cols)]:
            new_rank = st_obj.number_input(
                f"{ab_name} ({ab_id})", min_value=-5, max_value=30, # Max 30 for cosmic
                value=current_rank, key=_uk("adv_ab_input", ab_id), help=ab_desc,
                step=1
            )
            if new_rank != current_rank:
                update_char_value(['abilities', ab_id], new_rank)
                st_obj.rerun() # Immediate feedback on PP and derived values
            
            cost = new_rank * cost_factor
            mod = engine.get_ability_modifier(new_rank)
            st_obj.caption(f"Mod: {mod:+}, Cost: {cost} PP")
    
    total_ability_cost = engine.calculate_ability_cost(current_abilities)
    st_obj.markdown(f"**Total Ability Cost: {total_ability_cost} PP**")


# --- Defenses Section ---
def render_defenses_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable
):
    st_obj.header("Defenses")
    with st_obj.expander("🛡️ Understanding Defenses (Cost: 1 PP per +1 Bought Rank)", expanded=False):
        st_obj.markdown(rule_data.get("help_text",{}).get("defenses_help","Base from Abilities, buy ranks to increase. PL Caps are crucial!"))

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
    totals_for_cap_check = {}

    for i, d_conf in enumerate(defense_configs):
        with def_cols[i]:
            base_val = engine.get_ability_modifier(current_abilities.get(d_conf['base_ability_id'], 0))
            bought_val = bought_defenses.get(d_conf['id'], 0)
            
            # Note: True total Toughness calculation needs to sum STA_mod + bought_Toughness_ranks + Protection powers + Defensive Roll, etc.
            # For this input section, we focus on BOUGHT ranks. The displayed total should reflect all sources.
            # Let's assume engine.get_total_defense does this.
            total_val_display = engine.get_total_defense(char_state, d_conf['id'], d_conf['base_ability_id'])
            totals_for_cap_check[d_conf['id']] = total_val_display
            
            new_bought_val = st_obj.number_input(
                f"{d_conf['name']}", min_value=0, max_value=pl + 15, # Generous max for bought ranks input
                value=bought_val, key=_uk("adv_def_input", d_conf['id']),
                help=f"{d_conf['tooltip']}\nBase from {d_conf['base_ability_id']}: {base_val}\nCurrent Total (all sources): {total_val_display}"
            )
            if new_bought_val != bought_val:
                update_char_value(['defenses', d_conf['id']], new_bought_val)
                st_obj.rerun()
            st_obj.caption(f"Bought: {new_bought_val} (Cost: {new_bought_val} PP)")
            st_obj.metric(label=f"Total {d_conf['name']}", value=total_val_display)

    st_obj.markdown("---")
    st_obj.subheader("Defense Power Level Caps")
    cap_col1, cap_col2, cap_col3 = st_obj.columns(3)
    dt_sum = totals_for_cap_check.get('Dodge',0) + totals_for_cap_check.get('Toughness',0)
    pt_sum = totals_for_cap_check.get('Parry',0) + totals_for_cap_check.get('Toughness',0)
    fw_sum = totals_for_cap_check.get('Fortitude',0) + totals_for_cap_check.get('Will',0)
    
    with cap_col1: st_obj.metric("Dodge + Toughness", f"{dt_sum} / {pl_cap_paired}", delta="OK" if dt_sum <= pl_cap_paired else "OVER LIMIT!", delta_color="normal" if dt_sum <= pl_cap_paired else "inverse")
    with cap_col2: st_obj.metric("Parry + Toughness", f"{pt_sum} / {pl_cap_paired}", delta="OK" if pt_sum <= pl_cap_paired else "OVER LIMIT!", delta_color="normal" if pt_sum <= pl_cap_paired else "inverse")
    with cap_col3: st_obj.metric("Fortitude + Will", f"{fw_sum} / {pl_cap_paired}", delta="OK" if fw_sum <= pl_cap_paired else "OVER LIMIT!", delta_color="normal" if fw_sum <= pl_cap_paired else "inverse")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Defense")


# --- Skills Section ---
def render_skills_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable
):
    st_obj.header("Skills")
    with st_obj.expander("🎯 Understanding Skills (Cost: 1 PP per 2 Ranks Bought)", expanded=False):
        st_obj.markdown(rule_data.get("help_text",{}).get("skills_help","Total Skill Bonus = Ability Mod + Ranks Bought. Max Bonus = PL + 10. Max Ranks = PL + 5."))

    skill_rules: List[Dict[str, Any]] = rule_data.get('skills', [])
    current_skills = char_state.get('skills', {})
    current_abilities = char_state.get('abilities', {})
    pl = char_state.get('powerLevel', 10)
    skill_bonus_cap = pl + 10
    skill_rank_cap = pl + 5 # Max ranks that can be bought

    total_skill_ranks_bought = sum(current_skills.values())
    total_skill_cost = engine.calculate_skill_cost(current_skills)
    st_obj.subheader(f"Total Skill Ranks Bought: {total_skill_ranks_bought} | Total Skill Cost: {total_skill_cost} PP")
    st_obj.markdown("---")

    # Group skills by ability for better organization
    grouped_skills: Dict[str, List[Dict[str, Any]]] = {}
    for skill_info in skill_rules:
        group_key = skill_info.get('ability', 'General')
        if group_key not in grouped_skills: grouped_skills[group_key] = []
        grouped_skills[group_key].append(skill_info)

    skill_display_cols = st_obj.columns(3) # Adjust number of columns as needed
    col_idx = 0
    for ability_id_ordered in ["STR", "STA", "AGL", "DEX", "FGT", "INT", "AWE", "PRE", "General"]: # Order for display
        if ability_id_ordered in grouped_skills:
            with skill_display_cols[col_idx % len(skill_display_cols)]:
                st_obj.markdown(f"**{ability_id_ordered}-Based Skills**")
                for skill_info in grouped_skills[ability_id_ordered]:
                    skill_id = skill_info['id']
                    skill_name = skill_info['name']
                    gov_ab_id = skill_info.get('ability', '')
                    trained_only = skill_info.get('trainedOnly', False)
                    skill_desc = skill_info.get('description', '')

                    bought_rank = current_skills.get(skill_id, 0)
                    ability_mod = engine.get_ability_modifier(current_abilities.get(gov_ab_id, 0)) if gov_ab_id else 0
                    total_bonus = ability_mod + bought_rank
                    
                    label = f"{skill_name} {'(Trained Only)' if trained_only else ''}"
                    new_rank = st_obj.number_input(
                        label, min_value=0, max_value=skill_rank_cap,
                        value=bought_rank, 
                        key=_uk("adv_skill_input", skill_id), 
                        help=f"{skill_desc}\nGoverning Ability: {gov_ab_id or 'N/A'}\nAbility Mod: {ability_mod:+}\nTotal Bonus: {total_bonus:+}\nMax Ranks: {skill_rank_cap}, Max Bonus: {skill_bonus_cap:+}"
                    )
                    if new_rank != bought_rank:
                        update_char_value(['skills', skill_id], new_rank)
                        st_obj.rerun()
                    
                    bonus_display_str = f"Bonus: {total_bonus:+}"
                    if total_bonus > skill_bonus_cap:
                        st_obj.error(f"{bonus_display_str} (Cap: {skill_bonus_cap:+})", icon="⚠️")
                    else:
                        st_obj.caption(bonus_display_str)
                    st_obj.caption(f"Ranks: {new_rank}") # Show current rank being input
            col_idx += 1
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Skill")


# --- Advantages Section ---
def render_advantages_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable,
    generate_id_func: Callable[[str],str]
):
    st_obj.header("Advantages")
    with st_obj.expander("💡 Understanding Advantages (Cost: Usually 1 PP per Rank)", expanded=False):
        st_obj.markdown(rule_data.get("help_text",{}).get("advantages_help","Special talents, contacts, or benefits. Many require specific parameters."))

    current_advantages: List[AdvantageDefinition] = char_state.get('advantages', [])
    advantage_rules: List[Dict[str,Any]] = rule_data.get('advantages', [])
    
    total_adv_cost = engine.calculate_advantage_cost(current_advantages)
    st_obj.subheader(f"Total Advantage Cost: {total_adv_cost} PP")
    st_obj.markdown("---")

    st_obj.markdown("**Your Advantages:**")
    if not current_advantages: st_obj.caption("No advantages selected.")
    
    advantages_to_keep = []
    for i, adv_entry in enumerate(current_advantages):
        adv_rule = next((r for r in advantage_rules if r['id'] == adv_entry['id']), None)
        if not adv_rule: continue

        adv_instance_id = adv_entry.get("instance_id", generate_id_func(f"adv_{adv_entry['id']}_")) # Ensure each entry has a unique key for Streamlit lists
        if "instance_id" not in adv_entry: adv_entry["instance_id"] = adv_instance_id
        
        with st_obj.container(): # Use container for each advantage for better layout
            st_obj.markdown(f"**{adv_rule['name']}**")
            cols_adv_edit = st_obj.columns([0.6, 0.2, 0.1]) # Name/Params, Rank, Remove

            with cols_adv_edit[0]: # Parameter display/editing
                if adv_rule.get('parameter_needed'):
                    param_key_prefix = _uk("adv_param_edit", adv_instance_id)
                    adv_params = adv_entry.get('params', {})
                    original_params_json = json.dumps(adv_params, sort_keys=True) # To detect change

                    # This needs the full dynamic parameter input logic from previous "fully coded out advantages" step
                    # (select_skill, text_long, number_languages, select_attack, etc.)
                    # For brevity, this is a placeholder for that complex UI logic block:
                    st_obj.caption(f"Params: {adv_params}") # Placeholder - replace with dynamic inputs
                    # Example for one param type:
                    if adv_rule.get('parameter_type') == 'text':
                        adv_params['detail'] = st_obj.text_input(adv_rule.get('parameter_prompt','Detail:'), value=adv_params.get('detail',''), key=f"{param_key_prefix}_detail")
                    # ... Add all other parameter type handlers ...

                    if json.dumps(adv_params, sort_keys=True) != original_params_json:
                        adv_entry['params'] = adv_params
                        update_char_value(['advantages'], current_advantages, do_recalc=True) # Recalc if params might affect something
                        st_obj.rerun()
                else:
                    st_obj.caption(f"({adv_rule.get('description','').split('.')[0]})") # Short descr

            with cols_adv_edit[1]: # Rank editing
                current_rank_adv = adv_entry.get('rank', 1)
                if adv_rule.get('ranked', False):
                    max_adv_rank = adv_rule.get('maxRanks', 20)
                    if adv_rule.get('maxRanks_source') == 'AGL': max_adv_rank = char_state.get('abilities',{}).get('AGL',0)
                    
                    new_rank_adv = st_obj.number_input(
                        "Rank", value=current_rank_adv, min_value=1, max_value=max_adv_rank,
                        key=_uk("adv_rank_edit", adv_instance_id), label_visibility="collapsed"
                    )
                    if new_rank_adv != current_rank_adv:
                        adv_entry['rank'] = new_rank_adv
                        update_char_value(['advantages'], current_advantages)
                        st_obj.rerun()
                else:
                    st_obj.caption(f"Rank: {current_rank_adv}")
            
            if cols_adv_edit[2].button("✖", key=_uk("adv_remove_edit", adv_instance_id), help="Remove"):
                # Item will be removed by not being added to advantages_to_keep
                pass
            else:
                advantages_to_keep.append(adv_entry)
            st_obj.markdown("---") # Separator

    if len(advantages_to_keep) != len(current_advantages):
        update_char_value(['advantages'], advantages_to_keep)
        st_obj.rerun()

    # --- Add New Advantage UI ---
    st_obj.subheader("Add New Advantage")
    # ... (Full UI with st.form for adding new advantage, including dynamic parameter inputs based on selected adv_rule,
    #      similar to the detailed logic in the previous "fully coded advantages" response) ...
    st_obj.warning("Full Advantage Addition UI with dynamic parameters needs to be implemented here.")
    display_field_validation_errors(st_obj, char_state.get('validationErrors',[]), "Advantage")


# --- Powers Section ---
def render_powers_section_adv(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value: Callable,
    generate_id_func: Callable[[str],str],
    power_form_state_ref: Dict[str,Any] # Reference to st.session_state.power_form_state
):
    st_obj.header("Powers")
    with st_obj.expander("⚡ Understanding Powers (Advanced)", expanded=False):
        st_obj.markdown(rule_data.get("help_text",{}).get("powers_adv_help","Build custom powers with Effects, Extras, and Flaws. Watch PL Caps!"))

    # This function will now primarily call the more detailed power_builder_ui functions
    # from ui_sections.power_builder_ui import render_power_list, render_power_builder_form
    
    # Placeholder for where you'd import and call from power_builder_ui.py
    # render_power_list(st_obj, char_state, rule_data, engine, update_char_value, power_form_state_ref)
    # if st_obj.session_state.get('show_power_builder_form', False): # A flag to control form visibility
    #     render_power_builder_form(st_obj, char_state, rule_data, engine, update_char_value, power_form_state_ref, generate_id_func)
    st_obj.warning("Full Power Builder UI (calling functions from `power_builder_ui.py`) needs to be implemented here.")
    st_obj.markdown("This will include:")
    st_obj.markdown("- Listing current powers with edit/delete.")
    st_obj.markdown("- A comprehensive form (`st.session_state.power_form_state`) for adding/editing powers, including ALL effects, ALL modifiers with parameters, array configurations, Senses, Immunity, Variable (with mini-config builder), Create, Healing, Summon/Duplication (with structured stat block input), etc.")
    st_obj.markdown("- Contextual measurement display.")


# --- Other Advanced Mode Sections ---
def render_equipment_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str]):
    st_obj.header("Equipment")
    st_obj.markdown("*(Full UI from previous for Equipment, EP, standard/custom items)*")

def render_hq_builder_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], hq_form_state_ref: Dict[str,Any]):
    st_obj.header("Headquarters")
    st_obj.markdown("*(Full UI from previous for HQ builder: add/edit HQs, Size, Toughness, Features, EP)*")

def render_vehicle_builder_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str], vehicle_form_state_ref: Dict[str,Any]):
    st_obj.header("Vehicles")
    st_obj.markdown("*(Full UI from previous for Vehicle builder: add/edit Vehicles, Size, Base Stats, Features, EP)*")

def render_allies_section_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine, update_char_value: Callable, generate_id_func: Callable[[str],str]):
    st_obj.header("Companions (Allies)")
    st_obj.markdown("*(Full UI from previous for Allies: Minion/Sidekick/Summon/Duplicate structured stat blocks, PP pool validation)*")

def render_complications_section_adv(st_obj: Any, char_state: CharacterState, update_char_value: Callable):
    st_obj.header("Complications")
    st_obj.markdown("*(Full UI from previous for Complications: add/remove, min 2 validation)*")

def render_measurements_table_view_adv(st_obj: Any, rule_data: RuleData):
    st_obj.header("Measurements Table Reference")
    st_obj.markdown("*(Full UI from previous for Measurements Table display)*")

def render_character_sheet_view_in_app_adv(st_obj: Any, char_state: CharacterState, rule_data: RuleData, engine: CoreEngine):
    st_obj.header(f"In-App Sheet: {char_state.get('name', 'Unnamed Hero')}")
    st_obj.markdown("*(Full UI from previous for In-App Character Sheet using HTML/CSS from pdf_utils)*")
    # Example:
    # sheet_html = generate_pdf_html_content(char_state, rule_data, engine)
    # try:
    #     with open("assets/pdf_styles.css", "r", encoding="utf-8") as f:
    #         sheet_css = f"<style>{f.read()}</style>"
    #     st_obj.markdown(sheet_css, unsafe_allow_html=True)
    #     st_obj.markdown(sheet_html, unsafe_allow_html=True)
    # except FileNotFoundError: st_obj.error("pdf_styles.css not found.")

# This dispatch function would be called by app.py
def render_selected_advanced_view(
    view_name: str, 
    st_obj: Any, 
    char_state: CharacterState, 
    rule_data: RuleData, 
    engine: CoreEngine, 
    update_char_value: Callable,
    generate_id_func: Callable[[str],str], # For items needing unique IDs
    # Pass form states for complex builders if they are managed in app.py's main session state
    power_form_state_ref: Dict[str,Any], 
    hq_form_state_ref: Dict[str,Any],
    vehicle_form_state_ref: Dict[str,Any]
):
    if view_name == 'Abilities': render_abilities_section_adv(st_obj, char_state, rule_data, engine, update_char_value)
    elif view_name == 'Defenses': render_defenses_section_adv(st_obj, char_state, rule_data, engine, update_char_value)
    elif view_name == 'Skills': render_skills_section_adv(st_obj, char_state, rule_data, engine, update_char_value)
    elif view_name == 'Advantages': render_advantages_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func)
    elif view_name == 'Powers': render_powers_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, power_form_state_ref)
    elif view_name == 'Equipment': render_equipment_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func)
    elif view_name == 'Headquarters': render_hq_builder_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, hq_form_state_ref)
    elif view_name == 'Vehicles': render_vehicle_builder_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func, vehicle_form_state_ref)
    elif view_name == 'Companions (Allies)': render_allies_section_adv(st_obj, char_state, rule_data, engine, update_char_value, generate_id_func)
    elif view_name == 'Complications': render_complications_section_adv(st_obj, char_state, update_char_value)
    elif view_name == 'Measurements Table': render_measurements_table_view_adv(st_obj, rule_data)
    elif view_name == 'Character Sheet': render_character_sheet_view_in_app_adv(st_obj, char_state, rule_data, engine)
    else: st_obj.error(f"Unknown advanced view: {view_name}")