# app.py for HeroForge M&M (Streamlit Edition)
# Version: V1.0 "All Features" Fully Developed

import streamlit as st
import json
import copy
import math
import os
import uuid # For unique IDs
from typing import Dict, List, Any, Optional, Callable

# --- Core Application Logic and Data ---
# Ensure these type hints are available if your core_engine defines them clearly
from core_engine import CoreEngine, CharacterState, PowerDefinition, AdvantageDefinition, EquipmentDefinition, HQDefinition, VehicleDefinition, AllyDefinition
from pdf_utils import generate_pdf_bytes 

# --- UI Section Imports ---
# These imports assume your project structure has ui_sections at the same level as app.py,
# or your PYTHONPATH is set up accordingly. If app.py is in the root and ui_sections is a subdir,
# the imports would be like: from ui_sections.wizard_steps import ...
from ui_sections.wizard_steps import (
    render_wizard_step1_basics,
    render_wizard_step2_archetype,
    render_wizard_step3_abilities_guided,
    render_wizard_step4_defskills_guided,
    render_wizard_step5_powers_guided,
    render_wizard_step6_complreview_final
)
from ui_sections.advanced_mode_ui import (
    render_selected_advanced_view,
    DEFAULT_ADVANTAGE_EDITOR_CONFIG, 
    DEFAULT_EQUIPMENT_EDITOR_CONFIG,
    DEFAULT_HQ_EDITOR_CONFIG,
    DEFAULT_VEHICLE_EDITOR_CONFIG,
    DEFAULT_ALLY_EDITOR_CONFIG
)
from ui_sections.power_builder_ui import get_default_power_form_state 

# --- Page Configuration (do this first) ---
st.set_page_config(
    page_title="HeroForge M&M",
    page_icon="assets/icon.png", # Create this image file in assets/
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.d20herosrd.com/mutants-masterminds-3e-srd/', # Link to M&M SRD
        'Report a bug': "https://github.com/your_username/your_project_repo/issues", # Replace with your repo
        'About': "# HeroForge M&M Character Creator\nThis is a tool to help create characters for Mutants & Masterminds 3rd Edition."
    }
)

# --- Initialize Core Engine & Rule Data (Cached) ---
@st.cache_resource # Cache the engine instance and rule_data for the session
def load_core_resources():
    """Loads the CoreEngine and its rule data. Stops app on critical failure."""
    print("Loading Core Engine and Rule Data...")
    try:
        engine_instance = CoreEngine(rule_dir="rules")
        # CoreEngine now loads all rule files internally. Access via engine_instance.rule_data
        if not engine_instance.rule_data or not all(k in engine_instance.rule_data for k in [
            'abilities', 'skills', 'advantages_v1', 'power_effects', 
            'power_modifiers', 'power_senses_config', 'power_immunities_config',
            'equipment_items', 'hq_features', 'vehicle_features', 
            'vehicle_size_stats', 'archetypes', 'measurements_table'
            # Add 'prebuilt_powers_v1' if your archetypes rely on it and it's loaded by CoreEngine
        ]):
            st.error("Fatal Error: Core rule data files are missing or incomplete. Ensure all JSON files are present in the 'rules' directory and loaded by CoreEngine. Application cannot proceed.")
            st.stop()
        
        print("Core Engine and Rule Data loaded successfully.")
        return engine_instance, engine_instance.rule_data 
    except Exception as e:
        st.error(f"Fatal Error initializing Core Engine: {e}. Check console and 'rules' directory structure/content.")
        st.stop()

