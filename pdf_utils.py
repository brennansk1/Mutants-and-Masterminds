# pdf_utils.py

import math
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
    # Define dummy classes if WeasyPrint is not available to prevent import errors
    # if TYPE_CHECKING is used to satisfy linters but not cause runtime issues
    if not TYPE_CHECKING:
        class HTML: # type: ignore
            def __init__(self, string, base_url=None): pass
            def write_pdf(self, target=None, stylesheets=None, font_config=None): return b""
        class CSS: # type: ignore
            def __init__(self, string=None, filename=None, font_config=None): pass
        class FontConfiguration: # type: ignore
            def __init__(self): pass


if TYPE_CHECKING:
    from core_engine import CoreEngine # For type hinting engine_ref


# --- HTML Generation Helper Functions ---

def _escape_html(text: Optional[str]) -> str:
    """Basic HTML escaping for user-provided text."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def _format_modifier_for_pdf(mod_config: Dict[str, Any], all_mod_rules: List[Dict[str, Any]], character_state: CharacterState, rule_data: RuleData) -> str:
    """Formats a power modifier configuration for display in the PDF."""
    mod_rule = next((m for m in all_mod_rules if m['id'] == mod_config.get('id')), None)
    if not mod_rule:
        return _escape_html(mod_config.get('id', 'Unknown Modifier'))

    display_str = _escape_html(mod_rule['name'])
    rank_display = ""
    if mod_rule.get('ranked') and mod_config.get('rank', 1) > 1:
        rank_display = f" {mod_config['rank']}"
    
    display_str += rank_display

    user_input = mod_config.get('userInput')
    if mod_rule.get('parameter_needed') and user_input:
        param_display_val = ""
        param_type = mod_rule.get('parameter_type')

        if param_type == 'select_power_for_link' or param_type == 'select_attack_from_powers_or_text':
            linked_power_id = str(user_input)
            linked_power = next((p for p in character_state.get('powers', []) if p.get('id') == linked_power_id), None)
            param_display_val = linked_power.get('name', linked_power_id) if linked_power else linked_power_id
        elif param_type == 'select_skill' or param_type == 'select_skill_expertise_ritualist' or param_type == 'select_skill_technology_inventor':
            skill_id = str(user_input)
            skill_rule = next((s for s in rule_data.get('skills',{}).get('list',[]) if s.get('id') == skill_id), None)
            param_display_val = skill_rule.get('name', skill_id) if skill_rule else skill_id
        elif param_type == 'select_languages_list' and isinstance(user_input, list): # Assuming 'languages_list' is the param key
            param_display_val = ", ".join(map(_escape_html, user_input))
        else:
            param_display_val = _escape_html(str(user_input))
        
        if param_display_val:
            display_str += f": <span class='modifier-param'>{param_display_val}</span>"
            
    return display_str

def _generate_html_head(character_name: str) -> str:
    return f"""
    <head>
        <meta charset="UTF-8">
        <title>{_escape_html(character_name)} - M&M 3e Character Sheet</title>
        {/* CSS will be passed to WeasyPrint directly, or can be linked if assets are served */}
    </head>
    """

def _generate_sheet_header_html(character_state: CharacterState) -> str:
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
        
        <div class="concept-desc" style="grid-column: 1 / -1;"> {/* Spanning all columns */}
            <p><strong>Concept:</strong> {_escape_html(character_state.get('concept', ''))}</p>
            <p><strong>Description:</strong> {_escape_html(character_state.get('description', ''))}</p>
        </div>
    </header>
    """

def _generate_abilities_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    abilities = character_state.get('abilities', {})
    ability_rules = rule_data.get('abilities', [])
    html = """<div class="section abilities-section"><h3>Abilities</h3><div class="abilities-grid">"""
    for ab_rule in ability_rules:
        ab_id = ab_rule['id']
        ab_name = ab_rule['name']
        ab_rank = abilities.get(ab_id, 0)
        ab_mod = engine_ref.get_ability_modifier(ab_rank)
        html += f'<div class="ability-item"><span>{_escape_html(ab_name.upper())}</span><span>{ab_rank}</span><span>({ab_mod:+})</span></div>'
    html += """</div></div>"""
    return html

