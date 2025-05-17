# heroforge-mm-streamlit/ui_sections/wizard_steps.py

import streamlit as st
import copy
from typing import Dict, List, Any, Callable

if TYPE_CHECKING: # To avoid circular import issues for type hints if CoreEngine is also complex
    from core_engine import CoreEngine, CharacterState, RuleData # type: ignore
else: # Fallback for runtime if type checking context isn't perfect
    CoreEngine = Any
    CharacterState = Dict[str, Any]
    RuleData = Dict[str, Any]


# --- Helper for Wizard ---
def _wizard_header(step_number: int, max_steps: int, title: str):
    st.subheader(f"Step {step_number}: {title}")
    st.progress(step_number / max_steps)
    st.markdown("---")

# --- Step 1: Basics ---
def render_wizard_step1_basics(
    st_obj: Any, # streamlit object
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(1, 6, "The Basics - Name, Concept, Power Level")
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
        key="wiz_char_name"
    )
    if new_name != char_state.get('name', 'My Hero'):
        update_char_value_wiz(['name'], new_name)

    new_concept = st_obj.text_area(
        "Brief Concept/Origin:", 
        value=char_state.get('concept', ''), 
        key="wiz_char_concept",
        help="A few words about your hero (e.g., 'Alien powerhouse from a dying world', 'Mutated teen acrobat', 'Mystic guardian of ancient lore')."
    )
    if new_concept != char_state.get('concept', ''):
        update_char_value_wiz(['concept'], new_concept)

    current_pl = char_state.get('powerLevel', 10)
    new_pl = st_obj.slider(
        "Select Power Level (PL):", 
        min_value=1, max_value=20, value=current_pl, 
        key="wiz_char_pl",
        help=f"This sets your starting Power Points (PP). Current: {current_pl * 15} PP."
    )
    if new_pl != current_pl:
        update_char_value_wiz(['powerLevel'], new_pl)
        update_char_value_wiz(['totalPowerPoints'], new_pl * 15) # Recalculates state

    st_obj.info(f"Selected PL: {char_state.get('powerLevel')}. Starting Power Points: {char_state.get('totalPowerPoints')}")


# --- Step 2: Archetype ---
def render_wizard_step2_archetype(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine, # Engine needed to apply template
    apply_archetype_to_wizard_state: Callable[[str], None] # Callback from app.py
):
    _wizard_header(2, 6, "Choose an Archetype (Optional)")
    with st_obj.expander("ℹ️ What are Archetypes?", expanded=False):
        st_obj.markdown("""
            Archetypes are common superhero templates (like a strong 'Brick', a fast 'Speedster', or an 'Energy Projector').
            Selecting one gives you a pre-filled starting point with relevant abilities, skills, and a few core powers.
            It's a great way to get started quickly! You can customize everything afterwards in Advanced Mode.
            Or, choose 'Start from Scratch' for full control from the beginning.
        """)

    archetype_rules = rule_data.get('archetypes', [])
    arch_options = {"": "Start from Scratch / Custom Build"}
    for arch in archetype_rules:
        arch_options[arch['id']] = f"{arch['name']} - {arch.get('description', '')}"

    selected_arch_id = st_obj.selectbox(
        "Select Archetype:", 
        options=list(arch_options.keys()), 
        format_func=lambda x: arch_options[x],
        key="wiz_arch_select"
    )

    if st_obj.button("Apply Archetype & Continue", key="wiz_apply_arch_btn"):
        if selected_arch_id:
            apply_archetype_to_wizard_state(selected_arch_id) # This function in app.py will update wizard_char_state
            st_obj.success(f"Applied {arch_options[selected_arch_id].split(' - ')[0]} template! Review in next steps or click 'Next'.")
        else:
            st_obj.info("Continuing with a custom build (no archetype selected). Click 'Next'.")
        # No st.rerun() here, rely on main wizard nav to move and refresh


