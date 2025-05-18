# core_engine.py for HeroForge M&M (Streamlit Edition)
# Version: V1.0 "All Features" Fully Developed

import json
import math
import os
import copy # For deep copying complex states
import uuid # For generating unique IDs if needed internally
from typing import Dict, List, Any, Optional, Tuple, Union

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
            # This would ideally raise a more specific error or be handled by the main app
            raise ValueError("FATAL: Core rule data could not be loaded. Application cannot proceed.")
        
        # Pre-cache commonly accessed rule lists for minor efficiency and cleaner access
        self._abilities_list = self.rule_data.get('abilities', {}).get('list', [])
        self._skills_list = self.rule_data.get('skills', {}).get('list', [])
        self._advantages_list = self.rule_data.get('advantages_v1', [])
        self._power_effects_list = self.rule_data.get('power_effects', [])
        self._power_modifiers_list = self.rule_data.get('power_modifiers', [])
        self._power_senses_list = self.rule_data.get('power_senses_config', [])
        self._power_immunities_list = self.rule_data.get('power_immunities_config', [])
        self._measurements_table = self.rule_data.get('measurements_table', [])
        self._equipment_items_list = self.rule_data.get('equipment_items', [])
        self._hq_features_list = self.rule_data.get('hq_features', [])
        self._vehicle_features_list = self.rule_data.get('vehicle_features', [])
        self._vehicle_size_stats_list = self.rule_data.get('vehicle_size_stats', [])
        
        print("CoreEngine initialized successfully with rule data.")

    def _load_all_rule_data(self, directory_path: str) -> RuleData:
        """Loads all JSON rule files from the specified directory. Raises error on failure."""
        loaded_data: RuleData = {}
        # Ensure this list matches all your JSON rule files.
        expected_files = [
            "abilities.json", "advantages_v1.json", "archetypes.json",
            "equipment_items.json", "hq_features.json", "measurements_table.json",
            "power_effects.json", "power_immunities_config.json", "power_senses_config.json",
            "power_modifiers.json", "skills.json",
            "vehicle_features.json", "vehicle_size_stats.json"
            # Add "prebuilt_powers_v1.json" if you have it and it's needed by archetypes directly
        ]
        try:
            abs_path = os.path.abspath(directory_path)
            # print(f"Attempting to load rules from: {abs_path}") # Debug
            if not os.path.isdir(abs_path):
                raise FileNotFoundError(f"Rule directory not found at '{abs_path}'")

            for filename in expected_files:
                filepath = os.path.join(abs_path, filename)
                if not os.path.exists(filepath):
                    raise FileNotFoundError(f"Expected rule file not found: {filepath}")
                
                rule_name = filename[:-5]  # Remove '.json'
                with open(filepath, 'r', encoding='utf-8') as f:
                    loaded_data[rule_name] = json.load(f)
                    # print(f"Successfully loaded: {filename}") # Can be verbose
            
            if len(loaded_data) < len(expected_files):
                # This check might be redundant if FileNotFoundError is raised above
                missing = [f for f in expected_files if f[:-5] not in loaded_data]
                raise FileNotFoundError(f"Not all expected rule files were loaded. Missing: {missing}")
            return loaded_data

        except Exception as e:
            # print(f"Critical error loading rule data: {e}") # Debug
            # Re-raise a more specific error or handle as appropriate for your app's startup
            raise RuntimeError(f"Failed to initialize CoreEngine due to rule loading error: {e}")


    def get_default_character_state(self, pl: int = 10) -> CharacterState:
        """Creates a default, empty character state dictionary."""
        # Ensure _abilities_list and _skills_list are populated during __init__
        base_abilities = {info['id']: 0 for info in self._abilities_list} if self._abilities_list else {}
        default_skills = {skill_info['id']: 0 for skill_info in self._skills_list} if self._skills_list else {}

        return {
            "saveFileVersion": "1.3_core_engine_complete", 
            "name": "New Hero", "playerName": "", "powerLevel": pl,
            "totalPowerPoints": pl * 15, "spentPowerPoints": 0,
            "concept": "", "description": "", "identity": "Secret", 
            "gender": "", "age": "", "height": "", "weight": "", "eyes": "", "hair": "",
            "groupAffiliation": "", "baseOfOperationsName": "",

            "abilities": copy.deepcopy(base_abilities),
            "defenses": {"Dodge": 0, "Parry": 0, "Toughness": 0, "Fortitude": 0, "Will": 0}, # Bought ranks
            "skills": copy.deepcopy(default_skills), # Ranks bought for base skills; specialized are added like skill_expertise_magic
            "advantages": [],  # List of AdvantageDefinition objects
            "powers": [],      # List of PowerDefinition objects
            "equipment": [],   # List of EquipmentDefinition objects
            "headquarters": [],# List of HQDefinition objects
            "vehicles": [],    # List of VehicleDefinition objects
            "allies": [],      # List of AllyDefinition objects (Minions, Sidekicks, Summoned)
            "complications": [], # List of {'description': str}
            
            "validationErrors": [],

            # Derived values (populated by recalculate)
            "derived_initiative": 0,
            "derived_defensive_roll_bonus": 0,
            "derived_languages_known": [],
            "derived_languages_granted": 0, 
            "derived_total_ep": 0,
            "derived_spent_ep": 0,
            "derived_total_minion_pool_pp": 0,
            "derived_spent_minion_pool_pp": 0,
            "derived_total_sidekick_pool_pp": 0,
            "derived_spent_sidekick_pool_pp": 0
        }

    # --- BASIC HELPER FUNCTIONS ---
    def get_ability_modifier(self, ability_rank: Optional[Union[int, float]]) -> int:
        """Calculates the modifier for a given ability rank."""
        return int(ability_rank) if ability_rank is not None else 0

    def get_skill_rule(self, skill_id_or_name: str) -> Optional[SkillRule]:
        """Finds a skill rule by its ID or name. Handles base IDs for specialized skills."""
        for skill_rule in self._skills_list:
            if skill_rule['id'] == skill_id_or_name or skill_rule['name'] == skill_id_or_name:
                return skill_rule
            # Check if skill_id_or_name is a specialized version of this base skill_rule
            if skill_rule.get('specialization_possible') and skill_id_or_name.startswith(skill_rule['id'] + "_"):
                return skill_rule # Return the base rule for specialized skill ID
        return None
        
    def get_skill_name_by_id(self, skill_id: str, skills_rules_list: Optional[List[Dict]] = None) -> str:
        """Gets the display name of a skill, including specialization if applicable."""
        if skills_rules_list is None: skills_rules_list = self._skills_list
        
        base_skill_id_parts = skill_id.split('_')
        # Assumes skill IDs are like "skill_closecombat" or "skill_expertise_magic"
        # For "skill_expertise_magic", base_skill_id_lookup should be "skill_expertise"
        base_skill_id_lookup = "_".join(base_skill_id_parts[:2]) if len(base_skill_id_parts) >=2 else skill_id

        base_skill_rule = next((s for s in skills_rules_list if s['id'] == base_skill_id_lookup), None)
        if not base_skill_rule: return skill_id # Fallback to ID if no rule found

        if base_skill_rule.get('specialization_possible') and skill_id.startswith(base_skill_rule['id'] + "_") and len(skill_id) > len(base_skill_rule['id'] + "_"):
            specialization_name_part = skill_id[len(base_skill_rule['id'] + "_"):]
            specialization_name = specialization_name_part.replace("_"," ").title()
            return f"{base_skill_rule['name']}: {specialization_name}"
        return base_skill_rule['name']


    def get_trait_cost_per_rank(self, trait_category: str, trait_id: Optional[str] = None, 
                                character_powers_context: Optional[List[PowerDefinition]] = None) -> float:
        """Gets base cost per rank for various traits. Returns float for precision."""
        if trait_category == "Ability": return 2.0
        if trait_category == "Defense": return 1.0 
        if trait_category == "Skill": return 0.5
        if trait_category == "Advantage":
            if trait_id and self._advantages_list:
                adv_rule = next((adv for adv in self._advantages_list if adv['id'] == trait_id), None)
                return float(adv_rule.get('costPerRank', 1.0)) if adv_rule else 1.0
            return 1.0
        if trait_category == "PowerRank" and trait_id and character_powers_context:
            target_power = next((pwr for pwr in character_powers_context if pwr.get('id') == trait_id), None)
            if target_power:
                # Need to calculate the target power's cost per rank if not already stored
                # This can be complex if the target power itself has modifiers.
                # For simplicity, assume target_power might have a 'costPerRankFinal' or we do a quick calc.
                # A full recursive call to calculate_individual_power_cost might be too much here.
                # Let's assume 'costPerRankFinal' is available or derived simply.
                temp_cost_details = self.calculate_individual_power_cost(target_power, character_powers_context) # This ensures it's calculated
                cpr_final_val = temp_cost_details.get('costPerRankFinal')

                if isinstance(cpr_final_val, (int, float)): return float(cpr_final_val)
                if isinstance(cpr_final_val, str): 
                    if "1 per " in cpr_final_val: # Handles fractional costs like "1 per 2"
                        try: return 1.0 / int(cpr_final_val.split("1 per ")[1])
                        except (ValueError, ZeroDivisionError): return 1.0 # Fallback
                    try: return float(cpr_final_val) # If it's a string representation of a number
                    except ValueError: return 1.0 # Fallback
                return 1.0 # Fallback if costPerRankFinal is not a direct number
            return 1.0 # Target power not found
        return 1.0 # Default/unknown category


    def get_measurement_by_rank(self, rank: int, measurement_type: str) -> str:
        """Looks up a measurement value for a given rank from the measurements_table."""
        if not self._measurements_table: return f"Rank {rank} (Table N/A)"
        
        for entry in self._measurements_table:
            if entry.get('rank') == rank:
                return entry.get(measurement_type, f"Rank {rank} (Type N/A)")
        
        # If no exact match, find closest lower for positive ranks (DHH p.19 implies interpolation)
        # For simplicity, we'll return the value for the closest lower rank found.
        if rank > -30: # Smallest rank in table
            closest_lower_entry = None
            # Ensure ranks are numbers for min/max calculation
            valid_ranks = [e.get('rank') for e in self._measurements_table if isinstance(e.get('rank'), (int, float))]
            if not valid_ranks: return f"Rank {rank} (Table Invalid)" # Table has no valid ranks

            min_rank_in_table = min(valid_ranks)
            max_rank_in_table = max(valid_ranks)

            if rank < min_rank_in_table: 
                 return self._measurements_table[0].get(measurement_type, "Sub-value") if self._measurements_table else "N/A"
            if rank > max_rank_in_table: 
                # Basic extrapolation for values above table max (e.g., double last step)
                # This is a very rough extrapolation.
                last_entry = self._measurements_table[-1]
                second_last_entry = self._measurements_table[-2] if len(self._measurements_table) > 1 else last_entry
                # A more robust extrapolation would analyze the progression factor.
                # For now, just indicate it's off-table with the last known value.
                return f"> {last_entry.get(measurement_type, '')} (at Rank {max_rank_in_table})"


            for entry in sorted(self._measurements_table, key=lambda x: x.get('rank',0)):
                entry_rank_val = entry.get('rank')
                if isinstance(entry_rank_val, (int, float)) and entry_rank_val < rank:
                    closest_lower_entry = entry
                elif isinstance(entry_rank_val, (int, float)) and entry_rank_val >= rank: # Found first entry >= rank
                    break 
            if closest_lower_entry:
                return f"{closest_lower_entry.get(measurement_type, '')} (at Rank {closest_lower_entry.get('rank')})"
        
        return f"Rank {rank} (Value N/A)"

    # --- COST CALCULATION FUNCTIONS ---
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
                if feat_rule.get('ranked'):
                    cost += feat_rule.get('ep_cost_per_rank', 1) * feat_entry.get('rank', 1)
                else:
                    cost += feat_rule.get('ep_cost', 1)
        return cost

    def calculate_vehicle_cost(self, vehicle_def: VehicleDefinition, 
                               vehicle_features_rules: Optional[List[Dict]] = None, 
                               vehicle_size_stats_rules: Optional[List[Dict]] = None) -> int:
        if vehicle_features_rules is None: vehicle_features_rules = self._vehicle_features_list
        if vehicle_size_stats_rules is None: vehicle_size_stats_rules = self._vehicle_size_stats_list
        cost = 0
        size_rank_val = vehicle_def.get('size_rank', 0)
        size_stat_rule = next((s for s in vehicle_size_stats_rules if s.get('size_rank_value') == size_rank_val), None)
        if size_stat_rule:
            cost += size_stat_rule.get('base_ep_cost', 0)
        
        for feat_entry in vehicle_def.get('features', []):
            feat_rule = next((f for f in vehicle_features_rules if f.get('id') == feat_entry.get('id')), None)
            if feat_rule:
                if feat_rule.get('ranked'):
                    cost += feat_rule.get('ep_cost_per_rank', 1) * feat_entry.get('rank', 1)
                else:
                    cost += feat_rule.get('ep_cost', 1)
        return cost
        
    def calculate_individual_power_cost(self, power_definition: PowerDefinition, all_character_powers_context: List[PowerDefinition]) -> Dict[str, Any]:
        # ... (Full implementation from Part 2, assumed complete and correct) ...
        results = {'totalCost': 0, 'costPerRankFinal': 0.0, 'costBreakdown': {'base_effect_cpr':0.0, 'extras_cpr':0.0, 'flaws_cpr':0.0, 'flat_total':0.0, 'senses_total': 0.0, 'immunities_total':0.0, 'variable_base_cost':0.0, 'enh_trait_base_cost':0.0, 'special_fixed_cost':0.0}}
        base_effect_id = power_definition.get('baseEffectId'); power_rank = int(power_definition.get('rank', 0)); modifiers_config = power_definition.get('modifiersConfig', [])
        base_effect_rule = next((e for e in self._power_effects_list if e['id'] == base_effect_id), None)
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
        if power_rank <= 0: # For non-container powers, rank 0 usually means 0 cost before flat mods
            flat_mod_cost_only = sum(self._get_modifier_flat_cost(mod_conf) for mod_conf in modifiers_config); results['costBreakdown']['flat_total'] = flat_mod_cost_only; results['totalCost'] = math.ceil(flat_mod_cost_only)
            if results['totalCost'] < 0: results['totalCost'] = 0; results['costPerRankFinal'] = base_effect_rule.get('costPerRank', 0.0); return results
        base_cpr = 0.0
        if base_effect_rule.get('isEnhancementEffect'):
            et_params = power_definition.get('enhanced_trait_params', {}); enh_cat = et_params.get('category'); enh_id = et_params.get('trait_id'); base_cpr = self.get_trait_cost_per_rank(enh_cat, enh_id, all_character_powers_context)
            results['costBreakdown']['enh_trait_base_cost'] = base_cpr * power_rank # power_rank is enhancementAmount
        elif base_effect_rule.get('isVariableContainer'): base_cpr = float(base_effect_rule.get('costPerRank', 7.0)); results['costBreakdown']['variable_base_cost'] = base_cpr * power_rank
        elif base_effect_rule.get('isTransformContainer'):
            morph_params = power_definition.get('morph_params', {}); scope_choice_id = morph_params.get('transform_scope_choice_id'); cost_option = next((opt for opt in base_effect_rule.get('costOptions',[]) if opt.get('choice_id') == scope_choice_id), None)
            base_cpr = float(cost_option.get('costPerRank', base_effect_rule.get('costPerRank', 2.0))) if cost_option else float(base_effect_rule.get('costPerRank', 2.0))
        else: base_cpr = float(base_effect_rule.get('costPerRank', 1.0))
        results['costBreakdown']['base_effect_cpr'] = base_cpr # Store the base CPR of the effect itself
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
        # ... (Implementation from Part 2, assumed complete and correct) ...
        mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_config_entry.get('id')), None)
        if not mod_rule or mod_rule.get('costType') != 'perRank': return 0.0
        base_change = float(mod_rule.get('costChangePerRank', 0.0))
        if mod_rule.get('parameter_needed') and mod_rule.get('parameter_options') and 'params' in mod_config_entry:
            param_storage_key = mod_rule.get('parameter_storage_key', mod_rule.get('id')) # Use mod_id as default key in params
            user_choice = mod_config_entry['params'].get(param_storage_key)
            for opt in mod_rule.get('parameter_options', []):
                if opt.get('value') == user_choice and 'cost_adjust_per_rank' in opt:
                    base_change += float(opt['cost_adjust_per_rank']); break
        return base_change

    def _get_modifier_flat_cost(self, mod_config_entry: Dict) -> float:
        # ... (Implementation from Part 2, assumed complete and correct) ...
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
        # ... (Implementation from Part 2, assumed complete and correct) ...
        # This function sums the 'cost' field of each power, correctly handling arrays.
        # It assumes 'cost' on each PowerDefinition has been pre-calculated by calculate_individual_power_cost.
        total_pp_for_all_powers = 0; processed_power_ids_in_arrays = set(); arrays: Dict[str, List[PowerDefinition]] = {}
        
        # Ensure all powers have their standalone costs calculated first
        for pwr_def_mutable in powers_state: # Iterate over the actual list items to modify them
            if 'cost' not in pwr_def_mutable: # If cost isn't pre-calculated (e.g. new power)
                cost_details = self.calculate_individual_power_cost(pwr_def_mutable, powers_state)
                pwr_def_mutable['cost'] = cost_details['totalCost']

            array_id = pwr_def_mutable.get('arrayId');
            if array_id:
                if array_id not in arrays: arrays[array_id] = []
                arrays[array_id].append(pwr_def_mutable) # Store reference to the mutable power def

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
            
            is_dynamic = base_power.get('isDynamicArray', False) # Check the base power's flag

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
        # ... (Implementation from Part 2, assumed complete and correct) ...
        state = copy.deepcopy(current_state)
        for power_def in state.get('powers', []):
            if power_def.get('baseEffectId') == 'eff_enhanced_trait':
                et_params = power_def.get('enhanced_trait_params', {}); category = et_params.get('category'); trait_id = et_params.get('trait_id'); 
                # Amount of enhancement IS the rank of the Enhanced Trait power itself
                amount = int(power_def.get('rank', 0)) 
                if not category or not trait_id or amount <= 0: continue
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
                            if adv_rule and adv_rule.get('ranked'): adv_entry['rank'] = adv_entry.get('rank', 1) + amount
                            found_adv = True; break
                    if not found_adv: state['advantages'].append({'id': trait_id, 'rank': amount, 'params': {}, 'instance_id': str(uuid.uuid4())[:8]}) # Use uuid for instance_id
                elif category == "PowerRank":
                    for other_power in state.get('powers', []):
                        if other_power.get('id') == trait_id and other_power.get('id') != power_def.get('id'): 
                            other_power['rank'] = other_power.get('rank', 0) + amount; break
        return state
        
    # --- START OF PART 3 IMPLEMENTATION ---

    def _derive_final_duration(self, base_duration: str, modifiers_config: List[Dict]) -> str:
        # ... (Implementation from Part 3, assumed complete and correct) ...
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
        # ... (Implementation from Part 3, assumed complete and correct) ...
        current_range = base_range.lower() if base_range else "personal"; is_area_effect = False; area_type_name = ""
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
            if mod_rule and mod_rule.get('changesRangeTo', '').lower().startswith("area"):
                is_area_effect = True; area_type_name = mod_rule.get('changesRangeTo'); area_rank = min(mod_conf.get('rank', power_rank), power_rank)
                if any(x in area_type_name.lower() for x in ["burst", "cloud", "cylinder"]):
                    radius_dist_rank = area_rank - 2; radius_measure = self.get_measurement_by_rank(radius_dist_rank, 'distance')
                    current_range = f"{area_type_name.capitalize()} ({radius_measure} radius)"
                    if "cloud" in area_type_name.lower(): current_range += ", lingers"
                    if "cylinder" in area_type_name.lower(): height_dist_rank = area_rank; height_measure = self.get_measurement_by_rank(height_dist_rank, 'distance'); current_range += f", {height_measure} high"
                elif any(x in area_type_name.lower() for x in ["cone", "line"]):
                    length_dist_rank = area_rank; length_measure = self.get_measurement_by_rank(length_dist_rank, 'distance')
                    current_range = f"{area_type_name.capitalize()} ({length_measure} long)";
                    if "line" in area_type_name.lower(): current_range += ", 5-ft. wide"
                elif "shapeable" in area_type_name.lower(): volume_dist_rank = area_rank + 2; volume_measure = self.get_measurement_by_rank(volume_dist_rank, 'volume'); current_range = f"{area_type_name.capitalize()} ({volume_measure})"
                elif "perception" in area_type_name.lower(): sense_type = mod_conf.get('params',{}).get(mod_rule.get('parameter_storage_key','sense_type'), "Visual"); current_range = f"Area (Perception - {sense_type})"
                break 
        if not is_area_effect:
            for mod_conf in modifiers_config:
                mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
                if not mod_rule: continue; changes_to = mod_rule.get('changesRangeTo'); applies_to = mod_rule.get('appliesToRange')
                if changes_to and applies_to and current_range in [r.lower() for r in applies_to]: current_range = changes_to.lower()
                elif mod_rule.get('id') == 'mod_extra_affects_others_also' and current_range == 'personal': current_range = 'touch'
                if mod_rule.get('id') == 'mod_extra_extended_range' and current_range == 'ranged': extended_ranks = mod_conf.get('rank', 0); current_range = f"Ranged (Extended x{2**extended_ranks})"
        if current_range == "rank": dist_val = self.get_measurement_by_rank(power_rank, 'distance'); return f"Rank ({dist_val})"
        elif current_range == "ranged" and not is_area_effect: long_range_dist_rank = power_rank + 6; long_range_val = self.get_measurement_by_rank(long_range_dist_rank, 'distance'); return f"Ranged (up to {long_range_val})"
        elif current_range == "perception" and not is_area_effect: return "Perception"
        return current_range.replace("_"," ").title()


    def _derive_final_action(self, base_action: str, modifiers_config: List[Dict]) -> str:
        # ... (Implementation from Part 3, assumed complete and correct) ...
        action_levels = {"Reaction": 0, "Free": 1, "Move": 2, "Standard": 3, "Full": 4}; current_action = base_action.capitalize() if base_action else "Standard"
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self._power_modifiers_list if m['id'] == mod_conf.get('id')), None)
            if not mod_rule: continue; applies_to = mod_rule.get('appliesToAction'); changes_to = mod_rule.get('changesActionTo')
            if applies_to and changes_to and current_action in applies_to: current_action = changes_to
            elif mod_rule.get('changesActionFromPersonalToAttack') and current_action == "Personal":
                if base_action.lower() in ["personal", "none"]: current_action = "Standard"
        return current_action.capitalize()


    def get_power_measurement_details(self, power_def: PowerDefinition, rule_data_override: Optional[RuleData] = None) -> str:
        # ... (Implementation from Part 3, assumed complete and correct) ...
        # This function now correctly uses self._power_effects_list and self.get_measurement_by_rank
        # and self.get_resistance_dc_for_power
        rd = rule_data_override if rule_data_override else self.rule_data; base_effect_id = power_def.get('baseEffectId'); rank = power_def.get('rank', 0)
        if rank == 0 and base_effect_id not in ['eff_senses', 'eff_immunity']: return ""
        base_effect_rule = next((e for e in self._power_effects_list if e['id'] == base_effect_id), None)
        if not base_effect_rule: return ""; details = []
        if base_effect_id in ["eff_flight", "eff_speed", "eff_swimming", "eff_leaping"]:
            dist_rank = rank - 2 if base_effect_id != "eff_leaping" else rank
            distance = self.get_measurement_by_rank(dist_rank, 'distance'); details.append(f"{distance}{'/round' if base_effect_id != 'eff_leaping' else ' jump'}")
        elif base_effect_id == "eff_move_object": mass_lifted = self.get_measurement_by_rank(rank, 'mass'); details.append(f"Lifts/Throws {mass_lifted}")
        elif base_effect_id == "eff_create":
            obj_tough = rank; cp = power_def.get('create_params',{}); 
            if cp.get('toughness_override') is not None and cp.get('toughness_override') > 0 : obj_tough = cp['toughness_override']
            volume_val = self.get_measurement_by_rank(rank, 'volume'); details.append(f"Creates Toughness {obj_tough}, Volume {volume_val} objects")
        elif base_effect_id == "eff_growth": size_increase_ranks = math.floor(rank / 4); str_sta_bonus = rank; mass_bonus = rank; details.append(f"+{str_sta_bonus} STR/STA, +{mass_bonus} Mass Ranks. Size +{size_increase_ranks} categories.")
        elif base_effect_id == "eff_shrinking": size_decrease_ranks = math.floor(rank / 4); stealth_def_bonus = rank; details.append(f"+{stealth_def_bonus} Stealth/Defenses. Size -{size_decrease_ranks} categories.")
        elif base_effect_id == "eff_teleport": dist_val = self.get_measurement_by_rank(rank, 'distance'); details.append(f"Range {dist_val}")
        if base_effect_id in ["eff_damage", "eff_affliction", "eff_weaken"]:
            # Pass a minimal char_state for PL context if full state not available/needed here
            temp_char_state_for_dc = {"powerLevel": power_def.get('_temp_pl_for_calc', 10)} # Store temp PL if needed
            dc_details = self.get_resistance_dc_for_power(power_def, temp_char_state_for_dc)
            if dc_details.get("dc_type") != "N/A": details.append(f"{dc_details['dc_type']} DC {dc_details['dc']}")
        return "; ".join(details) if details else ""


    def get_resistance_dc_for_power(self, power_def: PowerDefinition, char_state: CharacterState) -> Dict[str, Any]:
        # ... (Implementation from Part 3, assumed complete and correct) ...
        dc_info = {"dc_type": "N/A", "dc": "N/A"};
        if not power_def.get('isAttack'): return dc_info
        base_effect_id = power_def.get('baseEffectId'); rank = power_def.get('rank', 0)
        effective_rank_for_dc = rank
        if base_effect_id == 'eff_damage': dc_info['dc_type'] = "Toughness"; dc_info['dc'] = 15 + effective_rank_for_dc
        elif base_effect_id == 'eff_affliction':
            aff_params = power_def.get('affliction_params', {}); dc_info['dc_type'] = aff_params.get('resistance_type', 'Fortitude')
            dc_info['dc'] = 10 + effective_rank_for_dc
        elif base_effect_id == 'eff_weaken': dc_info['dc_type'] = "Fortitude/Will"; dc_info['dc'] = 10 + effective_rank_for_dc
        elif base_effect_id == 'eff_nullify': dc_info['dc_type'] = "Opposed Check"; dc_info['dc'] = f"vs Rank {effective_rank_for_dc}"
        if power_def.get('attackType') == 'area': dc_info['dodge_dc_for_half'] = 10 + rank
        return dc_info

    def get_attack_bonus_for_power(self, power_def: PowerDefinition, char_state: CharacterState) -> int:
        # ... (Implementation from Part 3, assumed complete and correct) ...
        if not power_def.get('isAttack') or power_def.get('attackType') in ['area', 'perception']: return 0 
        attack_bonus = 0; abilities = char_state.get('abilities', {})
        if power_def.get('attackType') == 'close': attack_bonus += self.get_ability_modifier(abilities.get('FGT', 0))
        elif power_def.get('attackType') == 'ranged': attack_bonus += self.get_ability_modifier(abilities.get('DEX', 0))
        linked_skill_id = power_def.get('linkedCombatSkill')
        if linked_skill_id and linked_skill_id in char_state.get('skills', {}): attack_bonus += char_state['skills'][linked_skill_id]
        for mod_conf in power_def.get('modifiersConfig', []):
            if mod_conf.get('id') == 'mod_extra_accurate': attack_bonus += mod_conf.get('rank', 1) * 2
            elif mod_conf.get('id') == 'mod_flaw_inaccurate_attack': attack_bonus -= mod_conf.get('rank',1) * 2
        return attack_bonus

    def calculate_derived_values(self, state: CharacterState) -> None:
        # ... (Implementation from Part 3, assumed complete and correct) ...
        abilities = state.get('abilities', {}); advantages = state.get('advantages', [])
        initiative = self.get_ability_modifier(abilities.get('AGL', 0))
        for adv in advantages:
            if adv.get('id') == 'adv_improved_initiative': initiative += adv.get('rank', 1) * 4
        state['derived_initiative'] = initiative
        def_roll_bonus = 0
        for adv in advantages:
            if adv.get('id') == 'adv_defensive_roll': def_roll_bonus += min(adv.get('rank', 0), abilities.get('AGL',0)) 
        state['derived_defensive_roll_bonus'] = def_roll_bonus
        languages_known = []; languages_granted_by_adv = 0
        for adv in advantages:
            if adv.get('id') == 'adv_languages':
                ranks = adv.get('rank', 0); langs_per_rank = 1
                adv_rule = next((r for r in self._advantages_list if r['id'] == 'adv_languages'), None)
                if adv_rule: langs_per_rank = adv_rule.get('languages_per_rank',1)
                languages_granted_by_adv += ranks * langs_per_rank
                if adv.get('params') and adv['params'].get('details_list'): languages_known.extend(adv['params']['details_list'])
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
        # ... (Implementation from Part 3, assumed complete and correct) ...
        abilities = char_state.get('abilities', {}); bought_defenses = char_state.get('defenses', {})
        total_defense = self.get_ability_modifier(abilities.get(base_ability_id, 0)) + bought_defenses.get(defense_id, 0)
        if defense_id == 'Toughness':
            total_defense += char_state.get('derived_defensive_roll_bonus', 0)
            for pwr in char_state.get('powers', []):
                if pwr.get('baseEffectId') == 'eff_protection': total_defense += pwr.get('rank', 0)
        return total_defense

    def validate_all(self, state: CharacterState) -> List[str]:
        # ... (Implementation from Part 3, assumed complete and correct, with placeholders for more complex validations) ...
        errors: List[str] = []; pl = state.get('powerLevel', 10)
        if state.get('spentPowerPoints', 0) > state.get('totalPowerPoints', 0): errors.append(f"PP Limit Exceeded: Spent {state['spentPowerPoints']}, Total {state['totalPowerPoints']}.")
        dodge = self.get_total_defense(state, 'Dodge', 'AGL'); parry = self.get_total_defense(state, 'Parry', 'FGT'); toughness = self.get_total_defense(state, 'Toughness', 'STA'); fortitude = self.get_total_defense(state, 'Fortitude', 'STA'); will = self.get_total_defense(state, 'Will', 'AWE')
        pl_cap_paired = pl * 2
        if (dodge + toughness) > pl_cap_paired: errors.append(f"Defense Cap: Dodge ({dodge}) + Toughness ({toughness}) = {dodge + toughness} exceeds PLx2 ({pl_cap_paired}).")
        if (parry + toughness) > pl_cap_paired: errors.append(f"Defense Cap: Parry ({parry}) + Toughness ({toughness}) = {parry + toughness} exceeds PLx2 ({pl_cap_paired}).")
        if (fortitude + will) > pl_cap_paired: errors.append(f"Defense Cap: Fortitude ({fortitude}) + Will ({will}) = {fortitude + will} exceeds PLx2 ({pl_cap_paired}).")
        skill_bonus_cap = pl + 10; skill_rank_cap = pl + 5; abilities = state.get('abilities',{})
        for skill_id, ranks_bought in state.get('skills', {}).items():
            if ranks_bought > skill_rank_cap: skill_name_disp = self.get_skill_name_by_id(skill_id, self._skills_list); errors.append(f"Skill Rank Cap: {skill_name_disp} ranks ({ranks_bought}) exceeds PL+5 ({skill_rank_cap}).")
            skill_rule = self.get_skill_rule(skill_id)
            if skill_rule:
                gov_ab_id = skill_rule.get('ability'); ab_mod = self.get_ability_modifier(abilities.get(gov_ab_id,0)); total_bonus = ab_mod + ranks_bought
                if total_bonus > skill_bonus_cap: skill_name_disp = self.get_skill_name_by_id(skill_id, self._skills_list); errors.append(f"Skill Bonus Cap: {skill_name_disp} total bonus ({total_bonus}) exceeds PL+10 ({skill_bonus_cap}).")
        for pwr in state.get('powers', []):
            if pwr.get('isAttack'):
                effect_rank = pwr.get('rank', 0); attack_bonus = self.get_attack_bonus_for_power(pwr, state)
                if pwr.get('attackType') in ['area', 'perception']:
                    if effect_rank > pl: errors.append(f"Power Attack Cap: {pwr.get('name')} (Area/Perception) Effect Rank ({effect_rank}) exceeds PL ({pl}).")
                else: 
                    if (attack_bonus + effect_rank) > pl_cap_paired: errors.append(f"Power Attack Cap: {pwr.get('name')} Attack Bonus ({attack_bonus}) + Effect Rank ({effect_rank}) = {attack_bonus + effect_rank} exceeds PLx2 ({pl_cap_paired}).")
        if len(state.get('complications', [])) < 2: errors.append("Character Minimum: At least 2 Complications are recommended.")
        if state.get('derived_spent_ep', 0) > state.get('derived_total_ep', 0): errors.append(f"EP Limit Exceeded: Spent {state['derived_spent_ep']} EP, Total {state['derived_total_ep']} EP.")
        if state.get('derived_spent_minion_pool_pp', 0) > state.get('derived_total_minion_pool_pp', 0): errors.append(f"Minion Pool Overspent: Used {state['derived_spent_minion_pool_pp']} PP, Available {state['derived_total_minion_pool_pp']} PP.")
        if state.get('derived_spent_sidekick_pool_pp', 0) > state.get('derived_total_sidekick_pool_pp', 0): errors.append(f"Sidekick Pool Overspent: Used {state['derived_spent_sidekick_pool_pp']} PP, Available {state['derived_total_sidekick_pool_pp']} PP.")
        for adv in state.get('advantages', []):
            if adv.get('id') == 'adv_defensive_roll':
                agl_rank = abilities.get('AGL',0);
                if adv.get('rank',0) > agl_rank: errors.append(f"Advantage Validation: Defensive Roll rank ({adv.get('rank',0)}) cannot exceed Agility rank ({agl_rank}).")
            if adv.get('id') == 'adv_languages':
                ranks = adv.get('rank',0); langs_per_rank = 1; adv_rule_lang = next((r for r in self._advantages_list if r['id'] == 'adv_languages'),None)
                if adv_rule_lang: langs_per_rank = adv_rule_lang.get('languages_per_rank',1)
                num_granted = ranks * langs_per_rank; num_specified = len(adv.get('params',{}).get('details_list',[])) if adv.get('params',{}).get('details_list') else 0
                if num_specified > num_granted: errors.append(f"Advantage Validation: Languages grants {num_granted}, but {num_specified} specified.")
        return errors

    # --- MAIN RECALCULATION ORCHESTRATION ---
    def recalculate(self, state: CharacterState) -> CharacterState:
        # ... (Implementation from Part 3, assumed complete and correct) ...
        # This is the main entry point that calls all other calculation, derivation, and validation steps in order.
        recalc_state = copy.deepcopy(state); recalc_state['validationErrors'] = []
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
                if any(m.get('id') == 'mod_extra_attack_action' for m in pwr_def.get('modifiersConfig', [])): is_attack_flag = True
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
            cost_details = self.calculate_individual_power_cost(pwr_def, all_powers_for_context)
            pwr_def['cost'] = cost_details['totalCost']; pwr_def['costPerRankFinal'] = cost_details['costPerRankFinal']; pwr_def['costBreakdown'] = cost_details['costBreakdown']
            if pwr_def.get('isAttack'):
                 pwr_def['resistance_dc_details'] = self.get_resistance_dc_for_power(pwr_def, recalc_state)
                 pwr_def['attack_bonus_total'] = self.get_attack_bonus_for_power(pwr_def, recalc_state) 
            pwr_def['measurement_details_display'] = self.get_power_measurement_details(pwr_def, self.rule_data)
            updated_powers_list.append(pwr_def)
        recalc_state['powers'] = updated_powers_list
        self.calculate_derived_values(recalc_state) 
        recalc_state['spentPowerPoints'] = self.calculate_all_costs(recalc_state)
        recalc_state['validationErrors'] = self.validate_all(recalc_state)
        return recalc_state

    def calculate_all_costs(self, char_state: CharacterState) -> int:
        """Calculates total spent Power Points for the entire character."""
        total_pp = 0
        total_pp += self.calculate_ability_cost(char_state.get('abilities', {}))
        total_pp += self.calculate_defense_cost(char_state.get('defenses', {}))
        total_pp += self.calculate_skill_cost(char_state.get('skills', {}))
        total_pp += self.calculate_advantage_cost(char_state.get('advantages', []))
        total_pp += self.calculate_power_cost(char_state.get('powers', [])) # This sums individual power costs
        return total_pp