def _generate_defenses_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    abilities = character_state.get('abilities', {})
    bought_defenses = character_state.get('defenses', {})
    pl = character_state.get('powerLevel', 10)
    pl_cap = pl * 2

    total_dodge = engine_ref.get_total_defense(character_state, 'Dodge', 'AGL')
    total_parry = engine_ref.get_total_defense(character_state, 'Parry', 'FGT')
    total_toughness = engine_ref.get_total_defense(character_state, 'Toughness', 'STA') # V1.x: Add powers/advantages
    # Consider Defensive Roll for display
    def_roll_bonus = character_state.get('derived_defensive_roll_bonus', 0)
    toughness_display = f"{total_toughness}"
    if def_roll_bonus > 0:
        toughness_display += f" (+{def_roll_bonus} from Defensive Roll, conditional)"

    total_fortitude = engine_ref.get_total_defense(character_state, 'Fortitude', 'STA')
    total_will = engine_ref.get_total_defense(character_state, 'Will', 'AWE')

    html = f"""
    <div class="section defenses-section">
        <h3>Defenses</h3>
        <div class="defense-item"><span>Dodge</span><span>{total_dodge}</span><span>(Base {engine_ref.get_ability_modifier(abilities.get('AGL',0))}, Bought {bought_defenses.get('Dodge',0)})</span></div>
        <div class="defense-item"><span>Parry</span><span>{total_parry}</span><span>(Base {engine_ref.get_ability_modifier(abilities.get('FGT',0))}, Bought {bought_defenses.get('Parry',0)})</span></div>
        <div class="defense-item"><span>Toughness</span><span>{total_toughness}</span><span>(Base {engine_ref.get_ability_modifier(abilities.get('STA',0))}, Bought {bought_defenses.get('Toughness',0)}){f' (+{def_roll_bonus} DefRoll)' if def_roll_bonus > 0 else ''}</span></div>
        <div class="defense-item"><span>Fortitude</span><span>{total_fortitude}</span><span>(Base {engine_ref.get_ability_modifier(abilities.get('STA',0))}, Bought {bought_defenses.get('Fortitude',0)})</span></div>
        <div class="defense-item"><span>Will</span><span>{total_will}</span><span>(Base {engine_ref.get_ability_modifier(abilities.get('AWE',0))}, Bought {bought_defenses.get('Will',0)})</span></div>
        <hr class="sub-hr"/>
        <div class="defense-cap {'text-error' if (total_dodge + total_toughness) > pl_cap else ''}">Dodge + Toughness: {total_dodge + total_toughness} / {pl_cap}</div>
        <div class="defense-cap {'text-error' if (total_parry + total_toughness) > pl_cap else ''}">Parry + Toughness: {total_parry + total_toughness} / {pl_cap}</div>
        <div class="defense-cap {'text-error' if (total_fortitude + total_will) > pl_cap else ''}">Fortitude + Will: {total_fortitude + total_will} / {pl_cap}</div>
    </div>
    """
    return html

def _generate_combat_summary_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    initiative_bonus = character_state.get('derived_initiative', 0)
    html = f"""
    <div class="section combat-section">
        <h3>Combat Summary</h3>
        <div class="combat-grid">
            <div class="combat-stat"><strong>Initiative:</strong><span>{initiative_bonus:+}</span></div>
        </div>
        <h4>Attacks / Effects</h4>
        <table class="attacks-table">
            <thead><tr><th>Attack/Effect</th><th>Bonus</th><th>Effect (Rank)</th><th>Range</th><th>Resistance (DC)</th></tr></thead>
            <tbody>
    """
    attack_powers_found = False
    for pwr in character_state.get('powers', []):
        if pwr.get('isAttack'): # This flag must be accurately set by engine.recalculate()
            attack_powers_found = True
            attack_bonus_display = engine_ref.get_attack_bonus_for_power(pwr, character_state)
            if pwr.get('attackType') in ['area', 'perception']: attack_bonus_display = "N/A"
            else: attack_bonus_display = f"{attack_bonus_display:+}"

            base_effect_rule = next((e for e in rule_data.get('power_effects', []) if e['id'] == pwr.get('baseEffectId')), None)
            base_effect_name_display = base_effect_rule.get('name', 'Unknown Effect') if base_effect_rule else 'Unknown Effect'
            
            resistance_details = pwr.get('resistance_dc_details', {"dc_type": "N/A", "dc": "N/A"})

            html += f"""
                <tr>
                    <td>{_escape_html(pwr.get('name', 'Unnamed Power'))}</td>
                    <td>{attack_bonus_display}</td>
                    <td>{_escape_html(base_effect_name_display)} {pwr.get('rank',0)}</td>
                    <td>{_escape_html(pwr.get('final_range', 'N/A'))}</td>
                    <td>{_escape_html(str(resistance_details.get('dc_type', '')))} DC {_escape_html(str(resistance_details.get('dc', '')))}</td>
                </tr>
            """
    if not attack_powers_found:
        # Default Unarmed Strike
        unarmed_bonus = engine_ref.get_ability_modifier(character_state.get('abilities',{}).get('FGT',0))
        # Check for Close Attack advantage
        unarmed_bonus += sum(adv.get('rank',0) for adv in character_state.get('advantages',[]) if adv.get('id') == 'adv_close_atk') # Assuming adv_close_atk
        str_damage_rank = character_state.get('abilities',{}).get('STR',0)
        unarmed_dc = 15 + str_damage_rank
        html += f"""
            <tr><td>Unarmed Strike</td><td>{unarmed_bonus:+}</td><td>Damage {str_damage_rank} (Strength-based)</td><td>Close</td><td>Toughness DC {unarmed_dc}</td></tr>"""
    html += """</tbody></table></div>"""
    return html

