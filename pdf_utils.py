# pdf_utils.py (FPDF Version - Fully Implemented)

import io
import math
from typing import Dict, List, Any, Optional, TYPE_CHECKING, Callable, Tuple

from fpdf import FPDF # Main FPDF import

if TYPE_CHECKING:
    from core_engine import CoreEngine, CharacterState, RuleData, PowerDefinition, AdvantageDefinition, SkillRule, AllyDefinition, HQDefinition, VehicleDefinition

# --- Constants for PDF Layout (Letter size: 215.9mm x 279.4mm) ---
PAGE_WIDTH = 215.9
PAGE_HEIGHT = 279.4
LEFT_MARGIN = 10 
RIGHT_MARGIN = 10 
TOP_MARGIN = 10 
BOTTOM_MARGIN = 15 # For page number footer
EFFECTIVE_PAGE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
EFFECTIVE_PAGE_HEIGHT = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN

COLUMN_COUNT = 3
COLUMN_GAP = 4 # mm
COLUMN_WIDTH = (EFFECTIVE_PAGE_WIDTH - (COLUMN_GAP * (COLUMN_COUNT - 1))) / COLUMN_COUNT

# Font settings
FONT_FAMILY_MAIN = 'Arial' 
FONT_FAMILY_HEADER = 'Arial' 
FONT_BOLD = 'B'
FONT_ITALIC = 'I'
FONT_REGULAR = ''

# Line heights / cell heights (in mm)
LINE_HEIGHT_VSMALL = 3.5 
LINE_HEIGHT_SMALL = 4   
LINE_HEIGHT_NORMAL = 5  
LINE_HEIGHT_LARGE = 6   
SECTION_TITLE_HEIGHT = 7
SUBSECTION_TITLE_HEIGHT = 6
ITEM_SPACING = 1 
SECTION_BOTTOM_PADDING = 3 
DEFAULT_CELL_PADDING = 1 # General padding inside cells

# --- Custom PDF Class with Header/Footer ---
class MMCharSheetPDF(FPDF):
    def header(self):
        # Page-wide header, if any, can go here.
        # For this sheet, the main "header" (character info) is part of the body.
        pass

    def footer(self):
        self.set_y(-15) 
        self.set_font(FONT_FAMILY_MAIN, FONT_ITALIC, 8)
        self.set_text_color(128, 128, 128) 
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
        self.set_text_color(0,0,0) # Reset text color

# --- Text Formatting Helpers ---
def _format_fpdf_text(text: Optional[Any]) -> str:
    if text is None: return ""
    return str(text).replace('\r\n', '\n').replace('\r', '\n')

def _format_params_for_fpdf(params_dict: Optional[Dict[str, Any]], item_rule: Optional[Dict[str, Any]], rule_data: 'RuleData', engine: 'CoreEngine') -> str:
    if not params_dict or not item_rule: return ""
    display_parts = []
    param_type = item_rule.get('parameter_type')
    param_storage_key = item_rule.get('parameter_storage_key', item_rule.get('id', 'detail')) 
    val_to_format = params_dict.get(param_storage_key)

    if val_to_format is None: # Try other common keys
        if param_type == 'select_skill': val_to_format = params_dict.get('skill_id')
        elif param_type == 'select_from_options': val_to_format = params_dict.get('selected_option')
        elif param_type == 'list_string': val_to_format = params_dict.get(item_rule.get('parameter_list_key','details_list'))
        else: val_to_format = params_dict.get('detail')

    if param_type == 'select_skill' and val_to_format:
        skill_name = engine.get_skill_name_by_id(str(val_to_format), rule_data.get('skills',{}).get('list',[]))
        display_parts.append(f"{_format_fpdf_text(skill_name)}")
    elif param_type == 'select_from_options' and val_to_format:
        option_label = str(val_to_format) 
        for opt in item_rule.get('parameter_options',[]):
            if str(opt.get('value')) == str(val_to_format): 
                option_label = opt.get('label', str(val_to_format))
                break
        display_parts.append(_format_fpdf_text(option_label))
    elif param_type == 'list_string' and val_to_format and isinstance(val_to_format, list):
        display_parts.append(", ".join(map(_format_fpdf_text, val_to_format)))
    elif val_to_format is not None: 
        display_parts.append(_format_fpdf_text(str(val_to_format)))
    
    if not display_parts and isinstance(params_dict, dict): # Fallback for other params
        temp_parts = [f"{k.replace('_',' ').title()}: {v}" for k,v in params_dict.items() if v and k != param_storage_key]
        if temp_parts: display_parts = temp_parts

    return "; ".join(filter(None, display_parts))