engine, rule_data_app = load_core_resources() 

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes all necessary session state variables if they don't exist."""
    default_char_state = engine.get_default_character_state()

    if 'character' not in st.session_state:
        st.session_state.character = copy.deepcopy(default_char_state)
    else: 
        for key, value in default_char_state.items():
            if key not in st.session_state.character:
                st.session_state.character[key] = copy.deepcopy(value)

    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'Abilities' 
    
    if 'in_wizard_mode' not in st.session_state:
        st.session_state.in_wizard_mode = True 
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
    if 'wizard_character_state' not in st.session_state:
        st.session_state.wizard_character_state = copy.deepcopy(default_char_state)
    else: 
        for key, value in default_char_state.items():
            if key not in st.session_state.wizard_character_state:
                st.session_state.wizard_character_state[key] = copy.deepcopy(value)

    # Editor/Form States for Advanced Mode
    if 'power_form_state' not in st.session_state:
        st.session_state.power_form_state = get_default_power_form_state(rule_data_app)
    if 'show_power_builder_form' not in st.session_state: 
        st.session_state.show_power_builder_form = False

    if 'advantage_editor_config' not in st.session_state:
        st.session_state.advantage_editor_config = copy.deepcopy(DEFAULT_ADVANTAGE_EDITOR_CONFIG)
    if 'equipment_editor_config' not in st.session_state:
        st.session_state.equipment_editor_config = copy.deepcopy(DEFAULT_EQUIPMENT_EDITOR_CONFIG)
    if 'hq_form_state' not in st.session_state: 
        st.session_state.hq_form_state = copy.deepcopy(DEFAULT_HQ_EDITOR_CONFIG)
    if 'vehicle_form_state' not in st.session_state: 
        st.session_state.vehicle_form_state = copy.deepcopy(DEFAULT_VEHICLE_EDITOR_CONFIG)
    if 'ally_editor_config' not in st.session_state:
        st.session_state.ally_editor_config = copy.deepcopy(DEFAULT_ALLY_EDITOR_CONFIG)

initialize_session_state() 