# --- Step 3: Abilities (Guided) ---
def render_wizard_step3_abilities_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(3, 6, "Core Abilities")
    with st_obj.expander("ℹ️ Understanding Abilities (Cost: 2 PP per Rank)", expanded=True): # Expanded by default for this step
        st_obj.markdown("""
            Abilities are your hero's eight core natural talents and training levels (0 is human average). They affect almost everything!
            * **STR (Strength):** Physical might, melee damage, lifting.
            * **STA (Stamina):** Health, resilience, base Toughness & Fortitude defenses.
            * **AGL (Agility):** Coordination, balance, base Dodge defense, Initiative, Stealth & Acrobatics.
            * **DEX (Dexterity):** Hand-eye coordination, base Ranged attack bonus, Vehicles & Sleight of Hand.
            * **FGT (Fighting):** Close combat skill, base Parry defense.
            * **INT (Intellect):** Reason, learning, Technology, Investigation & Expertise skills.
            * **AWE (Awareness):** Perception, intuition, base Will defense, Insight & Perception skills.
            * **PRE (Presence):** Force of personality, leadership, Deception, Intimidation & Persuasion.
            Adjust these based on your hero concept and archetype (if chosen).
        """)

    ability_rules = rule_data.get('abilities', [])
    current_abilities = char_state.get('abilities', {})
    
    # Suggestion presets (could be more complex)
    if st_obj.button("Suggest Balanced Spread (All 0s)", key="wiz_ab_balanced"):
        for ab_info in ability_rules: update_char_value_wiz(['abilities', ab_info['id']], 0)
        st_obj.rerun()
    # Add more suggestion buttons if desired (e.g., "Brick-like", "Mentalist-like")

    cols = st_obj.columns(4)
    for i, ab_info in enumerate(ability_rules):
        ab_id = ab_info['id']
        ab_name = ab_info['name']
        ab_desc = ab_info.get('description', '')
        current_rank = current_abilities.get(ab_id, 0)
        
        with cols[i % len(cols)]:
            new_rank = st_obj.number_input(
                f"{ab_name} ({ab_id})", min_value=-5, max_value=20, # Max for PL10 is effectively lower due to PP
                value=current_rank, key=f"wiz_ab_input_{ab_id}", help=ab_desc,
                step=1
            )
            if new_rank != current_rank:
                update_char_value_wiz(['abilities', ab_id], new_rank)
                st_obj.rerun() # Update PP immediately
            
            cost = new_rank * engine.rule_data.get('abilities',{}).get('costFactor',2)
            mod = engine.get_ability_modifier(new_rank)
            st_obj.caption(f"Mod: {mod:+}, Cost: {cost} PP")