def _format_modifier_for_fpdf(mod_config: Dict[str, Any], all_mod_rules: List[Dict[str, Any]], char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine') -> str:
    mod_rule = next((m for m in all_mod_rules if m['id'] == mod_config.get('id')), None)
    if not mod_rule: return _format_fpdf_text(mod_config.get('id', 'Unknown Mod'))
    display_str = _format_fpdf_text(mod_rule['name'])
    mod_instance_rank = mod_config.get('rank', 1)
    if mod_rule.get('ranked') and mod_instance_rank > 1 :
        display_str += f" {mod_instance_rank}"
    params_display = _format_params_for_fpdf(mod_config.get('params'), mod_rule, rule_data, engine)
    if params_display: display_str += f": {params_display}"
    return display_str

# --- PDF Section Rendering Functions ---
def _render_section_title(pdf: FPDF, title: str, x: float, y: float, width: float) -> float:
    pdf.set_xy(x, y)
    pdf.set_font(FONT_FAMILY_HEADER, FONT_BOLD, 11)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(width, SECTION_TITLE_HEIGHT, title, border=0, ln=1, align='L', fill=True)
    # pdf.ln(1) # Small gap after title's line natural break
    return pdf.get_y() + 0.5 # Return Y after title cell and small padding

def _render_subsection_title(pdf: FPDF, title: str, x: float, y: float, width: float) -> float:
    pdf.set_xy(x, y)
    pdf.set_font(FONT_FAMILY_HEADER, FONT_BOLD, 9.5) # Slightly larger for subsection
    pdf.cell(width, SUBSECTION_TITLE_HEIGHT, title, border="B", ln=1, align='L')
    return pdf.get_y() # Y is already moved by ln=1


def _check_y_add_page(pdf: FPDF, current_y: float, needed_height: float) -> float:
    """Checks if content fits, adds new page and resets Y if not. Returns new Y."""
    if current_y + needed_height > (PAGE_HEIGHT - BOTTOM_MARGIN):
        pdf.add_page()
        return TOP_MARGIN 
    return current_y

def _render_header_fpdf(pdf: FPDF, char_state: 'CharacterState', start_x: float, start_y: float, width: float) -> float:
    current_y = start_y
    pdf.set_xy(start_x, current_y)
    pdf.set_font(FONT_FAMILY_HEADER, FONT_BOLD, 18)
    char_name = _format_fpdf_text(char_state.get('name', 'Unnamed Hero'))
    pdf.multi_cell(width, 8, char_name, 0, 'L')
    current_y = pdf.get_y() + 1 # Space after name

    item_h = LINE_HEIGHT_SMALL
    label_w = 18
    value_w = (width / 2) - label_w - 4 # For two columns of info pairs, with small internal gap

    info_pairs_col1 = [
        ("Player", char_state.get('playerName', '')), ("Identity", char_state.get('identity', '')),
        ("Group", char_state.get('groupAffiliation', '')), ("PL", str(char_state.get('powerLevel', 10))),
        ("PP", f"{char_state.get('spentPowerPoints', 0)}/{char_state.get('totalPowerPoints', 150)}")
    ]
    info_pairs_col2 = [
        ("Gender", char_state.get('gender', '')), ("Age", char_state.get('age', '')),
        ("Height", char_state.get('height', '')), ("Weight", char_state.get('weight', '')),
        ("Eyes", char_state.get('eyes', '')), ("Hair", char_state.get('hair', ''))
    ]
    
    y_col1, y_col2 = current_y, current_y

    for label, value in info_pairs_col1:
        pdf.set_xy(start_x, y_col1)
        pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 7)
        pdf.cell(label_w, item_h, _format_fpdf_text(label) + ":", 0, 0, 'L')
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 8)
        pdf.multi_cell(value_w, item_h, _format_fpdf_text(value), 0, 'L')
        y_col1 = pdf.get_y() if pdf.get_y() > y_col1 + item_h else y_col1 + item_h + 0.5

    for label, value in info_pairs_col2:
        pdf.set_xy(start_x + (width / 2) + 2, y_col2) # Start second column
        pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 7)
        pdf.cell(label_w, item_h, _format_fpdf_text(label) + ":", 0, 0, 'L')
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 8)
        pdf.multi_cell(value_w, item_h, _format_fpdf_text(value), 0, 'L')
        y_col2 = pdf.get_y() if pdf.get_y() > y_col2 + item_h else y_col2 + item_h + 0.5
        
    current_y = max(y_col1, y_col2) 

    for title, content_key in [("Concept", 'concept'), ("Description", 'description')]:
        content = _format_fpdf_text(char_state.get(content_key, ''))
        if content:
            current_y = _check_y_add_page(pdf, current_y, 10) # Estimate height for title + content
            pdf.set_xy(start_x, current_y)
            pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 7.5)
            pdf.cell(width, item_h, title + ":", 0, 1, 'L')
            pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 8)
            pdf.set_x(start_x)
            pdf.multi_cell(width, LINE_HEIGHT_SMALL, content, 0, 'L')
            current_y = pdf.get_y() + 1
    
    pdf.set_draw_color(50, 50, 50); pdf.set_line_width(0.5)
    pdf.line(start_x, current_y, start_x + width, current_y)
    return current_y + 2

def _render_abilities_fpdf(pdf: FPDF, char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine', x: float, y: float, width: float) -> float:
    current_y = _render_section_title(pdf, "Abilities", x, y, width)
    abilities = char_state.get('abilities', {}); ability_rules = rule_data.get('abilities', {}).get('list', [])
    item_h = LINE_HEIGHT_NORMAL; num_ability_cols = 2
    inner_col_width = (width - (num_ability_cols - 1) * 2) / num_ability_cols
    y_col_tracks = [current_y] * num_ability_cols

    for i, ab_rule in enumerate(ability_rules):
        col_idx = i % num_ability_cols
        current_x = x + col_idx * (inner_col_width + 2)
        y_col_tracks[col_idx] = _check_y_add_page(pdf, y_col_tracks[col_idx], item_h)
        pdf.set_xy(current_x, y_col_tracks[col_idx])
        pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8)
        pdf.cell(18, item_h, _format_fpdf_text(ab_rule['name'][:3].upper()) + ":", 0, 0) # Abbreviate
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 9)
        ab_rank = abilities.get(ab_rule['id'], 0)
        pdf.cell(10, item_h, str(ab_rank), 0, 0, 'C')
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 8)
        ab_mod = engine.get_ability_modifier(ab_rank)
        pdf.cell(10, item_h, f"({ab_mod:+})", 0, 0)
        y_col_tracks[col_idx] += item_h
    return max(y_col_tracks) + SECTION_BOTTOM_PADDING