# --- Helper Functions ---
def generate_unique_id(prefix="item_"):
    """Generates a unique ID string with a given prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"

def update_char_value(key_path: List[str], value: Any, target_state_key: str = 'character', do_recalc: bool = True):
    """
    Updates a value in the character state dictionary and optionally triggers recalculation.
    """
    if target_state_key not in st.session_state:
        st.error(f"Target state key '{target_state_key}' not found in session state.")
        return

    char_obj_ref = st.session_state[target_state_key]
    current_level = char_obj_ref
    try:
        for i, k_part in enumerate(key_path):
            if i == len(key_path) - 1:
                current_level[k_part] = value
            else:
                if not isinstance(current_level.get(k_part), dict):
                    current_level[k_part] = {} # Ensure path exists
                current_level = current_level[k_part]
    except TypeError as e:
        st.error(f"Error updating character state at path {key_path}: {e}. Current level was not a dictionary.")
        return
    
    if do_recalc:
        st.session_state[target_state_key] = engine.recalculate(char_obj_ref)

# --- Wizard Mode Callbacks ---
def update_char_value_wiz(key_path: List[str], value: Any, do_recalc: bool = True):
    update_char_value(key_path, value, target_state_key='wizard_character_state', do_recalc=do_recalc)

def apply_archetype_to_wizard_state_callback(archetype_id: str):
    if not archetype_id: # "Start from Scratch" selected
        current_pl = st.session_state.wizard_character_state.get('powerLevel', 10)
        # Preserve name, concept, PL if user entered them before choosing scratch
        name = st.session_state.wizard_character_state.get('name', 'New Hero')
        concept = st.session_state.wizard_character_state.get('concept', '')
        st.session_state.wizard_character_state = engine.get_default_character_state(pl=current_pl)
        st.session_state.wizard_character_state['name'] = name
        st.session_state.wizard_character_state['concept'] = concept
        st.session_state.wizard_character_state = engine.recalculate(st.session_state.wizard_character_state)

    else:
        archetype_rule = next((arch for arch in rule_data_app.get('archetypes', []) if arch['id'] == archetype_id), None)
        if not archetype_rule: 
            st.error(f"Archetype '{archetype_id}' not found.")
            return

        current_pl = st.session_state.wizard_character_state.get('powerLevel', 10)
        new_state = engine.get_default_character_state(pl=current_pl)
        
        new_state['name'] = st.session_state.wizard_character_state.get('name', archetype_rule.get('name', 'Hero'))
        new_state['concept'] = st.session_state.wizard_character_state.get('concept', archetype_rule.get('description', ''))
        
        template = archetype_rule.get('template', {})
        new_state['abilities'].update(template.get('abilities', {}))
        new_state['defenses'].update(template.get('defenses', {}))
        
        base_skill_rules_list = rule_data_app.get('skills',{}).get('list',[])
        for skill_id_template, rank in template.get('skills', {}).items():
            # Check if it's a base skill or a known specialized skill pattern
            is_valid_skill = False
            base_skill_of_template = None
            for base_skill_def in base_skill_rules_list:
                if skill_id_template == base_skill_def['id'] or \
                   (base_skill_def.get('specialization_possible') and skill_id_template.startswith(base_skill_def['id'] + "_")):
                    is_valid_skill = True
                    base_skill_of_template = base_skill_def
                    break
            if is_valid_skill:
                 new_state['skills'][skill_id_template] = rank
            else:
                st.warning(f"Skill '{skill_id_template}' from archetype not directly mapped. Ensure it's a valid base or specialized skill ID.")

        new_state['advantages'] = copy.deepcopy(template.get('advantages', []))
        for adv in new_state['advantages']:
            if 'instance_id' not in adv: # Ensure unique instance ID for each advantage
                adv['instance_id'] = generate_unique_id(f"adv_{adv.get('id','unknown')}_arch_")

        template_powers = template.get('powers', [])
        constructed_powers = []
        archetype_power_id_map: Dict[str, str] = {}

        for p_template in template_powers:
            new_power_instance_id = generate_unique_id("pwr_arch_")
            if p_template.get('id'): 
                archetype_power_id_map[p_template['id']] = new_power_instance_id

            power_entry: PowerDefinition = {
                'id': new_power_instance_id,
                'name': p_template.get('name', 'Archetype Power'),
                'baseEffectId': p_template.get('baseEffectId'),
                'rank': p_template.get('rank', 1),
                'descriptors': p_template.get('descriptors', ''),
                'modifiersConfig': copy.deepcopy(p_template.get('modifiersConfig', [])),
                'sensesConfig': copy.deepcopy(p_template.get('sensesConfig', [])),
                'immunityConfig': copy.deepcopy(p_template.get('immunityConfig', [])),
                'powerSpecificData': copy.deepcopy(p_template.get('powerSpecificData', {})), # For Affliction degrees etc.
                'linkedCombatSkill': p_template.get('linkedCombatSkill'),
                'arrayId': p_template.get('arrayId'),
                'isArrayBase': p_template.get('isArrayBase', False),
                'isAlternateEffectOf': None 
            }
            for mod_conf in power_entry['modifiersConfig']:
                if 'instance_id' not in mod_conf:
                    mod_conf['instance_id'] = generate_unique_id("mod_arch_")
            constructed_powers.append(power_entry)

        for pwr in constructed_powers: # Resolve AE links
            template_ae_base_id = next((pt['isAlternateEffectOf'] for pt_idx, pt in enumerate(template_powers) if archetype_power_id_map.get(pt.get('id',''),f"none_{pt_idx}") == pwr['id'] and pt.get('isAlternateEffectOf')), None)
            if template_ae_base_id and template_ae_base_id in archetype_power_id_map:
                pwr['isAlternateEffectOf'] = archetype_power_id_map[template_ae_base_id]
        
        new_state['powers'] = constructed_powers
        st.session_state.wizard_character_state = engine.recalculate(new_state)
    st.rerun()

def finish_wizard_callback():
    st.session_state.character = copy.deepcopy(st.session_state.wizard_character_state)
    st.session_state.character = engine.recalculate(st.session_state.character)
    st.session_state.in_wizard_mode = False
    st.session_state.current_view = 'Character Sheet' 
    st.session_state.wizard_character_state = engine.get_default_character_state(st.session_state.character.get('powerLevel',10))
    st.session_state.wizard_step = 1
    st.success("Character created! Switched to Advanced Mode.")
    st.rerun()

# --- Sidebar Rendering ---
def render_sidebar():
    with st.sidebar:
        st.title("HeroForge M&M")
        st.caption(f"v1.0 - M&M 3e Character Creator")
        st.markdown("---")

        active_char_state_key = 'wizard_character_state' if st.session_state.in_wizard_mode else 'character'
        active_char_state = st.session_state[active_char_state_key]

        st.header("Character Info")
        st.markdown(f"**Name:** {active_char_state.get('name', 'N/A')}")
        st.markdown(f"**PL:** {active_char_state.get('powerLevel', 0)}")
        st.markdown(f"**PP:** {active_char_state.get('spentPowerPoints',0)} / {active_char_state.get('totalPowerPoints',0)}")
        
        remaining_pp = active_char_state.get('totalPowerPoints',0) - active_char_state.get('spentPowerPoints',0)
        pp_color = "error" if remaining_pp < 0 else "success"
        st.markdown(f"<span style='color:{'red' if pp_color=='error' else 'green'};'>Remaining PP: {remaining_pp}</span>", unsafe_allow_html=True)
        st.markdown("---")

        if st.session_state.in_wizard_mode:
            st.subheader("Wizard Navigation")
            max_steps = 6
            cols_wiz_nav = st.columns(2)
            if cols_wiz_nav[0].button("⬅️ Previous", disabled=(st.session_state.wizard_step <= 1), use_container_width=True, key="wiz_prev_btn"):
                st.session_state.wizard_step -= 1; st.rerun()
            if cols_wiz_nav[1].button("Next ➡️", disabled=(st.session_state.wizard_step >= max_steps), use_container_width=True, key="wiz_next_btn"):
                st.session_state.wizard_step += 1; st.rerun()
            if st.button("Exit Wizard to Advanced Mode", key="exit_wizard_sidebar_btn", use_container_width=True):
                st.session_state.character = copy.deepcopy(st.session_state.wizard_character_state)
                st.session_state.character = engine.recalculate(st.session_state.character)
                st.session_state.in_wizard_mode = False
                st.session_state.current_view = 'Abilities'; st.rerun()
        else: 
            st.subheader("Advanced Sections")
            view_options = ["Abilities", "Defenses", "Skills", "Advantages", "Powers", "Equipment", "Headquarters", "Vehicles", "Companions (Allies)", "Complications", "Character Sheet", "Measurements Table"]
            current_view_adv = st.session_state.get('current_view', 'Abilities')
            if current_view_adv not in view_options: current_view_adv = 'Abilities'
            new_view = st.radio("Go to:", view_options, index=view_options.index(current_view_adv), key="adv_nav_radio_main")
            if new_view != current_view_adv:
                st.session_state.current_view = new_view; st.rerun()
            if st.button("✨ Start Character Wizard", key="start_wizard_btn_sidebar", use_container_width=True):
                st.session_state.wizard_character_state = engine.get_default_character_state(st.session_state.character.get('powerLevel',10))
                st.session_state.wizard_step = 1; st.session_state.in_wizard_mode = True; st.rerun()
        st.markdown("---")

        st.subheader("File Operations")
        if st.button("➕ New Character", key="new_char_sidebar_btn", use_container_width=True):
            default_pl = st.session_state.character.get('powerLevel', 10)
            st.session_state.character = engine.get_default_character_state(pl=default_pl)
            st.session_state.wizard_character_state = engine.get_default_character_state(pl=default_pl)
            st.session_state.power_form_state = get_default_power_form_state(rule_data_app)
            st.session_state.advantage_editor_config = copy.deepcopy(DEFAULT_ADVANTAGE_EDITOR_CONFIG)
            st.session_state.equipment_editor_config = copy.deepcopy(DEFAULT_EQUIPMENT_EDITOR_CONFIG)
            st.session_state.hq_form_state = copy.deepcopy(DEFAULT_HQ_EDITOR_CONFIG)
            st.session_state.vehicle_form_state = copy.deepcopy(DEFAULT_VEHICLE_EDITOR_CONFIG)
            st.session_state.ally_editor_config = copy.deepcopy(DEFAULT_ALLY_EDITOR_CONFIG)
            st.session_state.show_power_builder_form = False
            st.session_state.current_view = 'Abilities' if not st.session_state.in_wizard_mode else st.session_state.current_view
            st.session_state.wizard_step = 1 if st.session_state.in_wizard_mode else st.session_state.wizard_step
            st.success("New character started."); st.rerun()

        char_json_data = json.dumps(st.session_state.character, indent=4)
        char_name_for_file = "".join(c for c in st.session_state.character.get('name', 'M_M_Hero') if c.isalnum() or c in (' ', '_')).rstrip()
        st.download_button(label="💾 Save Character (JSON)", data=char_json_data, file_name=f"{char_name_for_file}.json", mime="application/json", key="save_char_json_sidebar_btn", use_container_width=True)

        uploaded_file = st.file_uploader("📂 Load Character (JSON)", type=["json"], key="load_char_json_sidebar_uploader")
        if uploaded_file is not None:
            try:
                loaded_data = json.load(uploaded_file)
                if 'powerLevel' in loaded_data and 'abilities' in loaded_data:
                    default_for_load = engine.get_default_character_state(loaded_data.get('powerLevel',10))
                    merged_char_state = default_for_load
                    merged_char_state.update(loaded_data) 
                    st.session_state.character = engine.recalculate(merged_char_state)
                    st.session_state.in_wizard_mode = False 
                    st.session_state.current_view = 'Character Sheet'
                    st.success(f"Character '{st.session_state.character.get('name')}' loaded successfully!"); st.rerun()
                else: st.error("Invalid character file format.")
            except Exception as e: st.error(f"Error loading character: {e}")
        
        if st.button("📄 Export to PDF", key="export_pdf_sidebar_btn", use_container_width=True):
            pdf_char_state = st.session_state.character # Use the main character state for PDF
            with st.spinner("Generating PDF..."):
                pdf_bytes = generate_pdf_bytes(pdf_char_state, rule_data_app, engine)
                if pdf_bytes:
                    st.download_button(label="📥 Download PDF Sheet", data=pdf_bytes, file_name=f"{pdf_char_state.get('name', 'M_M_Hero')}_Sheet.pdf", mime="application/pdf", key="download_pdf_final_sidebar_btn", use_container_width=True)
                    # st.success("PDF ready for download!") # Button itself is the call to action
                else: st.error("Failed to generate PDF.")
        st.markdown("---")

        st.subheader("Validation Status")
        validation_errors = active_char_state.get('validationErrors', [])
        if not validation_errors:
            st.success("✅ Character is Valid!")
        else:
            st.error(f"⚠️ {len(validation_errors)} Validation Issue(s) Found:")
            for err_idx, error_msg in enumerate(validation_errors):
                st.markdown(f"- {error_msg}", key=_uk("sidebar_validation_error_disp", err_idx)) # Unique key
        st.markdown("---")
        
        if st.button("🔄 Force Full Recalculate", key="force_recalc_sidebar_btn", use_container_width=True):
            st.session_state[active_char_state_key] = engine.recalculate(active_char_state)
            st.success("Character data recalculated."); st.rerun()

# --- Main Application Flow ---
def main():
    render_sidebar() 
    if st.session_state.in_wizard_mode:
        wizard_render_functions = {
            1: render_wizard_step1_basics, 2: render_wizard_step2_archetype,
            3: render_wizard_step3_abilities_guided, 4: render_wizard_step4_defskills_guided,
            5: render_wizard_step5_powers_guided, 6: render_wizard_step6_complreview_final
        }
        current_wizard_step_func = wizard_render_functions.get(st.session_state.wizard_step)
        if current_wizard_step_func:
            wizard_args = {
                "st_obj": st, "char_state": st.session_state.wizard_character_state,
                "rule_data": rule_data_app, "engine": engine,
                "update_char_value_wiz": update_char_value_wiz
            }
            if st.session_state.wizard_step == 2: wizard_args["apply_archetype_to_wizard_state"] = apply_archetype_to_wizard_state_callback
            if st.session_state.wizard_step == 5: wizard_args["generate_unique_id_func"] = generate_unique_id
            if st.session_state.wizard_step == 6: wizard_args["finish_wizard_func"] = finish_wizard_callback
            current_wizard_step_func(**wizard_args)
        else: st.error(f"Unknown wizard step: {st.session_state.wizard_step}")
    else: 
        render_selected_advanced_view(
            view_name=st.session_state.current_view, st_obj=st, 
            char_state=st.session_state.character, rule_data=rule_data_app, 
            engine=engine, update_char_value=update_char_value, 
            generate_id_func=generate_unique_id,
            power_form_state_ref=st.session_state.power_form_state,
            advantage_editor_config_ref=st.session_state.advantage_editor_config,
            equipment_editor_config_ref=st.session_state.equipment_editor_config,
            hq_form_state_ref=st.session_state.hq_form_state,
            vehicle_form_state_ref=st.session_state.vehicle_form_state,
            ally_editor_config_ref=st.session_state.ally_editor_config
        )

if __name__ == '__main__':
    main()
