# pdf_utils.py

import math
import os # For base_url in HTML object if needed for local assets
from io import BytesIO
from typing import Dict, List, Any, Optional, TYPE_CHECKING

# WeasyPrint is an optional import, only fail if generate_pdf_bytes is called
try:
    from weasyprint import HTML, CSS
    from weasyprint.fonts import FontConfiguration # For embedding fonts if needed
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WARNING: WeasyPrint library not found. PDF export will not be available.")
    if not TYPE_CHECKING:
        class HTML: # type: ignore
            def __init__(self, string=None, base_url=None, url_fetcher=None, media_type='screen'): pass
            def write_pdf(self, target=None, stylesheets=None, font_config=None, presentational_hints=True): return b""
        class CSS: # type: ignore
            def __init__(self, string=None, filename=None, font_config=None, base_url=None, media_type='screen'): pass
        class FontConfiguration: # type: ignore
            def __init__(self): pass


if TYPE_CHECKING:
    from core_engine import CoreEngine, CharacterState, RuleData, PowerDefinition, AdvantageDefinition, SkillRule, AllyDefinition, HQDefinition, VehicleDefinition


# --- HTML Generation Helper Functions ---

def _escape_html(text: Optional[Any]) -> str:
    """Basic HTML escaping for user-provided text."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def _format_params_for_pdf(params_dict: Optional[Dict[str, Any]], item_rule: Optional[Dict[str, Any]], rule_data: 'RuleData', engine: 'CoreEngine') -> str:
    """Helper to format a generic params dictionary for PDF display."""
    if not params_dict or not item_rule:
        return ""
    
    display_parts = []
    # Iterate through expected parameters based on item_rule if possible, or just all keys in params_dict
    # This example assumes params_dict keys are descriptive enough or item_rule guides formatting.
    
    # Specific handling for common parameter types based on how they are stored by UI
    if item_rule.get('parameter_type') == 'select_skill':
        skill_id = params_dict.get('skill_id')
        if skill_id:
            # Use engine's helper if available, or local lookup
            skill_name = engine.get_skill_name_by_id(skill_id, rule_data.get('skills',{}).get('list',[]))
            display_parts.append(f"Skill: {_escape_html(skill_name)}")
    elif item_rule.get('parameter_type') == 'select_from_options':
        selected_val = params_dict.get('selected_option')
        if selected_val:
            option_label = selected_val # Default to value
            for opt in item_rule.get('parameter_options',[]):
                if opt.get('value') == selected_val:
                    option_label = opt.get('label', selected_val)
                    break
            display_parts.append(_escape_html(option_label))
    elif item_rule.get('parameter_type') == 'list_string':
        list_key = item_rule.get('parameter_list_key', 'details_list')
        items = params_dict.get(list_key, [])
        if items:
            display_parts.append(", ".join(map(_escape_html, items)))
    else: # Generic fallback for other text/detail parameters
        for key, value in params_dict.items():
            if value: # Only display if there's a value
                # Attempt to make key more readable
                label = key.replace('_', ' ').title()
                if isinstance(value, list):
                    display_parts.append(f"{_escape_html(label)}: {', '.join(map(_escape_html, value))}")
                else:
                    display_parts.append(f"{_escape_html(label)}: {_escape_html(str(value))}")
    
    return "; ".join(display_parts)


def _format_modifier_for_pdf(mod_config: Dict[str, Any], all_mod_rules: List[Dict[str, Any]], char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine') -> str:
    """Formats a power modifier configuration for display in the PDF."""
    mod_rule = next((m for m in all_mod_rules if m['id'] == mod_config.get('id')), None)
    if not mod_rule:
        return _escape_html(mod_config.get('id', 'Unknown Modifier'))

    display_str = _escape_html(mod_rule['name'])
    
    # Display modifier's own rank if it's ranked (e.g., Accurate 2)
    mod_instance_rank = mod_config.get('rank', 1)
    if mod_rule.get('ranked') and mod_instance_rank > 1 : # Only show rank if > 1 for brevity
        display_str += f" {mod_instance_rank}"
    
    # Format parameters stored in mod_config['params']
    params_display = _format_params_for_pdf(mod_config.get('params'), mod_rule, rule_data, engine)
    if params_display:
        display_str += f": <span class='modifier-param'>{params_display}</span>"
            
    return display_str

def _generate_html_head(character_name: str) -> str:
    return f"""
    <head>
        <meta charset="UTF-8">
        <title>{_escape_html(character_name)} - M&M 3e Character Sheet</title>
        {/* CSS is injected by generate_pdf_bytes */}
    </head>
    """

def _generate_sheet_header_html(character_state: 'CharacterState') -> str:
    # ... (Content from previous version, assumed mostly complete) ...
    return f"""
    <header class="sheet-header">
        <div class="char-name">{_escape_html(character_state.get('name', 'Unnamed Hero'))}</div>
        <div class="grid-group"><span>Player:</span><span>{_escape_html(character_state.get('playerName', ''))}</span></div>
        <div class="grid-group"><span>Identity:</span><span>{_escape_html(character_state.get('identity', ''))}</span></div>
        <div class="grid-group"><span>Group:</span><span>{_escape_html(character_state.get('groupAffiliation', ''))}</span></div>
        <div class="grid-group"><span>Gender:</span><span>{_escape_html(character_state.get('gender', ''))}</span></div>
        <div class="grid-group"><span>Age:</span><span>{_escape_html(character_state.get('age', ''))}</span></div>
        <div class="grid-group"><span>Height:</span><span>{_escape_html(character_state.get('height', ''))}</span></div>
        <div class="grid-group"><span>Weight:</span><span>{_escape_html(character_state.get('weight', ''))}</span></div>
        <div class="grid-group"><span>Eyes:</span><span>{_escape_html(character_state.get('eyes', ''))}</span></div>
        <div class="grid-group"><span>Hair:</span><span>{_escape_html(character_state.get('hair', ''))}</span></div>
        <div class="grid-group"><span>PL:</span><span>{character_state.get('powerLevel', 10)}</span></div>
        <div class="grid-group"><span>PP:</span><span>{character_state.get('spentPowerPoints', 0)}/{character_state.get('totalPowerPoints', 150)}</span></div>
        <div class="concept-desc" style="grid-column: 1 / -1;">
            <p><strong>Concept:</strong> {_escape_html(character_state.get('concept', ''))}</p>
            <p><strong>Description:</strong> {_escape_html(character_state.get('description', ''))}</p>
        </div>
    </header>
    """

def _generate_abilities_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    # ... (Content from previous version, assumed mostly complete) ...
    abilities = character_state.get('abilities', {})
    ability_rules_list = rule_data.get('abilities', {}).get('list', [])
    html = """<div class="section abilities-section"><h3 class="section-title">Abilities</h3><div class="abilities-grid">"""
    for ab_rule in ability_rules_list:
        ab_id = ab_rule['id']; ab_name = ab_rule['name']; ab_rank = abilities.get(ab_id, 0)
        ab_mod = engine_ref.get_ability_modifier(ab_rank)
        html += f'<div class="ability-item"><span>{_escape_html(ab_name.upper())}</span><span>{ab_rank}</span><span>({ab_mod:+})</span></div>'
    html += """</div></div>"""
    return html

def _generate_defenses_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    # ... (Content from previous version, assumed mostly complete) ...
    # This function should use engine_ref.get_total_defense for all displayed totals.
    abilities = character_state.get('abilities', {}); bought_defenses = character_state.get('defenses', {})
    pl = character_state.get('powerLevel', 10); pl_cap = pl * 2
    
    html = f"""<div class="section defenses-section"><h3 class="section-title">Defenses</h3>"""
    defense_details = []
    for def_id, base_ab_id in [("Dodge", "AGL"), ("Parry", "FGT"), ("Toughness", "STA"), ("Fortitude", "STA"), ("Will", "AWE")]:
        total_val = engine_ref.get_total_defense(character_state, def_id, base_ab_id)
        base_from_ab = engine_ref.get_ability_modifier(abilities.get(base_ab_id,0))
        bought = bought_defenses.get(def_id,0)
        detail_str = f"(Base {base_from_ab}, Bought {bought})"
        if def_id == "Toughness" and character_state.get('derived_defensive_roll_bonus',0) > 0:
            detail_str += f" +{character_state['derived_defensive_roll_bonus']} DefRoll"
        # Add contributions from Protection powers for Toughness if not already in get_total_defense
        # (engine.get_total_defense should handle this)
        defense_details.append(f'<div class="defense-item"><span>{_escape_html(def_id)}</span><span>{total_val}</span><span>{_escape_html(detail_str)}</span></div>')
    html += "".join(defense_details)
    
    total_dodge = engine_ref.get_total_defense(character_state, 'Dodge', 'AGL')
    total_parry = engine_ref.get_total_defense(character_state, 'Parry', 'FGT')
    total_toughness = engine_ref.get_total_defense(character_state, 'Toughness', 'STA')
    total_fortitude = engine_ref.get_total_defense(character_state, 'Fortitude', 'STA')
    total_will = engine_ref.get_total_defense(character_state, 'Will', 'AWE')
    
    html += f"""<hr class="sub-hr"/>
        <div class="defense-cap {'text-error' if (total_dodge + total_toughness) > pl_cap else ''}">Dodge + Toughness: {total_dodge + total_toughness} / {pl_cap}</div>
        <div class="defense-cap {'text-error' if (total_parry + total_toughness) > pl_cap else ''}">Parry + Toughness: {total_parry + total_toughness} / {pl_cap}</div>
        <div class="defense-cap {'text-error' if (total_fortitude + total_will) > pl_cap else ''}">Fortitude + Will: {total_fortitude + total_will} / {pl_cap}</div>
    </div>"""
    return html

def _generate_combat_summary_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    # ... (Content from previous version, ensure attack display is comprehensive) ...
    initiative_bonus = character_state.get('derived_initiative', 0)
    html = f"""<div class="section combat-section"><h3 class="section-title">Combat</h3>
        <div class="combat-grid"><div class="combat-stat"><strong>Initiative:</strong><span>{initiative_bonus:+}</span></div></div>
        <h4>Attacks / Effects</h4><table class="attacks-table">
        <thead><tr><th>Attack/Effect</th><th>Bonus</th><th>Effect (Rank)</th><th>Range</th><th>Resistance (DC)</th></tr></thead><tbody>"""
    
    attacks_html_parts = []
    for pwr in character_state.get('powers', []):
        if pwr.get('isAttack'):
            attack_bonus_val = pwr.get('attack_bonus_total', engine_ref.get_attack_bonus_for_power(pwr, character_state))
            attack_bonus_display = "N/A" if pwr.get('attackType') in ['area', 'perception'] else f"{attack_bonus_val:+}"
            
            base_effect_rule = next((e for e in rule_data.get('power_effects', []) if e['id'] == pwr.get('baseEffectId')), None)
            base_effect_name_display = base_effect_rule.get('name', 'Unknown Effect') if base_effect_rule else 'Unknown'
            
            res_details = pwr.get('resistance_dc_details', {})
            res_display = f"{_escape_html(res_details.get('dc_type', ''))} DC {_escape_html(str(res_details.get('dc', 'N/A')))}"
            if res_details.get('dodge_dc_for_half'):
                res_display += f" (Dodge DC {res_details['dodge_dc_for_half']} for half)"

            attacks_html_parts.append(f"""<tr>
                <td>{_escape_html(pwr.get('name', 'Unnamed'))}</td><td>{attack_bonus_display}</td>
                <td>{_escape_html(base_effect_name_display)} {pwr.get('rank',0)}</td><td>{_escape_html(pwr.get('final_range', 'N/A'))}</td>
                <td>{res_display}</td></tr>""")
    
    # Default Unarmed Strike if no other attacks listed or as a baseline
    fgt_mod = engine_ref.get_ability_modifier(character_state.get('abilities',{}).get('FGT',0))
    close_attack_adv_bonus = sum(adv.get('rank',0) for adv in character_state.get('advantages',[]) if adv.get('id') == 'adv_close_attack')
    unarmed_bonus = fgt_mod + close_attack_adv_bonus
    str_rank = character_state.get('abilities',{}).get('STR',0)
    unarmed_dc = 15 + str_rank
    attacks_html_parts.append(f"""<tr><td>Unarmed Strike</td><td>{unarmed_bonus:+}</td><td>Damage {str_rank} (Strength-based)</td><td>Close</td><td>Toughness DC {unarmed_dc}</td></tr>""")
    
    html += "".join(attacks_html_parts) + "</tbody></table></div>"
    return html

def _generate_skills_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section skills-section"><h3 class="section-title">Skills</h3>"""
    skills_state = character_state.get('skills', {})
    abilities = character_state.get('abilities', {})
    all_skill_rules = rule_data.get('skills', {}).get('list', [])
    pl = character_state.get('powerLevel', 10)
    skill_bonus_cap = pl + 10
    
    skill_entries_html = []
    # Display all skills the character has ranks in, or untrained skills they can use
    # This requires a more complex iteration: iterate rule_skills, then check char_state
    # Or iterate char_state.skills and lookup rule. The latter is better for specialized skills.
    
    # Sort skills for display: base skills first, then specialized alphabetically
    sorted_skill_ids = sorted(skills_state.keys(), key=lambda x: (engine_ref.get_skill_rule(x) is not None and not engine_ref.get_skill_rule(x).get('specialization_possible', False), x))


    for skill_id, rank in sorted_skill_ids.items():
        skill_rule = engine_ref.get_skill_rule(skill_id) # Gets base rule even for specialized ID
        if not skill_rule and not "_" in skill_id: continue # Skip if truly unknown base skill
        
        # If skill_id is specialized (e.g. "skill_expertise_magic"), get_skill_name_by_id handles it.
        skill_name_display = engine_ref.get_skill_name_by_id(skill_id, all_skill_rules)
        
        gov_ab_id = skill_rule.get('ability', 'N/A') if skill_rule else 'N/A'
        ability_mod = engine_ref.get_ability_modifier(abilities.get(gov_ab_id, 0))
        total_bonus = ability_mod + rank
        
        is_capped = total_bonus > skill_bonus_cap
        cap_note = f" <span class='text-error'>(Cap Exceeded: {skill_bonus_cap})</span>" if is_capped else ""
        
        # Only display if rank > 0 or if it's an untrained skill the character might use (though typically we only list trained ones)
        # For PDF, usually only list skills with ranks or important untrained ones.
        # Let's list if rank > 0.
        if rank > 0:
            skill_entries_html.append(
                f'<div class="skill-entry"><span class="skill-name">{_escape_html(skill_name_display)}</span> <span class="skill-ability">({gov_ab_id})</span> <span class="skill-bonus">{total_bonus:+}</span> <span class="skill-ranks">(R: {rank}){cap_note}</span></div>'
            )

    if not skill_entries_html: skill_entries_html.append("<p>No skills with ranks purchased.</p>")
    
    # Two-column layout
    half_len = math.ceil(len(skill_entries_html) / 2)
    col1_skills = "".join(skill_entries_html[:half_len])
    col2_skills = "".join(skill_entries_html[half_len:])

    html += f"""<div class="skills-columns"><div class="skills-column">{col1_skills}</div><div class="skills-column">{col2_skills}</div></div></div>"""
    return html