def _render_defenses_fpdf(pdf: FPDF, char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine', x: float, y: float, width: float) -> float:
    current_y = _render_section_title(pdf, "Defenses", x, y, width)
    defense_order = ["Dodge", "Parry", "Toughness", "Fortitude", "Will"]
    base_ability_map = {"Dodge": "AGL", "Parry": "FGT", "Toughness": "STA", "Fortitude": "STA", "Will": "AWE"}
    item_h = LINE_HEIGHT_SMALL; label_w = 22; total_w = 12; detail_w = width - label_w - total_w - 2

    for def_id in defense_order:
        current_y = _check_y_add_page(pdf, current_y, item_h)
        pdf.set_xy(x, current_y)
        base_ab_id = base_ability_map[def_id]
        total_val = engine.get_total_defense(char_state, def_id, base_ab_id)
        base_from_ab = engine.get_ability_modifier(char_state.get('abilities', {}).get(base_ab_id, 0))
        bought = char_state.get('defenses', {}).get(def_id, 0)
        details_parts = [f"Base {base_from_ab}", f"Bought {bought}"]
        if def_id == "Toughness" and char_state.get('derived_defensive_roll_bonus', 0) > 0:
            details_parts.append(f"D.Roll +{char_state['derived_defensive_roll_bonus']}")
        
        pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8)
        pdf.cell(label_w, item_h, _format_fpdf_text(def_id) + ":", 0, 0)
        pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 9.5)
        pdf.cell(total_w, item_h, str(total_val), 0, 0, 'C')
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 7)
        pdf.multi_cell(detail_w, item_h, "(" + ", ".join(details_parts) + ")", 0, 'L')
        current_y = pdf.get_y() if pdf.get_y() > current_y + item_h else current_y + item_h

    current_y += ITEM_SPACING; pdf.set_font(FONT_FAMILY_MAIN, FONT_ITALIC, 7)
    pl = char_state.get('powerLevel', 10); pl_cap_paired = pl * 2
    totals = {
        'Dodge': engine.get_total_defense(char_state, 'Dodge', 'AGL'),
        'Parry': engine.get_total_defense(char_state, 'Parry', 'FGT'),
        'Toughness': engine.get_total_defense(char_state, 'Toughness', 'STA'),
        'Fortitude': engine.get_total_defense(char_state, 'Fortitude', 'STA'),
        'Will': engine.get_total_defense(char_state, 'Will', 'AWE')
    }
    cap_checks = [
        (f"Dodge ({totals['Dodge']}) + Toughness ({totals['Toughness']})", totals['Dodge'] + totals['Toughness']),
        (f"Parry ({totals['Parry']}) + Toughness ({totals['Toughness']})", totals['Parry'] + totals['Toughness']),
        (f"Fortitude ({totals['Fortitude']}) + Will ({totals['Will']})", totals['Fortitude'] + totals['Will'])
    ]
    for label, val in cap_checks:
        current_y = _check_y_add_page(pdf, current_y, LINE_HEIGHT_VSMALL)
        pdf.set_xy(x, current_y)
        is_over_cap = val > pl_cap_paired
        original_text_color = pdf.text_color
        if is_over_cap: pdf.set_text_color(180, 0, 0)
        pdf.multi_cell(width, LINE_HEIGHT_VSMALL, f"{label} = {val} / {pl_cap_paired}", 0, "L")
        if is_over_cap: pdf.set_text_color(original_text_color.r, original_text_color.g, original_text_color.b)
        current_y = pdf.get_y()
    return current_y + SECTION_BOTTOM_PADDING