# --- Step 4: Defenses & Key Skills (Guided) ---
def render_wizard_step4_defskills_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None]
):
    _wizard_header(4, 6, "Defenses & Key Skills")
    
    # Guided Defenses
    with st_obj.expander("🛡️ Understanding Defenses (Cost: 1 PP per +1 Bought Rank)", expanded=True):
        st_obj.markdown("""
            Defenses protect your hero. They get a base value from Abilities and can be increased by buying ranks.
            * **Dodge (AGL):** Avoids ranged/area attacks.
            * **Parry (FGT):** Avoids close attacks.
            * **Toughness (STA):** Resists damage. (Can also come from powers like Protection).
            * **Fortitude (STA):** Resists effects on health (poison, disease).
            * **Will (AWE):** Resists mental effects.
            **PL Caps are CRITICAL:**
            * `Dodge + Toughness` total cannot exceed `PL x 2`.
            * `Parry + Toughness` total cannot exceed `PL x 2`.
            * `Fortitude + Will` total cannot exceed `PL x 2`.
            Aim to reach these caps for a survivable hero!
        """)
    
    pl = char_state.get('powerLevel', 10)
    pl_cap_paired = pl * 2
    current_defenses = char_state.get('defenses', {})
    current_abilities = char_state.get('abilities', {})

    defense_configs_wiz = [
        {"id": "Dodge", "base_ability_id": "AGL", "tooltip": "Helps avoid ranged attacks."},
        {"id": "Parry", "base_ability_id": "FGT", "tooltip": "Helps avoid close attacks."},
        {"id": "Toughness", "base_ability_id": "STA", "tooltip": "Reduces damage taken. Can also be increased by powers."},
        {"id": "Fortitude", "base_ability_id": "STA", "tooltip": "Resists sickness, poison, fatigue."},
        {"id": "Will", "base_ability_id": "AWE", "tooltip": "Resists mental control, illusions, etc."}
    ]
    
    def_cols = st_obj.columns(len(defense_configs_wiz))
    for i, d_conf in enumerate(defense_configs_wiz):
        with def_cols[i]:
            base_val = engine.get_ability_modifier(current_abilities.get(d_conf['base_ability_id'], 0))
            bought_val = current_defenses.get(d_conf['id'], 0)
            total_val_disp = base_val + bought_val
            
            new_bought_val = st_obj.number_input(
                f"Buy {d_conf['id']}", min_value=0, max_value=pl + 10, # Generous max for bought ranks
                value=bought_val, key=f"wiz_def_input_{d_conf['id']}",
                help=f"{d_conf['tooltip']} Base from {d_conf['base_ability_id']}: {base_val}. Current Total: {total_val_disp}"
            )
            if new_bought_val != bought_val:
                update_char_value_wiz(['defenses', d_conf['id']], new_bought_val)
                st_obj.rerun()
            st_obj.caption(f"Total: {total_val_disp} (Cost: {new_bought_val} PP)")

    # Display PL Cap status
    st_obj.markdown("**Defense Cap Check:**")
    # ... (PL Cap display logic from app.py sidebar, using wizard_char_state) ...
    # This part reuses the logic that would be in render_sidebar or a helper
    total_dodge_wiz = engine.get_total_defense(char_state, 'Dodge', 'AGL')
    total_parry_wiz = engine.get_total_defense(char_state, 'Parry', 'FGT')
    total_toughness_wiz = engine.get_total_defense(char_state, 'Toughness', 'STA')
    total_fortitude_wiz = engine.get_total_defense(char_state, 'Fortitude', 'STA')
    total_will_wiz = engine.get_total_defense(char_state, 'Will', 'AWE')

    dt_sum = total_dodge_wiz + total_toughness_wiz
    pt_sum = total_parry_wiz + total_toughness_wiz
    fw_sum = total_fortitude_wiz + total_will_wiz
    st_obj.markdown(f"- Dodge ({total_dodge_wiz}) + Toughness ({total_toughness_wiz}) = **{dt_sum}** / {pl_cap_paired} {'✅' if dt_sum <= pl_cap_paired else '⚠️ Exceeded!'}")
    st_obj.markdown(f"- Parry ({total_parry_wiz}) + Toughness ({total_toughness_wiz}) = **{pt_sum}** / {pl_cap_paired} {'✅' if pt_sum <= pl_cap_paired else '⚠️ Exceeded!'}")
    st_obj.markdown(f"- Fortitude ({total_fortitude_wiz}) + Will ({total_will_wiz}) = **{fw_sum}** / {pl_cap_paired} {'✅' if fw_sum <= pl_cap_paired else '⚠️ Exceeded!'}")


    # Guided Skills
    st_obj.markdown("---")
    with st_obj.expander("🎯 Understanding Skills (Cost: 1 PP per 2 Ranks)", expanded=True):
        st_obj.markdown("""
            Skills represent specific training. Your **Total Skill Bonus** = `Governing Ability Modifier + Ranks Bought`.
            This Total Bonus cannot exceed `Power Level + 10`.
            Consider skills matching your hero's concept. **Perception** is useful for everyone!
            Combat skills like **Close Combat: Unarmed** or **Ranged Combat: Energy Blasts** improve your chance to hit.
        """)

    skill_rules = rule_data.get('skills', [])
    current_skills_wiz = char_state.get('skills', {})
    # Archetype might have pre-filled some skills. Wizard presents a few key ones.
    # For V1 wizard, let's suggest a small, curated list of common skills.
    # More advanced: dynamically suggest based on archetype or high abilities.
    key_skill_ids_for_wizard = ["Athletics", "Perception", "Stealth", "Persuasion", "Close Combat: Unarmed", "Ranged Combat: General"] # User can rename "General"

    skill_cols = st_obj.columns(3)
    for i, skill_id_wiz in enumerate(key_skill_ids_for_wizard):
        skill_info_wiz = next((s for s in skill_rules if s['id'] == skill_id_wiz or s['name'] == skill_id_wiz), None)
        
        actual_skill_id_to_edit = skill_id_wiz
        skill_name_display = skill_id_wiz
        gov_ab_wiz = "N/A"

        if skill_info_wiz:
            actual_skill_id_to_edit = skill_info_wiz['id']
            skill_name_display = skill_info_wiz['name']
            gov_ab_wiz = skill_info_wiz['ability']
        elif skill_id_wiz == "Ranged Combat: General": # Allow specializing one Ranged Combat
            custom_rc_name_wiz = st_obj.text_input("Specialize Ranged Combat (e.g., Blasts)", value=current_skills_wiz.get("Ranged Combat: _custom_name", "Energy Blasts"), key="wiz_rc_custom_name")
            if custom_rc_name_wiz:
                actual_skill_id_to_edit = f"Ranged Combat: {custom_rc_name_wiz}"
                skill_name_display = actual_skill_id_to_edit
                # Store the custom name part if needed, or use the full string as ID
                # For simplicity, using full string as ID. `core_engine` must handle custom skill IDs if they don't match ruleData.
                # Or, assume skill_id in char_state is always from ruleData, and Ranged Combat: X is a param of the Ranged Combat skill.
                # For wizard simplicity, let's assume "Ranged Combat: General" maps to a generic "Ranged Combat" skill ID from ruleData, and the specialization is flavor for now.
                # OR, better, the wizard pre-selects a common specific ranged combat skill from the archetype, or asks user to name one.
                # For now, let's assume the "Ranged Combat: General" is a placeholder for one such skill.
                # A more robust wizard would have a selectbox of actual Ranged Combat skills or a text input to create one.
                # Let's go with user input for specialization
                if "Ranged Combat: _custom_name" in current_skills_wiz and custom_rc_name_wiz != current_skills_wiz.get("Ranged Combat: _custom_name"):
                    # Clear old custom skill if name changes
                    old_custom_skill_id = f"Ranged Combat: {current_skills_wiz.get('Ranged Combat: _custom_name')}"
                    current_skills_wiz.pop(old_custom_skill_id, None)
                current_skills_wiz["Ranged Combat: _custom_name"] = custom_rc_name_wiz # Store the name part
                gov_ab_wiz = "DEX" # Ranged Combat is DEX based
            else:
                continue # Skip if no custom name given for this slot


        with skill_cols[i % len(skill_cols)]:
            current_rank_wiz = current_skills_wiz.get(actual_skill_id_to_edit, 0)
            ability_mod_wiz = engine.get_ability_modifier(current_abilities.get(gov_ab_wiz, 0))
            total_bonus_wiz = ability_mod_wiz + current_rank_wiz
            skill_bonus_cap = pl + 10
            
            new_rank_wiz = st_obj.number_input(
                f"{skill_name_display} ({gov_ab_wiz})", 
                min_value=0, max_value=pl + 10, # Ranks bought, not total bonus
                value=current_rank_wiz, 
                key=f"wiz_skill_input_{actual_skill_id_to_edit.replace(':', '_').replace(' ','_')}",
                help=f"Total Bonus: {total_bonus_wiz:+}. Max Skill Bonus for PL{pl} is {skill_bonus_cap:+}"
            )
            if new_rank_wiz != current_rank_wiz:
                # If it's the custom named skill, update logic needs to be careful
                if skill_id_wiz == "Ranged Combat: General" and actual_skill_id_to_edit.startswith("Ranged Combat:"):
                    # Remove old entry if name part changed previously
                    old_name_part = current_skills_wiz.get("Ranged Combat: _custom_name_prev_val")
                    if old_name_part and old_name_part != custom_rc_name_wiz:
                         current_skills_wiz.pop(f"Ranged Combat: {old_name_part}", None)
                    
                    current_skills_wiz[actual_skill_id_to_edit] = new_rank_wiz
                    current_skills_wiz["Ranged Combat: _custom_name_prev_val"] = custom_rc_name_wiz # Track for next change
                else:
                    current_skills_wiz[actual_skill_id_to_edit] = new_rank_wiz

                update_char_value_wiz(['skills'], current_skills_wiz)
                st_obj.rerun()
            
            if total_bonus_wiz > skill_bonus_cap:
                st_obj.error(f"Bonus {total_bonus_wiz:+}, Cap {skill_bonus_cap:+}", icon="⚠️")


