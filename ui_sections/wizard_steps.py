# heroforge-mm-streamlit/ui_sections/wizard_steps.py

import streamlit as st
import copy
import math # Ensure math is imported
from typing import Dict, List, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING: 
    from ..core_engine import CoreEngine, CharacterState, RuleData 
else: 
    CoreEngine = Any
    CharacterState = Dict[str, Any]
    RuleData = Dict[str, Any]


# --- Helper for Wizard ---
def _wizard_header(st_obj: Any, step_number: int, max_steps: int, title: str):
    """Renders the header for each wizard step."""
    st_obj.subheader(f"Step {step_number} of {max_steps}: {title}")
    st_obj.progress(float(step_number) / max_steps)
    st_obj.markdown("---")

# --- Unique Key Helper for Wizard ---
def _uk_wiz(base: str, *args: Any) -> str:
    """Creates a unique key for Streamlit widgets within the Wizard."""
    str_args = [str(a).replace(":", "_").replace(" ", "_").replace("[", "_").replace("]", "_").replace("(", "_").replace(")", "_").replace("/", "_") for a in args if a is not None]
    return f"wiz_{base}_{'_'.join(str_args)}"

# --- Step 1: Basics ---
def render_wizard_step1_basics(
    st_obj: Any, 
    char_state: CharacterState,
    rule_data: RuleData, 
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(st_obj, 1, 6, "The Basics - Name, Concept, Power Level")
    st_obj.markdown("Welcome to HeroForge M&M! This wizard will guide you in creating your superhero. Let's start with the fundamentals.")

    with st_obj.expander("ℹ️ What is Power Level (PL)?", expanded=False):
        st_obj.markdown("""
            Power Level (PL) is a number (usually 8-12 for starting heroes) that sets the overall 'power budget' and limits for your character.
            * **Power Points (PP):** You get PP equal to `PL x 15` (e.g., PL10 = 150 PP) to buy everything: Abilities, Skills, Powers, etc.
            * **Caps:** PL also limits how high your Attack Bonuses, Effect Ranks, Defenses, and Skill Bonuses can go. This keeps characters balanced.
            This tool will help you track these! Default is PL10 (150 PP).
        """)

    new_name = st_obj.text_input(
        "Character Name:", 
        value=char_state.get('name', 'My Hero'), 
        key=_uk_wiz("char_name")
    )
    if new_name != char_state.get('name'): 
        update_char_value_wiz(['name'], new_name)
        # No explicit rerun needed here, as text_input typically updates state on blur/enter
        # and the next interaction or step will use the updated name.

    new_concept = st_obj.text_area(
        "Brief Concept/Origin:", 
        value=char_state.get('concept', ''), 
        key=_uk_wiz("char_concept"),
        help="A few words about your hero (e.g., 'Alien powerhouse from a dying world', 'Mutated teen acrobat', 'Mystic guardian of ancient lore')."
    )
    if new_concept != char_state.get('concept'):
        update_char_value_wiz(['concept'], new_concept)

    current_pl = char_state.get('powerLevel', 10)
    new_pl = st_obj.slider(
        "Select Power Level (PL):", 
        min_value=1, max_value=20, value=current_pl, 
        key=_uk_wiz("char_pl"),
        help=f"This sets your starting Power Points (PP). Current: {char_state.get('powerLevel', 10) * 15} PP."
    )
    if new_pl != current_pl:
        update_char_value_wiz(['powerLevel'], new_pl)
        update_char_value_wiz(['totalPowerPoints'], new_pl * 15) 
        st_obj.rerun() 

    st_obj.info(f"Selected PL: {char_state.get('powerLevel')}. Starting Power Points: {char_state.get('totalPowerPoints')}")


# --- Step 2: Archetype ---
def render_wizard_step2_archetype(
    st_obj: Any,
    char_state: CharacterState, 
    rule_data: RuleData,
    engine: CoreEngine, 
    apply_archetype_to_wizard_state: Callable[[str], None] 
):
    _wizard_header(st_obj, 2, 6, "Choose an Archetype (Optional)")
    with st_obj.expander("ℹ️ What are Archetypes?", expanded=False):
        st_obj.markdown("""
            Archetypes are common superhero templates (like a strong 'Brick', a fast 'Speedster', or an 'Energy Projector').
            Selecting one gives you a pre-filled starting point with relevant abilities, skills, and a few core powers.
            It's a great way to get started quickly! You can customize everything afterwards in Advanced Mode.
            Or, choose 'Start from Scratch' for full control from the beginning.
        """)

    archetype_rules_list = rule_data.get('archetypes', []) 
    arch_options = {"": "Start from Scratch / Custom Build"}
    for arch in archetype_rules_list:
        arch_options[arch['id']] = f"{arch['name']} - {arch.get('description', '')}"

    selected_arch_id = st_obj.selectbox(
        "Select Archetype:", 
        options=list(arch_options.keys()), 
        format_func=lambda x: arch_options[x],
        key=_uk_wiz("arch_select")
    )

    if st_obj.button("Apply Archetype & Continue", key=_uk_wiz("apply_arch_btn")):
        apply_archetype_to_wizard_state(selected_arch_id) # This callback in app.py will handle state update & rerun
        if selected_arch_id and selected_arch_id in arch_options :
            st_obj.success(f"Applied {arch_options[selected_arch_id].split(' - ')[0]} template! Review in next steps or click 'Next'.")
        else:
            st_obj.info("Continuing with a custom build (no archetype selected or 'Start from Scratch' applied). Click 'Next'.")


# --- Step 3: Abilities (Guided) ---
def render_wizard_step3_abilities_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(st_obj, 3, 6, "Core Abilities")
    abilities_data = rule_data.get('abilities',{})
    help_text_data = abilities_data.get('help_text',{})

    with st_obj.expander("ℹ️ Understanding Abilities (Cost: 2 PP per Rank)", expanded=True):
        st_obj.markdown(help_text_data.get('general', "Abilities are your hero's eight core natural talents..."))
        for ab_rule in abilities_data.get('list',[]):
            st_obj.markdown(f"* **{ab_rule.get('id','')} ({ab_rule.get('name','')})**: {help_text_data.get(ab_rule.get('id',''), ab_rule.get('description',''))}")

    ability_rules_list = abilities_data.get('list', [])
    current_abilities = char_state.get('abilities', {})
    
    if st_obj.button("Suggest Balanced Spread (All 0s)", key=_uk_wiz("ab_balanced_btn")):
        for ab_info_btn in ability_rules_list: 
            update_char_value_wiz(['abilities', ab_info_btn['id']], 0)
        st_obj.rerun()

    cols = st_obj.columns(4)
    for i, ab_info in enumerate(ability_rules_list):
        ab_id = ab_info['id']
        ab_name = ab_info['name']
        ab_desc_help = help_text_data.get(ab_id, ab_info.get('description', ''))
        current_rank = current_abilities.get(ab_id, 0)
        
        with cols[i % len(cols)]:
            new_rank = st_obj.number_input(
                f"{ab_name} ({ab_id})", min_value=-5, max_value=char_state.get('powerLevel',10) + 5, 
                value=current_rank, key=_uk_wiz("ab_input", ab_id), help=ab_desc_help,
                step=1
            )
            if new_rank != current_rank:
                update_char_value_wiz(['abilities', ab_id], new_rank)
                st_obj.rerun() 
            
            cost = new_rank * abilities_data.get('costFactor',2) # Use costFactor from rules
            mod = engine.get_ability_modifier(new_rank)
            st_obj.caption(f"Mod: {mod:+}, Cost: {cost} PP", key=_uk_wiz("ab_caption", ab_id))

# --- Step 4: Defenses & Key Skills (Guided) ---
def render_wizard_step4_defskills_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(st_obj, 4, 6, "Defenses & Key Skills")
    
    pl = char_state.get('powerLevel', 10)
    pl_cap_paired = pl * 2
    current_defenses = char_state.get('defenses', {})
    current_abilities = char_state.get('abilities', {})

    with st_obj.expander("🛡️ Understanding Defenses (Cost: 1 PP per +1 Bought Rank)", expanded=True):
        st_obj.markdown(rule_data.get("help_text",{}).get("defenses_wizard_help", "Default defense help..."))
    
    defense_configs_wiz = [
        {"id": "Dodge", "base_ability_id": "AGL", "tooltip": "Helps avoid ranged attacks."},
        {"id": "Parry", "base_ability_id": "FGT", "tooltip": "Helps avoid close attacks."},
        {"id": "Toughness", "base_ability_id": "STA", "tooltip": "Reduces damage. Base from STA; powers can increase further."},
        {"id": "Fortitude", "base_ability_id": "STA", "tooltip": "Resists sickness, poison, fatigue."},
        {"id": "Will", "base_ability_id": "AWE", "tooltip": "Resists mental control, illusions, etc."}
    ]
    
    def_cols = st_obj.columns(len(defense_configs_wiz))
    for i, d_conf in enumerate(defense_configs_wiz):
        with def_cols[i]:
            base_val = engine.get_ability_modifier(current_abilities.get(d_conf['base_ability_id'], 0))
            bought_val = current_defenses.get(d_conf['id'], 0)
            total_val_for_input_display = base_val + bought_val 
            
            new_bought_val = st_obj.number_input(
                f"Buy {d_conf['id']}", min_value=0, max_value=pl + 10, 
                value=bought_val, key=_uk_wiz("def_input", d_conf['id']),
                help=f"{d_conf['tooltip']} Base from {d_conf['base_ability_id']}: {base_val}. Current (base+bought): {total_val_for_input_display}"
            )
            if new_bought_val != bought_val:
                update_char_value_wiz(['defenses', d_conf['id']], new_bought_val)
                st_obj.rerun()
            st_obj.caption(f"Total (base+bought): {total_val_for_input_display} (Cost: {new_bought_val} PP)")

    st_obj.markdown("**Defense Cap Check (includes all sources like powers):**")
    # ... (Defense cap checks as before, using engine.get_total_defense) ...
    total_dodge_wiz = engine.get_total_defense(char_state, 'Dodge', 'AGL'); total_parry_wiz = engine.get_total_defense(char_state, 'Parry', 'FGT'); total_toughness_wiz = engine.get_total_defense(char_state, 'Toughness', 'STA'); total_fortitude_wiz = engine.get_total_defense(char_state, 'Fortitude', 'STA'); total_will_wiz = engine.get_total_defense(char_state, 'Will', 'AWE')
    dt_sum = total_dodge_wiz + total_toughness_wiz; pt_sum = total_parry_wiz + total_toughness_wiz; fw_sum = total_fortitude_wiz + total_will_wiz
    st_obj.markdown(f"- Dodge ({total_dodge_wiz}) + Toughness ({total_toughness_wiz}) = **{dt_sum}** / {pl_cap_paired} {'✅ Valid' if dt_sum <= pl_cap_paired else '⚠️ Exceeded Cap!'}")
    st_obj.markdown(f"- Parry ({total_parry_wiz}) + Toughness ({total_toughness_wiz}) = **{pt_sum}** / {pl_cap_paired} {'✅ Valid' if pt_sum <= pl_cap_paired else '⚠️ Exceeded Cap!'}")
    st_obj.markdown(f"- Fortitude ({total_fortitude_wiz}) + Will ({total_will_wiz}) = **{fw_sum}** / {pl_cap_paired} {'✅ Valid' if fw_sum <= pl_cap_paired else '⚠️ Exceeded Cap!'}")


    st_obj.markdown("---"); skills_rules_data = rule_data.get('skills', {})
    with st_obj.expander("🎯 Understanding Skills (Cost: 1 PP per 2 Ranks)", expanded=True):
        st_obj.markdown(skills_rules_data.get("help_text",{}).get("general_wizard", "Default skills help..."))

    skill_rules_list = skills_rules_data.get('list', [])
    
    key_skill_base_ids = ["skill_athletics", "skill_perception", "skill_stealth", "skill_persuasion", "skill_close_combat", "skill_ranged_combat"]
    skill_cols = st_obj.columns(3)

    # Get a mutable copy of skills for modification within this rendering pass
    # This copy will be passed to update_char_value_wiz if changes occur.
    skills_being_edited = dict(char_state.get('skills', {}))

    for i, base_skill_id_wiz in enumerate(key_skill_base_ids):
        skill_info_base = next((s for s in skill_rules_list if s['id'] == base_skill_id_wiz), None)
        if not skill_info_base: continue

        actual_skill_id_to_edit = base_skill_id_wiz
        skill_name_display = skill_info_base['name']
        gov_ab_wiz = skill_info_base['ability']
        
        if skill_info_base.get('specialization_possible'):
            session_key_for_spec_name = _uk_wiz("skill_spec_name_persist", base_skill_id_wiz) # Ensure key is unique & persistent
            
            # Get default or current value from session_state
            default_spec_name_val = "Unarmed" if base_skill_id_wiz == "skill_close_combat" else "General"
            
            # If a specialization for this base skill already exists in char_state, try to use that one first
            # This is a simple check for the first found specialized skill of this base type.
            existing_spec_for_base = None
            for sk_id_check in skills_being_edited.keys():
                if sk_id_check.startswith(base_skill_id_wiz + "_"):
                    existing_spec_for_base = sk_id_check.split(base_skill_id_wiz + "_", 1)[1].replace("_", " ").title()
                    break # Use the first one found for the wizard's default display
            
            initial_spec_name_in_ss = st.session_state.get(session_key_for_spec_name, existing_spec_for_base or default_spec_name_val)

            custom_spec_name_input = st_obj.text_input(
                f"Specialize {skill_info_base['name']}:", 
                value=initial_spec_name_in_ss, 
                key=_uk_wiz("skill_spec_name_input_widget", base_skill_id_wiz) 
            )
            
            # Logic when specialization name changes
            if custom_spec_name_input != initial_spec_name_in_ss:
                old_spec_name_sanitized = initial_spec_name_in_ss.strip().lower().replace(' ','_')
                old_full_spec_id = f"{base_skill_id_wiz}_{old_spec_name_sanitized}"
                
                if old_full_spec_id in skills_being_edited and skills_being_edited[old_full_spec_id] > 0:
                    st_obj.caption(f"Note: Ranks from '{initial_spec_name_in_ss}' will be removed if you change ranks for '{custom_spec_name_input}'.", key=_uk_wiz("spec_change_note", base_skill_id_wiz))
                    # The actual removal of ranks from old_full_spec_id should happen if the user confirms
                    # new ranks for the *new* specialization, or can be done proactively.
                    # For wizard simplicity: if name changes, old spec ranks are conceptually "moved" (or zeroed).
                    # We will remove the old entry IF its rank was > 0 and set its rank to 0 effectively.
                    # And then the new spec name will get the ranks from the number_input below.
                    if old_full_spec_id in skills_being_edited: # Check again, as it's a copy
                        skills_being_edited.pop(old_full_spec_id, None) # Remove from our working copy

                st.session_state[session_key_for_spec_name] = custom_spec_name_input # Update persistent name
                # The actual_skill_id_to_edit will be formed with the new name below.
                # Ranks for this new ID will be fetched (likely 0) and then can be set.
                update_char_value_wiz(['skills'], skills_being_edited) # Update state after removing old
                st.rerun() # Rerun to reflect name change and process new ID correctly
                return # Return to avoid processing with old state

            # Use the (potentially updated) name from session state for consistency
            current_spec_name_for_id = st.session_state.get(session_key_for_spec_name, default_spec_name_val)
            actual_skill_id_to_edit = f"{base_skill_id_wiz}_{current_spec_name_for_id.strip().lower().replace(' ','_')}"
            skill_name_display = f"{skill_info_base['name']}: {current_spec_name_for_id.strip()}"
        
        with skill_cols[i % len(skill_cols)]:
            current_rank_wiz = skills_being_edited.get(actual_skill_id_to_edit, 0)
            ability_mod_wiz = engine.get_ability_modifier(current_abilities.get(gov_ab_wiz, 0))
            total_bonus_wiz = ability_mod_wiz + current_rank_wiz
            skill_bonus_cap_wiz = pl + 10; skill_rank_cap_wiz = pl + 5

            new_rank_wiz = st_obj.number_input(
                f"{skill_name_display} ({gov_ab_wiz}) Ranks:", 
                min_value=0, max_value=skill_rank_cap_wiz, value=current_rank_wiz, 
                key=_uk_wiz("skill_rank_input_val", actual_skill_id_to_edit), # Ensure key uses the actual ID
                help=f"Total: {total_bonus_wiz:+}. Max Ranks: {skill_rank_cap_wiz}, Max Bonus: {skill_bonus_cap_wiz:+}"
            )
            if new_rank_wiz != current_rank_wiz:
                skills_being_edited[actual_skill_id_to_edit] = new_rank_wiz
                update_char_value_wiz(['skills'], skills_being_edited) 
                st.rerun()
            
            if total_bonus_wiz > skill_bonus_cap_wiz:
                st_obj.error(f"Bonus {total_bonus_wiz:+} > Cap {skill_bonus_cap_wiz:+}", icon="⚠️", key=_uk_wiz("skill_err_cap", actual_skill_id_to_edit))
            else:
                st_obj.caption(f"Total Bonus: {total_bonus_wiz:+}", key=_uk_wiz("skill_bonus_cap_ok", actual_skill_id_to_edit))


# --- Step 5: Guided Powers ---
def render_wizard_step5_powers_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None],
    generate_id_func: Callable[[],str] 
):
    _wizard_header(st_obj, 5, 6, "Core Powers")
    with st_obj.expander("⚡ Understanding Powers (Wizard Focus)", expanded=True):
        st_obj.markdown(rule_data.get("help_text",{}).get("powers_wizard_help", "Default powers help..."))

    current_powers_wiz = char_state.get('powers', [])
    st_obj.markdown("**Current Powers:**")
    if not current_powers_wiz: st_obj.caption("None yet.")
    
    powers_to_keep = []
    for idx, pwr_entry in enumerate(current_powers_wiz):
        pwr_id_for_key = pwr_entry.get('id', f"pwr_idx_{idx}") # Use actual ID if present
        p_cols = st_obj.columns([0.6, 0.2, 0.1, 0.1]) 
        p_cols[0].markdown(f"**{pwr_entry.get('name', 'Unnamed')}**", key=_uk_wiz("pwr_disp_name", pwr_id_for_key))
        p_cols[1].caption(f"Rank {pwr_entry.get('rank',0)}", key=_uk_wiz("pwr_disp_rank", pwr_id_for_key))
        
        temp_power_cost_details = engine.calculate_individual_power_cost(pwr_entry, current_powers_wiz)
        p_cols[2].caption(f"{temp_power_cost_details.get('totalCost',0)} PP", key=_uk_wiz("pwr_disp_cost", pwr_id_for_key))

        if p_cols[3].button("➖", key=_uk_wiz("pwr_del_btn", pwr_id_for_key), help="Remove Power"): pass
        else: powers_to_keep.append(pwr_entry)
        
        measurement_display = engine.get_power_measurement_details(pwr_entry, rule_data)
        if measurement_display: st_obj.caption(f"└─ {measurement_display}", key=_uk_wiz("pwr_measure_disp", pwr_id_for_key))
        st_obj.markdown("---", key=_uk_wiz("pwr_disp_sep", pwr_id_for_key))

    if len(powers_to_keep) != len(current_powers_wiz):
        update_char_value_wiz(['powers'], powers_to_keep); st.rerun()

    st_obj.markdown("---"); st_obj.markdown("**Add a Common Power:** (Max 2-3 suggested for Wizard)")
    
    power_limit_heuristic = math.floor(char_state.get('powerLevel',10) / 3) + 1 # math.floor added
    power_limit_heuristic = max(2, min(power_limit_heuristic, 4)) 

    if len(current_powers_wiz) >= power_limit_heuristic : 
        st_obj.info(f"You've selected enough core powers ({len(current_powers_wiz)}/{power_limit_heuristic}) for the wizard! More can be added in Advanced Mode.")
    else:
        # This relies on 'prebuilt_powers_v1.json' being loaded into rule_data by core_engine.
        # If this data is missing, prebuilt_power_rules will be empty, and the selectbox won't show options.
        prebuilt_power_rules = [pbr for pbr in rule_data.get('prebuilt_powers_v1', []) if pbr.get('wizard_pickable', True)]
        if not prebuilt_power_rules:
            st_obj.caption("No common power templates available. Add powers in Advanced Mode or check rule files (prebuilt_powers_v1.json).")
        else:
            common_power_options = {"": "Select a common power type..."}
            for pbr_opt in prebuilt_power_rules:
                cost_per_rank = pbr_opt.get('costPerRank', pbr_opt.get('cost_per_rank_base')); fixed_cost = pbr_opt.get('fixed_cost')
                cost_str = f"{cost_per_rank}{'/r' if cost_per_rank else ''}" if cost_per_rank is not None else (f"{fixed_cost}pts" if fixed_cost is not None else "Var")
                common_power_options[pbr_opt['id']] = f"{pbr_opt['name']} ({cost_str})"
            
            selected_prebuilt_id_wiz = st_obj.selectbox("Common Powers:", options=list(common_power_options.keys()), format_func=lambda x: common_power_options[x], key=_uk_wiz("pwr_select_common_dd"))
            
            if selected_prebuilt_id_wiz:
                chosen_prebuilt_rule = next((pbr for pbr in prebuilt_power_rules if pbr['id'] == selected_prebuilt_id_wiz), None)
                if chosen_prebuilt_rule:
                    default_rank_wiz = max(1, min(char_state.get('powerLevel', 10), chosen_prebuilt_rule.get('defaultRank',5)))
                    with st_obj.form(key=_uk_wiz("add_pwr_form", selected_prebuilt_id_wiz)):
                        st_obj.markdown(f"**Configuring: {chosen_prebuilt_rule.get('name')}**"); st_obj.caption(chosen_prebuilt_rule.get('description',''))
                        power_name_wiz_val = st_obj.text_input("Name this power:", value=chosen_prebuilt_rule.get('name'), key=_uk_wiz("pwr_name_cfg_form", selected_prebuilt_id_wiz))
                        max_rank_for_wizard = char_state.get('powerLevel', 10)
                        power_rank_wiz_val = st_obj.number_input("Set Power Rank:", min_value=1, max_value=max_rank_for_wizard, value=default_rank_wiz, key=_uk_wiz("pwr_rank_cfg_form", selected_prebuilt_id_wiz))
                        if st_obj.form_submit_button("Add This Power"):
                            new_power_entry = copy.deepcopy(chosen_prebuilt_rule); new_power_entry['id'] = generate_id_func() 
                            new_power_entry['name'] = power_name_wiz_val; new_power_entry['rank'] = power_rank_wiz_val
                            if 'baseEffectId' not in new_power_entry: new_power_entry['baseEffectId'] = "eff_feature" 
                            if 'modifiersConfig' not in new_power_entry: new_power_entry['modifiersConfig'] = []
                            current_powers_wiz_list = list(char_state.get('powers', [])); current_powers_wiz_list.append(new_power_entry)
                            update_char_value_wiz(['powers'], current_powers_wiz_list)
                            st_obj.success(f"Added {power_name_wiz_val}!"); st.rerun()