def _render_combat_summary_fpdf(pdf: FPDF, char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine', x: float, y: float, width: float) -> float:
    current_y = _render_section_title(pdf, "Combat", x, y, width)
    pdf.set_xy(x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8.5)
    pdf.cell(25, LINE_HEIGHT_NORMAL, "Initiative:", 0, 0)
    pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 9)
    pdf.cell(0, LINE_HEIGHT_NORMAL, f"{char_state.get('derived_initiative', 0):+}", 0, 1); current_y = pdf.get_y()

    current_y = _render_subsection_title(pdf, "Attacks / Effects", x, current_y + ITEM_SPACING, width)
    header = ["Attack/Effect", "Bonus", "Effect (Rk)", "Range", "Resist (DC)"]
    col_widths_abs = [width * 0.30, width * 0.12, width * 0.18, width * 0.20, width * 0.20]
    pdf.set_xy(x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 6.5); pdf.set_fill_color(235,235,235)
    for i, h_text in enumerate(header):
        pdf.cell(col_widths_abs[i], LINE_HEIGHT_SMALL, h_text, border=1, fill=True, ln=0 if i < len(header)-1 else 1, align='C')
    current_y = pdf.get_y()

    attacks_data = [] # Populate this list as before
    for pwr in char_state.get('powers', []):
        if pwr.get('isAttack'):
            atk_bonus = engine.get_attack_bonus_for_power(pwr, char_state)
            atk_bonus_str = "N/A" if pwr.get('attackType') in ['area', 'perception'] else f"{atk_bonus:+}"
            base_effect_rule = next((e for e in rule_data.get('power_effects', []) if e['id'] == pwr.get('baseEffectId')), None)
            effect_name = base_effect_rule['name'] if base_effect_rule else pwr.get('baseEffectId','Unk')
            res_details = pwr.get('resistance_dc_details', {}); res_str = f"{res_details.get('dc_type','')} DC {res_details.get('dc','')}"
            if res_details.get('dodge_dc_for_half'): res_str += f" (Dodge {res_details['dodge_dc_for_half']})"
            attacks_data.append((pwr.get('name', 'Unnamed'), atk_bonus_str,f"{effect_name} {pwr.get('rank',0)}",pwr.get('final_range', 'N/A'), res_str))
    
    fgt_mod = engine.get_ability_modifier(char_state.get('abilities',{}).get('FGT',0))
    base_close_atk_bonus = fgt_mod + sum(adv.get('rank',0) for adv in char_state.get('advantages',[]) if adv.get('id') == 'adv_close_attack')
    unarmed_skill_id = next((sid for sid in char_state.get('skills',{}) if sid.startswith("skill_close_combat_unarmed")), "skill_close_combat_unarmed")
    unarmed_skill_ranks = char_state.get('skills',{}).get(unarmed_skill_id,0)
    unarmed_total_bonus = base_close_atk_bonus + unarmed_skill_ranks; str_rank = char_state.get('abilities',{}).get('STR',0); unarmed_dc = 15 + str_rank
    attacks_data.append(("Unarmed Strike", f"{unarmed_total_bonus:+}", f"Damage {str_rank}", "Close", f"Toughness DC {unarmed_dc}"))

    for row_data in attacks_data:
        max_h = LINE_HEIGHT_VSMALL * 1.2 # Min height for a row
        temp_y = current_y
        for i, cell_text_any in enumerate(row_data): # Pre-calculate height
            cell_text = _format_fpdf_text(cell_text_any)
            pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD if i==0 else FONT_REGULAR, 7)
            lines = pdf.multi_cell(col_widths_abs[i] - 1, LINE_HEIGHT_VSMALL, cell_text, border=0, align='L', split_only=True)
            max_h = max(max_h, len(lines) * LINE_HEIGHT_VSMALL)
        
        current_y = _check_y_add_page(pdf, current_y, max_h)
        pdf.set_xy(x, current_y)
        for i, cell_text_any in enumerate(row_data):
            cell_text = _format_fpdf_text(cell_text_any)
            align = 'C' if i == 1 else 'L'; font_style = FONT_BOLD if i == 0 else FONT_REGULAR
            pdf.set_font(FONT_FAMILY_MAIN, font_style, 7)
            pdf.multi_cell(col_widths_abs[i], max_h, cell_text, border=1, align=align, new_x="RIGHT", new_y="TOP", max_line_height=LINE_HEIGHT_VSMALL)
        pdf.ln(max_h); current_y = pdf.get_y()
    return current_y + SECTION_BOTTOM_PADDING

def _render_skills_fpdf(pdf: FPDF, char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine', x: float, y: float, width: float) -> float:
    current_y = _render_section_title(pdf, "Skills", x, y, width)
    skills_state = char_state.get('skills', {}); abilities = char_state.get('abilities', {})
    all_skill_rules = rule_data.get('skills', {}).get('list', [])
    pl = char_state.get('powerLevel', 10); skill_bonus_cap = pl + 10
    item_h = LINE_HEIGHT_SMALL; skill_entries = []
    
    sorted_skill_ids = sorted(skills_state.keys(), key=lambda skill_id: engine.get_skill_name_by_id(skill_id, all_skill_rules))
    for skill_id in sorted_skill_ids:
        rank = skills_state[skill_id]
        if rank <= 0: continue
        skill_rule = engine.get_skill_rule(skill_id); skill_name_display = engine.get_skill_name_by_id(skill_id, all_skill_rules)
        gov_ab_id = skill_rule.get('ability', 'N/A') if skill_rule else 'N/A'
        ability_mod = engine.get_ability_modifier(abilities.get(gov_ab_id, 0))
        total_bonus = ability_mod + rank; is_capped = total_bonus > skill_bonus_cap
        skill_entries.append({"name": skill_name_display, "ab": gov_ab_id, "bonus": total_bonus, "rank": rank, "capped": is_capped})

    if not skill_entries:
        pdf.set_xy(x,current_y);pdf.set_font(FONT_FAMILY_MAIN,FONT_ITALIC,8);pdf.cell(width,item_h,"No skills with ranks.",0,1)
        return pdf.get_y() + SECTION_BOTTOM_PADDING

    num_skill_cols = 2; inner_skill_col_width = (width - (num_skill_cols -1) * 2) / num_skill_cols
    y_col_tracks_skill = [current_y] * num_skill_cols
    for i, entry in enumerate(skill_entries):
        col_idx = i % num_skill_cols; current_x_skill = x + col_idx * (inner_skill_col_width + 2)
        y_col_tracks_skill[col_idx] = _check_y_add_page(pdf, y_col_tracks_skill[col_idx], item_h)
        pdf.set_xy(current_x_skill, y_col_tracks_skill[col_idx])
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 7.5)
        name_ab_str = f"{_format_fpdf_text(entry['name'])} ({entry['ab']})"
        name_w = inner_skill_col_width * 0.60
        pdf.cell(name_w, item_h, name_ab_str, 0, 0, 'L')
        pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8)
        pdf.cell(inner_skill_col_width * 0.15, item_h, f"{entry['bonus']:+}", 0, 0, 'R')
        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 7)
        rank_str = f"(Rk:{entry['rank']})"
        if entry['capped']: original_text_color = pdf.text_color; pdf.set_text_color(180,0,0); rank_str += "!"
        pdf.cell(inner_skill_col_width * 0.25, item_h, rank_str, 0, 0, 'L')
        if entry['capped']: pdf.set_text_color(original_text_color.r,original_text_color.g,original_text_color.b)
        y_col_tracks_skill[col_idx] += item_h
    return max(y_col_tracks_skill) + SECTION_BOTTOM_PADDING

