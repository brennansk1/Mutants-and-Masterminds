# core_engine.py for HeroForge M&M (Streamlit Edition)
# Version: V1.1 "Refined Calculations & Validations"

import json
import math
import os
import copy # For deep copying complex states
import uuid # For generating unique IDs if needed internally
from typing import Dict, List, Any, Optional, Tuple, Union, Set

# --- Type Hint for Character State & Other Structures ---
CharacterState = Dict[str, Any]
RuleData = Dict[str, Any]
PowerDefinition = Dict[str, Any] 
AdvantageDefinition = Dict[str, Any]
EquipmentDefinition = Dict[str, Any]
HQDefinition = Dict[str, Any]
VehicleDefinition = Dict[str, Any]
AllyDefinition = Dict[str, Any] 
VariableConfigTrait = Dict[str, Any]
SkillRule = Dict[str, Any] 

class CoreEngine:
    """
    The CoreEngine for HeroForge M&M.
    Handles all rule calculations, validations, and character state manipulations
    based on the Mutants & Masterminds 3rd Edition Hero's Handbook (DHH).
    """

    def __init__(self, rule_dir: str = "rules"):
        self.rule_data: RuleData = self._load_all_rule_data(rule_dir)
        if not self.rule_data:
            raise ValueError("FATAL: Core rule data could not be loaded. Application cannot proceed.")
        
        self._abilities_list = self.rule_data.get('abilities', {}).get('list', [])
        self._skills_list = self.rule_data.get('skills', {}).get('list', [])
        self._advantages_list = self.rule_data.get('advantages_v1', [])
        self._power_effects_list = self.rule_data.get('power_effects', [])
        self._power_modifiers_list = self.rule_data.get('power_modifiers', [])
        self._power_senses_list = self.rule_data.get('power_senses_config', [])
        self._power_immunities_list = self.rule_data.get('power_immunities_config', [])
        self._measurements_table_orig = self.rule_data.get('measurements_table', []) # Keep original
        self._measurements_table = sorted( # Ensure sorted by rank for lookups
            [entry for entry in self._measurements_table_orig if isinstance(entry.get('rank'), (int, float))],
            key=lambda x: x.get('rank', 0)
        )
        self._equipment_items_list = self.rule_data.get('equipment_items', [])
        self._hq_features_list = self.rule_data.get('hq_features', [])
        self._vehicle_features_list = self.rule_data.get('vehicle_features', [])
        self._vehicle_size_stats_list = self.rule_data.get('vehicle_size_stats', [])
        
        print("CoreEngine initialized successfully with rule data.")

    def _load_all_rule_data(self, directory_path: str) -> RuleData:
        loaded_data: RuleData = {}
        expected_files = [
            "abilities.json", "advantages_v1.json", "archetypes.json",
            "equipment_items.json", "hq_features.json", "measurements_table.json",
            "power_effects.json", "power_immunities_config.json", "power_senses_config.json",
            "power_modifiers.json", "skills.json",
            "vehicle_features.json", "vehicle_size_stats.json"
        ]
        try:
            abs_path = os.path.abspath(directory_path)
            if not os.path.isdir(abs_path):
                raise FileNotFoundError(f"Rule directory not found at '{abs_path}'")

            for filename in expected_files:
                filepath = os.path.join(abs_path, filename)
                if not os.path.exists(filepath):
                    raise FileNotFoundError(f"Expected rule file not found: {filepath}")
                
                rule_name = filename[:-5]  # Remove '.json'
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        loaded_data[rule_name] = json.load(f)
                    except json.JSONDecodeError as jde:
                        raise RuntimeError(f"Failed to decode JSON from {filename}: {jde}")
            
            if len(loaded_data) < len(expected_files):
                missing = [f for f in expected_files if f[:-5] not in loaded_data]
                raise FileNotFoundError(f"Not all expected rule files were loaded. Missing: {missing}")
            return loaded_data

        except Exception as e:
            raise RuntimeError(f"Failed to initialize CoreEngine due to rule loading error: {e}")


    def get_default_character_state(self, pl: int = 10) -> CharacterState:
        base_abilities = {info['id']: 0 for info in self._abilities_list} if self._abilities_list else {}
        default_skills = {skill_info['id']: 0 for skill_info in self._skills_list if not skill_info.get('specialization_possible')} if self._skills_list else {}

        return {
            "saveFileVersion": "1.4_core_engine_refinements", 
            "name": "New Hero", "playerName": "", "powerLevel": pl,
            "totalPowerPoints": pl * 15, "spentPowerPoints": 0,
            "concept": "", "description": "", "identity": "Secret", 
            "gender": "", "age": "", "height": "", "weight": "", "eyes": "", "hair": "",
            "groupAffiliation": "", "baseOfOperationsName": "",
            "abilities": copy.deepcopy(base_abilities),
            "defenses": {"Dodge": 0, "Parry": 0, "Toughness": 0, "Fortitude": 0, "Will": 0},
            "skills": copy.deepcopy(default_skills), 
            "advantages": [], "powers": [], "equipment": [], "headquarters": [],
            "vehicles": [], "allies": [], "complications": [], 
            "validationErrors": [],
            "derived_initiative": 0, "derived_defensive_roll_bonus": 0,
            "derived_languages_known": [], "derived_languages_granted": 0, 
            "derived_total_ep": 0, "derived_spent_ep": 0,
            "derived_total_minion_pool_pp": 0, "derived_spent_minion_pool_pp": 0,
            "derived_total_sidekick_pool_pp": 0, "derived_spent_sidekick_pool_pp": 0
        }

    def get_ability_modifier(self, ability_rank: Optional[Union[int, float]]) -> int:
        return int(ability_rank) if ability_rank is not None else 0

    def get_skill_rule(self, skill_id_or_name: str) -> Optional[SkillRule]:
        for skill_rule in self._skills_list:
            if skill_rule['id'] == skill_id_or_name or skill_rule['name'] == skill_id_or_name:
                return skill_rule
            if skill_rule.get('specialization_possible') and skill_id_or_name.startswith(skill_rule['id'] + "_"):
                return skill_rule 
        return None
        
    def get_skill_name_by_id(self, skill_id: str, skills_rules_list: Optional[List[Dict]] = None) -> str:
        if skills_rules_list is None: skills_rules_list = self._skills_list
        base_skill_id_parts = skill_id.split('_')
        base_skill_id_lookup = "_".join(base_skill_id_parts[:2]) if len(base_skill_id_parts) >=2 else skill_id
        base_skill_rule = next((s for s in skills_rules_list if s['id'] == base_skill_id_lookup), None)
        if not base_skill_rule: return skill_id 
        if base_skill_rule.get('specialization_possible') and skill_id.startswith(base_skill_rule['id'] + "_") and len(skill_id) > len(base_skill_rule['id'] + "_"):
            specialization_name_part = skill_id[len(base_skill_rule['id'] + "_"):]
            specialization_name = specialization_name_part.replace("_"," ").title()
            return f"{base_skill_rule['name']}: {specialization_name}"
        return base_skill_rule['name']

    def get_trait_cost_per_rank(
        self, 
        trait_category: str, 
        trait_id: Optional[str] = None, 
        character_powers_context: Optional[List[PowerDefinition]] = None,
        _costing_recursion_set: Optional[Set[str]] = None # For recursion detection
    ) -> float:
        if trait_category == "Ability": return 2.0
        if trait_category == "Defense": return 1.0 
        if trait_category == "Skill": return 0.5
        if trait_category == "Advantage":
            if trait_id and self._advantages_list:
                adv_rule = next((adv for adv in self._advantages_list if adv['id'] == trait_id), None)
                return float(adv_rule.get('costPerRank', 1.0)) if adv_rule else 1.0
            return 1.0
        if trait_category == "PowerRank" and trait_id and character_powers_context:
            if _costing_recursion_set and trait_id in _costing_recursion_set:
                print(f"Warning: Recursion detected for PowerRank enhancement of {trait_id}. Returning default cost.")
                return 1.0 # Break recursion, return default

            target_power = next((pwr for pwr in character_powers_context if pwr.get('id') == trait_id), None)
            if target_power:
                # Pass the recursion set down
                temp_recursion_set = set(_costing_recursion_set) if _costing_recursion_set else set()
                temp_recursion_set.add(trait_id) # Add current power being costed for enhancing another
                
                # We need the base power ID that is being enhanced, not the enhancer's ID here.
                # The trait_id is the ID of the power being enhanced.
                
                cost_details = self.calculate_individual_power_cost(target_power, character_powers_context, _costing_recursion_set=temp_recursion_set)
                cpr_final_val = cost_details.get('costPerRankFinal')
                if isinstance(cpr_final_val, (int, float)): return float(cpr_final_val)
                if isinstance(cpr_final_val, str): 
                    if "1 per " in cpr_final_val:
                        try: return 1.0 / int(cpr_final_val.split("1 per ")[1])
                        except (ValueError, ZeroDivisionError): return 1.0 
                    try: return float(cpr_final_val) 
                    except ValueError: return 1.0 
                return 1.0 
            return 1.0 
        return 1.0

    def get_measurement_by_rank(self, rank: int, measurement_type: str) -> str:
        if not self._measurements_table: return f"Rank {rank} (Table N/A)"
        
        # Direct match
        for entry in self._measurements_table:
            if entry.get('rank') == rank:
                return entry.get(measurement_type, f"Rank {rank} (Type N/A in Table Entry)")
        
        # Handle ranks outside the defined table range
        min_rank_in_table = self._measurements_table[0].get('rank', -float('inf'))
        max_rank_in_table = self._measurements_table[-1].get('rank', float('inf'))

        if rank < min_rank_in_table:
            return f"< {self._measurements_table[0].get(measurement_type, '')} (Below Table Minimum)"
        
        if rank > max_rank_in_table:
            # Refined Extrapolation
            if len(self._measurements_table) >= 2:
                last_entry = self._measurements_table[-1]
                second_last_entry = self._measurements_table[-2]
                
                try:
                    # Attempt to parse values as numbers for extrapolation
                    # This simplified parsing may not work for all M&M table string formats (e.g. "1/2 mile")
                    def parse_measurement_value(val_str: str) -> Optional[float]:
                        if isinstance(val_str, (int, float)): return float(val_str)
                        if isinstance(val_str, str):
                            # Basic parsing for numbers, fractions, and some units - very simplified
                            if 'Subatomic' in val_str or 'Planetary' in val_str: return None
                            val_str_cleaned = val_str.split(" ")[0].replace(",", "") # "25 Kilograms" -> "25"
                            if "/" in val_str_cleaned: # "1/2"
                                num, den = val_str_cleaned.split("/")
                                return float(num) / float(den)
                            return float(val_str_cleaned)
                        return None

                    last_val_num = parse_measurement_value(last_entry.get(measurement_type))
                    second_last_val_num = parse_measurement_value(second_last_entry.get(measurement_type))
                    
                    last_rank_val = last_entry.get('rank')
                    second_last_rank_val = second_last_entry.get('rank')

                    if last_val_num is not None and second_last_val_num is not None and \
                       isinstance(last_rank_val, (int, float)) and isinstance(second_last_rank_val, (int, float)) and \
                       last_rank_val != second_last_rank_val:
                        
                        rank_diff_table = last_rank_val - second_last_rank_val
                        val_diff_table = last_val_num - second_last_val_num
                        
                        # If it's an M&M-style doubling per X ranks, simple linear won't work well.
                        # For many M&M progressions, a large jump means a multiplicative factor.
                        # For a small jump, an additive factor.
                        # This is still an approximation.
                        
                        ranks_above_max = rank - last_rank_val
                        
                        if abs(val_diff_table) > abs(second_last_val_num * rank_diff_table * 0.5) and second_last_val_num != 0: # Heuristic: large jump suggests multiplicative
                            # Multiplicative factor over one rank step in the table
                            if second_last_val_num != 0 and rank_diff_table > 0:
                                factor_per_table_rank_step = (last_val_num / second_last_val_num) ** (1/rank_diff_table) if second_last_val_num !=0 else 2 # default factor
                                extrapolated_value = last_val_num * (factor_per_table_rank_step ** ranks_above_max)
                                return f"~{extrapolated_value:.2g} (Extrapolated Multiplicatively)"
                        else: # Additive
                            increment_per_rank_step = val_diff_table / rank_diff_table
                            extrapolated_value = last_val_num + (increment_per_rank_step * ranks_above_max)
                            # M&M often has doubling of increment for steps beyond table for *some* measures
                            # This is too specific to generalize without knowing measurement_type behavior
                            # Simple linear for now if not clearly multiplicative
                            return f"~{extrapolated_value:.2g} (Extrapolated Linearly)"
                except (ValueError, TypeError, ZeroDivisionError):
                    # Fallback if numeric conversion/calculation fails
                    pass # Handled by returning last known value below
            
            # Fallback for non-numeric or if extrapolation fails
            return f"> {self._measurements_table[-1].get(measurement_type, '')} (Above Table Maximum)"

        # Interpolation for ranks within the table but not explicitly listed
        # (The provided table is quite dense, so this might not be hit often)
        closest_lower_entry = None
        for entry in self._measurements_table: # Already sorted
            entry_rank_val = entry.get('rank')
            if isinstance(entry_rank_val, (int, float)) and entry_rank_val < rank:
                closest_lower_entry = entry
            elif isinstance(entry_rank_val, (int, float)) and entry_rank_val >= rank:
                break # Found first entry >= rank, closest_lower_entry is set
        
        if closest_lower_entry:
            return f"{closest_lower_entry.get(measurement_type, '')} (at Rank {closest_lower_entry.get('rank')}, value for rank {rank} not explicitly listed)"
        
        return f"Rank {rank} (Value N/A or out of typical range)"


    def calculate_ability_cost(self, abilities_state: Dict[str, int]) -> int:
        cost = 0
        cost_factor = self.rule_data.get('abilities', {}).get('costFactor', 2)
        for rank_val in abilities_state.values(): 
            cost += rank_val * cost_factor 
        return cost

    def calculate_defense_cost(self, bought_defenses_state: Dict[str, int]) -> int:
        return sum(bought_defenses_state.values())

    def calculate_skill_cost(self, skills_state: Dict[str, int]) -> int:
        total_ranks_bought = sum(skills_state.values())
        return math.ceil(total_ranks_bought * 0.5)

    def calculate_advantage_cost(self, advantages_state: List[AdvantageDefinition]) -> int:
        cost = 0
        if not self._advantages_list: return 0
        for adv_entry in advantages_state:
            adv_rule = next((r for r in self._advantages_list if r['id'] == adv_entry.get('id')), None)
            cost_per_rank = adv_rule.get('costPerRank', 1) if adv_rule else 1
            rank_taken = adv_entry.get('rank', 1)
            cost += rank_taken * cost_per_rank
        return cost

    def calculate_equipment_cost_ep(self, equipment_list: List[EquipmentDefinition]) -> int:
        return sum(item.get('ep_cost', 0) for item in equipment_list)

    def calculate_hq_cost(self, hq_definition: HQDefinition, hq_features_rules: Optional[List[Dict]] = None) -> int:
        if hq_features_rules is None: hq_features_rules = self._hq_features_list
        cost = 0
        size_id = hq_definition.get('size_id')
        size_rule = next((f for f in hq_features_rules if f.get('id') == size_id and f.get('type') == 'Size'), None)
        if size_rule: cost += size_rule.get('ep_cost', 0)
        cost += hq_definition.get('bought_toughness_ranks', 0)
        for feat_entry in hq_definition.get('features', []):
            feat_rule = next((f for f in hq_features_rules if f.get('id') == feat_entry.get('id')), None)
            if feat_rule:
                cost_val = feat_rule.get('ep_cost', feat_rule.get('ep_cost_per_rank', 1))
                if feat_rule.get('ranked'):
                    cost += cost_val * feat_entry.get('rank', 1)
                else:
                    cost += cost_val
        return cost

    def calculate_vehicle_cost(self, vehicle_def: VehicleDefinition, 
                               vehicle_features_rules: Optional[List[Dict]] = None, 
                               vehicle_size_stats_rules: Optional[List[Dict]] = None) -> int:
        if vehicle_features_rules is None: vehicle_features_rules = self._vehicle_features_list
        if vehicle_size_stats_rules is None: vehicle_size_stats_rules = self._vehicle_size_stats_list
        cost = 0
        size_rank_val = vehicle_def.get('size_rank', 0)
        size_stat_rule = next((s for s in vehicle_size_stats_rules if s.get('size_rank_value') == size_rank_val), None)
        if size_stat_rule: cost += size_stat_rule.get('base_ep_cost', 0)
        for feat_entry in vehicle_def.get('features', []):
            feat_rule = next((f for f in vehicle_features_rules if f.get('id') == feat_entry.get('id')), None)
            if feat_rule:
                cost_val = feat_rule.get('ep_cost', feat_rule.get('ep_cost_per_rank', 1))
                if feat_rule.get('ranked'):
                    cost += cost_val * feat_entry.get('rank', 1)
                else:
                    cost += cost_val
        return cost
        
    def calculate_individual_power_cost(
        self, 
        power_definition: PowerDefinition, 
        all_character_powers_context: List[PowerDefinition],
        _costing_recursion_set: Optional[Set[str]] = None # For recursion detection in Enhanced Trait (PowerRank)
    ) -> Dict[str, Any]:
        results = {'totalCost': 0, 'costPerRankFinal': 0.0, 'costBreakdown': {'base_effect_cpr':0.0, 'extras_cpr':0.0, 'flaws_cpr':0.0, 'flat_total':0.0, 'senses_total': 0.0, 'immunities_total':0.0, 'variable_base_cost':0.0, 'enh_trait_base_cost':0.0, 'special_fixed_cost':0.0}}
        base_effect_id = power_definition.get('baseEffectId'); power_rank = int(power_definition.get('rank', 0)); modifiers_config = power_definition.get('modifiersConfig', [])
        base_effect_rule = next((e for e in self._power_effects_list if e['id'] == base_effect_id), None)
        
        current_power_id = power_definition.get('id')
        if current_power_id and _costing_recursion_set and current_power_id in _costing_recursion_set:
            # This specific check is more relevant if this function were called recursively for the *same* power.
            # The primary recursion check for Enhanced Trait (PowerRank) happens in get_trait_cost_per_rank.
            # However, if this function itself could be called in a loop for the same power, this would catch it.
            # For now, the recursion set is mainly for Enhanced Trait (PowerRank).
            pass 

        local_recursion_set = set(_costing_recursion_set) if _costing_recursion_set else set()
        if current_power_id:
            local_recursion_set.add(current_power_id)


        if not base_effect_rule: return results 
        if base_effect_rule.get('isSenseContainer'):
            sense_total_cost = sum(s_rule.get('cost',0) for s_id in power_definition.get('sensesConfig', []) for s_rule in self._power_senses_list if s_rule['id'] == s_id)
            results['costBreakdown']['senses_total'] = float(sense_total_cost); flat_mod_cost = sum(self._get_modifier_flat_cost(mod_conf) for mod_conf in modifiers_config)
            results['costBreakdown']['flat_total'] = flat_mod_cost; results['totalCost'] = math.ceil(sense_total_cost + flat_mod_cost); results['costPerRankFinal'] = "N/A (Senses Package)"; return results
        if base_effect_rule.get('isImmunityContainer'):
            immunity_total_cost = sum(i_rule.get('cost',0) for i_id in power_definition.get('immunityConfig', []) for i_rule in self._power_immunities_list if i_rule['id'] == i_id)
            results['costBreakdown']['immunities_total'] = float(immunity_total_cost); flat_mod_cost = sum(self._get_modifier_flat_cost(mod_conf) for mod_conf in modifiers_config)
            results['costBreakdown']['flat_total'] = flat_mod_cost; results['totalCost'] = math.ceil(immunity_total_cost + flat_mod_cost); results['costPerRankFinal'] = "N/A (Immunity Package)"; return results
        if base_effect_rule.get('id') == 'eff_insubstantial' and base_effect_rule.get('isFixedCostByRank'):
            fixed_costs = base_effect_rule.get('fixedCosts', {}); base_total_cost = float(fixed_costs.get(str(power_rank), 0))
            results['costBreakdown']['special_fixed_cost'] = base_total_cost; cpr_mod_sum = sum(self._get_modifier_cpr_change(mod_conf) for mod_conf in modifiers_config); flat_mod_cost = sum(self._get_modifier_flat_cost(mod_conf) for mod_conf in modifiers_config)
            results['costBreakdown']['extras_cpr'] = sum(self._get_modifier_cpr_change(mc) for mc in modifiers_config if self._get_modifier_cpr_change(mc) > 0) * power_rank; results['costBreakdown']['flaws_cpr'] = sum(self._get_modifier_cpr_change(mc) for mc in modifiers_config if self._get_modifier_cpr_change(mc) < 0) * power_rank
            results['costBreakdown']['flat_total'] = flat_mod_cost; results['totalCost'] = math.ceil(base_total_cost + (cpr_mod_sum * power_rank) + flat_mod_cost); results['costPerRankFinal'] = f"Fixed Total (Rank {power_rank})"; 
            if results['totalCost'] < 1 and power_rank > 0: results['totalCost'] = 1; return results
        if power_rank <= 0: 
            flat_mod_cost_only = sum(self._get_modifier_flat_cost(mod_conf) for mod_conf in modifiers_config); results['costBreakdown']['flat_total'] = flat_mod_cost_only; results['totalCost'] = math.ceil(flat_mod_cost_only)
            if results['totalCost'] < 0: results['totalCost'] = 0; results['costPerRankFinal'] = base_effect_rule.get('costPerRank', 0.0); return results
        base_cpr = 0.0
        if base_effect_rule.get('isEnhancementEffect'):
            et_params = power_definition.get('enhanced_trait_params', {}); enh_cat = et_params.get('category'); enh_id = et_params.get('trait_id'); 
            base_cpr = self.get_trait_cost_per_rank(enh_cat, enh_id, all_character_powers_context, _costing_recursion_set=local_recursion_set)
            results['costBreakdown']['enh_trait_base_cost'] = base_cpr * power_rank 
        elif base_effect_rule.get('isVariableContainer'): base_cpr = float(base_effect_rule.get('costPerRank', 7.0)); results['costBreakdown']['variable_base_cost'] = base_cpr * power_rank
        elif base_effect_rule.get('isTransformContainer'):
            morph_params = power_definition.get('morph_params', {}); scope_choice_id = morph_params.get('transform_scope_choice_id'); 
            cost_option = next((opt for opt in base_effect_rule.get('costOptions',[]) if opt.get('choice_id') == scope_choice_id), None)
            base_cpr = float(cost_option.get('costPerRank', base_effect_rule.get('costPerRank', 2.0))) if cost_option else float(base_effect_rule.get('costPerRank', 2.0))
        else: base_cpr = float(base_effect_rule.get('costPerRank', 1.0))
        results['costBreakdown']['base_effect_cpr'] = base_cpr 
        current_total_cpr = base_cpr; total_flat_cost_adj = 0.0; current_extras_cpr_sum = 0.0; current_flaws_cpr_sum = 0.0
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
            if not mod_rule or mod_rule.get('costType') == 'special_alternate_effect' or mod_rule.get('costType') == 'special_linked': continue
            if mod_rule.get('costType') == 'perRank':
                change = self._get_modifier_cpr_change(mod_conf); current_total_cpr += change
                if change > 0: current_extras_cpr_sum += change
                else: current_flaws_cpr_sum += change
            elif mod_rule.get('costType') == 'flat' or mod_rule.get('costType') == 'flatPerRankOfModifier': total_flat_cost_adj += self._get_modifier_flat_cost(mod_conf)
            elif mod_rule.get('costType') == 'special_removable': power_definition['_has_removable_flaw'] = mod_rule.get('removable_type', 'standard')
        results['costBreakdown']['extras_cpr'] = current_extras_cpr_sum; results['costBreakdown']['flaws_cpr'] = current_flaws_cpr_sum
        results['costBreakdown']['flat_total'] = total_flat_cost_adj; results['costPerRankFinal'] = current_total_cpr
        ranked_cost_unrounded = 0.0
        if current_total_cpr >= 1.0: ranked_cost_unrounded = current_total_cpr * power_rank
        elif current_total_cpr > 0: ranks_per_point = math.ceil(1.0 / current_total_cpr); ranked_cost_unrounded = math.ceil(float(power_rank) / ranks_per_point)
        total_cost_before_removable = ranked_cost_unrounded + total_flat_cost_adj
        if power_definition.get('_has_removable_flaw'):
            removable_type = power_definition['_has_removable_flaw']; cost_for_removable_calc = math.ceil(total_cost_before_removable)
            if cost_for_removable_calc < 1: cost_for_removable_calc = 1
            reduction_factor = 1 if removable_type == 'standard' else 2; removable_discount = math.floor(cost_for_removable_calc / 5.0) * reduction_factor
            total_cost_before_removable -= removable_discount
        results['totalCost'] = math.ceil(total_cost_before_removable)
        if results['totalCost'] < 1 and power_rank > 0 and not (base_effect_rule.get('isSenseContainer') or base_effect_rule.get('isImmunityContainer')): results['totalCost'] = 1
        elif results['totalCost'] < 0: results['totalCost'] = 0
        power_definition.pop('_has_removable_flaw', None); return results

    def _get_modifier_cpr_change(self, mod_config_entry: Dict) -> float:
        mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_config_entry.get('id')), None)
        if not mod_rule or mod_rule.get('costType') != 'perRank': return 0.0
        base_change = float(mod_rule.get('costChangePerRank', 0.0))
        if mod_rule.get('parameter_needed') and mod_rule.get('parameter_options') and 'params' in mod_config_entry:
            param_storage_key = mod_rule.get('parameter_storage_key', mod_rule.get('id')) 
            user_choice = mod_config_entry['params'].get(param_storage_key)
            for opt in mod_rule.get('parameter_options', []):
                if opt.get('value') == user_choice and 'cost_adjust_per_rank' in opt:
                    base_change += float(opt['cost_adjust_per_rank']); break
        return base_change

    def _get_modifier_flat_cost(self, mod_config_entry: Dict) -> float:
        mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_config_entry.get('id')), None)
        if not mod_rule: return 0.0; flat_cost = 0.0
        if mod_rule.get('costType') == 'flat':
            flat_cost = float(mod_rule.get('flatCostChange', 0.0))
            if mod_rule.get('parameter_needed') and mod_rule.get('parameter_options') and 'params' in mod_config_entry:
                param_storage_key = mod_rule.get('parameter_storage_key', mod_rule.get('id'))
                user_choice = mod_config_entry['params'].get(param_storage_key)
                for opt in mod_rule.get('parameter_options', []):
                    if opt.get('value') == user_choice and 'cost_adjust_flat' in opt:
                        flat_cost += float(opt['cost_adjust_flat']); break
        elif mod_rule.get('costType') == 'flatPerRankOfModifier':
            flat_cost = float(mod_rule.get('flatCost', 0.0)) * mod_config_entry.get('rank', 1)
        return flat_cost

    def calculate_power_cost(self, powers_state: List[PowerDefinition]) -> int:
        total_pp_for_all_powers = 0; processed_power_ids_in_arrays = set(); arrays: Dict[str, List[PowerDefinition]] = {}
        for pwr_def_mutable in powers_state: 
            if 'cost' not in pwr_def_mutable: 
                # Initialize recursion set for this top-level power costing if it's part of Enhancement calc
                initial_recursion_set = set()
                if pwr_def_mutable.get('id'):
                    initial_recursion_set.add(pwr_def_mutable['id'])
                cost_details = self.calculate_individual_power_cost(pwr_def_mutable, powers_state, _costing_recursion_set=initial_recursion_set)
                pwr_def_mutable['cost'] = cost_details['totalCost']
            array_id = pwr_def_mutable.get('arrayId');
            if array_id:
                if array_id not in arrays: arrays[array_id] = []
                arrays[array_id].append(pwr_def_mutable) 
        for array_id, powers_in_array in arrays.items():
            if not powers_in_array: continue
            base_power = next((p for p in powers_in_array if p.get('isArrayBase')), None)
            if not base_power:
                potential_bases = [p for p in powers_in_array if not p.get('isAlternateEffectOf')]
                if not potential_bases: 
                    for p_ae_orphan in powers_in_array:
                        if p_ae_orphan.get('id') not in processed_power_ids_in_arrays: 
                            total_pp_for_all_powers += p_ae_orphan.get('cost', 0)
                            processed_power_ids_in_arrays.add(p_ae_orphan.get('id',''))
                    continue 
                base_power = max(potential_bases, key=lambda p: p.get('cost', 0))
            array_total_cost = base_power.get('cost', 0)
            processed_power_ids_in_arrays.add(base_power.get('id',''))
            is_dynamic = base_power.get('isDynamicArray', False) 
            for ae_power in powers_in_array:
                if ae_power.get('isAlternateEffectOf') == base_power.get('id') and ae_power.get('id') != base_power.get('id'):
                    array_total_cost += 2 if is_dynamic else 1
                    processed_power_ids_in_arrays.add(ae_power.get('id',''))
            total_pp_for_all_powers += array_total_cost
        for pwr_def in powers_state:
            if pwr_def.get('id','') not in processed_power_ids_in_arrays: 
                total_pp_for_all_powers += pwr_def.get('cost', 0)
        return total_pp_for_all_powers

    def apply_enhancements(self, current_state: CharacterState) -> CharacterState:
        state = copy.deepcopy(current_state)
        for power_def in state.get('powers', []):
            if power_def.get('baseEffectId') == 'eff_enhanced_trait':
                et_params = power_def.get('enhanced_trait_params', {}); category = et_params.get('category'); trait_id = et_params.get('trait_id'); 
                amount = int(power_def.get('rank', 0)) # Rank of ET power is the enhancement amount
                if not category or not trait_id or amount <= 0: continue
                
                # Use a unique instance ID generator for new advantages added via enhancement
                new_adv_instance_id = str(uuid.uuid4())[:12]

                if category == "Ability":
                    if trait_id in state['abilities']: state['abilities'][trait_id] = state['abilities'].get(trait_id, 0) + amount
                elif category == "Defense":
                    if trait_id in state['defenses']: state['defenses'][trait_id] = state['defenses'].get(trait_id, 0) + amount
                elif category == "Skill": 
                    state['skills'][trait_id] = state['skills'].get(trait_id, 0) + amount
                elif category == "Advantage":
                    found_adv = False
                    for adv_entry in state.get('advantages', []):
                        if adv_entry.get('id') == trait_id:
                            adv_rule = next((r for r in self._advantages_list if r['id'] == trait_id), None)
                            if adv_rule and adv_rule.get('ranked'): 
                                adv_entry['rank'] = adv_entry.get('rank', 1) + amount
                            elif adv_rule and not adv_rule.get('ranked') and adv_entry.get('rank',1) < amount : # Non-ranked adv, effectively buying it if not already there
                                adv_entry['rank'] = 1 # Can't have more than 1 rank if not ranked.
                            found_adv = True; break
                    if not found_adv: 
                        adv_rule_for_new = next((r for r in self._advantages_list if r['id'] == trait_id), None)
                        new_rank_for_adv = amount if adv_rule_for_new and adv_rule_for_new.get('ranked') else 1
                        state['advantages'].append({'id': trait_id, 'rank': new_rank_for_adv, 'params': {}, 'instance_id': new_adv_instance_id})
                elif category == "PowerRank":
                    for other_power in state.get('powers', []):
                        if other_power.get('id') == trait_id and other_power.get('id') != power_def.get('id'): 
                            other_power['rank'] = other_power.get('rank', 0) + amount; break
        return state
        
    def _derive_final_duration(self, base_duration: str, modifiers_config: List[Dict]) -> str:
        duration_levels = ["Instant", "Concentration", "Sustained", "Continuous", "Permanent"]
        current_duration = base_duration.capitalize() if base_duration else "Instant"
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
            if not mod_rule: continue
            applies_to = mod_rule.get('appliesToDuration'); changes_to = mod_rule.get('changesDurationTo')
            if applies_to and changes_to and current_duration in applies_to: current_duration = changes_to
            elif mod_rule.get('id') == 'mod_extra_sustained_on_permanent' and current_duration == "Permanent": current_duration = "Sustained"
            elif mod_rule.get('id') == 'mod_flaw_permanent_duration_flaw' and current_duration in ["Continuous", "Sustained"]: current_duration = "Permanent (Cannot be turned off)"
        return current_duration.capitalize()

    def _derive_final_range(self, base_range: str, modifiers_config: List[Dict], power_rank: int, base_effect_rule: Dict) -> str:
        current_range = base_range.lower() if base_range else "personal"; is_area_effect = False; area_type_name = ""
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
            if mod_rule and mod_rule.get('changesRangeTo', '').lower().startswith("area"):
                is_area_effect = True; area_type_name = mod_rule.get('changesRangeTo'); area_rank = min(mod_conf.get('rank', power_rank), power_rank)
                # Distance Rank for Area radius/length per DHH p.149:
                # Burst, Cloud, Cylinder: Area Rank - 2 (gives 30ft radius at Area Rank 2)
                # Cone, Line: Area Rank (gives 60ft length/height at Area Rank 2)
                # Shapeable: Area Rank + 2 (gives 250 cft at Area Rank 2)
                if any(x in area_type_name.lower() for x in ["burst", "cloud", "cylinder"]):
                    radius_dist_rank = area_rank - 2; radius_measure = self.get_measurement_by_rank(radius_dist_rank, 'distance')
                    current_range = f"{area_type_name.capitalize()} ({radius_measure} radius)"
                    if "cloud" in area_type_name.lower(): current_range += ", lingers"
                    if "cylinder" in area_type_name.lower(): 
                        height_dist_rank = area_rank; height_measure = self.get_measurement_by_rank(height_dist_rank, 'distance')
                        current_range += f", {height_measure} high"
                elif any(x in area_type_name.lower() for x in ["cone", "line"]):
                    length_dist_rank = area_rank; length_measure = self.get_measurement_by_rank(length_dist_rank, 'distance')
                    current_range = f"{area_type_name.capitalize()} ({length_measure} long)";
                    if "line" in area_type_name.lower(): current_range += ", 5-ft. wide" # Default width
                elif "shapeable" in area_type_name.lower(): 
                    volume_dist_rank = area_rank + 2; volume_measure = self.get_measurement_by_rank(volume_dist_rank, 'volume')
                    current_range = f"{area_type_name.capitalize()} ({volume_measure})"
                elif "perception" in area_type_name.lower(): 
                    sense_type = mod_conf.get('params',{}).get(mod_rule.get('parameter_storage_key','sense_type'), "Visual"); 
                    current_range = f"Area (Perception - {sense_type.capitalize()})"
                break 
        if not is_area_effect:
            for mod_conf in modifiers_config:
                mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
                if not mod_rule: continue; changes_to = mod_rule.get('changesRangeTo'); applies_to = mod_rule.get('appliesToRange')
                if changes_to and applies_to and current_range in [r.lower() for r in applies_to]: current_range = changes_to.lower()
                elif mod_rule.get('id') == 'mod_extra_affects_others_also' and current_range == 'personal': current_range = 'touch'
                if mod_rule.get('id') == 'mod_extra_extended_range' and current_range == 'ranged': 
                    extended_ranks = mod_conf.get('rank', 0); current_range = f"Ranged (Extended x{2**extended_ranks})"
        
        if current_range == "rank": 
            dist_val = self.get_measurement_by_rank(power_rank, 'distance'); return f"Rank ({dist_val})"
        elif current_range == "ranged" and not is_area_effect: 
            # Standard ranged increments: Close (PRx25ft), Medium (PRx50ft), Long (PRx100ft)
            # This corresponds to Distance Ranks of (PR-2), (PR-1), (PR) approx
            # For display, usually max range (Long) is shown. PRx100ft is Dist Rank (PR) for distance.
            long_range_dist_val = self.get_measurement_by_rank(power_rank, 'distance') # DHH p.155: default long range.
            return f"Ranged (up to {long_range_dist_val})"
        elif current_range == "perception" and not is_area_effect: return "Perception"
        return current_range.replace("_"," ").title()

    def _derive_final_action(self, base_action: str, modifiers_config: List[Dict]) -> str:
        action_levels = {"Reaction": 0, "Free": 1, "Move": 2, "Standard": 3, "Full": 4}; current_action = base_action.capitalize() if base_action else "Standard"
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
            if not mod_rule: continue; applies_to = mod_rule.get('appliesToAction'); changes_to = mod_rule.get('changesActionTo')
            if applies_to and changes_to and current_action in applies_to: current_action = changes_to
            elif mod_rule.get('changesActionFromPersonalToAttack') and current_action == "Personal":
                if base_action.lower() in ["personal", "none"]: current_action = "Standard"
        return current_action.capitalize()

    def get_power_measurement_details(self, power_def: PowerDefinition, rule_data_override: Optional[RuleData] = None) -> str:
        rd = rule_data_override if rule_data_override else self.rule_data; base_effect_id = power_def.get('baseEffectId'); rank = power_def.get('rank', 0)
        if rank == 0 and base_effect_id not in ['eff_senses', 'eff_immunity']: return ""
        base_effect_rule = next((e for e in self._power_effects_list if e['id'] == base_effect_id), None)
        if not base_effect_rule: return ""; details = []
        
        if base_effect_id in ["eff_flight", "eff_speed", "eff_swimming"]: # DHH p.131 (Flight), p.143 (Speed/Swimming) Speed Rank = Power Rank
            # Movement distance per round = Distance Rank (Speed Rank - 2)
            dist_rank_for_speed = rank - 2
            distance_per_round = self.get_measurement_by_rank(dist_rank_for_speed, 'distance')
            details.append(f"{distance_per_round}/round")
        elif base_effect_id == "eff_leaping": # DHH p.137 Leap Distance Rank = Power Rank
            leap_distance = self.get_measurement_by_rank(rank, 'distance')
            details.append(f"{leap_distance} jump")
        elif base_effect_id == "eff_move_object": # DHH p.138 Mass Rank = Power Rank
            mass_lifted = self.get_measurement_by_rank(rank, 'mass')
            details.append(f"Lifts/Throws {mass_lifted}")
        elif base_effect_id == "eff_create": # DHH p.126 Object Toughness = Rank, Volume Rank = Rank
            obj_tough = rank; cp = power_def.get('create_params',{}); 
            if cp.get('toughness_override') is not None and cp.get('toughness_override') > 0 : obj_tough = cp['toughness_override']
            volume_val = self.get_measurement_by_rank(rank, 'volume'); details.append(f"Creates Toughness {obj_tough}, Volume {volume_val} objects")
        elif base_effect_id == "eff_growth": # DHH p.132
            # Growth gives +1 STR & STA per rank. Size increases +1 category per 4 ranks. Mass increases +1 rank per rank.
            # Intimidation +1 per 2 ranks. Stealth -1 per rank. Defenses -1 per 2 ranks. Reach improves with size.
            str_sta_bonus = rank; mass_bonus = rank
            size_increase_ranks = math.floor(rank / 4) # Each 4 ranks = +1 size category from normal human (Medium)
            # Speed changes if size increases (DHH p.187 Size and Mass Table) - complex to map here simply
            # For simplicity, show primary effects.
            intim_bonus = math.floor(rank / 2); stealth_penalty = rank; def_penalty = math.floor(rank / 2)
            growth_details_list = [
                f"+{str_sta_bonus} STR & STA",
                f"+{mass_bonus} Mass Ranks",
                f"Size Category +{size_increase_ranks} (e.g., Human base +{size_increase_ranks})",
                f"+{intim_bonus} Intimidation, -{stealth_penalty} Stealth, -{def_penalty} Active Defenses"
            ]
            # Reach: Large (+1 size cat from Medium) gets 5ft reach. Huge (+2) 10ft, etc.
            if size_increase_ranks == 1: growth_details_list.append("Reach 5 ft.")
            elif size_increase_ranks == 2: growth_details_list.append("Reach 10 ft.")
            elif size_increase_ranks >=3: growth_details_list.append(f"Reach {10 + (size_increase_ranks-2)*5} ft.") # Approximation
            details.append("; ".join(growth_details_list))
        elif base_effect_id == "eff_shrinking": # DHH p.142
            # Shrinking gives +1 Stealth & Defenses per 4 ranks. STR penalty.
            # Size decreases -1 category per 4 ranks.
            stealth_def_bonus = math.floor(rank / 4) * 2 # DHH p.142: "bonuses to Dodge and Parry and Stealth equal to half Shrinking rank, rounded down" - this is +1 per 2 ranks effectively.
                                                        # Wait, DHH p.142 "Your active defenses (Dodge and Parry) and Stealth skill modifier increase by +1 for each –1 rank in size you are smaller"
                                                        # And "Size decreases by 1 rank for every 4 ranks of Shrinking"
                                                        # So, +1 Def/Stealth per 4 ranks of Shrinking.
            stealth_def_bonus_final = math.floor(rank / 4)

            size_decrease_ranks = math.floor(rank / 4)
            str_penalty = rank # Typically STR penalty = Shrinking rank
            shrinking_details_list = [
                f"+{stealth_def_bonus_final} Stealth/Defenses",
                f"Size Category -{size_decrease_ranks} (e.g., Human base -{size_decrease_ranks})",
                f"STR Penalty approx -{str_penalty} (GM may adjust)"
            ]
            details.append("; ".join(shrinking_details_list))
        elif base_effect_id == "eff_teleport": # DHH p.143 Distance Rank = Power Rank
            dist_val = self.get_measurement_by_rank(rank, 'distance')
            details.append(f"Range {dist_val}")
        
        # Add Resistance DC if applicable
        if base_effect_id in ["eff_damage", "eff_affliction", "eff_weaken", "eff_nullify"]:
            # Create a minimal CharacterState for DC calculation if a full one isn't available/needed
            # The power_def itself should contain all necessary info for DC if it's an attack.
            # For PL cap checks, a full char_state IS needed, but DC itself is often Rank + 10/15.
            # This function is for measurement_details_display, not validation.
            # For now, assume PL is not directly needed for base DC string.
            temp_char_state_for_dc = {"powerLevel": power_def.get('_temp_pl_for_calc', 10)} 
            dc_details = self.get_resistance_dc_for_power(power_def, temp_char_state_for_dc)
            if dc_details.get("dc_type") != "N/A": 
                dc_val_str = str(dc_details['dc'])
                if dc_details.get('dodge_dc_for_half'):
                    dc_val_str += f" (Dodge DC {dc_details['dodge_dc_for_half']} for half)"
                details.append(f"{dc_details['dc_type']} DC {dc_val_str}")

        return "; ".join(details) if details else ""


    def get_resistance_dc_for_power(self, power_def: PowerDefinition, char_state: CharacterState) -> Dict[str, Any]:
        dc_info = {"dc_type": "N/A", "dc": "N/A"};
        if not power_def.get('isAttack'): return dc_info # Only attacks have resistance DCs this way
        
        base_effect_id = power_def.get('baseEffectId'); rank = power_def.get('rank', 0)
        effective_rank_for_dc = rank # Modifiers like Area might change this rule, but typically it's effect rank
        
        # DHH p.127 (Damage): Resisted by Toughness DC 15 + effect rank
        if base_effect_id == 'eff_damage': 
            dc_info['dc_type'] = "Toughness"; dc_info['dc'] = 15 + effective_rank_for_dc
        # DHH p.121 (Affliction): Resisted by Fort/Will/Dodge DC 10 + effect rank
        elif base_effect_id == 'eff_affliction':
            aff_params = power_def.get('affliction_params', power_def.get('powerSpecificData',{}).get('affliction_params',{}))
            dc_info['dc_type'] = aff_params.get('resistance_type', 'Fortitude') # Default if not specified
            dc_info['dc'] = 10 + effective_rank_for_dc
        # DHH p.145 (Weaken): Resisted by Fort/Will DC 10 + effect rank
        elif base_effect_id == 'eff_weaken': 
            # Weaken resistance depends on trait. Assume common (Fort/Will) unless specified otherwise.
            # A more complex system might pull from weaken_params.
            dc_info['dc_type'] = "Fortitude or Will"; dc_info['dc'] = 10 + effective_rank_for_dc
        # DHH p.139 (Nullify): Opposed Check (Nullify rank vs. effect rank or Will of target)
        elif base_effect_id == 'eff_nullify': 
            dc_info['dc_type'] = "Opposed Check"; dc_info['dc'] = f"vs Rank {effective_rank_for_dc} (or Target's Will)"
        
        # Area effects allow Dodge for half (DHH p.149)
        if power_def.get('attackType') == 'area': 
            # Area effect rank used for Dodge DC is the rank of the Area modifier itself,
            # which can be different from the base power's effect rank if ranks are bought separately.
            # For simplicity, often Area rank = Power rank. Assume this for now.
            area_mod_config = next((mod for mod in power_def.get('modifiersConfig',[]) if mod.get('id','').startswith("mod_extra_area_")), None)
            area_mod_rank = area_mod_config.get('rank', rank) if area_mod_config else rank # Default to power rank if area mod rank not specified
            dc_info['dodge_dc_for_half'] = 10 + area_mod_rank
            
        return dc_info

    def get_attack_bonus_for_power(self, power_def: PowerDefinition, char_state: CharacterState) -> int:
        if not power_def.get('isAttack') or power_def.get('attackType') in ['area', 'perception']: return 0 
        attack_bonus = 0; abilities = char_state.get('abilities', {})
        if power_def.get('attackType') == 'close': attack_bonus += self.get_ability_modifier(abilities.get('FGT', 0))
        elif power_def.get('attackType') == 'ranged': attack_bonus += self.get_ability_modifier(abilities.get('DEX', 0))
        
        linked_skill_id = power_def.get('linkedCombatSkill')
        if linked_skill_id and linked_skill_id in char_state.get('skills', {}): 
            attack_bonus += char_state['skills'][linked_skill_id]
        
        for mod_conf in power_def.get('modifiersConfig', []):
            if mod_conf.get('id') == 'mod_extra_accurate': attack_bonus += mod_conf.get('rank', 1) * 2
            elif mod_conf.get('id') == 'mod_flaw_inaccurate_attack': attack_bonus -= mod_conf.get('rank',1) * 2
        return attack_bonus

    def calculate_derived_values(self, state: CharacterState) -> None:
        abilities = state.get('abilities', {}); advantages = state.get('advantages', [])
        initiative = self.get_ability_modifier(abilities.get('AGL', 0))
        for adv in advantages:
            if adv.get('id') == 'adv_improved_initiative': initiative += adv.get('rank', 1) * 4
        state['derived_initiative'] = initiative
        def_roll_bonus = 0
        for adv in advantages:
            if adv.get('id') == 'adv_defensive_roll': 
                # Defensive Roll rank is capped by Agility rank (DHH p.110)
                def_roll_bonus += min(adv.get('rank', 0), self.get_ability_modifier(abilities.get('AGL',0))) 
        state['derived_defensive_roll_bonus'] = def_roll_bonus
        languages_known = []; languages_granted_by_adv = 0
        for adv in advantages:
            if adv.get('id') == 'adv_languages':
                ranks = adv.get('rank', 0); langs_per_rank = 1
                adv_rule = next((r for r in self._advantages_list if r['id'] == 'adv_languages'), None)
                if adv_rule: langs_per_rank = adv_rule.get('languages_per_rank',1)
                languages_granted_by_adv += ranks * langs_per_rank
                if adv.get('params') and adv['params'].get('details_list'): 
                    languages_known.extend(adv['params']['details_list'])
        state['derived_languages_known'] = list(set(languages_known)); state['derived_languages_granted'] = languages_granted_by_adv
        total_ep_from_adv = 0
        for adv in advantages:
            if adv.get('id') == 'adv_equipment':
                adv_rule = next((r for r in self._advantages_list if r['id'] == 'adv_equipment'), None)
                if adv_rule: total_ep_from_adv += adv.get('rank', 0) * adv_rule.get('epPerRank', 5)
        state['derived_total_ep'] = total_ep_from_adv
        spent_ep = self.calculate_equipment_cost_ep(state.get('equipment', []))
        for hq_def in state.get('headquarters', []): spent_ep += self.calculate_hq_cost(hq_def, self._hq_features_list)
        for v_def in state.get('vehicles', []): spent_ep += self.calculate_vehicle_cost(v_def, self._vehicle_features_list, self._vehicle_size_stats_list)
        state['derived_spent_ep'] = spent_ep
        minion_pool_pp = 0; sidekick_pool_pp = 0
        for adv in advantages:
            adv_rule = next((r for r in self._advantages_list if r['id'] == adv.get('id')), None)
            if not adv_rule: continue
            if adv.get('id') == 'adv_minions': minion_pool_pp += adv.get('rank', 0) * adv_rule.get('points_per_rank_for_ally', 15)
            elif adv.get('id') == 'adv_sidekick': sidekick_pool_pp += adv.get('rank', 0) * adv_rule.get('points_per_rank_for_ally', 5)
        state['derived_total_minion_pool_pp'] = minion_pool_pp; state['derived_total_sidekick_pool_pp'] = sidekick_pool_pp
        spent_minion_pp = 0; spent_sidekick_pp = 0
        for ally_def in state.get('allies', []):
            if ally_def.get('source_type') == 'advantage_pool':
                if ally_def.get('type') == 'Minion': spent_minion_pp += ally_def.get('cost_pp_asserted_by_user', 0)
                elif ally_def.get('type') == 'Sidekick': spent_sidekick_pp += ally_def.get('cost_pp_asserted_by_user', 0)
        state['derived_spent_minion_pool_pp'] = spent_minion_pp; state['derived_spent_sidekick_pool_pp'] = spent_sidekick_pp

    def get_total_defense(self, char_state: CharacterState, defense_id: str, base_ability_id: str) -> int:
        abilities = char_state.get('abilities', {}); bought_defenses = char_state.get('defenses', {})
        total_defense = self.get_ability_modifier(abilities.get(base_ability_id, 0)) + bought_defenses.get(defense_id, 0)
        if defense_id == 'Toughness':
            total_defense += char_state.get('derived_defensive_roll_bonus', 0) # Already capped by AGL
            for pwr in char_state.get('powers', []):
                if pwr.get('baseEffectId') == 'eff_protection': total_defense += pwr.get('rank', 0)
                elif pwr.get('baseEffectId') == 'eff_enhanced_trait' and \
                     pwr.get('enhanced_trait_params',{}).get('category') == 'Defense' and \
                     pwr.get('enhanced_trait_params',{}).get('trait_id') == 'Toughness':
                    total_defense += pwr.get('rank',0) # Rank of ET is enhancement amount
        return total_defense

    def validate_all(self, state: CharacterState) -> List[str]:
        errors: List[str] = []; pl = state.get('powerLevel', 10)
        abilities = state.get('abilities',{})
        if state.get('spentPowerPoints', 0) > state.get('totalPowerPoints', 0): errors.append(f"PP Limit Exceeded: Spent {state['spentPowerPoints']}, Total {state['totalPowerPoints']}.")
        
        # Defense Caps
        dodge = self.get_total_defense(state, 'Dodge', 'AGL'); parry = self.get_total_defense(state, 'Parry', 'FGT'); toughness = self.get_total_defense(state, 'Toughness', 'STA'); fortitude = self.get_total_defense(state, 'Fortitude', 'STA'); will = self.get_total_defense(state, 'Will', 'AWE')
        pl_cap_paired = pl * 2
        if (dodge + toughness) > pl_cap_paired: errors.append(f"Defense Cap: Dodge ({dodge}) + Toughness ({toughness}) = {dodge + toughness} exceeds PLx2 ({pl_cap_paired}).")
        if (parry + toughness) > pl_cap_paired: errors.append(f"Defense Cap: Parry ({parry}) + Toughness ({toughness}) = {parry + toughness} exceeds PLx2 ({pl_cap_paired}).")
        if (fortitude + will) > pl_cap_paired: errors.append(f"Defense Cap: Fortitude ({fortitude}) + Will ({will}) = {fortitude + will} exceeds PLx2 ({pl_cap_paired}).")
        
        # Skill Caps
        skill_bonus_cap = pl + 10; skill_rank_cap = pl + 5
        for skill_id, ranks_bought in state.get('skills', {}).items():
            skill_name_disp = self.get_skill_name_by_id(skill_id, self._skills_list)
            if ranks_bought > skill_rank_cap: errors.append(f"Skill Rank Cap: {skill_name_disp} ranks ({ranks_bought}) exceeds PL+5 ({skill_rank_cap}).")
            skill_rule = self.get_skill_rule(skill_id)
            if skill_rule:
                gov_ab_id = skill_rule.get('ability'); ab_mod = self.get_ability_modifier(abilities.get(gov_ab_id,0)); total_bonus = ab_mod + ranks_bought
                if total_bonus > skill_bonus_cap: errors.append(f"Skill Bonus Cap: {skill_name_disp} total bonus ({total_bonus}) exceeds PL+10 ({skill_bonus_cap}).")
        
        # Power Attack Caps
        for pwr in state.get('powers', []):
            if pwr.get('isAttack'):
                effect_rank = pwr.get('rank', 0); attack_bonus = self.get_attack_bonus_for_power(pwr, state)
                pwr_name_disp = pwr.get('name', 'Unnamed Power')
                if pwr.get('attackType') in ['area', 'perception']:
                    if effect_rank > pl: errors.append(f"Power Attack Cap: {pwr_name_disp} (Area/Perception) Effect Rank ({effect_rank}) exceeds PL ({pl}).")
                else: 
                    if (attack_bonus + effect_rank) > pl_cap_paired: errors.append(f"Power Attack Cap: {pwr_name_disp} Attack Bonus ({attack_bonus}) + Effect Rank ({effect_rank}) = {attack_bonus + effect_rank} exceeds PLx2 ({pl_cap_paired}).")
        
        # Complications
        if len(state.get('complications', [])) < 2: errors.append("Character Minimum: At least 2 Complications are recommended for Hero Point generation.")
        
        # Equipment Points
        if state.get('derived_spent_ep', 0) > state.get('derived_total_ep', 0): errors.append(f"EP Limit Exceeded: Spent {state['derived_spent_ep']} EP, Total {state['derived_total_ep']} EP.")
        
        # Ally Pools
        if state.get('derived_spent_minion_pool_pp', 0) > state.get('derived_total_minion_pool_pp', 0): errors.append(f"Minion Pool Overspent: Used {state['derived_spent_minion_pool_pp']} PP, Available {state['derived_total_minion_pool_pp']} PP.")
        if state.get('derived_spent_sidekick_pool_pp', 0) > state.get('derived_total_sidekick_pool_pp', 0): errors.append(f"Sidekick Pool Overspent: Used {state['derived_spent_sidekick_pool_pp']} PP, Available {state['derived_total_sidekick_pool_pp']} PP.")
        
        # Advantage Specific Validations
        for adv_entry in state.get('advantages', []):
            adv_rule = next((r for r in self._advantages_list if r['id'] == adv_entry.get('id')), None)
            if not adv_rule: continue
            
            adv_name_disp = adv_rule.get('name', adv_entry.get('id'))
            current_rank = adv_entry.get('rank', 1)
            max_rank_allowed = float('inf')
            max_rank_source_text = ""

            if adv_rule.get('maxRanks_source'): # e.g., "AGL" for Defensive Roll
                source_ability_id = adv_rule['maxRanks_source']
                # For Defensive Roll, max rank is AGL *modifier*, not rank. DHH p.110
                # But the rule file should specify if it's mod or rank. Assume rank if just ID.
                # Defensive Roll specifically says "Your maximum Defensive Roll rank is equal to your Agility rank."
                # So, this should be Agility *rank*, not modifier.
                max_rank_allowed = abilities.get(source_ability_id, 0)
                max_rank_source_text = f"{source_ability_id} rank ({max_rank_allowed})"
                if current_rank > max_rank_allowed:
                    errors.append(f"Advantage Validation: {adv_name_disp} rank ({current_rank}) cannot exceed {max_rank_source_text}.")
            elif adv_rule.get('maxRanks') is not None: # Numeric maxRanks
                max_rank_allowed = adv_rule['maxRanks']
                max_rank_source_text = str(max_rank_allowed)
                if current_rank > max_rank_allowed:
                     errors.append(f"Advantage Validation: {adv_name_disp} rank ({current_rank}) cannot exceed max rank of {max_rank_source_text}.")
            
            # Parameter Validations
            if adv_rule.get('parameter_needed'):
                params = adv_entry.get('params', {})
                param_storage_key = adv_rule.get('parameter_storage_key', adv_rule.get('id', 'detail')) # Check if specific key needed
                
                # General check for presence of any relevant parameter if 'params' is expected.
                # This is simplified; a truly robust check would look for specific expected keys based on param_type.
                if not params or not params.get(param_storage_key, params.get('detail', params.get('selected_option', params.get('skill_id', params.get('details_list'))))): # Check common param keys
                     # Check for specific known param structures
                    if adv_rule.get('parameter_type') == "list_string" and not params.get(adv_rule.get('parameter_list_key','details_list'),[]):
                         errors.append(f"Advantage Validation: {adv_name_disp} requires details to be specified (e.g., for Benefit, Languages).")
                    elif adv_rule.get('parameter_type') not in ["list_string", "complex_config_note"] and not params: # Generic check if not list or note type
                        errors.append(f"Advantage Validation: {adv_name_disp} requires specific parameter(s) to be set.")


                if adv_rule.get('parameter_type') == 'select_from_options':
                    selected_val = params.get(param_storage_key, params.get('selected_option'))
                    allowed_options = [opt.get('value') for opt in adv_rule.get('parameter_options', [])]
                    if selected_val not in allowed_options:
                        errors.append(f"Advantage Validation: Invalid parameter '{selected_val}' for {adv_name_disp}. Allowed: {allowed_options}.")
                
                elif adv_rule.get('parameter_type') == 'select_skill':
                    skill_id_param = params.get(param_storage_key, params.get('skill_id'))
                    if not skill_id_param or not self.get_skill_rule(skill_id_param):
                        errors.append(f"Advantage Validation: Invalid or missing skill parameter for {adv_name_disp}.")

                # Languages specific count check
                if adv_entry.get('id') == 'adv_languages':
                    langs_per_rank = adv_rule.get('languages_per_rank',1)
                    num_granted = current_rank * langs_per_rank
                    specified_langs = params.get(adv_rule.get('parameter_list_key','details_list'), [])
                    num_specified = len(specified_langs) if specified_langs else 0
                    if num_specified > num_granted: 
                        errors.append(f"Advantage Validation: {adv_name_disp} grants {num_granted} language(s), but {num_specified} are specified.")
                    elif num_specified < num_granted and num_granted > 0 : # If they bought ranks but didn't specify all
                         errors.append(f"Advantage Validation: {adv_name_disp} grants {num_granted} language(s), but only {num_specified} are specified.")
        return errors

    def recalculate(self, state: CharacterState) -> CharacterState:
        recalc_state = copy.deepcopy(state); recalc_state['validationErrors'] = []
        
        # Initialize recursion detection set for this recalculation cycle
        # This set will be passed down through power costing functions.
        costing_recursion_detection_set = set()

        recalc_state = self.apply_enhancements(recalc_state)
        updated_powers_list = []
        all_powers_for_context = list(recalc_state.get('powers', [])) 
        for pwr_def_orig in recalc_state.get('powers', []): 
            pwr_def = copy.deepcopy(pwr_def_orig) 
            base_effect_rule = next((e for e in self._power_effects_list if e['id'] == pwr_def.get('baseEffectId')), None)
            if base_effect_rule:
                pwr_def['final_duration'] = self._derive_final_duration(base_effect_rule.get('defaultDuration', 'Instant'), pwr_def.get('modifiersConfig', []))
                pwr_def['final_range'] = self._derive_final_range(base_effect_rule.get('defaultRange', 'Personal'), pwr_def.get('modifiersConfig', []), pwr_def.get('rank',0), base_effect_rule)
                pwr_def['final_action'] = self._derive_final_action(base_effect_rule.get('defaultAction', 'Standard'), pwr_def.get('modifiersConfig', []))
                is_attack_flag = base_effect_rule.get('type', '').lower() == 'attack'
                # Check if any modifier explicitly makes it an attack (e.g. "Attack" Extra on a Personal effect)
                if any(m_rule.get('changesActionFromPersonalToAttack') for m_conf in pwr_def.get('modifiersConfig', []) for m_rule in [next((m for m in self._power_modifiers_list if m['id'] == m_conf.get('id')), None)] if m_rule):
                    is_attack_flag = True
                pwr_def['isAttack'] = is_attack_flag

                if is_attack_flag:
                    current_range_derived = pwr_def['final_range'].lower()
                    if 'perception' in current_range_derived: pwr_def['attackType'] = 'perception'
                    elif 'area' in current_range_derived: pwr_def['attackType'] = 'area'
                    elif 'ranged' in current_range_derived: pwr_def['attackType'] = 'ranged'
                    else: pwr_def['attackType'] = 'close' 
                else: pwr_def['attackType'] = 'none'
            if pwr_def.get('baseEffectId') == 'eff_variable': pwr_def['variablePointPool'] = pwr_def.get('rank', 0) * 5
            if base_effect_rule and base_effect_rule.get('isAllyEffect'): pwr_def['allotted_pp_for_creation'] = pwr_def.get('rank', 0) * base_effect_rule.get('grantsAllyPointsFactor', 15)
            
            # Pass the initialized (or power-specific) recursion set
            current_pwr_id_for_costing = pwr_def.get('id')
            initial_recursion_set_for_this_power = set(costing_recursion_detection_set) # Copy from overall set for this power
            if current_pwr_id_for_costing:
                initial_recursion_set_for_this_power.add(current_pwr_id_for_costing)

            cost_details = self.calculate_individual_power_cost(pwr_def, all_powers_for_context, _costing_recursion_set=initial_recursion_set_for_this_power)
            pwr_def['cost'] = cost_details['totalCost']; pwr_def['costPerRankFinal'] = cost_details['costPerRankFinal']; pwr_def['costBreakdown'] = cost_details['costBreakdown']
            if pwr_def.get('isAttack'):
                 pwr_def['resistance_dc_details'] = self.get_resistance_dc_for_power(pwr_def, recalc_state)
                 pwr_def['attack_bonus_total'] = self.get_attack_bonus_for_power(pwr_def, recalc_state) 
            pwr_def['measurement_details_display'] = self.get_power_measurement_details(pwr_def, self.rule_data)
            updated_powers_list.append(pwr_def)
        recalc_state['powers'] = updated_powers_list
        self.calculate_derived_values(recalc_state) 
        recalc_state['spentPowerPoints'] = self.calculate_all_costs(recalc_state)
        recalc_state['validationErrors'].extend(self.validate_all(recalc_state)) # Use extend to preserve other errors
        
        # Recursion validation errors are not directly added here, but a warning would be printed during costing.
        # A more robust system might collect these warnings and add them to validationErrors.
        # For now, the costing function prints a warning to console.

        return recalc_state

    def calculate_all_costs(self, char_state: CharacterState) -> int:
        total_pp = 0
        total_pp += self.calculate_ability_cost(char_state.get('abilities', {}))
        total_pp += self.calculate_defense_cost(char_state.get('defenses', {}))
        total_pp += self.calculate_skill_cost(char_state.get('skills', {}))
        total_pp += self.calculate_advantage_cost(char_state.get('advantages', []))
        total_pp += self.calculate_power_cost(char_state.get('powers', []))
        return total_pp