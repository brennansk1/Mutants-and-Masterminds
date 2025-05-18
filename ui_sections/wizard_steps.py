# heroforge-mm-streamlit/ui_sections/wizard_steps.py

import streamlit as st
import copy
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
    rule_data: RuleData, # Expected to be the pre-processed dict from app.py
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
    if new_name != char_state.get('name'): # Check against current state directly
        update_char_value_wiz(['name'], new_name)
        # No rerun needed, text_input updates on enter or blur by default if on_change not used

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
        st_obj.rerun() # Rerun to update PP display immediately

    st_obj.info(f"Selected PL: {char_state.get('powerLevel')}. Starting Power Points: {char_state.get('totalPowerPoints')}")


# --- Step 2: Archetype ---
def render_wizard_step2_archetype(
    st_obj: Any,
    char_state: CharacterState, # This is wizard_character_state
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

    archetype_rules_list = rule_data.get('archetypes', []) # Assuming rule_data['archetypes'] is the list
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
        if selected_arch_id:
            apply_archetype_to_wizard_state(selected_arch_id) 
            st_obj.success(f"Applied {arch_options[selected_arch_id].split(' - ')[0]} template! Review in next steps or click 'Next'.")
            # App.py's apply_archetype_to_wizard_state should handle the rerun or state update that causes it.
        else:
            st_obj.info("Continuing with a custom build (no archetype selected). Click 'Next'.")
        # Rely on main wizard navigation in app.py to move to the next step and refresh.

# --- Step 3: Abilities (Guided) ---
def render_wizard_step3_abilities_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(st_obj, 3, 6, "Core Abilities")
    with st_obj.expander("ℹ️ Understanding Abilities (Cost: 2 PP per Rank)", expanded=True):
        st_obj.markdown(rule_data.get('abilities',{}).get('help_text',{}).get('general', "Abilities are your hero's eight core natural talents..."))
        # Display individual ability help texts if desired
        for ab_rule in rule_data.get('abilities',{}).get('list',[]):
            st_obj.markdown(f"* **{ab_rule.get('id','')} ({ab_rule.get('name','')})**: {rule_data.get('abilities',{}).get('help_text',{}).get(ab_rule.get('id',''), ab_rule.get('description',''))}")


    ability_rules_list = rule_data.get('abilities', {}).get('list', [])
    current_abilities = char_state.get('abilities', {})
    
    if st_obj.button("Suggest Balanced Spread (All 0s)", key=_uk_wiz("ab_balanced_btn")):
        for ab_info_btn in ability_rules_list: 
            update_char_value_wiz(['abilities', ab_info_btn['id']], 0)
        st_obj.rerun()

    cols = st_obj.columns(4)
    for i, ab_info in enumerate(ability_rules_list):
        ab_id = ab_info['id']
        ab_name = ab_info['name']
        ab_desc_help = rule_data.get('abilities',{}).get('help_text',{}).get(ab_id, ab_info.get('description', ''))
        current_rank = current_abilities.get(ab_id, 0)
        
        with cols[i % len(cols)]:
            new_rank = st_obj.number_input(
                f"{ab_name} ({ab_id})", min_value=-5, max_value=char_state.get('powerLevel',10) + 5, # Max rank is PL+5 for abilities in some interpretations, or PL for others. PP will limit.
                value=current_rank, key=_uk_wiz("ab_input", ab_id), help=ab_desc_help,
                step=1
            )
            if new_rank != current_rank:
                update_char_value_wiz(['abilities', ab_id], new_rank)
                st_obj.rerun() 
            
            cost = new_rank * engine.rule_data.get('abilities',{}).get('costFactor',2)
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

    # Guided Defenses
    with st_obj.expander("🛡️ Understanding Defenses (Cost: 1 PP per +1 Bought Rank)", expanded=True):
        st_obj.markdown(rule_data.get("help_text",{}).get("defenses_wizard_help", """
            Defenses protect your hero. Base value from Abilities, can be increased by buying ranks.
            * **Dodge (AGL):** Avoids ranged/area attacks.
            * **Parry (FGT):** Avoids close attacks.
            * **Toughness (STA):** Resists damage. (Can also come from powers like Protection).
            * **Fortitude (STA):** Resists effects on health (poison, disease).
            * **Will (AWE):** Resists mental effects.
            **PL Caps:** `Dodge + Toughness <= PLx2`, `Parry + Toughness <= PLx2`, `Fortitude + Will <= PLx2`.
        """))
    
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
            # Total for display in wizard (base + bought only for this input step)
            # The engine.get_total_defense will include powers for the cap check below.
            total_val_for_input_display = base_val + bought_val 
            
            new_bought_val = st_obj.number_input(
                f"Buy {d_conf['id']}", min_value=0, max_value=pl + 10, 
                value=bought_val, key=_uk_wiz("def_input", d_conf['id']),
                help=f"{d_conf['tooltip']} Base from {d_conf['base_ability_id']}: {base_val}. Current Total (from base+bought): {total_val_for_input_display}"
            )
            if new_bought_val != bought_val:
                update_char_value_wiz(['defenses', d_conf['id']], new_bought_val)
                st_obj.rerun()
            st_obj.caption(f"Total (base+bought): {total_val_for_input_display} (Cost: {new_bought_val} PP)")

    st_obj.markdown("**Defense Cap Check (includes all sources like powers):**")
    total_dodge_wiz = engine.get_total_defense(char_state, 'Dodge', 'AGL')
    total_parry_wiz = engine.get_total_defense(char_state, 'Parry', 'FGT')
    total_toughness_wiz = engine.get_total_defense(char_state, 'Toughness', 'STA')
    total_fortitude_wiz = engine.get_total_defense(char_state, 'Fortitude', 'STA')
    total_will_wiz = engine.get_total_defense(char_state, 'Will', 'AWE')

    dt_sum = total_dodge_wiz + total_toughness_wiz
    pt_sum = total_parry_wiz + total_toughness_wiz
    fw_sum = total_fortitude_wiz + total_will_wiz
    st_obj.markdown(f"- Dodge ({total_dodge_wiz}) + Toughness ({total_toughness_wiz}) = **{dt_sum}** / {pl_cap_paired} {'✅ Valid' if dt_sum <= pl_cap_paired else '⚠️ Exceeded Cap!'}")
    st_obj.markdown(f"- Parry ({total_parry_wiz}) + Toughness ({total_toughness_wiz}) = **{pt_sum}** / {pl_cap_paired} {'✅ Valid' if pt_sum <= pl_cap_paired else '⚠️ Exceeded Cap!'}")
    st_obj.markdown(f"- Fortitude ({total_fortitude_wiz}) + Will ({total_will_wiz}) = **{fw_sum}** / {pl_cap_paired} {'✅ Valid' if fw_sum <= pl_cap_paired else '⚠️ Exceeded Cap!'}")

    # Guided Skills
    st_obj.markdown("---")
    skills_rules_data = rule_data.get('skills', {})
    with st_obj.expander("🎯 Understanding Skills (Cost: 1 PP per 2 Ranks)", expanded=True):
        st_obj.markdown(skills_rules_data.get("help_text",{}).get("general_wizard", """
            Skills represent specific training. **Total Skill Bonus** = `Governing Ability Modifier + Ranks Bought`.
            This Total Bonus cannot exceed `Power Level + 10`. Max Ranks you can buy is `PL + 5`.
            Consider skills matching your hero's concept. **Perception** is useful for everyone!
            Combat skills like **Close Combat: Unarmed** or **Ranged Combat: Energy Blasts** improve your chance to hit.
        """))

    skill_rules_list = skills_rules_data.get('list', [])
    current_skills_wiz = char_state.get('skills', {})
    
    # Curated list for wizard, ensuring they are valid skill IDs from rules.
    key_skill_base_ids = ["skill_athletics", "skill_perception", "skill_stealth", "skill_persuasion", "skill_close_combat", "skill_ranged_combat"]
    
    skill_cols = st_obj.columns(3)
    for i, base_skill_id_wiz in enumerate(key_skill_base_ids):
        skill_info_base = next((s for s in skill_rules_list if s['id'] == base_skill_id_wiz), None)
        if not skill_info_base: continue # Skip if base skill rule not found

        actual_skill_id_to_edit = base_skill_id_wiz
        skill_name_display = skill_info_base['name']
        gov_ab_wiz = skill_info_base['ability']
        
        # Handle specialization input for combat skills
        if skill_info_base.get('specialization_possible'):
            # Use a session state key to store the current specialization for this skill slot in the wizard
            # This avoids issues with text_input resetting on reruns if not handled carefully
            session_key_for_spec_name = _uk_wiz("skill_spec_name", base_skill_id_wiz)
            default_spec_name = "Unarmed" if base_skill_id_wiz == "skill_close_combat" else "General Blasts"
            
            # Retrieve or set initial specialization name
            if session_key_for_spec_name not in st.session_state:
                # Check if an archetype pre-filled a specific specialization
                # This is complex: need to find if char_state.skills has skill_close_combat_X
                # For simplicity, wizard starts with a default or user types one.
                st.session_state[session_key_for_spec_name] = default_spec_name

            custom_spec_name = st_obj.text_input(
                f"Specialize {skill_info_base['name']} (e.g., {skill_info_base.get('specialization_prompt','Swords')}):", 
                value=st.session_state[session_key_for_spec_name], 
                key=_uk_wiz("skill_spec_name_input", base_skill_id_wiz) # Input widget key
            )
            if custom_spec_name != st.session_state[session_key_for_spec_name]:
                 # If name changed, remove old specialized skill ranks from char_state before adding new one
                old_spec_id_to_remove = f"{base_skill_id_wiz}_{st.session_state[session_key_for_spec_name].lower().replace(' ','_')}"
                if old_spec_id_to_remove in current_skills_wiz:
                    current_skills_wiz.pop(old_spec_id_to_remove) # Modifying copy
                st.session_state[session_key_for_spec_name] = custom_spec_name # Update session state
                # New ID will be formed below, ranks will be 0 initially if name changed.

            actual_skill_id_to_edit = f"{base_skill_id_wiz}_{custom_spec_name.strip().lower().replace(' ','_')}"
            skill_name_display = f"{skill_info_base['name']}: {custom_spec_name.strip()}"
        
        with skill_cols[i % len(skill_cols)]:
            current_rank_wiz = current_skills_wiz.get(actual_skill_id_to_edit, 0)
            ability_mod_wiz = engine.get_ability_modifier(current_abilities.get(gov_ab_wiz, 0))
            total_bonus_wiz = ability_mod_wiz + current_rank_wiz
            skill_bonus_cap_wiz = pl + 10
            skill_rank_cap_wiz = pl + 5 # Max ranks that can be bought

            new_rank_wiz = st_obj.number_input(
                f"{skill_name_display} ({gov_ab_wiz}) Ranks:", 
                min_value=0, max_value=skill_rank_cap_wiz, 
                value=current_rank_wiz, 
                key=_uk_wiz("skill_rank_input", actual_skill_id_to_edit),
                help=f"Total Bonus: {total_bonus_wiz:+}. Max Ranks: {skill_rank_cap_wiz}, Max Bonus: {skill_bonus_cap_wiz:+}"
            )
            if new_rank_wiz != current_rank_wiz:
                # Update the specific (possibly specialized) skill ID
                current_skills_wiz[actual_skill_id_to_edit] = new_rank_wiz
                update_char_value_wiz(['skills'], current_skills_wiz) # Update the whole skills dict
                st_obj.rerun()
            
            if total_bonus_wiz > skill_bonus_cap_wiz:
                st_obj.error(f"Total Bonus {total_bonus_wiz:+}, Cap {skill_bonus_cap_wiz:+}", icon="⚠️")
            else:
                st_obj.caption(f"Total Bonus: {total_bonus_wiz:+}")


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
        st_obj.markdown(rule_data.get("help_text",{}).get("powers_wizard_help", """
            Powers are your hero's main superhuman abilities. They are built from **Effects**, have a **Rank**, and can have **Modifiers**.
            * **Cost:** Based on Effect, Rank, and Modifiers.
            * **PL Caps for Attacks:** `Attack Bonus + Effect Rank <= PL x 2`.
            * **PL Caps for Area/Perception Effects:** `Effect Rank <= PL`.
            This wizard offers a few common, pre-defined powers. Customize fully in Advanced Mode.
        """))

    current_powers_wiz = char_state.get('powers', [])
    st_obj.markdown("**Current Powers:**")
    if not current_powers_wiz: st_obj.caption("None yet.")
    
    powers_to_keep = []
    for idx, pwr_entry in enumerate(current_powers_wiz):
        p_cols = st_obj.columns([0.6, 0.2, 0.1, 0.1]) # Name, Rank, Cost, Remove
        p_cols[0].markdown(f"**{pwr_entry.get('name', 'Unnamed')}**")
        p_cols[1].caption(f"Rank {pwr_entry.get('rank',0)}")
        
        # Recalculate cost for display as it might change if PL changed
        # This is a simplified display; engine.recalculate on char_state is the source of truth
        temp_power_cost_details = engine.calculate_individual_power_cost(pwr_entry, current_powers_wiz)
        p_cols[2].caption(f"{temp_power_cost_details.get('totalCost',0)} PP")

        if p_cols[3].button("➖", key=_uk_wiz("pwr_del_btn", pwr_entry.get('id', idx)), help="Remove Power"):
            # This power will be omitted when rebuilding powers_to_keep
            pass
        else:
            powers_to_keep.append(pwr_entry)
        
        measurement_display = engine.get_power_measurement_details(pwr_entry, rule_data)
        if measurement_display: st_obj.caption(f"└─ {measurement_display}")
        st_obj.markdown("---", key=_uk_wiz("pwr_disp_sep", pwr_entry.get('id', idx)))

    if len(powers_to_keep) != len(current_powers_wiz):
        update_char_value_wiz(['powers'], powers_to_keep)
        st_obj.rerun()


    st_obj.markdown("---")
    st_obj.markdown("**Add a Common Power:** (Max 2-3 suggested for Wizard)")
    
    # Heuristic limit based on PL for wizard
    power_limit_heuristic = math.floor(char_state.get('powerLevel',10) / 3) + 1 
    power_limit_heuristic = max(2, min(power_limit_heuristic, 4)) # Ensure at least 2, max 4 for wizard

    if len(current_powers_wiz) >= power_limit_heuristic : 
        st_obj.info(f"You've selected a good number of core powers ({len(current_powers_wiz)}/{power_limit_heuristic}) for the wizard! More can be added in Advanced Mode.")
    else:
        # Assuming 'prebuilt_powers_v1' key exists in rule_data and contains list of power templates
        prebuilt_power_rules = [pbr for pbr in rule_data.get('prebuilt_powers_v1', []) if pbr.get('wizard_pickable', True)]
        common_power_options = {"": "Select a common power type..."}
        for pbr_opt in prebuilt_power_rules:
            cost_per_rank = pbr_opt.get('costPerRank', pbr_opt.get('cost_per_rank_base')) # Check both keys
            fixed_cost = pbr_opt.get('fixed_cost')
            cost_str = f"{cost_per_rank}{'/rank' if cost_per_rank else ''}" if cost_per_rank is not None else (f"{fixed_cost} pts" if fixed_cost is not None else "Var. Cost")
            common_power_options[pbr_opt['id']] = f"{pbr_opt['name']} ({cost_str})"
        
        selected_prebuilt_id_wiz = st_obj.selectbox(
            "Common Powers:", 
            options=list(common_power_options.keys()), 
            format_func=lambda x: common_power_options[x], 
            key=_uk_wiz("pwr_select_common")
        )
        
        if selected_prebuilt_id_wiz:
            chosen_prebuilt_rule = next((pbr for pbr in prebuilt_power_rules if pbr['id'] == selected_prebuilt_id_wiz), None)
            if chosen_prebuilt_rule:
                default_rank_wiz = max(1, min(char_state.get('powerLevel', 10), chosen_prebuilt_rule.get('defaultRank',5)))
                
                with st_obj.form(key=_uk_wiz("add_pwr_form", selected_prebuilt_id_wiz)):
                    st_obj.markdown(f"**Configuring: {chosen_prebuilt_rule.get('name')}**")
                    st_obj.caption(chosen_prebuilt_rule.get('description',''))

                    power_name_wiz_val = st_obj.text_input("Name this power:", value=chosen_prebuilt_rule.get('name'), key=_uk_wiz("pwr_name_cfg", selected_prebuilt_id_wiz))
                    
                    # Determine max rank: PL for area/perception, PL*2 for attacks (but effect rank itself is PL capped)
                    # For simplicity in wizard, cap rank at PL. Advanced can go higher if PL caps allow.
                    max_rank_for_wizard = char_state.get('powerLevel', 10)

                    power_rank_wiz_val = st_obj.number_input(
                        "Set Power Rank:", min_value=1, 
                        max_value=max_rank_for_wizard, 
                        value=default_rank_wiz, key=_uk_wiz("pwr_rank_cfg", selected_prebuilt_id_wiz)
                    )
                    
                    submitted_wiz_pwr = st_obj.form_submit_button("Add This Power")
                    if submitted_wiz_pwr:
                        new_power_entry = copy.deepcopy(chosen_prebuilt_rule) 
                        new_power_entry['id'] = generate_id_func() 
                        new_power_entry['name'] = power_name_wiz_val
                        new_power_entry['rank'] = power_rank_wiz_val
                        # Ensure essential fields for engine are present from prebuilt
                        if 'baseEffectId' not in new_power_entry: new_power_entry['baseEffectId'] = "eff_feature" # Fallback
                        if 'modifiersConfig' not in new_power_entry: new_power_entry['modifiersConfig'] = []
                        
                        current_powers_wiz_list = list(char_state.get('powers', [])) # Get mutable copy
                        current_powers_wiz_list.append(new_power_entry)
                        update_char_value_wiz(['powers'], current_powers_wiz_list)
                        st_obj.success(f"Added {power_name_wiz_val}!")
                        st_obj.rerun()

# --- Step 6: Complications & Review ---
def render_wizard_step6_complreview_final(
    st_obj: Any,
    char_state: CharacterState, # This is wizard_character_state
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None],
    finish_wizard_func: Callable[[], None] 
):
    _wizard_header(st_obj, 6, 6, "Complications & Final Review")
    with st_obj.expander("ℹ️ Why Complications?", expanded=True):
        st_obj.markdown(rule_data.get("help_text",{}).get("complications_wizard_help", """
            Complications are problems, weaknesses, or responsibilities that make your hero's life interesting.
            They don't cost Power Points. Instead, when they cause trouble, your GM awards Hero Points!
            Hero Points let you re-roll dice, recover quickly, or perform power stunts.
            You need at least **two** Complications.
        """))

    current_complications_wiz_list = list(char_state.get('complications', [])) 
    
    if current_complications_wiz_list:
        st_obj.markdown("**Your Complications:**")
    
    # Use a loop that allows modification by rebuilding the list
    complications_to_keep_final = []
    for i, comp_entry in enumerate(current_complications_wiz_list):
        c_cols = st_obj.columns([0.9, 0.1])
        
        # To make text_input update on_change-like behavior, we need to manage its state
        # or use a form for each. Simpler: update on button press or when navigating away.
        # For direct editing, text_area with on_change is better if available or use a sub-form.
        # For wizard, let's keep it simple: edit in place, save happens via main state.
        key_comp_text_edit = _uk_wiz("comp_text_edit", i)
        edited_desc = c_cols[0].text_area(f"#{i+1}", value=comp_entry.get('description',''), 
                                         key=key_comp_text_edit, height=75)
        
        if edited_desc != comp_entry.get('description'):
            # Update the description in the original list being iterated (or a copy)
            # This requires careful state handling if update_char_value_wiz triggers immediate rerun
            # A safer way: collect all changes and update once.
            # For now, this direct update might work if update_char_value_wiz is robust.
            temp_list_for_update = list(char_state.get('complications', []))
            if i < len(temp_list_for_update):
                temp_list_for_update[i]['description'] = edited_desc
                update_char_value_wiz(['complications'], temp_list_for_update)
                # st_obj.rerun() # Rerun to reflect change, but can make UI jumpy.

        if c_cols[1].button("🗑️", key=_uk_wiz("comp_del_final", i), help="Remove Complication"):
            # This complication will be omitted
            pass
        else:
            # If not deleted, ensure we keep the potentially edited version
            complications_to_keep_final.append({'description': edited_desc}) 

    # If the list length changed due to deletion
    if len(complications_to_keep_final) != len(current_complications_wiz_list):
        update_char_value_wiz(['complications'], complications_to_keep_final)
        st_obj.rerun()
    elif any(current_complications_wiz_list[i].get('description') != complications_to_keep_final[i].get('description') for i in range(len(current_complications_wiz_list))):
        # If only descriptions changed, ensure the state is updated (might already be by text_area's implicit behavior or on_change if added)
        # This explicit update ensures it if on_change wasn't used.
        update_char_value_wiz(['complications'], complications_to_keep_final)
        # No rerun needed here if just text changed and it's reflected.

    # Add new complication
    with st_obj.form(key=_uk_wiz("add_complication_form_final"), clear_on_submit=True):
        new_comp_text_input = st.text_area("Add New Complication Description:", key=_uk_wiz("new_comp_desc_input_final"), height=75)
        submitted_add_comp = st.form_submit_button("➕ Add Complication")
        if submitted_add_comp and new_comp_text_input.strip():
            current_comps = list(char_state.get('complications', [])) # Get fresh list
            current_comps.append({'description': new_comp_text_input.strip()})
            update_char_value_wiz(['complications'], current_comps)
            st_obj.rerun()
    
    st_obj.caption(f"Number of Complications: {len(char_state.get('complications',[]))}. Minimum 2 required.")
    st_obj.markdown("---")

    st_obj.markdown("**Final Review:**")
    # Ensure the char_state passed to recalculate is the most current wizard state
    recalculated_wiz_state = engine.recalculate(char_state) 
    # Update session state directly if char_state is a direct reference to it
    if id(char_state) == id(st.session_state.wizard_character_state):
         st.session_state.wizard_character_state = recalculated_wiz_state
    else: # If char_state was a copy, this won't update the original session state.
          # This depends on how app.py calls this. Assume char_state IS st.session_state.wizard_character_state
          pass


    st_obj.info(f"**Name:** {recalculated_wiz_state.get('name')} | **PL:** {recalculated_wiz_state.get('powerLevel')} | **PP:** {recalculated_wiz_state.get('spentPowerPoints')} / {recalculated_wiz_state.get('totalPowerPoints')}")
    
    with st_obj.expander("Quick Stats Overview (Full details in Advanced Mode)", expanded=False):
        st_obj.write("**Abilities:**")
        for ab_id, ab_rank in recalculated_wiz_state.get('abilities', {}).items():
            ab_rule = next((r for r in rule_data.get('abilities',{}).get('list',[]) if r['id'] == ab_id), None)
            ab_name = ab_rule['name'] if ab_rule else ab_id
            st_obj.markdown(f"- {ab_name}: {ab_rank} (Mod: {engine.get_ability_modifier(ab_rank):+})")

        st_obj.write("**Defenses (Totals):**")
        for def_id in ["Dodge", "Parry", "Toughness", "Fortitude", "Will"]:
            base_ab_id = next((d['base_ability_id'] for d in defense_configs_wiz if d['id'] == def_id), None)
            st_obj.markdown(f"- {def_id}: {engine.get_total_defense(recalculated_wiz_state, def_id, base_ab_id if base_ab_id else '')}")
        
        st_obj.write("**Key Skills (Bonus > 0):**")
        has_skills = False
        for sk_id, sk_rank in recalculated_wiz_state.get('skills', {}).items():
            if sk_rank > 0:
                has_skills = True
                sk_rule = engine.get_skill_rule(sk_id, rule_data.get('skills',{}).get('list',[])) # Helper needed in engine or here
                sk_name = sk_rule['name'] if sk_rule else sk_id.replace("skill_","").replace("_"," ").title()
                if sk_rule and sk_rule.get('specialization_possible') and sk_id.count('_') > 1: # Is specialized
                    base_name = sk_rule['name']
                    spec_name = sk_id.split(sk_rule['id']+"_")[-1].replace("_"," ").title()
                    sk_name = f"{base_name}: {spec_name}"

                gov_ab = sk_rule['ability'] if sk_rule else 'N/A'
                ab_mod = engine.get_ability_modifier(recalculated_wiz_state.get('abilities',{}).get(gov_ab,0))
                st_obj.markdown(f"- {sk_name}: {ab_mod + sk_rank:+}")
        if not has_skills: st_obj.caption("None with ranks > 0.")

        st_obj.write("**Advantages:**")
        if not recalculated_wiz_state.get('advantages'): st_obj.caption("None.")
        for adv in recalculated_wiz_state.get('advantages',[]):
            adv_rule = next((r for r in rule_data.get('advantages_v1',[]) if r['id'] == adv['id']), None)
            adv_name_disp = adv_rule['name'] if adv_rule else adv['id']
            adv_rank_disp = f" (Rank {adv['rank']})" if adv_rule and adv_rule.get('ranked') and adv['rank'] > 1 else ""
            st_obj.markdown(f"- {adv_name_disp}{adv_rank_disp}")

        st_obj.write("**Powers:**")
        if not recalculated_wiz_state.get('powers'): st_obj.caption("None.")
        for pwr in recalculated_wiz_state.get('powers',[]):
            st_obj.markdown(f"- {pwr.get('name','Unnamed Power')} (Rank {pwr.get('rank',0)})")


    st_obj.markdown("---")
    final_errors_wiz = recalculated_wiz_state.get('validationErrors', [])
    pp_ok_wiz = recalculated_wiz_state.get('spentPowerPoints', 0) <= recalculated_wiz_state.get('totalPowerPoints', 0)
    complications_ok_wiz = len(recalculated_wiz_state.get('complications', [])) >= 2

    if not final_errors_wiz and pp_ok_wiz and complications_ok_wiz:
        st_obj.success("Character is valid and ready!")
        if st_obj.button("🎉 Finish Character & Go to Full Character Sheet", type="primary", key=_uk_wiz("finish_wizard_final_btn")):
            finish_wizard_func() 
            st_obj.rerun() 
    else:
        st_obj.error("Please resolve issues before finishing:")
        if not pp_ok_wiz:
            st_obj.warning(f"Power Points issue: Spent {recalculated_wiz_state.get('spentPowerPoints')} / Available {recalculated_wiz_state.get('totalPowerPoints')}")
        if not complications_ok_wiz:
            st_obj.warning(f"You need at least 2 complications (currently {len(recalculated_wiz_state.get('complications', []))}).")
        for err_wiz in final_errors_wiz: st_obj.warning(f"- {err_wiz}")