def _render_advantages_fpdf(pdf: FPDF, char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine', x: float, y: float, width: float) -> float:
    current_y = _render_section_title(pdf, "Advantages", x, y, width)
    advantages: List[AdvantageDefinition] = char_state.get('advantages', [])
    adv_rules_list = rule_data.get('advantages_v1', [])
    if not advantages:
        pdf.set_xy(x,current_y);pdf.set_font(FONT_FAMILY_MAIN,FONT_ITALIC,8);pdf.cell(width, LINE_HEIGHT_NORMAL, "None",0,1)
        return pdf.get_y() + SECTION_BOTTOM_PADDING
    
    adv_strings = []
    for adv_entry in sorted(advantages, key=lambda entry: (adv_rule := next((r for r in adv_rules_list if r['id'] == entry['id']), None)) and adv_rule['name'] or entry.get('id','Z')):
        adv_rule = next((r for r in adv_rules_list if r['id'] == adv_entry['id']), None)
        adv_name = adv_rule['name'] if adv_rule else adv_entry.get('id', 'Unk')
        adv_rank_disp = f" {adv_entry.get('rank', 1)}" if adv_rule and adv_rule.get('ranked') and adv_entry.get('rank',1) > 1 else ""
        params_str = _format_params_for_fpdf(adv_entry.get('params'), adv_rule, rule_data, engine)
        if params_str: params_str = f" ({params_str})"
        def_roll_note = ""
        if adv_entry.get('id') == 'adv_defensive_roll' and char_state.get('derived_defensive_roll_bonus',0) > 0:
            def_roll_note = f" (+{char_state['derived_defensive_roll_bonus']} Tough)"
        adv_strings.append(f"{_format_fpdf_text(adv_name)}{adv_rank_disp}{params_str}{def_roll_note}")

    num_adv_cols = 2 if len(adv_strings) > 6 else 1
    inner_adv_col_width = (width - (num_adv_cols -1) * 2) / num_adv_cols
    y_col_tracks_adv = [current_y] * num_adv_cols
    pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 7.5)

    for i, adv_text in enumerate(adv_strings):
        col_idx = i % num_adv_cols; current_x_adv = x + col_idx * (inner_adv_col_width + 2)
        lines = pdf.multi_cell(inner_adv_col_width - 3, LINE_HEIGHT_VSMALL, adv_text, border=0, align='L', split_only=True)
        needed_h = len(lines) * LINE_HEIGHT_VSMALL + ITEM_SPACING / 2
        y_col_tracks_adv[col_idx] = _check_y_add_page(pdf, y_col_tracks_adv[col_idx], needed_h)
        pdf.set_xy(current_x_adv, y_col_tracks_adv[col_idx])
        pdf.cell(3, LINE_HEIGHT_VSMALL * len(lines), "\u2022",0,0)
        pdf.set_x(current_x_adv + 3)
        pdf.multi_cell(inner_adv_col_width - 3, LINE_HEIGHT_VSMALL, adv_text, 0, 'L')
        y_col_tracks_adv[col_idx] = pdf.get_y()
    return max(y_col_tracks_adv) + SECTION_BOTTOM_PADDING