def _generate_advantages_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section advantages-section"><h3 class="section-title">Advantages</h3><ul class="advantages-list">"""
    advantages: List[AdvantageDefinition] = character_state.get('advantages', [])
    adv_rules_list = rule_data.get('advantages_v1', [])

    if not advantages: html += "<li>None</li>"
    else:
        for adv_entry in sorted(advantages, key=lambda x: x.get('name', x.get('id','Z'))): # Sort by name if available
            adv_rule = next((r for r in adv_rules_list if r['id'] == adv_entry['id']), None)
            adv_name = adv_rule['name'] if adv_rule else adv_entry.get('id', 'Unknown Advantage')
            adv_rank_display = f" {adv_entry.get('rank', 1)}" if adv_rule and adv_rule.get('ranked') and adv_entry.get('rank', 1) > 1 else ""
            
            params_str = _format_params_for_pdf(adv_entry.get('params'), adv_rule, rule_data, engine_ref)
            if params_str: params_str = f" ({params_str})"

            def_roll_note = ""
            if adv_entry.get('id') == 'adv_defensive_roll' and adv_entry.get('rank',0) > 0 :
                actual_def_roll = character_state.get('derived_defensive_roll_bonus', 0)
                if actual_def_roll > 0: def_roll_note = f" *(+{actual_def_roll} cond. Toughness)*"
            
            html += f'<li><strong>{_escape_html(adv_name)}</strong>{adv_rank_display}{params_str}{def_roll_note}</li>'
    html += "</ul></div>"
    return html