# --- Step 5: Guided Powers ---
def render_wizard_step5_powers_guided(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None],
    generate_unique_id_func: Callable[[],str] # Passed from app.py
):
    _wizard_header(5, 6, "Core Powers")
    with st_obj.expander("⚡ Understanding Powers (Wizard Focus)", expanded=True):
        st_obj.markdown("""
            Powers are your hero's main superhuman abilities (Flight, Energy Blasts, Super-Strength, etc.).
            They are built from **Effects** (the basic function), have a **Rank** (how strong), and can have **Modifiers** (Extras improve them for more PP, Flaws limit them for fewer PP).
            * **Cost:** Based on Effect, Rank, and Modifiers.
            * **PL Caps for Attacks:** If a power is an attack, its `Attack Bonus + Effect Rank` cannot exceed `Power Level (PL) x 2`.
            * **PL Caps for Area/Perception Effects:** If an effect hits an area or works by perception (no attack roll), its `Effect Rank` cannot exceed `PL`.
            For this wizard, we'll focus on adding a few common, pre-defined powers. You can build highly custom powers in Advanced Mode later!
        """)

    current_powers_wiz = char_state.get('powers', [])
    st_obj.markdown("**Current Powers:**")
    if not current_powers_wiz: st_obj.caption("None yet.")
    for idx, pwr in enumerate(current_powers_wiz):
        # Allow removing archetype/wizard-added powers
        p_cols = st_obj.columns([0.7, 0.2, 0.1])
        p_cols[0].markdown(f"**{pwr.get('name', 'Unnamed')}** (Rank {pwr.get('rank',0)})")
        p_cols[1].caption(f"{pwr.get('cost',0)} PP")
        if p_cols[2].button("➖", key=f"wiz_pwr_del_btn_{pwr.get('id', idx)}", help="Remove Power"):
            new_powers_list = [p for p in current_powers_wiz if p.get('id') != pwr.get('id')]
            update_char_value_wiz(['powers'], new_powers_list)
            st_obj.rerun()
        
        # Display measurement details if available
        measurement_display = pwr.get('measurement_details_display') # Engine should populate this
        if measurement_display: st_obj.caption(f"└─ {measurement_display}")


    st_obj.markdown("---")
    st_obj.markdown("**Add a Common Power:** (Max 2-3 suggested for Wizard)")
    
    if len(current_powers_wiz) >= (char_state.get('powerLevel',10) / 4) + 2 : # Heuristic limit for wizard
        st_obj.info("You've selected a good number of core powers for the wizard! More can be added in Advanced Mode.")
    else:
        prebuilt_power_rules = [pbr for pbr in rule_data.get('prebuilt_powers_v1', []) if pbr.get('wizard_pickable', True)]
        common_power_options = {"": "Select a common power type..."}
        for pbr in prebuilt_power_rules:
            cost_str = f"{pbr.get('cost_per_rank_base', pbr.get('fixed_cost',0))}{'/rank' if pbr.get('cost_per_rank_base') else ' pts'}"
            common_power_options[pbr['id']] = f"{pbr['name']} ({cost_str})"
        
        selected_prebuilt_id_wiz = st_obj.selectbox("Common Powers:", options=list(common_power_options.keys()), format_func=lambda x: common_power_options[x], key="wiz_pwr_select_final_step5")
        
        if selected_prebuilt_id_wiz:
            chosen_prebuilt_rule = next((pbr for pbr in prebuilt_power_rules if pbr['id'] == selected_prebuilt_id_wiz), None)
            if chosen_prebuilt_rule:
                default_rank_wiz = max(1, min(char_state.get('powerLevel', 10), chosen_prebuilt_rule.get('defaultRank',5)))
                
                with st_obj.form(key=f"wiz_add_pwr_form_{selected_prebuilt_id_wiz}"):
                    st_obj.markdown(f"**Configuring: {chosen_prebuilt_rule.get('name')}**")
                    st_obj.caption(chosen_prebuilt_rule.get('description',''))

                    power_name_wiz_val = st_obj.text_input("Name this power:", value=chosen_prebuilt_rule.get('name'), key=f"wiz_pwr_name_cfg_{selected_prebuilt_id_wiz}")
                    power_rank_wiz_val = st_obj.number_input(
                        "Set Power Rank:", min_value=1, 
                        max_value=char_state.get('powerLevel', 20), # Rank can be up to PL for some effects
                        value=default_rank_wiz, key=f"wiz_pwr_rank_cfg_{selected_prebuilt_id_wiz}"
                    )
                    # For Wizard, don't offer modifier changes on pre-builts to keep it simple.
                    # Advanced mode is for that.

                    submitted_wiz_pwr = st_obj.form_submit_button("Add This Power")
                    if submitted_wiz_pwr:
                        # Construct the power using full definition from prebuilt_powers_v1.json
                        new_power_entry = copy.deepcopy(chosen_prebuilt_rule) 
                        new_power_entry['id'] = generate_unique_id_func() # Use passed in ID generator
                        new_power_entry['name'] = power_name_wiz_val
                        new_power_entry['rank'] = power_rank_wiz_val
                        # Cost will be recalculated by engine based on its full definition including internal modifiersConfig
                        
                        current_powers_wiz.append(new_power_entry)
                        update_char_value_wiz(['powers'], current_powers_wiz)
                        st_obj.success(f"Added {power_name_wiz_val}!")
                        st_obj.rerun()