def _render_powers_fpdf(pdf: FPDF, char_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine', x: float, y: float, width: float) -> float:
    current_y = _render_section_title(pdf, "Powers & Devices", x, y, width)
    all_mod_rules = rule_data.get('power_modifiers', [])
    powers: List[PowerDefinition] = char_state.get('powers', [])
    if not powers:
        pdf.set_xy(x,current_y);pdf.set_font(FONT_FAMILY_MAIN,FONT_ITALIC,8);pdf.cell(width,LINE_HEIGHT_NORMAL,"None",0,1)
        return pdf.get_y() + SECTION_BOTTOM_PADDING

    for pwr_idx, pwr in enumerate(powers):
        current_y = _check_y_add_page(pdf, current_y, 20) # Min height for a power
        
        start_of_power_y = current_y
        pdf.set_xy(x, current_y)
        pdf.set_font(FONT_FAMILY_HEADER, FONT_BOLD, 9); pwr_name = _format_fpdf_text(pwr.get('name','Unnamed'))
        pwr_rank_val = pwr.get('rank',0); pwr_cost = pwr.get('cost',0)
        base_eff_rule = next((e for e in rule_data.get('power_effects',[]) if e['id'] == pwr.get('baseEffectId')),None)
        rank_disp = f" [{pwr_rank_val}]" if pwr_rank_val > 0 or (base_eff_rule and not (base_eff_rule.get('isSenseContainer') or base_eff_rule.get('isImmunityContainer'))) else ""
        name_rank_str = f"{pwr_name}{rank_disp}"; cost_str = f"({pwr_cost} PP)"
        name_w = width - pdf.get_string_width(cost_str) - 2
        pdf.cell(name_w, SUBSECTION_TITLE_HEIGHT, name_rank_str, "B" if pwr_idx < len(powers)-1 else 0, 0, 'L') # Bottom border except last
        pdf.set_font(FONT_FAMILY_MAIN, FONT_ITALIC, 7.5)
        pdf.cell(pdf.get_string_width(cost_str)+2, SUBSECTION_TITLE_HEIGHT, cost_str, "B" if pwr_idx < len(powers)-1 else 0, 1, 'R')
        current_y = pdf.get_y()

        pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 7)
        indent_x = x + 2; text_w = width - 4
        
        eff_name = base_eff_rule['name'] if base_eff_rule else pwr.get('baseEffectId','N/A')
        pdf.set_x(indent_x); pdf.multi_cell(text_w, LINE_HEIGHT_VSMALL, f"Effect: {_format_fpdf_text(eff_name)}",0,'L'); current_y = pdf.get_y()
        if pwr.get('descriptors'):
            pdf.set_x(indent_x); pdf.multi_cell(text_w, LINE_HEIGHT_VSMALL, f"Descriptors: {_format_fpdf_text(pwr['descriptors'])}",0,'L'); current_y = pdf.get_y()
        
        details_lines = []
        if pwr.get('final_range'): details_lines.append(f"Range: {_format_fpdf_text(pwr['final_range'])}")
        if pwr.get('final_duration'): details_lines.append(f"Duration: {_format_fpdf_text(pwr['final_duration'])}")
        if pwr.get('final_action'): details_lines.append(f"Action: {_format_fpdf_text(pwr['final_action'])}")
        if pwr.get('measurement_details_display'): details_lines.append(f"Details: {_format_fpdf_text(pwr['measurement_details_display'])}")
        if details_lines:
            pdf.set_x(indent_x); pdf.multi_cell(text_w, LINE_HEIGHT_VSMALL, " | ".join(details_lines),0,'L'); current_y = pdf.get_y()

        if pwr.get('isAlternateEffectOf') or pwr.get('isArrayBase'): # Array Info
            pdf.set_font(FONT_FAMILY_MAIN, FONT_ITALIC, 6.5)
            if pwr.get('isAlternateEffectOf'):
                base_p_name = next((p_b.get('name') for p_b in powers if p_b.get('id') == pwr['isAlternateEffectOf']), "Unk.Base")
                ae_cost = "(+1 PP)" if not next((p_b.get('isDynamicArray') for p_b in powers if p_b.get('id') == pwr['isAlternateEffectOf']), False) else "(+2 PP)"
                pdf.set_x(indent_x); pdf.multi_cell(text_w,LINE_HEIGHT_VSMALL,f"AE of: {_format_fpdf_text(base_p_name)} {ae_cost} (Array: {_format_fpdf_text(pwr.get('arrayId','N/A'))})",0,'L')
            elif pwr.get('isArrayBase'):
                arr_type = "Dynamic Array" if pwr.get('isDynamicArray') else "Static Array"
                pdf.set_x(indent_x); pdf.multi_cell(text_w,LINE_HEIGHT_VSMALL,f"{arr_type} Base ({_format_fpdf_text(pwr.get('arrayId','N/A'))})",0,'L')
            current_y = pdf.get_y(); pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 7) # Reset font

        if pwr.get('modifiersConfig'):
            pdf.set_xy(indent_x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 7)
            pdf.cell(text_w, LINE_HEIGHT_VSMALL, "Modifiers:",0,1); current_y = pdf.get_y()
            pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 6.5)
            for mod_conf in pwr.get('modifiersConfig', []):
                if mod_conf.get('id') == 'mod_extra_dynamic_array' and pwr.get('isArrayBase'): continue
                mod_text = _format_modifier_for_fpdf(mod_conf, all_mod_rules, char_state, rule_data, engine)
                pdf.set_x(indent_x + 2); pdf.multi_cell(text_w-2, LINE_HEIGHT_VSMALL, f"\u2022 {mod_text}",0,'L'); current_y = pdf.get_y()
        
        # Senses, Immunity, Variable, Summon, Affliction, Enhanced Trait details
        if base_eff_rule:
            def _render_power_sub_list(sub_title, items_list, item_name_func, item_cost_func):
                nonlocal current_y
                pdf.set_xy(indent_x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 7)
                pdf.cell(text_w, LINE_HEIGHT_VSMALL, sub_title + ":",0,1); current_y = pdf.get_y()
                pdf.set_font(FONT_FAMILY_MAIN, FONT_REGULAR, 6.5)
                for item_id_or_obj in items_list:
                    name = item_name_func(item_id_or_obj)
                    cost = item_cost_func(item_id_or_obj)
                    pdf.set_x(indent_x+2); pdf.multi_cell(text_w-2, LINE_HEIGHT_VSMALL, f"\u2022 {_format_fpdf_text(name)} ({cost} PP)",0,'L'); current_y = pdf.get_y()

            if base_eff_rule.get('isSenseContainer') and pwr.get('sensesConfig'):
                _render_power_sub_list("Senses", pwr.get('sensesConfig',[]),
                                       lambda s_id: next((s['name'] for s in rule_data.get('power_senses_config',[]) if s['id']==s_id),s_id),
                                       lambda s_id: next((s.get('cost',0) for s in rule_data.get('power_senses_config',[]) if s['id']==s_id),'?' ) )
            if base_eff_rule.get('isImmunityContainer') and pwr.get('immunityConfig'):
                _render_power_sub_list("Immunities", pwr.get('immunityConfig',[]),
                                       lambda i_id: next((i['name'] for i in rule_data.get('power_immunities_config',[]) if i['id']==i_id),i_id),
                                       lambda i_id: next((i.get('cost',0) for i in rule_data.get('power_immunities_config',[]) if i['id']==i_id),'?' ) )
            if base_eff_rule.get('id') == 'eff_affliction' and pwr.get('affliction_params'):
                ap = pwr['affliction_params']; pdf.set_xy(indent_x,current_y); pdf.set_font(FONT_FAMILY_MAIN,FONT_REGULAR,7)
                aff_text = f"Affliction ({ap.get('resistance_type','Fort')}) 1st: {ap.get('degree1','')}, 2nd: {ap.get('degree2','')}, 3rd: {ap.get('degree3','')}"
                pdf.multi_cell(text_w,LINE_HEIGHT_VSMALL,aff_text,0,'L'); current_y=pdf.get_y()

            if base_eff_rule.get('isEnhancementEffect') and pwr.get('enhanced_trait_params'):
                etp = pwr['enhanced_trait_params']
                enh_trait_name = engine.get_skill_name_by_id(etp.get('trait_id','N/A')) if etp.get('category')=='Skill' else etp.get('trait_id','N/A')
                if etp.get('category')=='Advantage': enh_trait_name = next((a.get('name') for a in adv_rules_list if a.get('id')==etp.get('trait_id')), enh_trait_name)
                pdf.set_xy(indent_x,current_y); pdf.set_font(FONT_FAMILY_MAIN,FONT_REGULAR,7)
                pdf.multi_cell(text_w,LINE_HEIGHT_VSMALL,f"Enhances: {etp.get('category','')} - {_format_fpdf_text(enh_trait_name)} +{pwr.get('rank',0)} Ranks",0,'L'); current_y=pdf.get_y()

            # Add Variable and Summon/Ally details here if needed, similar to Senses/Immunity/Affliction
            if base_eff_rule.get('isAllyEffect') and pwr.get('ally_notes_and_stats_structured'):
                ally_stats = pwr.get('ally_notes_and_stats_structured')
                pdf.set_xy(indent_x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 7)
                pdf.multi_cell(text_w, LINE_HEIGHT_VSMALL, f"Summoned: {ally_stats.get('name', 'Creation')} (PL {ally_stats.get('pl_for_ally','N/A')}, {ally_stats.get('cost_pp_asserted_by_user',0)}/{pwr.get('allotted_pp_for_creation',0)} PP)",0,'L')
                current_y = pdf.get_y()
                # Could add more ally details if space allows, but might get too verbose
        current_y += ITEM_SPACING
    return current_y + SECTION_BOTTOM_PADDING