# --- Step 6: Complications & Review ---
def render_wizard_step6_complreview_final(
    st_obj: Any,
    char_state: CharacterState, 
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None],
    finish_wizard_func: Callable[[], None] 
):
    _wizard_header(st_obj, 6, 6, "Complications & Final Review")
    with st_obj.expander("ℹ️ Why Complications?", expanded=True):
        st_obj.markdown(rule_data.get("help_text",{}).get("complications_wizard_help", "Default complications help..."))

    current_complications_wiz_list = list(char_state.get('complications', [])) 
    if current_complications_wiz_list: st_obj.markdown("**Your Complications:**")
    
    complications_to_keep_final = []
    complications_changed_in_loop = False
    for i, comp_entry_loop in enumerate(current_complications_wiz_list):
        # Give each complication an instance ID for keying if it doesn't have one
        # This is more robust if list items are added/removed and indices shift.
        # For wizard_steps, simple index might be fine if full list is always re-rendered or replaced.
        # Using index 'i' for keys here as list is rebuilt each time for deletion.
        comp_instance_key_part = comp_entry_loop.get('instance_id', str(i)) # Prefer instance_id if it exists

        c_cols = st_obj.columns([0.9, 0.1])
        key_comp_text_edit = _uk_wiz("comp_text_edit_area", comp_instance_key_part)
        edited_desc = c_cols[0].text_area(f"Complication #{i+1}", value=comp_entry_loop.get('description',''), key=key_comp_text_edit, height=75)
        
        current_desc_in_state = comp_entry_loop.get('description','')
        if edited_desc != current_desc_in_state:
            # Prepare to update if changed.
            comp_entry_loop['description'] = edited_desc # Modify the entry from the list directly for now
            complications_changed_in_loop = True
            # Direct update via update_char_value_wiz will happen after the loop if complications_changed_in_loop is true
            # or if list length changes. This avoids multiple reruns inside the loop.
            
        if c_cols[1].button("🗑️", key=_uk_wiz("comp_del_final_btn", comp_instance_key_part), help="Remove Complication"):
            # This complication will be omitted by not adding to complications_to_keep_final
            complications_changed_in_loop = True # Signal that list needs update
        else:
            complications_to_keep_final.append(comp_entry_loop) # Keep (potentially edited)

    # Update state if list length changed OR if any description changed within the loop
    if len(complications_to_keep_final) != len(char_state.get('complications', [])) or complications_changed_in_loop:
        update_char_value_wiz(['complications'], complications_to_keep_final)
        st.rerun() # Rerun to reflect changes immediately

    with st_obj.form(key=_uk_wiz("add_complication_form_final_wizard"), clear_on_submit=True):
        new_comp_text_input = st.text_area("Add New Complication Description:", key=_uk_wiz("new_comp_desc_input_final_wizard_ta"), height=75)
        if st.form_submit_button("➕ Add Complication"):
            if new_comp_text_input.strip():
                current_comps = list(char_state.get('complications', [])) 
                current_comps.append({'description': new_comp_text_input.strip(), 'instance_id': generate_id_func("comp_wiz_")}) # Add instance_id
                update_char_value_wiz(['complications'], current_comps)
                st.rerun()
    
    st_obj.caption(f"Number of Complications: {len(char_state.get('complications',[]))}. Minimum 2 required.")
    st_obj.markdown("---")

    st_obj.markdown("**Final Review:**")
    # Use the char_state that this step function received, which is st.session_state.wizard_character_state
    # The engine.recalculate will operate on this and return a new, fully calculated state.
    recalculated_wiz_state = engine.recalculate(char_state) 
    
    # Crucially, update st.session_state.wizard_character_state if it was passed as char_state
    # This ensures that subsequent calls or the final "finish" uses the fully recalculated one.
    if id(char_state) == id(st.session_state.get('wizard_character_state')):
         st.session_state.wizard_character_state = recalculated_wiz_state
    # If char_state was a copy (not typical for how app.py calls this for wizard), 
    # then only the local recalculated_wiz_state is fresh. The finish_wizard_func
    # should operate on st.session_state.wizard_character_state.

    st_obj.info(f"**Name:** {recalculated_wiz_state.get('name')} | **PL:** {recalculated_wiz_state.get('powerLevel')} | **PP:** {recalculated_wiz_state.get('spentPowerPoints')} / {recalculated_wiz_state.get('totalPowerPoints')}")
    
    with st_obj.expander("Quick Stats Overview (Full details in Advanced Mode)", expanded=False):
        # Display logic for Abilities, Defenses, Skills, Advantages, Powers as before...
        st_obj.write("**Abilities:**"); ability_rules_list_review = rule_data.get('abilities',{}).get('list',[])
        for ab_id, ab_rank in recalculated_wiz_state.get('abilities', {}).items():
            ab_rule_rev = next((r for r in ability_rules_list_review if r['id'] == ab_id), None); ab_name_rev = ab_rule_rev['name'] if ab_rule_rev else ab_id
            st_obj.markdown(f"- {ab_name_rev}: {ab_rank} (Mod: {engine.get_ability_modifier(ab_rank):+})", key=_uk_wiz("rev_ab",ab_id))
        st_obj.write("**Defenses (Totals):**"); defense_configs_wiz_rev = [{"id":"Dodge","base_ability_id":"AGL"},{"id":"Parry","base_ability_id":"FGT"},{"id":"Toughness","base_ability_id":"STA"},{"id":"Fortitude","base_ability_id":"STA"},{"id":"Will","base_ability_id":"AWE"}]
        for def_conf_rev in defense_configs_wiz_rev:
            st_obj.markdown(f"- {def_conf_rev['id']}: {engine.get_total_defense(recalculated_wiz_state, def_conf_rev['id'], def_conf_rev['base_ability_id'])}", key=_uk_wiz("rev_def",def_conf_rev['id']))
        st_obj.write("**Key Skills (Bonus > 0):**"); has_skills_rev = False; skill_rules_list_rev = rule_data.get('skills',{}).get('list',[])
        for sk_id, sk_rank in recalculated_wiz_state.get('skills', {}).items():
            if sk_rank > 0:
                has_skills_rev = True; sk_rule_rev = engine.get_skill_rule(sk_id, skill_rules_list_rev); sk_name_rev = engine.get_skill_name_by_id(sk_id, skill_rules_list_rev)
                gov_ab_rev = sk_rule_rev['ability'] if sk_rule_rev else 'N/A'; ab_mod_rev = engine.get_ability_modifier(recalculated_wiz_state.get('abilities',{}).get(gov_ab_rev,0))
                st_obj.markdown(f"- {sk_name_rev}: {ab_mod_rev + sk_rank:+}", key=_uk_wiz("rev_sk",sk_id))
        if not has_skills_rev: st_obj.caption("None with ranks > 0.")
        st_obj.write("**Advantages:**"); adv_rules_list_rev = rule_data.get('advantages_v1',[])
        if not recalculated_wiz_state.get('advantages'): st_obj.caption("None.")
        for adv_rev in recalculated_wiz_state.get('advantages',[]):
            adv_rule_rev = next((r for r in adv_rules_list_rev if r['id'] == adv_rev['id']), None); adv_name_disp_rev = adv_rule_rev['name'] if adv_rule_rev else adv_rev['id']
            adv_rank_disp_rev = f" (Rank {adv_rev['rank']})" if adv_rule_rev and adv_rule_rev.get('ranked') and adv_rev.get('rank',1) > 1 else ""
            st_obj.markdown(f"- {adv_name_disp_rev}{adv_rank_disp_rev}", key=_uk_wiz("rev_adv", adv_rev.get('instance_id', adv_rev.get('id'))))
        st_obj.write("**Powers:**")
        if not recalculated_wiz_state.get('powers'): st_obj.caption("None.")
        for pwr_rev in recalculated_wiz_state.get('powers',[]):
            st_obj.markdown(f"- {pwr_rev.get('name','Unnamed Power')} (Rank {pwr_rev.get('rank',0)})", key=_uk_wiz("rev_pwr", pwr_rev.get('id','pwr')))

    st_obj.markdown("---")
    final_errors_wiz = recalculated_wiz_state.get('validationErrors', [])
    pp_ok_wiz = recalculated_wiz_state.get('spentPowerPoints', 0) <= recalculated_wiz_state.get('totalPowerPoints', 0)
    complications_ok_wiz = len(recalculated_wiz_state.get('complications', [])) >= 2

    if not final_errors_wiz and pp_ok_wiz and complications_ok_wiz:
        st_obj.success("Character is valid and ready!")
        if st_obj.button("🎉 Finish Character & Go to Full Character Sheet", type="primary", key=_uk_wiz("finish_wizard_final_btn")):
            finish_wizard_func() 
            # Rerun is handled by app.py after finish_wizard_func changes mode
    else:
        st_obj.error("Please resolve issues before finishing:")
        if not pp_ok_wiz: st_obj.warning(f"Power Points issue: Spent {recalculated_wiz_state.get('spentPowerPoints')} / Available {recalculated_wiz_state.get('totalPowerPoints')}")
        if not complications_ok_wiz: st_obj.warning(f"You need at least 2 complications (currently {len(recalculated_wiz_state.get('complications', []))}).")
        for err_idx, err_wiz in enumerate(final_errors_wiz): st_obj.warning(f"- {err_wiz}", key=_uk_wiz("final_err_disp", err_idx))