def _generate_skills_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    # ... (Full implementation from previous response, ensuring two-column layout) ...
    html = """<div class="section skills-section"><h3>Skills</h3>"""
    skills = character_state.get('skills', {})
    abilities = character_state.get('abilities', {})
    skill_rules = rule_data.get('skills', [])
    pl = character_state.get('powerLevel', 10)
    skill_bonus_cap = pl + 10
    
    skill_entries_html = []
    for skill_info in skill_rules:
        skill_id = skill_info['id']
        rank = skills.get(skill_id, 0)
        if rank > 0 or not skill_info.get('trainedOnly', False):
            ability_mod = engine_ref.get_ability_modifier(abilities.get(skill_info['ability']))
            total_bonus = ability_mod + rank
            skill_name = skill_info.get('name', skill_id)
            gov_ability_short = skill_info.get('ability', '')
            is_capped = total_bonus > skill_bonus_cap
            cap_note = f" <span class='text-error'>(Cap {skill_bonus_cap})</span>" if is_capped else ""
            skill_entries_html.append(
                f'<div class="skill-entry"><span class="skill-name">{_escape_html(skill_name)}</span> <span class="skill-ability">({gov_ability_short})</span> <span class="skill-bonus">{total_bonus:+}</span> <span class="skill-ranks">(R: {rank}){cap_note}</span></div>'
            )
    if not skill_entries_html: skill_entries_html.append("<p>No notable skills.</p>")
    
    half_len = math.ceil(len(skill_entries_html) / 2)
    col1_skills = "".join(skill_entries_html[:half_len])
    col2_skills = "".join(skill_entries_html[half_len:])

    html += f"""
        <div class="skills-columns">
            <div class="skills-column">{col1_skills}</div>
            <div class="skills-column">{col2_skills}</div>
        </div>
    </div>
    """
    return html

def _generate_advantages_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    # ... (Full implementation from previous response, displaying all parameters clearly) ...
    html = """<div class="section advantages-section"><h3>Advantages</h3><ul class="advantages-list">"""
    advantages = character_state.get('advantages', [])
    if not advantages: html += "<li>None</li>"
    else:
        for adv_entry in advantages:
            # ... (Detailed parameter display logic from previous response) ...
            adv_rule = next((r for r in rule_data.get('advantages_v1', []) if r['id'] == adv_entry['id']), None)
            adv_name = adv_rule['name'] if adv_rule else adv_entry.get('id', 'Unknown Advantage')
            adv_rank_display = f" {adv_entry['rank']}" if adv_rule and adv_rule.get('ranked') and adv_entry.get('rank', 1) > 1 else ""
            params_display_list = []
            # ... (Logic to build params_final_display from adv_entry.get('params', {})) ...
            params_str = ""
            if adv_entry.get('params'):
                for p_key, p_val in adv_entry.get('params', {}).items():
                    if p_val: params_display_list.append(f"{_escape_html(str(p_val))}")
            if params_display_list: params_str = f" ({'; '.join(params_display_list)})"

            def_roll_note = ""
            if adv_entry.get('id') == 'adv_defensive_roll' and adv_entry.get('rank',0) > 0 :
                agl_for_def_roll = character_state.get('abilities',{}).get('AGL',0)
                actual_def_roll = min(adv_entry.get('rank',0), agl_for_def_roll)
                def_roll_note = f" *(+{actual_def_roll} cond. Toughness)*"
            html += f'<li><strong>{_escape_html(adv_name)}</strong>{adv_rank_display}{_escape_html(params_str)}{def_roll_note}</li>'
    html += "</ul></div>"
    return html