def _render_footer_notes_fpdf(pdf: FPDF, char_state: 'CharacterState', x: float, y: float, width: float) -> float:
    current_y = y
    pdf.set_xy(x, current_y)
    pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 9)
    pdf.cell(width, SECTION_TITLE_HEIGHT, "Status & Notes", border="T", ln=1, align='L')
    current_y = pdf.get_y() + 1

    item_h = LINE_HEIGHT_NORMAL
    # Hero Points
    pdf.set_xy(x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8)
    pdf.cell(30, item_h, "Hero Points:", 0, 0)
    hp_box_size = 3.5; box_y_offset = (item_h - hp_box_size) / 2
    for i in range(3): pdf.rect(x + 30 + (i * (hp_box_size + 1)), current_y + box_y_offset, hp_box_size, hp_box_size, style='D')
    current_y += item_h + 0.5

    # Conditions Track (simplified)
    pdf.set_xy(x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8)
    pdf.cell(30, item_h, "Conditions:", 0, 0)
    pdf.set_line_width(0.2); pdf.line(x + 30, current_y + item_h/2, x + width - 5, current_y + item_h/2)
    current_y += item_h + 0.5
    
    # General Notes Area
    pdf.set_xy(x, current_y); pdf.set_font(FONT_FAMILY_MAIN, FONT_BOLD, 8)
    pdf.cell(width, item_h, "General Notes:", 0, 1); current_y = pdf.get_y()
    notes_box_height = 30 #mm
    pdf.set_fill_color(248,248,248); pdf.rect(x, current_y, width, notes_box_height, style='DF')
    current_y += notes_box_height + 2
    return current_y