def _generate_powers_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section powers-section"><h3 class="section-title">Powers & Devices</h3>"""
    all_power_modifier_rules = rule_data.get('power_modifiers', [])
    powers: List[PowerDefinition] = character_state.get('powers', [])
    if not powers: html += "<p>None.</p>"
    else:
        for pwr in powers:
            pwr_name = pwr.get('name', 'Unnamed Power')
            pwr_rank_val = pwr.get('rank', 0)
            pwr_cost = pwr.get('cost', 0)
            base_effect_rule = next((e for e in rule_data.get('power_effects', []) if e['id'] == pwr.get('baseEffectId')), None)
            base_effect_name = base_effect_rule.get('name', 'Unknown Effect') if base_effect_rule else 'N/A'
            
            # Display rank only if meaningful (not for 0-rank containers unless it's a placeholder)
            pwr_rank_display = ""
            if pwr_rank_val > 0 or (base_effect_rule and not (base_effect_rule.get('isSenseContainer') or base_effect_rule.get('isImmunityContainer'))):
                pwr_rank_display = f" [{pwr_rank_val}]"

            html += f"""<div class="power-entry">
                            <div class="power-header">
                                <span class="power-name">{_escape_html(pwr_name)}{pwr_rank_display}</span>
                                <span class="power-cost">({pwr_cost} PP)</span>
                            </div>"""
            html += f"<div class='power-base-effect'><em>Effect:</em> {_escape_html(base_effect_name)}</div>"
            if pwr.get('descriptors'):
                html += f"<div class='power-descriptors'><em>Descriptors:</em> {_escape_html(pwr['descriptors'])}</div>"

            # Derived characteristics (Range, Duration, Action)
            derived_details = []
            if pwr.get('final_range'): derived_details.append(f"Range: {_escape_html(pwr['final_range'])}")
            if pwr.get('final_duration'): derived_details.append(f"Duration: {_escape_html(pwr['final_duration'])}")
            if pwr.get('final_action'): derived_details.append(f"Action: {_escape_html(pwr['final_action'])}")
            if derived_details:
                html += f"<p class='power-sub-details'>{' | '.join(derived_details)}</p>"

            measurement_display = pwr.get('measurement_details_display')
            if measurement_display:
                html += f'<p class="power-sub-details"><strong>Details:</strong> {_escape_html(measurement_display)}</p>'
            
            if pwr.get('isAlternateEffectOf'):
                base_pwr_for_ae = next((p_base for p_base in powers if p_base.get('id') == pwr['isAlternateEffectOf']), None)
                base_pwr_name = base_pwr_for_ae.get('name', "Unknown Base") if base_pwr_for_ae else "Unknown Base"
                ae_cost_note = "(+1 PP)" if not (base_pwr_for_ae and base_pwr_for_ae.get('isDynamicArray')) else "(+2 PP)"
                html += f"<div class='power-array-info'><em>Alternate Effect of: {_escape_html(base_pwr_name)} {ae_cost_note} (Array: {_escape_html(pwr.get('arrayId','N/A'))})</em></div>"
            elif pwr.get('isArrayBase'):
                array_type = "Dynamic Array" if pwr.get('isDynamicArray') else "Static Array"
                html += f"<div class='power-array-info'><em>{array_type} Base ({_escape_html(pwr.get('arrayId','N/A'))})</em></div>"

            if pwr.get('modifiersConfig'):
                html += '<ul class="power-modifiers-list"><strong>Modifiers:</strong>'
                for mod_conf in pwr.get('modifiersConfig', []):
                    # Skip dynamic array marker if it's the base, it's implied by isDynamicArray flag
                    if mod_conf.get('id') == 'mod_extra_dynamic_array' and pwr.get('isArrayBase'): continue 
                    html += f"<li>{_format_modifier_for_pdf(mod_conf, all_power_modifier_rules, character_state, rule_data, engine_ref)}</li>"
                html += '</ul>'

            # Effect-specific details
            if base_effect_rule:
                if base_effect_rule.get('isSenseContainer') and pwr.get('sensesConfig'):
                    senses_html = "<ul>"
                    for sense_id in pwr.get('sensesConfig',[]):
                        sense_rule = next((s for s in rule_data.get('power_senses_config',[]) if s['id'] == sense_id), None)
                        senses_html += f"<li>{_escape_html(sense_rule['name'] if sense_rule else sense_id)} ({sense_rule.get('cost',0) if sense_rule else '?' }PP)</li>"
                    senses_html += "</ul>"
                    html += f"<div class='power-sub-details'><strong>Senses Acquired:</strong>{senses_html}</div>"
                
                if base_effect_rule.get('isImmunityContainer') and pwr.get('immunityConfig'):
                    imm_html = "<ul>"
                    for imm_id in pwr.get('immunityConfig',[]):
                        imm_rule = next((im for im in rule_data.get('power_immunities_config',[]) if im['id'] == imm_id), None)
                        imm_html += f"<li>{_escape_html(imm_rule['name'] if imm_rule else imm_id)} ({imm_rule.get('cost',0) if imm_rule else '?' }PP)</li>"
                    imm_html += "</ul>"
                    html += f"<div class='power-sub-details'><strong>Immunities Gained:</strong>{imm_html}</div>"

                if base_effect_rule.get('isVariableContainer'):
                    html += f"<p class='power-sub-details'><strong>Descriptors:</strong> {_escape_html(pwr.get('variableDescriptors', 'N/A'))}</p>"
                    html += f"<p class='power-sub-details'><strong>Point Pool:</strong> {pwr.get('variablePointPool',0)} PP to allocate</p>"
                    if pwr.get('variableConfigurations'):
                        html += "<div class='variable-configs-list'><strong>Sample Configurations:</strong><ul>"
                        for cfg in pwr.get('variableConfigurations',[]):
                            cfg_cost = sum(t.get('pp_cost_in_variable',0) for t in cfg.get('configTraits',[])) # Sum trait costs
                            traits_desc_list = [f"{t.get('name','Trait')} ({t.get('pp_cost_in_variable',0)}PP)" for t in cfg.get('configTraits',[])]
                            html += f"<li><strong>{_escape_html(cfg.get('configName',''))}</strong> ({cfg_cost} PP): {_escape_html(', '.join(traits_desc_list) if traits_desc_list else 'No traits defined')}</li>"
                        html += "</ul></div>"
                
                if base_effect_rule.get('isAllyEffect') and pwr.get('ally_notes_and_stats_structured'):
                    ally_stats = pwr.get('ally_notes_and_stats_structured')
                    html += f"<div class='power-ally-notes'><strong>Summon/Duplicate Details ({ally_stats.get('name', 'Creation')}):</strong><br/>"
                    html += f"  PL: {ally_stats.get('pl_for_ally','N/A')}, Asserted PP Cost: {ally_stats.get('cost_pp_asserted_by_user',0)} / {pwr.get('allotted_pp_for_creation',0)} Allotted<br/>"
                    html += f"  Abilities: {_escape_html(ally_stats.get('abilities_summary_text','N/A'))}<br/>"
                    html += f"  Defenses: {_escape_html(ally_stats.get('defenses_summary_text','N/A'))}<br/>"
                    html += f"  Skills: {_escape_html(ally_stats.get('skills_summary_text','N/A'))}<br/>"
                    html += f"  Powers/Adv: <pre>{_escape_html(ally_stats.get('powers_advantages_summary_text','N/A'))}</pre>"
                    if ally_stats.get('notes'): html += f"  Notes: <pre>{_escape_html(ally_stats.get('notes'))}</pre>"
                    html += "</div>"
                
                if base_effect_id == 'eff_affliction' and pwr.get('affliction_params'):
                    aff_p = pwr['affliction_params']
                    html += f"<p class='power-sub-details'><strong>Affliction:</strong> Resisted by {_escape_html(aff_p.get('resistance_type','N/A'))}.<br/>"
                    html += f"  1st Degree: {_escape_html(aff_p.get('degree1','N/A'))}<br/>"
                    html += f"  2nd Degree: {_escape_html(aff_p.get('degree2','N/A'))}<br/>"
                    html += f"  3rd Degree: {_escape_html(aff_p.get('degree3','N/A'))}</p>"

                if base_effect_id == 'eff_enhanced_trait' and pwr.get('enhanced_trait_params'):
                    et_p = pwr['enhanced_trait_params']
                    trait_name = et_p.get('trait_id', 'N/A')
                    if et_p.get('category') == "Skill": trait_name = engine_ref.get_skill_name_by_id(trait_name)
                    elif et_p.get('category') == "Advantage":
                        adv_r = next((adv for adv in rule_data.get('advantages_v1',[]) if adv['id'] == trait_name), None)
                        if adv_r : trait_name = adv_r['name']
                    html += f"<p class='power-sub-details'><strong>Enhances:</strong> {_escape_html(et_p.get('category','N/A'))} - {_escape_html(trait_name)} by +{et_p.get('enhancementAmount',0)} ranks.</p>"
            html += "</div>" # End power-entry
    html += "</div>" # End powers-section
    return html