def _generate_powers_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    html = """<div class="section powers-section"><h3>Powers & Devices</h3>"""
    all_power_modifier_rules = rule_data.get('power_modifiers', [])
    powers = character_state.get('powers', [])
    if not powers: html += "<p>None.</p>"
    else:
        for pwr in powers:
            pwr_name = pwr.get('name', 'Unnamed Power')
            pwr_rank_val = pwr.get('rank', 0)
            pwr_rank_display = f" [{pwr_rank_val}]" if pwr_rank_val > 0 or (pwr.get('baseEffectId') not in ['eff_senses', 'eff_immunity']) else ""
            pwr_cost = pwr.get('cost', 0)
            base_effect_rule = next((e for e in rule_data.get('power_effects', []) if e['id'] == pwr.get('baseEffectId')), None)
            base_effect_name = base_effect_rule.get('name', 'Unknown Effect') if base_effect_rule else 'Unknown Effect'

            html += f"""<div class="power-entry">
                            <div class="power-header">
                                <span class="power-name">{_escape_html(pwr_name)}{pwr_rank_display}</span>
                                <span class="power-cost">({pwr_cost} PP)</span>
                            </div>
                            <div class="power-base-effect"><em>Effect:</em> {_escape_html(base_effect_name)}</div>"""
            
            measurement_display = pwr.get('measurement_details_display')
            if measurement_display:
                html += f'<p class="power-sub-details"><strong>Details:</strong> {_escape_html(measurement_display)}</p>'
            
            # Display Array Info, Modifiers, Senses, Immunity, Variable Configs, Summon/Dupe notes
            # This needs the full logic from previous responses for comprehensive display
            if pwr.get('isAlternateEffectOf'):
                base_pwr_name = next((p.get('name') for p in powers if p.get('id') == pwr['isAlternateEffectOf']), "Unknown Base")
                html += f"<div class='power-array-info'><em>AE of: {_escape_html(base_pwr_name)} ({_escape_html(pwr.get('arrayId','N/A'))})</em></div>"
            elif pwr.get('isArrayBase'):
                array_type = "Dynamic Array" if any(m.get('id') == 'mod_dynamic_array' for m in pwr.get('modifiersConfig',[])) else "Static Array"
                html += f"<div class='power-array-info'><em>{array_type} Base ({_escape_html(pwr.get('arrayId','N/A'))})</em></div>"

            if pwr.get('modifiersConfig'):
                html += '<ul class="power-modifiers-list">'
                for mod_conf in pwr.get('modifiersConfig', []):
                    if mod_conf.get('id') == 'mod_dynamic_array' and pwr.get('isArrayBase'): continue
                    html += f"<li>{_format_modifier_for_pdf(mod_conf, all_power_modifier_rules, character_state, rule_data)}</li>"
                html += '</ul>'

            if base_effect_rule and base_effect_rule.get('isSenseContainer') and pwr.get('sensesConfig'):
                # ... (Senses display logic) ...
                html += "<p class='power-sub-details'><strong>Senses:</strong> ...</p>"
            if base_effect_rule and base_effect_rule.get('isImmunityContainer') and pwr.get('immunityConfig'):
                # ... (Immunity display logic) ...
                html += "<p class='power-sub-details'><strong>Immunities:</strong> ...</p>"
            if base_effect_rule and base_effect_rule.get('isVariableContainer'):
                html += f"<p class='power-sub-details'><strong>Descriptors:</strong> {_escape_html(pwr.get('variableDescriptors', 'N/A'))}</p>"
                html += f"<p class='power-sub-details'><strong>Point Pool:</strong> {pwr.get('variablePointPool',0)} PP to allocate</p>"
                if pwr.get('variableConfigurations'):
                    html += "<div class='variable-configs-list'><strong>Sample Configurations:</strong><ul>"
                    for cfg in pwr.get('variableConfigurations',[]):
                        html += f"<li><strong>{_escape_html(cfg.get('configName',''))}</strong> ({cfg.get('calculated_config_cost_engine',0)} PP): <pre class='config-traits-desc'>{_escape_html(cfg.get('configTraitsDescription','N/A'))}</pre></li>"
                    html += "</ul></div>"
            
            if base_effect_rule and base_effect_rule.get('isAllyEffect'): # Summon/Duplication
                html += f"<p class='power-sub-details'><em>Grants Ally Pool:</em> {pwr.get('allotted_pp_for_creation',0)} PP</p>"
                if pwr.get('ally_notes_and_stats_structured'): # If we use the structured block
                    ally_stats = pwr.get('ally_notes_and_stats_structured')
                    html += f"<div class='power-ally-notes'><strong>Summon/Duplicate Details:</strong><br/>"
                    html += f"  PL: {ally_stats.get('pl_for_ally','N/A')}, Asserted PP: {ally_stats.get('cost_pp_asserted_by_user',0)}<br/>"
                    html += f"  Abilities: {_escape_html(str(ally_stats.get('abilities_summary',{})))}<br/>"
                    html += f"  Defenses: {_escape_html(ally_stats.get('key_defenses','N/A'))}<br/>"
                    html += f"  Skills: {_escape_html(ally_stats.get('key_skills','N/A'))}<br/>"
                    html += f"  Powers/Adv: <pre>{_escape_html(ally_stats.get('key_powers_advantages','N/A'))}</pre></div>"


            html += "</div>" # power-entry
    html += "</div>" # powers-section
    return html