# --- Step 6: Complications & Review ---
def render_wizard_step6_complreview_final(
    st_obj: Any,
    char_state: CharacterState,
    rule_data: RuleData,
    engine: CoreEngine,
    update_char_value_wiz: Callable[[List[str], Any], None],
    finish_wizard_func: Callable[[], None] # Passed from app.py
):
    _wizard_header(6, 6, "Complications & Final Review")
    with st_obj.expander("ℹ️ Why Complications?", expanded=True):
        st_obj.markdown("""
            Complications are problems, weaknesses, or responsibilities that make your hero's life interesting (e.g., Secret Identity, Enemy, Weakness to Kryptonite, Responsibility to protect the city).
            They don't cost Power Points. Instead, when your Complications cause trouble during the game, your Gamemaster (GM) awards you **Hero Points!**
            Hero Points are valuable – they let you re-roll dice, recover quickly, edit a scene, or perform amazing power stunts.
            You need at least **two** Complications for a complete character.
        """)

    current_complications_wiz = char_state.get('complications', []) # List of {'description': str}
    
    # Display existing complications with delete option
    if current_complications_wiz:
        st_obj.markdown("**Your Complications:**")
    for i, comp_entry in enumerate(current_complications_wiz):
        c_cols = st_obj.columns([0.9, 0.1])
        c_cols[0].text_input(f"Complication #{i+1}", value=comp_entry.get('description',''), 
                             key=f"wiz_comp_text_{i}",
                             on_change=lambda i=i: update_char_value_wiz(['complications', i, 'description'], st_obj.session_state[f"wiz_comp_text_{i}"]))
        if c_cols[1].button("🗑️", key=f"wiz_comp_del_{i}", help="Remove Complication"):
            current_complications_wiz.pop(i)
            update_char_value_wiz(['complications'], current_complications_wiz)
            st_obj.rerun()

    # Add new complication
    new_comp_text_wiz = st_obj.text_input("Add New Complication Description:", key="wiz_new_comp_desc_input")
    if st_obj.button("Add Complication", key="wiz_add_comp_button") and new_comp_text_wiz.strip():
        current_complications_wiz.append({'description': new_comp_text_wiz.strip()})
        update_char_value_wiz(['complications'], current_complications_wiz)
        st_obj.rerun()
    
    st_obj.caption(f"Number of Complications: {len(current_complications_wiz)}. Minimum 2 required.")
    st_obj.markdown("---")

    # Final Review Summary
    st_obj.markdown("**Final Review:**")
    recalculated_wiz_state = engine.recalculate(char_state) # Ensure it's fully up-to-date
    st_obj.session_state.wizard_character_state = recalculated_wiz_state # Update state for display

    st_obj.info(f"**Name:** {recalculated_wiz_state.get('name')} | **PL:** {recalculated_wiz_state.get('powerLevel')} | **PP:** {recalculated_wiz_state.get('spentPowerPoints')} / {recalculated_wiz_state.get('totalPowerPoints')}")
    
    with st_obj.expander("Quick Stats Overview (Full details in Advanced Mode)", expanded=False):
        st_obj.write("Abilities:", recalculated_wiz_state.get('abilities'))
        # Display simple lists of Defenses (totals), Skills (>0 ranks), Advantages, Powers (name/rank)
        # ... (this can be a simplified loop or call to a mini-sheet display helper) ...

    st_obj.markdown("---")
    final_errors_wiz = recalculated_wiz_state.get('validationErrors', [])
    pp_ok_wiz = recalculated_wiz_state.get('spentPowerPoints', 0) <= recalculated_wiz_state.get('totalPowerPoints', 0)
    complications_ok_wiz = len(recalculated_wiz_state.get('complications', [])) >= 2

    if not final_errors_wiz and pp_ok_wiz and complications_ok_wiz:
        st_obj.success("Character is valid and ready!")
        if st_obj.button("🎉 Finish Character & Go to Full Character Sheet", type="primary", key="finish_wizard_final_btn"):
            finish_wizard_func() # This callback in app.py handles state transfer and mode switch
            st_obj.rerun() # Ensure app.py reruns in the new mode
    else:
        st_obj.error("Please resolve issues before finishing:")
        if not pp_ok_wiz:
            st_obj.warning(f"Power Points issue: {recalculated_wiz_state.get('spentPowerPoints')} / {recalculated_wiz_state.get('totalPowerPoints')}")
        if not complications_ok_wiz:
            st_obj.warning(f"You need at least 2 complications (currently {len(recalculated_wiz_state.get('complications', []))}).")
        for err_wiz in final_errors_wiz: st_obj.warning(f"- {err_wiz}")