def _generate_equipment_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section equipment-section"><h3 class="section-title">Equipment</h3>"""
    total_ep = character_state.get('derived_total_ep',0)
    spent_ep = character_state.get('derived_spent_ep',0) 
    html += f"<p class='ep-summary'>Spent: {spent_ep} EP / Total Available: {total_ep} EP</p>"
    
    equipment_list: List[EquipmentDefinition] = character_state.get('equipment', [])
    if not equipment_list: html += "<p>No standard equipment items.</p>"
    else:
        html += "<ul class='equipment-list'>"
        for item in equipment_list:
            item_name = _escape_html(item.get('name', 'Unnamed Item'))
            item_cost = item.get('ep_cost', 0)
            item_desc = _escape_html(item.get('description', item.get('effects_text', '')))
            params_str = ""
            if item.get('params'):
                item_rule = next((i_rule for i_rule in rule_data.get('equipment_items',[]) if i_rule['id'] == item.get('id')), None)
                params_str = _format_params_for_pdf(item.get('params'), item_rule, rule_data, engine_ref)
                if params_str: params_str = f" ({params_str})"
            
            html += f"<li><strong>{item_name}</strong> ({item_cost} EP){params_str}<em>{f' - {item_desc}' if item_desc else ''}</em></li>"
        html += "</ul>"
    html += "</div>"
    return html