def _generate_equipment_html(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    # ... (Full implementation from previous response) ...
    html = """<div class="section equipment-section"><h3>Equipment</h3>"""
    total_ep = character_state.get('derived_total_ep',0)
    spent_ep = character_state.get('derived_spent_ep',0) # This should now sum HQs and Vehicles too
    html += f"<p class='ep-summary'>Spent: {spent_ep} EP / Total: {total_ep} EP</p>"
    # ... list items ...
    return html

def _generate_hq_html(character_state: CharacterState, rule_data: Dict[str, Any], engine_ref: 'CoreEngine') -> str:
    html = """<div class="section hq-section"><h3>Headquarters</h3>"""
    hqs = character_state.get('headquarters', [])
    if not hqs: html += "<p>None.</p>"
    else:
        for hq in hqs:
            size_rule = next((s for s in rule_data.get('hq_features',[]) if s.get('id') == hq.get('size_id')), None)
            size_name = size_rule.get('name','Unknown Size') if size_rule else 'Unknown Size'
            base_tough = size_rule.get('toughness_provided',0) if size_rule else 0
            total_tough = base_tough + hq.get('bought_toughness_ranks',0)
            html += f"<div class='hq-entry'><h4>{_escape_html(hq.get('name','Unnamed HQ'))} ({engine_ref.calculate_hq_cost(hq)} EP)</h4>"
            html += f"<p class='hq-stat'><strong>Size:</strong> {size_name}</p>"
            html += f"<p class='hq-stat'><strong>Toughness:</strong> {total_tough}</p>"
            if hq.get('features'):
                html += "<ul class='hq-feature-list'><strong>Features:</strong>"
                for feat_entry in hq.get('features',[]):
                    feat_rule = next((f for f in rule_data.get('hq_features',[]) if f['id'] == feat_entry['id']), None)
                    feat_name = feat_rule.get('name', feat_entry['id']) if feat_rule else feat_entry['id']
                    feat_rank_disp = f" {feat_entry['rank']}" if feat_rule and feat_rule.get('ranked') and feat_entry.get('rank',1) > 1 else ""
                    html += f"<li>{_escape_html(feat_name)}{feat_rank_disp}</li>"
                html += "</ul>"
            html += "</div>"
    html += "</div>"
    return html

def _generate_vehicles_html(character_state: CharacterState, rule_data: Dict[str, Any], engine_ref: 'CoreEngine') -> str:
    html = """<div class="section vehicle-section"><h3>Vehicles</h3>"""
    vehicles = character_state.get('vehicles', [])
    if not vehicles: html += "<p>None.</p>"
    else:
        for vh in vehicles:
            # Derive base stats from size_rank using vehicle_size_stats.json
            size_rank_val = vh.get('size_rank',0)
            size_stats_rule = next((s for s in rule_data.get('vehicle_size_stats',[]) if s.get('size_rank') == size_rank_val), None)
            base_str, base_spd, base_def, base_tou = 0,0,10,0 # Defaults
            if size_stats_rule:
                base_str = size_stats_rule.get('str',0)
                base_spd = size_stats_rule.get('spd',0)
                base_def = size_stats_rule.get('def',0)
                base_tou = size_stats_rule.get('tou',0)
            
            html += f"<div class='vehicle-entry'><h4>{_escape_html(vh.get('name','Unnamed Vehicle'))} ({engine_ref.calculate_vehicle_cost(vh)} EP)</h4>"
            html += f"<p class='vehicle-stat'><strong>Size Rank:</strong> {size_rank_val}</p>"
            html += f"<p class='vehicle-stat'><strong>Strength:</strong> {base_str} | <strong>Speed:</strong> {base_spd} | <strong>Defense:</strong> {base_def} | <strong>Toughness:</strong> {base_tou}</p>" # These can be enhanced by features
            if vh.get('features'):
                html += "<ul class='vehicle-feature-list'><strong>Features:</strong>"
                for feat_entry in vh.get('features',[]):
                    feat_rule = next((f for f in rule_data.get('vehicle_features',[]) if f['id'] == feat_entry['id']), None)
                    feat_name = feat_rule.get('name', feat_entry['id']) if feat_rule else feat_entry['id']
                    feat_rank_disp = f" {feat_entry['rank']}" if feat_rule and feat_rule.get('ranked') and feat_entry.get('rank',1) > 1 else ""
                    html += f"<li>{_escape_html(feat_name)}{feat_rank_disp}</li>"
                html += "</ul>"
            html += "</div>"
    html += "</div>"
    return html

def _generate_allies_html(character_state: CharacterState, rule_data: Dict[str, Any], engine_ref: 'CoreEngine') -> str:
    # ... (Full implementation from previous response, displaying structured stat blocks) ...
    html = """<div class="section allies-section"><h3>Companions</h3>"""
    allies = character_state.get('allies', [])
    if not allies: html += "<p>None.</p>"
    else:
        # Display Minion/Sidekick Pool Summaries
        min_pool = character_state.get('derived_total_minion_pool_pp', 0)
        min_spent = character_state.get('derived_spent_minion_pool_pp', 0)
        side_pool = character_state.get('derived_total_sidekick_pool_pp', 0)
        side_spent = character_state.get('derived_spent_sidekick_pool_pp', 0)
        if min_pool > 0: html += f"<p><strong>Minion Pool:</strong> {min_spent} / {min_pool} PP</p>"
        if side_pool > 0: html += f"<p><strong>Sidekick Pool:</strong> {side_spent} / {side_pool} PP</p>"

        for ally in allies:
            html += f"""
            <div class="ally-entry">
                <h4>{_escape_html(ally.get('name', 'Unnamed'))} ({_escape_html(ally.get('type', 'N/A'))}) - PL {ally.get('pl_for_ally','N/A')}</h4>
                <p><strong>Asserted PP Cost for Build:</strong> {ally.get('cost_pp_asserted_by_user', 0)}</p>
                <div class="ally-stat-block">
                    <p><strong>Key Abilities:</strong> {_escape_html(str(ally.get('abilities_summary', {})))}</p>
                    <p><strong>Key Defenses:</strong> {_escape_html(ally.get('key_defenses', 'N/A'))}</p>
                    <p><strong>Key Skills:</strong> {_escape_html(ally.get('key_skills', 'N/A'))}</p>
                    <div><strong>Key Powers/Advantages:</strong><pre>{_escape_html(ally.get('key_powers_advantages', 'N/A'))}</pre></div>
                    <div><strong>Notes:</strong><pre>{_escape_html(ally.get('notes', 'N/A'))}</pre></div>
                </div>
            </div>"""
    # Also list Summons/Duplicates from powers (if they have stat blocks stored)
    # This requires powers to store their detailed ally_notes_and_stats_structured
    # ...
    html += "</div>"
    return html

def _generate_complications_html(character_state: CharacterState) -> str:
    # ... (Full implementation from previous response) ...
    html = """<div class="section complications-section"><h3>Complications</h3><ul>"""
    complications = character_state.get('complications',[])
    if not complications: html += "<li>None (Min. 2 Recommended)</li>"
    else:
        for comp in complications: html+= f"<li>{_escape_html(comp.get('description','N/A'))}</li>"
    html += "</ul></div>"
    return html

def _generate_footer_html(character_state: CharacterState) -> str:
    # ... (Full implementation from previous response with Hero Points, Conditions, Notes area) ...
    html = """
    <footer class="sheet-footer">
        <div class="section footer-notes-section">
            <div class="hero-points"><strong>Hero Points:</strong> <span class="value-box"></span> <span class="value-box"></span> <span class="value-box"></span> </div>
            <div class="conditions-track"><strong>Conditions Track:</strong> <span class="line-fill"></span></div>
            <div class="general-notes"><strong>Notes:</strong> <div class="notes-area"></div></div>
        </div>
    </footer>
    """
    return html

# --- Main PDF Generation Functions ---
def generate_pdf_html_content(character_state: CharacterState, rule_data: RuleData, engine_ref: 'CoreEngine') -> str:
    """Generates the full HTML content string for the character sheet."""
    char_name = character_state.get('name', 'M&M Character')
    
    # Ensure derived values are present for PDF generation
    # Note: recalculate should have already populated these on character_state
    # but calling it here ensures PDF always gets latest.
    # However, this might be slow if called every time PDF is generated.
    # Best practice: PDF generation should use the *already calculated* state.
    # For safety, if some derived values were on engine, pass engine_ref.

    html_parts = [
        _generate_html_head(char_name),
        "<body><div class='sheet-container'>",
        _generate_sheet_header_html(character_state),
        "<main class='sheet-body'>",
        "<section class='column column-one'>",
        _generate_abilities_html(character_state, rule_data, engine_ref),
        _generate_defenses_html(character_state, rule_data, engine_ref),
        _generate_combat_summary_html(character_state, rule_data, engine_ref),
        "</section>",
        "<section class='column column-two'>",
        _generate_skills_html(character_state, rule_data, engine_ref),
        _generate_advantages_html(character_state, rule_data, engine_ref),
        _generate_equipment_html(character_state, rule_data, engine_ref), # Standard Gear
        "</section>",
        "<section class='column column-three'>",
        _generate_powers_html(character_state, rule_data, engine_ref), # This can be long
        _generate_complications_html(character_state),
        _generate_allies_html(character_state, rule_data, engine_ref), # Minions, Sidekicks, Summons
        _generate_hq_html(character_state, rule_data, engine_ref), # HQs
        _generate_vehicles_html(character_state, rule_data, engine_ref), # Vehicles
        "</section>",
        "</main>",
        _generate_footer_html(character_state),
        "</div></body></html>"
    ]
    return "\n".join(html_parts)

def generate_pdf_bytes(character_state: CharacterState, rule_data_ref: RuleData, engine_ref: 'CoreEngine') -> Optional[BytesIO]:
    """Generates PDF bytes using WeasyPrint from the character state."""
    if not WEASYPRINT_AVAILABLE:
        print("Error: WeasyPrint is not installed. PDF generation aborted.")
        return None
    
    try:
        html_string = generate_pdf_html_content(character_state, rule_data_ref, engine_ref)
        
        css_string = ""
        # Try to load external CSS, provide extensive defaults if not found
        # The Dockerfile should ensure pdf_styles.css is in assets/
        css_file_path = "assets/pdf_styles.css" 
        try:
            with open(css_file_path, "r", encoding="utf-8") as f:
                css_string = f.read()
            print(f"Loaded CSS from {css_file_path}")
        except FileNotFoundError:
            print(f"Warning: '{css_file_path}' not found. Using fallback basic PDF styles.")
            # Provide more robust fallback CSS here if the file is critical
            css_string = """ 
                body { font-family: sans-serif; margin: 20mm; font-size: 9pt; line-height: 1.3; } 
                h1, h3 { color: #333; } .section { margin-bottom: 12px; padding: 8px; border: 1px solid #ddd; page-break-inside: avoid;}
                /* Add more essential fallback styles for basic readability */
            """
        
        font_config = FontConfiguration() # For potential custom font handling later
        
        pdf_bytes_io = BytesIO()
        HTML(string=html_string, base_url=os.getcwd()).write_pdf(
            pdf_bytes_io,
            stylesheets=[CSS(string=css_string, font_config=font_config)],
            font_config=font_config
            # presentational_hints=True # If relying on some HTML attributes for styling
        )
        pdf_bytes_io.seek(0)
        print("PDF generated successfully in memory.")
        return pdf_bytes_io
    except Exception as e:
        print(f"Error during PDF generation with WeasyPrint: {e}")
        # Consider logging the full traceback for debugging
        # import traceback
        # print(traceback.format_exc())
        return None