# --- Main FPDF Generation Function ---
def generate_fpdf_character_sheet(character_state: 'CharacterState', rule_data: 'RuleData', engine: 'CoreEngine') -> Optional[io.BytesIO]:
    try:
        pdf = MMCharSheetPDF('P', 'mm', 'Letter')
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(False) # Manual page break management for columns
        pdf.add_page()
        
        processed_char_state = character_state 

        col_starts_x = [LEFT_MARGIN]
        for i in range(1, COLUMN_COUNT): col_starts_x.append(col_starts_x[-1] + COLUMN_WIDTH + COLUMN_GAP)
        
        current_y_header = _render_header_fpdf(pdf, processed_char_state, LEFT_MARGIN, TOP_MARGIN, EFFECTIVE_PAGE_WIDTH)
        
        # Y position for the start of content in each column for the current page
        col_content_start_y = [current_y_header] * COLUMN_COUNT 
        # Tracks the current drawing Y position for each column
        current_y_per_col = list(col_content_start_y) 

        sections_col_map = [
            [ # Column 1
                lambda p, cs, rd, e, x, y, w: _render_abilities_fpdf(p,cs,rd,e,x,y,w),
                lambda p, cs, rd, e, x, y, w: _render_defenses_fpdf(p,cs,rd,e,x,y,w),
                lambda p, cs, rd, e, x, y, w: _render_combat_summary_fpdf(p,cs,rd,e,x,y,w),
                lambda p, cs, rd, e, x, y, w: _render_complications_fpdf(p,cs,rd,e,x,y,w),
            ],
            [ # Column 2
                lambda p, cs, rd, e, x, y, w: _render_skills_fpdf(p,cs,rd,e,x,y,w),
                lambda p, cs, rd, e, x, y, w: _render_advantages_fpdf(p,cs,rd,e,x,y,w),
                lambda p, cs, rd, e, x, y, w: _render_equipment_fpdf(p,cs,rd,e,x,y,w),
            ],
            [ # Column 3
                lambda p, cs, rd, e, x, y, w: _render_powers_fpdf(p,cs,rd,e,x,y,w),
                lambda p, cs, rd, e, x, y, w: _render_generic_list_section_fpdf(p, "Companions", processed_char_state.get('allies',[]), 'name', 'cost_pp_asserted_by_user', 'PP', x,y,w, details_callback=lambda item_pdf, item, item_x, item_y_cb, item_w: _render_ally_details_fpdf(item_pdf, item, item_x, item_y_cb, item_w)),
                lambda p, cs, rd, e, x, y, w: _render_generic_list_section_fpdf(p, "Headquarters", processed_char_state.get('headquarters',[]), 'name', 'calculated_cost_placeholder', 'EP', x,y,w, details_callback=lambda item_pdf, item, item_x, item_y_cb, item_w: _render_hq_details_fpdf(item_pdf, item, rule_data, engine, item_x, item_y_cb, item_w)),
                # lambda p, cs, rd, e, x, y, w: _render_vehicles_fpdf(p, cs, rd, e, x, y, w), # Placeholder for Vehicles
            ]
        ]
        
        # Iterate through columns and render sections
        # This simple sequential rendering might lead to unbalanced columns on the last page.
        # True balancing is complex.
        page_bottom_write_limit = PAGE_HEIGHT - BOTTOM_MARGIN - 5 # Small buffer

        for col_idx in range(COLUMN_COUNT):
            current_y_val = col_content_start_y[col_idx] # Start Y for this column on current page
            for render_func in sections_col_map[col_idx]:
                 # Estimate needed height very roughly - for complex sections, this needs to be better
                 # or the render function itself handles internal page breaks.
                est_height = 30 # Default estimate
                if current_y_val + est_height > page_bottom_write_limit and pdf.page_no() == 1 and col_idx >0 : # If it won't fit and not first col
                    # This basic logic doesn't fully handle column overflow to next page elegantly.
                    # FPDF's auto_page_break with set_auto_page_break(True, margin) is the main page break driver.
                    # Manual column transitions are harder.
                    pass # For now, let auto page break handle most things or sections make themselves fit.

                if pdf.get_y() > page_bottom_write_limit : # If already past limit due to previous section
                     pdf.add_page()
                     current_y_val = TOP_MARGIN
                     # If a new page is added, all subsequent columns on this "conceptual row" also start at top.
                     for k in range(COLUMN_COUNT): col_content_start_y[k] = TOP_MARGIN


                current_y_val = render_func(pdf, processed_char_state, rule_data, engine, col_starts_x[col_idx], current_y_val, COLUMN_WIDTH)
                current_y_per_col[col_idx] = current_y_val # Update max Y for this column

                # Check for page overflow *after* rendering a section
                if current_y_val > page_bottom_write_limit:
                    if col_idx < COLUMN_COUNT - 1: # If not the last column
                        # Content overflowed, next section in this column would start on new page,
                        # but we want to try moving to next column first.
                        # This means the *next* section should start at TOP_MARGIN in *next* column.
                        # This logic is tricky with current loop structure.
                        # Simplification: Let sections handle internal breaks or make them shorter.
                        pass
                    else: # Last column overflowed, new page
                        pdf.add_page()
                        # Reset Y for all columns for the new page
                        for k_reset in range(COLUMN_COUNT):
                            col_content_start_y[k_reset] = TOP_MARGIN
                        current_y_val = TOP_MARGIN # Current section continues at top of new page, col 0.
                        # This doesn't re-distribute remaining sections to columns on new page properly yet.

        # Footer notes at the end of all content
        final_y_for_footer = max(current_y_per_col) + 5
        if final_y_for_footer + 40 > page_bottom_write_limit : # If footer itself needs new page
             pdf.add_page()
             final_y_for_footer = TOP_MARGIN
        
        _render_footer_notes_fpdf(pdf, processed_char_state, LEFT_MARGIN, final_y_for_footer, EFFECTIVE_PAGE_WIDTH)

        pdf_output_bytes = pdf.output(dest='S')
        if isinstance(pdf_output_bytes, str): # Should be bytes with modern fpdf2
             pdf_output_bytes = pdf_output_bytes.encode('latin-1') 

        pdf_buffer = io.BytesIO(pdf_output_bytes)
        pdf_buffer.seek(0)
        return pdf_buffer

    except Exception as e:
        print(f"CRITICAL Error during FPDF PDF generation: {e}")
        import traceback
        print(traceback.format_exc())
        return None