def _generate_hq_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section hq-section"><h3 class="section-title">Headquarters</h3>"""
    hqs: List[HQDefinition] = character_state.get('headquarters', [])
    hq_features_rules = rule_data.get('hq_features',[])
    if not hqs: html += "<p>None.</p>"
    else:
        for hq_entry in hqs:
            hq_name = _escape_html(hq_entry.get('name','Unnamed HQ'))
            hq_cost = engine_ref.calculate_hq_cost(hq_entry, hq_features_rules) 
            
            size_rule = next((s for s in hq_features_rules if s.get('id') == hq_entry.get('size_id')), None)
            size_name = _escape_html(size_rule.get('name','Unknown Size')) if size_rule else 'Unknown Size'
            base_tough_from_size = size_rule.get('base_toughness_provided',0) if size_rule else 0
            total_tough = base_tough_from_size + hq_entry.get('bought_toughness_ranks',0)

            html += f"<div class='hq-entry'><h4>{hq_name} ({hq_cost} EP)</h4>"
            html += f"<p class='hq-stat'><strong>Size:</strong> {size_name}</p>"
            html += f"<p class='hq-stat'><strong>Toughness:</strong> {total_tough}</p>"
            if hq_entry.get('features'):
                html += "<ul class='hq-feature-list'><strong>Features:</strong>"
                for feat_entry in hq_entry.get('features',[]):
                    feat_rule = next((f for f in hq_features_rules if f['id'] == feat_entry['id']), None)
                    feat_name = _escape_html(feat_rule.get('name', feat_entry['id'])) if feat_rule else _escape_html(feat_entry['id'])
                    feat_rank_disp = f" (Rank {feat_entry.get('rank',1)})" if feat_rule and feat_rule.get('ranked') and feat_entry.get('rank',1) > 1 else ""
                    feat_params_str = _format_params_for_pdf(feat_entry.get('params'), feat_rule, rule_data, engine_ref)
                    if feat_params_str: feat_params_str = f" ({feat_params_str})"
                    html += f"<li>{feat_name}{feat_rank_disp}{feat_params_str}</li>"
                html += "</ul>"
            html += "</div>"
    html += "</div>"
    return html

def _generate_vehicles_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section vehicle-section"><h3 class="section-title">Vehicles</h3>"""
    vehicles: List[VehicleDefinition] = character_state.get('vehicles', [])
    vehicle_features_rules = rule_data.get('vehicle_features',[])
    vehicle_size_stats_rules = rule_data.get('vehicle_size_stats',[])
    if not vehicles: html += "<p>None.</p>"
    else:
        for vh_entry in vehicles:
            vh_name = _escape_html(vh_entry.get('name','Unnamed Vehicle'))
            vh_cost = engine_ref.calculate_vehicle_cost(vh_entry, vehicle_features_rules, vehicle_size_stats_rules)
            
            size_rank_val = vh_entry.get('size_rank',0)
            size_stats_rule = next((s for s in vehicle_size_stats_rules if s.get('size_rank_value') == size_rank_val), None)
            
            # Get effective stats after features might modify them
            # This requires the engine to have processed the vehicle_def fully.
            # For now, display base from size, and features separately.
            # A more advanced PDF would show final effective Str, Spd, Def, Tou.
            eff_str, eff_spd, eff_def, eff_tou = "N/A", "N/A", "N/A", "N/A"
            if size_stats_rule:
                eff_str = size_stats_rule.get('base_str',0) + sum(f.get('rank',0) for f in vh_entry.get('features',[]) if f.get('id') == 'vh_stat_boost_strength')
                eff_spd = size_stats_rule.get('base_spd',0) + sum(f.get('rank',0) for f in vh_entry.get('features',[]) if f.get('id') == 'vh_stat_boost_speed')
                eff_def = size_stats_rule.get('base_def',0) + sum(f.get('rank',0) for f in vh_entry.get('features',[]) if f.get('id') == 'vh_stat_boost_defense')
                eff_tou = size_stats_rule.get('base_tou',0) + sum(f.get('rank',0) for f in vh_entry.get('features',[]) if f.get('id') == 'vh_stat_boost_toughness')


            html += f"<div class='vehicle-entry'><h4>{vh_name} ({vh_cost} EP)</h4>"
            html += f"<p class='vehicle-stat'><strong>Size Rank:</strong> {size_rank_val} ({size_stats_rule.get('size_name','N/A') if size_stats_rule else 'N/A'})</p>"
            html += f"<p class='vehicle-stat'><strong>Str:</strong> {eff_str} | <strong>Spd:</strong> {eff_spd} | <strong>Def:</strong> {eff_def} | <strong>Tou:</strong> {eff_tou}</p>"
            if vh_entry.get('features'):
                html += "<ul class='vehicle-feature-list'><strong>Features:</strong>"
                for feat_entry in vh_entry.get('features',[]):
                    feat_rule = next((f for f in vehicle_features_rules if f['id'] == feat_entry['id']), None)
                    feat_name = _escape_html(feat_rule.get('name', feat_entry['id'])) if feat_rule else _escape_html(feat_entry['id'])
                    feat_rank_disp = f" (Rank {feat_entry.get('rank',1)})" if feat_rule and feat_rule.get('ranked') and feat_entry.get('rank',1) > 1 else ""
                    feat_params_str = _format_params_for_pdf(feat_entry.get('params'), feat_rule, rule_data, engine_ref)
                    if feat_params_str: feat_params_str = f" ({feat_params_str})"
                    html += f"<li>{feat_name}{feat_rank_disp}{feat_params_str}</li>"
                html += "</ul>"
            html += "</div>"
    html += "</div>"
    return html

def _generate_allies_html(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    html = """<div class="section allies-section"><h3 class="section-title">Companions</h3>"""
    allies: List[AllyDefinition] = character_state.get('allies', [])
    
    min_pool = character_state.get('derived_total_minion_pool_pp', 0)
    min_spent = character_state.get('derived_spent_minion_pool_pp', 0)
    side_pool = character_state.get('derived_total_sidekick_pool_pp', 0)
    side_spent = character_state.get('derived_spent_sidekick_pool_pp', 0)
    
    pool_info = []
    if min_pool > 0 or min_spent > 0: pool_info.append(f"Minion Pool: {min_spent}/{min_pool} PP")
    if side_pool > 0 or side_spent > 0: pool_info.append(f"Sidekick Pool: {side_spent}/{side_pool} PP")
    if pool_info: html += f"<p class='ally-pool-summary'><strong>Advantage Pools:</strong> {'; '.join(pool_info)}</p>"

    advantage_allies = [a for a in allies if a.get('source_type') == 'advantage_pool']
    power_allies = [a for a in allies if a.get('source_type') == 'power_creation'] # This assumes engine populates 'allies' list from powers too

    if not advantage_allies and not power_allies: html += "<p>None.</p>"
    
    if advantage_allies:
        html += "<h5>From Advantages (Minions/Sidekicks):</h5>"
        for ally in advantage_allies:
            html += f"""<div class="ally-entry">
                <h6>{_escape_html(ally.get('name', 'Unnamed'))} ({_escape_html(ally.get('type', 'N/A'))}) - PL {ally.get('pl_for_ally','N/A')} [{ally.get('cost_pp_asserted_by_user', 0)} PP]</h6>
                <div class="ally-stat-block">
                    <p><strong>Abilities:</strong> {_escape_html(ally.get('abilities_summary_text', 'N/A'))}</p>
                    <p><strong>Defenses:</strong> {_escape_html(ally.get('defenses_summary_text', 'N/A'))}</p>
                    <p><strong>Skills:</strong> {_escape_html(ally.get('skills_summary_text', 'N/A'))}</p>
                    <div><strong>Powers/Advantages:</strong><pre>{_escape_html(ally.get('powers_advantages_summary_text', 'N/A'))}</pre></div>
                    {f"<div><strong>Notes:</strong><pre>{_escape_html(ally.get('notes'))}</pre></div>" if ally.get('notes') else ''}
                </div></div>"""
    
    # Display allies from Summon/Duplication powers
    # These are stored in power_definition.ally_notes_and_stats_structured
    # The main 'allies' list in char_state might not be the place for these unless engine explicitly copies them there.
    # For now, let's assume we iterate powers to find these.
    summoned_display = []
    for pwr_entry in character_state.get('powers', []):
        if pwr_entry.get('baseEffectId') in ['eff_summon', 'eff_duplication'] and pwr_entry.get('ally_notes_and_stats_structured'):
            ally_stats = pwr_entry.get('ally_notes_and_stats_structured')
            source_power_name = pwr_entry.get('name', 'Unknown Power')
            allotted_pp = pwr_entry.get('allotted_pp_for_creation',0)
            
            summon_html = f"""<div class="ally-entry summoned-ally">
                <h6>{_escape_html(ally_stats.get('name', 'Unnamed Creation'))} (from <i>{_escape_html(source_power_name)}</i>) - PL {ally_stats.get('pl_for_ally','N/A')} [{ally_stats.get('cost_pp_asserted_by_user',0)}/{allotted_pp} PP]</h6>
                <div class="ally-stat-block">
                    <p><strong>Abilities:</strong> {_escape_html(ally_stats.get('abilities_summary_text', 'N/A'))}</p>
                    <p><strong>Defenses:</strong> {_escape_html(ally_stats.get('defenses_summary_text', 'N/A'))}</p>
                    <p><strong>Skills:</strong> {_escape_html(ally_stats.get('skills_summary_text', 'N/A'))}</p>
                    <div><strong>Powers/Advantages:</strong><pre>{_escape_html(ally_stats.get('powers_advantages_summary_text', 'N/A'))}</pre></div>
                    {f"<div><strong>Notes:</strong><pre>{_escape_html(ally_stats.get('notes'))}</pre></div>" if ally_stats.get('notes') else ''}
                </div></div>"""
            summoned_display.append(summon_html)
    if summoned_display:
        html += "<h5>From Powers (Summon/Duplication):</h5>" + "".join(summoned_display)

    html += "</div>"
    return html

def _generate_complications_html(character_state: 'CharacterState') -> str:
    html = """<div class="section complications-section"><h3 class="section-title">Complications</h3><ul class="complications-list">"""
    complications = character_state.get('complications',[])
    if not complications: html += "<li>None (Min. 2 Recommended)</li>"
    else:
        for comp in complications: html+= f"<li>{_escape_html(comp.get('description','N/A'))}</li>"
    html += "</ul></div>"
    return html

def _generate_footer_html(character_state: 'CharacterState') -> str:
    html = """
    <footer class="sheet-footer">
        <div class="section footer-notes-section">
            <div class="hero-points"><strong>Hero Points:</strong> <span class="value-box"></span> <span class="value-box"></span> <span class="value-box"></span> </div>
            <div class="conditions-track"><strong>Conditions Track:</strong> <span class="line-fill"></span></div>
            <div class="general-notes"><strong>Notes:</strong> <div class="notes-area"></div></div>
        </div>
        <p class="generation-info">Sheet generated by HeroForge M&M. M&M 3e &copy; Green Ronin Publishing.</p>
    </footer>
    """
    return html

# --- Main PDF Generation Functions ---
def generate_pdf_html_content(character_state: 'CharacterState', rule_data: 'RuleData', engine_ref: 'CoreEngine') -> str:
    """Generates the full HTML content string for the character sheet."""
    char_name = character_state.get('name', 'M&M Character')
    
    # Ensure character_state is fully recalculated before generating HTML
    # This is crucial if this function is called independently of the main app's recalculate cycle.
    # However, app.py should ideally pass an already recalculated state.
    # For safety, let's assume character_state is up-to-date.

    html_parts = [
        "<!DOCTYPE html><html lang='en'>", # Added Doctype and html lang
        _generate_html_head(char_name),
        "<body><div class='sheet-container'>",
        _generate_sheet_header_html(character_state),
        "<main class='sheet-body'>",
        # Column 1: Core Stats
        "<section class='column column-one'>",
        _generate_abilities_html(character_state, rule_data, engine_ref),
        _generate_defenses_html(character_state, rule_data, engine_ref),
        _generate_combat_summary_html(character_state, rule_data, engine_ref),
        _generate_complications_html(character_state), # Moved Complications to col 1 for balance
        "</section>",
        # Column 2: Skills, Advantages, Equipment
        "<section class='column column-two'>",
        _generate_skills_html(character_state, rule_data, engine_ref),
        _generate_advantages_html(character_state, rule_data, engine_ref),
        _generate_equipment_html(character_state, rule_data, engine_ref), 
        "</section>",
        # Column 3: Powers, Support Structures
        "<section class='column column-three'>",
        _generate_powers_html(character_state, rule_data, engine_ref), 
        _generate_allies_html(character_state, rule_data, engine_ref), 
        _generate_hq_html(character_state, rule_data, engine_ref), 
        _generate_vehicles_html(character_state, rule_data, engine_ref), 
        "</section>",
        "</main>",
        _generate_footer_html(character_state),
        "</div></body></html>"
    ]
    return "\n".join(html_parts)

def generate_pdf_bytes(character_state: 'CharacterState', rule_data_ref: 'RuleData', engine_ref: 'CoreEngine') -> Optional[BytesIO]:
    """Generates PDF bytes using WeasyPrint from the character state."""
    if not WEASYPRINT_AVAILABLE:
        print("Error: WeasyPrint is not installed. PDF generation aborted.")
        # In a Streamlit app, you might use st.error() here if called from main thread.
        return None
    
    try:
        # Ensure character state is fully processed before generating HTML
        # It's best if app.py ensures this, but a final recalc here can be a safeguard.
        processed_char_state = engine_ref.recalculate(character_state)
        
        html_string = generate_pdf_html_content(processed_char_state, rule_data_ref, engine_ref)
        
        css_string = ""
        css_file_path = "assets/pdf_styles.css" 
        try:
            with open(css_file_path, "r", encoding="utf-8") as f:
                css_string = f.read()
            # print(f"DEBUG: Loaded CSS from {css_file_path}")
        except FileNotFoundError:
            print(f"Warning: PDF CSS file '{css_file_path}' not found. PDF will have minimal styling.")
            # Basic fallback CSS for structure if file is missing
            css_string = """
                body { font-family: sans-serif; margin: 15mm; font-size: 9pt; line-height: 1.3; } 
                .section { margin-bottom: 10px; padding: 5px; border: 1px solid #ccc; page-break-inside: avoid;}
                .sheet-header { border-bottom: 1px solid black; margin-bottom: 10px; padding-bottom: 5px;}
                .char-name { font-size: 18pt; font-weight: bold; }
                h3.section-title { font-size: 12pt; border-bottom: 1px solid #666; margin-top:10px; margin-bottom:5px;}
                h4 {font-size: 10pt; margin-top:8px; margin-bottom:3px;}
                table { width: 100%; border-collapse: collapse; font-size: 8pt; } 
                th, td { border: 1px solid #ddd; padding: 2px 4px; text-align: left; } th { background-color: #f0f0f0; }
                .power-entry { margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px dotted #eee; }
                .power-header { display: flex; justify-content: space-between; } .power-name { font-weight: bold; }
                .power-modifiers-list { list-style-type: disc; margin-left: 20px; }
            """
        
        font_config = FontConfiguration() 
        
        # Using BytesIO as the target for write_pdf
        pdf_buffer = BytesIO()
        HTML(string=html_string, base_url=os.getcwd()).write_pdf(
            target=pdf_buffer, # Write to the buffer
            stylesheets=[CSS(string=css_string, font_config=font_config)],
            font_config=font_config,
            presentational_hints=True # Important for some HTML attributes to be considered for styling
        )
        pdf_buffer.seek(0) # Rewind the buffer to the beginning for reading
        # print("DEBUG: PDF generated successfully in memory.")
        return pdf_buffer
    except Exception as e:
        print(f"Error during PDF generation with WeasyPrint: {e}")
        # import traceback # For debugging
        # print(traceback.format_exc())
        return None

