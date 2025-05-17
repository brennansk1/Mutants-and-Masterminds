# core_engine.py for HeroForge M&M (Streamlit Edition)
# Version: V1.0 "All Features" Conceptual Full Build

import json
import math
import os
import copy # For deep copying complex states
import uuid # For generating unique IDs if needed internally
from typing import Dict, List, Any, Optional, Tuple, Union

# --- Type Hint for Character State ---
CharacterState = Dict[str, Any]
RuleData = Dict[str, Any]
PowerDefinition = Dict[str, Any] # For individual powers
AllyDefinition = Dict[str, Any] # For minions, sidekicks, summons, duplicates
VariableConfigTrait = Dict[str, Any] # For traits within a Variable Power config

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
        print("CoreEngine initialized successfully with rule data.")

    def _load_all_rule_data(self, directory_path: str) -> Optional[RuleData]:
        """Loads all JSON rule files from the specified directory."""
        loaded_data: RuleData = {}
        expected_files = [
            "abilities.json", "advantages_v1.json", "archetypes.json",
            "equipment_items.json", "hq_features.json", "measurements_table.json",
            "power_effects.json", "power_immunities_config.json",
            "power_modifiers.json", "power_senses_config.json", "skills.json",
            "vehicle_features.json", "vehicle_size_stats.json"
        ]
        try:
            print(f"Attempting to load rules from: {os.path.abspath(directory_path)}")
            if not os.path.isdir(directory_path):
                print(f"Error: Rule directory not found at '{os.path.abspath(directory_path)}'")
                return None

            for filename in expected_files:
                filepath = os.path.join(directory_path, filename)
                if not os.path.exists(filepath):
                    print(f"Warning: Expected rule file not found: {filepath}")
                    # Depending on how critical, could return None or allow partial load
                    # For "all features", all are pretty critical.
                    return None # Strict: all files must exist
                
                rule_name = filename[:-5]  # Remove '.json'
                with open(filepath, 'r', encoding='utf-8') as f:
                    # TODO: Potentially apply any known M&M 3e errata programmatically here after loading
                    loaded_data[rule_name] = json.load(f)
                    print(f"Successfully loaded: {filename}")
            
            if len(loaded_data) < len(expected_files):
                print("Error: Not all expected rule files were loaded successfully.")
                return None
            return loaded_data

        except Exception as e:
            print(f"Critical error loading rule data: {e}")
            return None

    def get_default_character_state(self, pl: int = 10) -> CharacterState:
        """Creates a default, empty character state dictionary."""
        base_abilities = {info['id']: 0 for info in self.rule_data.get('abilities', {}).get('list', [])}
        skill_rules = self.rule_data.get('skills', {}).get('list', [])
        default_skills = {skill_info['id']: 0 for skill_info in skill_rules}

        return {
            "saveFileVersion": "1.0_all_features",
            "name": "New Hero",
            "playerName": "",
            "powerLevel": pl,
            "totalPowerPoints": pl * 15,
            "spentPowerPoints": 0,
            "concept": "",
            "description": "",
            "identity": "", # Public, Secret
            "gender": "", "age": "", "height": "", "weight": "", "eyes": "", "hair": "",
            "groupAffiliation": "", "baseOfOperationsName": "",

            "abilities": copy.deepcopy(base_abilities),
            # Store 'base_ranks' separately if Enhanced Trait is to be non-destructive on this dict
            # For now, 'abilities' stores the *current effective rank* including enhancements
            "defenses": {"Dodge": 0, "Parry": 0, "Toughness": 0, "Fortitude": 0, "Will": 0}, # Bought ranks
            "skills": copy.deepcopy(default_skills), # Ranks bought
            "advantages": [],  # List of {'id': adv_id, 'rank': X, 'params': {'key': 'value'}}
            "powers": [],      # List of PowerDefinition objects
            "equipment": [],   # List of {'id': item_id, 'name': str, 'custom_ep_cost': X (optional)}
            "headquarters": [],# List of HQ definitions
            "vehicles": [],    # List of Vehicle definitions
            "allies": [],      # List of Minion/Sidekick/Summon/Duplicate stat blocks
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

    # --- HELPER FUNCTIONS ---
    def get_ability_modifier(self, ability_rank: Optional[Union[int, float]]) -> int:
        return int(ability_rank) if ability_rank is not None else 0

    def get_trait_cost_per_rank(self, trait_category: str, trait_id: Optional[str] = None, 
                                character_powers_context: Optional[List[PowerDefinition]] = None) -> float:
        """Gets base cost per rank for various traits. Returns float for precision with skills."""
        if trait_category == "Ability": return 2.0
        if trait_category == "Defense": return 1.0
        if trait_category == "Skill": return 0.5
        if trait_category == "Advantage":
            if trait_id:
                adv_rule = next((adv for adv in self.rule_data.get('advantages_v1', []) if adv['id'] == trait_id), None)
                return float(adv_rule.get('costPerRank', 1.0)) if adv_rule else 1.0
            return 1.0
        if trait_category == "PowerRank" and trait_id and character_powers_context:
            target_power = next((pwr for pwr in character_powers_context if pwr.get('id') == trait_id), None)
            if target_power:
                cpr_final = target_power.get('costPerRankFinal', 1.0) # Should be calculated for target power
                if isinstance(cpr_final, (int, float)): return float(cpr_final)
                if isinstance(cpr_final, str) and "1 per " in cpr_final:
                    try: return 1.0 / int(cpr_final.split("1 per ")[1])
                    except ValueError: return 1.0 # Fallback
                return 1.0 # Fallback
            return 1.0
        return 1.0 # Default

    def get_measurement_by_rank(self, rank: int, measurement_type: str) -> str:
        """Looks up a measurement value for a given rank."""
        if 'measurements_table' not in self.rule_data: return f"Rank {rank} (Table N/A)"
        
        # Exact match or closest lower for simplicity (as implemented before)
        # A more robust version would interpolate or handle ranges better.
        exact_match = next((entry for entry in self.rule_data['measurements_table'] if entry.get('rank') == rank), None)
        if exact_match:
            return exact_match.get(measurement_type, f"Rank {rank} (Type N/A)")
        
        # Find closest lower if no exact match and rank is positive
        if rank > 0:
            closest_lower = None
            for entry in self.rule_data['measurements_table']:
                entry_rank = entry.get('rank')
                if isinstance(entry_rank, int) and entry_rank < rank:
                    if closest_lower is None or entry_rank > closest_lower.get('rank', -float('inf')):
                        closest_lower = entry
            if closest_lower:
                return f"Approx. {closest_lower.get(measurement_type, '')} (for Rank {closest_lower.get('rank')})"
        
        return f"Rank {rank} (Value N/A)" # Fallback for ranks not directly in table

    # --- COST CALCULATION FUNCTIONS ---
    def calculate_ability_cost(self, abilities_state: Dict[str, int]) -> int:
        cost = 0
        cost_factor = self.rule_data.get('abilities', {}).get('costFactor', 2)
        for rank in abilities_state.values():
            cost += rank * cost_factor
        return cost

    def calculate_defense_cost(self, bought_defenses_state: Dict[str, int]) -> int:
        return sum(bought_defenses_state.values()) # 1 PP per bought rank

    def calculate_skill_cost(self, bought_skills_state: Dict[str, int]) -> int:
        total_ranks = sum(bought_skills_state.values())
        return math.ceil(total_ranks * 0.5) # 1 PP per 2 ranks

    def calculate_advantage_cost(self, advantages_state: List[Dict[str, Any]]) -> int:
        cost = 0
        for adv_entry in advantages_state:
            adv_rule = next((r for r in self.rule_data.get('advantages_v1', []) if r['id'] == adv_entry.get('id')), None)
            cost_per_rank = adv_rule.get('costPerRank', 1) if adv_rule else 1
            cost += adv_entry.get('rank', 1) * cost_per_rank
        return cost

    def calculate_individual_power_cost(self, power_definition: PowerDefinition, all_character_powers_context: List[PowerDefinition]) -> Dict[str, Any]:
        """
        Calculates the cost of a single power based on its definition, including all modifiers.
        This is the most complex costing function.
        """
        # Initialize results structure
        results = {
            'totalCost': 0, 
            'costPerRankFinal': 0.0, # Store as float internally
            'costBreakdown': {'base':0.0, 'extras_cpr':0.0, 'flaws_cpr':0.0, 'flat_total':0.0, 'senses': 0.0, 'immunities':0.0, 'variable_base':0.0, 'ally_base':0.0, 'enhancement_base':0.0},
            'final_duration': "", 'final_range': "", 'final_action':"" # For display
        }

        base_effect_id = power_definition.get('baseEffectId')
        power_rank = int(power_definition.get('rank', 1)) # Ensure integer for rank math
        modifiers_config = power_definition.get('modifiersConfig', []) # [{'id': mod_id, 'rank': X, 'userInput': Y}]
        
        base_effect_rule = next((e for e in self.rule_data.get('power_effects', []) if e['id'] == base_effect_id), None)
        if not base_effect_rule:
            print(f"Warning: Base effect rule not found for ID: {base_effect_id}")
            return results # Return empty costs

        # Store default action, range, duration
        results['final_action'] = base_effect_rule.get('defaultAction', 'Standard')
        results['final_range'] = base_effect_rule.get('defaultRange', 'Personal')
        results['final_duration'] = base_effect_rule.get('defaultDuration', 'Instant')

        # --- Special Handling for Unique Costing Effects ---
        if base_effect_rule.get('isSenseContainer'):
            sense_total_cost = 0.0
            for sense_id in power_definition.get('sensesConfig', []):
                sense_rule = next((s for s in self.rule_data.get('power_senses_config', []) if s['id'] == sense_id), None)
                if sense_rule: sense_total_cost += float(sense_rule.get('cost', 0.0))
            results['costBreakdown']['senses'] = sense_total_cost
            # Modifiers on Senses package are usually flat
            current_flat_cost = 0.0
            for mod_conf in modifiers_config:
                mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf['id']), None)
                if mod_rule and mod_rule.get('costType') == 'flat': current_flat_cost += float(mod_rule.get('flatCostChange',0.0))
                elif mod_rule and mod_rule.get('costType') == 'flatPerRankOfModifier': current_flat_cost += float(mod_rule.get('flatCost',0.0)) * mod_conf.get('rank',1)
            results['costBreakdown']['flat_total'] = current_flat_cost
            results['totalCost'] = math.ceil(sense_total_cost + current_flat_cost)
            results['costPerRankFinal'] = "N/A (Senses)"
            return results

        if base_effect_rule.get('isImmunityContainer'):
            immunity_total_cost = 0.0
            for immunity_id in power_definition.get('immunityConfig', []):
                immunity_rule = next((i for i in self.rule_data.get('power_immunities_config', []) if i['id'] == immunity_id), None)
                if immunity_rule: immunity_total_cost += float(immunity_rule.get('cost', 0.0))
            results['costBreakdown']['immunities'] = immunity_total_cost
            # Modifiers on Immunity (e.g. Affects Others, Sustained)
            # Sustained is +0. Affects Others is +1/rank for the *Immunity Ranks defined by fixed cost*.
            # This is tricky. DHH p.113: "Affects Others +1 cost per rank" - implies for Immunity, it's +1 per *point of base Immunity cost*.
            # For V1.x perfection, this needs clarification. Assume +1/rank of *power rank* for now if power rank has meaning for Immunity package.
            # Or more likely, flat cost for these. Let's treat modifiers on Immunity package as flat for now.
            current_flat_cost_imm = 0.0
            for mod_conf in modifiers_config:
                mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf['id']), None)
                if mod_rule and mod_rule.get('costType') == 'flat': current_flat_cost_imm += float(mod_rule.get('flatCostChange',0.0))
                elif mod_rule and mod_rule.get('costType') == 'flatPerRankOfModifier': current_flat_cost_imm += float(mod_rule.get('flatCost',0.0)) * mod_conf.get('rank',1)
            results['costBreakdown']['flat_total'] = current_flat_cost_imm
            results['totalCost'] = math.ceil(immunity_total_cost + current_flat_cost_imm)
            results['costPerRankFinal'] = "Fixed (Immunity)"
            return results
            
        if base_effect_rule.get('isVariableContainer'): # Variable Power itself
            base_cpr = float(base_effect_rule.get('costPerRank', 7.0))
            effective_cpr = base_cpr
            flat_total = 0.0
            extras_cpr_val = 0.0
            flaws_cpr_val = 0.0
            for mod_conf in modifiers_config: # Modifiers on Variable power (e.g., Action, Slow)
                mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf['id']), None)
                if not mod_rule: continue
                if mod_rule.get('costType') == 'perRank':
                    change = float(mod_rule.get('costChangePerRank', 0.0))
                    effective_cpr += change
                    if change > 0: extras_cpr_val += change
                    else: flaws_cpr_val += change
                elif mod_rule.get('costType') == 'flat': flat_total += float(mod_rule.get('flatCostChange', 0.0))
                elif mod_rule.get('costType') == 'flatPerRankOfModifier': flat_total += float(mod_rule.get('flatCost', 0.0)) * mod_conf.get('rank', 1)
            
            results['costBreakdown']['base'] = base_cpr * power_rank
            results['costBreakdown']['extras_cpr'] = extras_cpr_val * power_rank
            results['costBreakdown']['flaws_cpr'] = flaws_cpr_val * power_rank # flaws_cpr_val is negative
            results['costBreakdown']['flat_total'] = flat_total
            results['costPerRankFinal'] = effective_cpr
            results['totalCost'] = math.ceil((effective_cpr * power_rank) + flat_total)
            if results['totalCost'] < 1 and power_rank > 0: results['totalCost'] = 1
            return results

        if base_effect_rule.get('id') == 'eff_insubstantial': # Ranks 1-4 have fixed total costs
            fixed_insub_costs = {1: 5, 2: 10, 3: 15, 4: 20}
            if power_rank in fixed_insub_costs:
                base_total_cost = float(fixed_insub_costs[power_rank])
                # Modifiers apply to this base total cost.
                # This means "per rank" modifiers for Insubstantial are complex.
                # DHH p.154: "Extras are +1 cost per rank, Flaws are -1 cost per rank." This usually means effect's ranks.
                # So, if Insub 4 (20 PP) has Continuous (+1/r), it becomes 20 + (1*4) = 24 PP.
                cpr_mod_adjustment = 0.0
                flat_mod_adjustment = 0.0
                for mod_conf in modifiers_config:
                    mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf['id']), None)
                    if not mod_rule: continue
                    if mod_rule.get('costType') == 'perRank': cpr_mod_adjustment += float(mod_rule.get('costChangePerRank',0.0))
                    elif mod_rule.get('costType') == 'flat': flat_mod_adjustment += float(mod_rule.get('flatCostChange',0.0))
                    elif mod_rule.get('costType') == 'flatPerRankOfModifier': flat_mod_adjustment += float(mod_rule.get('flatCost',0.0)) * mod_conf.get('rank',1)
                
                results['totalCost'] = math.ceil(base_total_cost + (cpr_mod_adjustment * power_rank) + flat_mod_adjustment)
                results['costPerRankFinal'] = f"Fixed Total (Rank {power_rank})"
                results['costBreakdown']['base'] = base_total_cost
                results['costBreakdown']['extras_cpr'] = (cpr_mod_adjustment if cpr_mod_adjustment > 0 else 0) * power_rank
                results['costBreakdown']['flaws_cpr'] = (cpr_mod_adjustment if cpr_mod_adjustment < 0 else 0) * power_rank
                results['costBreakdown']['flat_total'] = flat_mod_adjustment
                if results['totalCost'] < 1 and power_rank > 0: results['totalCost'] = 1
                return results

        if base_effect_rule.get('isEnhancementEffect'):
            # ... (Enhanced Trait costing from previous, ensure it uses floats and final ceil) ...
            # Cost depends on the trait being enhanced.
            enh_cat = power_definition.get('enhancedTraitCategory')
            enh_id = power_definition.get('enhancedTraitId')
            enh_amt = power_definition.get('enhancementAmount', power_rank) # Use power_rank if specific amount not given
            
            cost_of_base_trait_per_rank = self.get_trait_cost_per_rank(enh_cat, enh_id, all_character_powers_context)
            effective_cpr = cost_of_base_trait_per_rank
            flat_total = 0.0
            extras_cpr_val = 0.0
            flaws_cpr_val = 0.0

            for mod_conf in modifiers_config: # Modifiers on Enhanced Trait itself
                mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf['id']), None)
                if not mod_rule: continue
                if mod_rule.get('costType') == 'perRank':
                    change = float(mod_rule.get('costChangePerRank',0.0))
                    effective_cpr += change
                    if change > 0: extras_cpr_val += change
                    else: flaws_cpr_val += change
                elif mod_rule.get('costType') == 'flat': flat_total += float(mod_rule.get('flatCostChange',0.0))
                elif mod_rule.get('costType') == 'flatPerRankOfModifier': flat_total += float(mod_rule.get('flatCost',0.0)) * mod_conf.get('rank',1)

            unrounded_total = (effective_cpr * enh_amt) + flat_total
            if enh_cat == "Skill": # Skills are 0.5 per rank, so total is ceil'd
                results['totalCost'] = math.ceil(unrounded_total)
            else:
                results['totalCost'] = math.ceil(unrounded_total) # Most traits result in whole points from enh.

            results['costPerRankFinal'] = effective_cpr # This is cost per rank of *enhanced trait*
            results['costBreakdown']['enhancement_base'] = cost_of_base_trait_per_rank * enh_amt
            results['costBreakdown']['extras_cpr'] = extras_cpr_val * enh_amt
            results['costBreakdown']['flaws_cpr'] = flaws_cpr_val * enh_amt
            results['costBreakdown']['flat_total'] = flat_total
            if results['totalCost'] < 1 and enh_amt > 0: results['totalCost'] = 1
            return results


        # --- Standard Ranked Power Costing (if not handled above) ---
        if power_rank <= 0: return results

        current_cpr_val = float(base_effect_rule.get('costPerRank', 1.0))
        initial_base_ranked_cost = current_cpr_val * power_rank
        results['costBreakdown']['base'] = initial_base_ranked_cost
        
        cpr_extras_total_change = 0.0
        cpr_flaws_total_change = 0.0
        flat_total_val = 0.0

        for mod_conf in modifiers_config:
            mod_id = mod_conf.get('id')
            mod_rank_for_flat_cost = mod_conf.get('rank', 1)
            mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_id), None)
            if not mod_rule: continue
            if mod_id == 'mod_linked': continue # Linked is 0 cost for modifier itself

            cost_type = mod_rule.get('costType', 'perRank')
            if cost_type == 'perRank':
                change = float(mod_rule.get('costChangePerRank', 0.0))
                current_cpr_val += change
                if change > 0: cpr_extras_total_change += change
                else: cpr_flaws_total_change += change # change is negative
            elif cost_type == 'flat':
                flat_total_val += float(mod_rule.get('flatCostChange', 0.0))
            elif cost_type == 'flatPerRankOfModifier':
                flat_total_val += float(mod_rule.get('flatCost', 0.0)) * mod_rank_for_flat_cost
        
        results['costBreakdown']['extras_cpr'] = cpr_extras_total_change * power_rank
        results['costBreakdown']['flaws_cpr'] = cpr_flaws_total_change * power_rank
        results['costBreakdown']['flat_total'] = flat_total_val
        
        # Fractional Cost Logic for the per-rank portion
        if current_cpr_val < 1.0:
            ranks_per_pp = 1
            if current_cpr_val == 0.0: ranks_per_pp = 2
            elif current_cpr_val < 0.0: ranks_per_pp = int(1.0 - current_cpr_val + 1.0)
            elif current_cpr_val > 0.0: # e.g. 0.5
                 try: ranks_per_pp = round(1.0 / current_cpr_val)
                 except ZeroDivisionError: ranks_per_pp = float('inf') # effectively free per rank if cpr is 0, but min cost of 1pp overall
            if ranks_per_pp <= 0: ranks_per_pp = float('inf') # Avoid division by zero or negative ranks

            if ranks_per_pp == float('inf'): # Effectively free per rank, but flat costs still apply
                cost_for_ranked_part = 0.0
                results['costPerRankFinal'] = "Effectively 0/rank (before flat costs)" if power_rank > 0 else 0.0
            else:
                cost_for_ranked_part = math.ceil(float(power_rank) / ranks_per_pp)
                results['costPerRankFinal'] = f"1 per {ranks_per_pp}" if ranks_per_pp > 1 else "1"
        else:
            cost_for_ranked_part = current_cpr_val * power_rank
            results['costPerRankFinal'] = current_cpr_val
        
        final_total_unrounded = cost_for_ranked_part + flat_total_val
        results['totalCost'] = math.ceil(final_total_unrounded)
        
        if results['totalCost'] < 1 and power_rank > 0: results['totalCost'] = 1
        
        # Derive final duration, range, action based on modifiers
        # This is complex and needs careful iteration through modifiers that affect these.
        # Placeholder:
        # results['final_duration'] = derive_final_duration(base_effect_rule.get('defaultDuration'), modifiers_config, self.rule_data)
        # results['final_range'] = derive_final_range(base_effect_rule.get('defaultRange'), modifiers_config, self.rule_data)
        # results['final_action'] = derive_final_action(base_effect_rule.get('defaultAction'), modifiers_config, self.rule_data)

        return results


    def calculate_power_cost(self, powers_state: List[PowerDefinition]) -> int: # Total PP for all powers
        """Calculates total PP cost for all powers, considering arrays fully."""
        total_pp_for_all_powers = 0
        
        # Create a map of powers by ID for easier lookup, with calculated individual costs
        # Cost on power_def should be updated by recalculate before this is called.
        powers_with_costs: Dict[str, PowerDefinition] = {p['id']: p for p in powers_state}

        # Identify arrays
        arrays: Dict[str, List[PowerDefinition]] = {} # array_id: [list of power_defs in array]
        processed_power_ids_in_arrays = set()

        for pwr_def in powers_state:
            array_id = pwr_def.get('arrayId')
            if array_id:
                if array_id not in arrays: arrays[array_id] = []
                arrays[array_id].append(pwr_def)
        
        # Calculate cost for each array
        for array_id, powers_in_array in arrays.items():
            if not powers_in_array: continue

            base_power_for_array = next((p for p in powers_in_array if p.get('isArrayBase')), None)
            
            if not base_power_for_array: # Heuristic: find most expensive non-AE if no explicit base
                potential_bases = [p for p in powers_in_array if not p.get('isAlternateEffectOf')]
                if not potential_bases: # All seem to be AEs without a clear base in this array group
                    print(f"Warning: Array '{array_id}' has no clear base power. Costing AEs individually (likely incorrect).")
                    for p_ae in powers_in_array: 
                        total_pp_for_all_powers += p_ae.get('cost',0) # Use its pre-calculated standalone cost
                        processed_power_ids_in_arrays.add(p_ae['id'])
                    continue
                base_power_for_array = max(potential_bases, key=lambda p: p.get('cost',0))
            
            array_cost = base_power_for_array.get('cost', 0) # Cost of the base power itself
            processed_power_ids_in_arrays.add(base_power_for_array['id'])

            is_dynamic_array = any(mod.get('id') == 'mod_dynamic_array' for mod in base_power_for_array.get('modifiersConfig', []))
            # The 'mod_dynamic_array' itself should have costed +1 flat point to the base_power_for_array's cost already.

            for p_ae in powers_in_array:
                if p_ae.get('isAlternateEffectOf') == base_power_for_array['id']:
                    if p_ae['id'] in processed_power_ids_in_arrays : continue # Already counted if somehow it was also the base

                    # Validate AE cost: cost of AE config <= cost of base_power_for_array config
                    if p_ae.get('cost',0) > base_power_for_array.get('cost',0):
                        # This should be a validation error caught elsewhere or flagged.
                        # For costing, we still add its AE cost.
                        print(f"Warning: AE '{p_ae.get('name')}' cost ({p_ae.get('cost',0)}) > base power cost ({base_power_for_array.get('cost',0)}) in array '{array_id}'.")

                    array_cost += 2 if is_dynamic_array else 1 # DAEs cost 2, Static AEs cost 1
                    processed_power_ids_in_arrays.add(p_ae['id'])
            
            total_pp_for_all_powers += array_cost

        # Add costs of standalone powers (not part of any processed array)
        for pwr_def in powers_state:
            if pwr_def['id'] not in processed_power_ids_in_arrays:
                total_pp_for_all_powers += pwr_def.get('cost', 0) # Uses pre-calculated cost
                
        return total_pp_for_all_powers

    # ... (calculate_all_costs sums all categories including the refined calculate_power_cost) ...
    # ... (Headquarters and Vehicle costing functions calculate_hq_cost, calculate_vehicle_cost) ...
    # ... (get_total_equipment_points, get_spent_equipment_points as before, ensuring they sum gear + HQs + Vehicles) ...

    # --- `recalculate` function's order of operations is paramount ---
    def recalculate(self, state: CharacterState) -> CharacterState:
        print("Recalculating full character state...")
        recalc_state = copy.deepcopy(state) # Work on a copy

        # 1. Apply all global trait enhancements from Powers (Enhanced Trait)
        # This modifies abilities, skills, defenses, advantage ranks, or even other power ranks *before* their costs are finalized or PL limits checked.
        recalc_state = self.apply_enhancements(recalc_state) # This function needs to be very robust

        # 2. For EACH power definition in recalc_state['powers']:
        updated_powers_list = []
        all_powers_context_for_enh_trait = recalc_state.get('powers', []) # For Enhanced Power Rank context

        for pwr_def_orig in recalc_state.get('powers', []):
            pwr_def = copy.deepcopy(pwr_def_orig) # Process a copy of each power definition

            # a. Derive fundamental properties based on base effect and ALL modifiers
            #    (isAttack, attackType, final_duration, final_range, resistance, etc.)
            #    This is a complex step that requires iterating modifiers.
            base_effect_rule = next((e for e in self.rule_data.get('power_effects', []) if e['id'] == pwr_def.get('baseEffectId')), None)
            if base_effect_rule:
                pwr_def['final_duration'] = self._derive_final_duration(base_effect_rule.get('defaultDuration'), pwr_def.get('modifiersConfig', []))
                pwr_def['final_range'] = self._derive_final_range(base_effect_rule.get('defaultRange'), pwr_def.get('modifiersConfig', []), pwr_def.get('rank',0), base_effect_rule)
                pwr_def['final_action'] = self._derive_final_action(base_effect_rule.get('defaultAction'), pwr_def.get('modifiersConfig', []))
                
                # Derive isAttack and attackType (critical for combat validation)
                # This needs to be robust based on effect type and modifiers like Ranged, Area, Perception, Attack extra
                is_attack_flag = base_effect_rule.get('type', '').lower() == 'attack'
                # If Attack extra is present, it makes a non-Attack effect into an Attack
                if any(m.get('id') == 'mod_attack_extra' for m in pwr_def.get('modifiersConfig', [])): # 'mod_attack_extra' is an example ID
                    is_attack_flag = True
                pwr_def['isAttack'] = is_attack_flag
                
                if is_attack_flag:
                    current_range = pwr_def['final_range'] # Use the derived final range
                    if 'perception' in current_range.lower(): pwr_def['attackType'] = 'perception'
                    elif 'area' in current_range.lower() or any(m.get('id','').startswith('mod_area_') for m in pwr_def.get('modifiersConfig',[])): pwr_def['attackType'] = 'area'
                    elif 'ranged' in current_range.lower(): pwr_def['attackType'] = 'ranged'
                    else: pwr_def['attackType'] = 'close'
                else:
                    pwr_def['attackType'] = 'none'

            # b. If Variable, calculate its variablePointPool
            if pwr_def.get('baseEffectId') == 'eff_variable':
                pwr_def['variablePointPool'] = pwr_def.get('rank', 0) * 5

            # c. If Summon/Duplication, calculate its allotted_pp_for_creation
            if base_effect_rule and base_effect_rule.get('isAllyEffect'):
                pwr_def['allotted_pp_for_creation'] = pwr_def.get('rank', 0) * base_effect_rule.get('grantsAllyPointsFactor', 15)

            # d. Calculate its own final PP cost and store details
            cost_details = self.calculate_individual_power_cost(pwr_def, all_powers_context_for_enh_trait)
            pwr_def['cost'] = cost_details['totalCost']
            pwr_def['costPerRankFinal'] = cost_details['costPerRankFinal']
            pwr_def['costBreakdown'] = cost_details['costBreakdown']
            
            # e. If an attack, get its resistance_dc_details
            if pwr_def.get('isAttack'):
                 pwr_def['resistance_dc_details'] = self.get_resistance_dc_for_power(pwr_def, recalc_state) # Pass full recalc_state for context
            
            # f. Calculate and store its measurement_details_display
            pwr_def['measurement_details_display'] = self.get_power_measurement_details(pwr_def)
            
            updated_powers_list.append(pwr_def)
        recalc_state['powers'] = updated_powers_list

        # 3. Calculate other derived character values (initiative, EP, ally pools from advantages, etc.)
        self.calculate_derived_values(recalc_state) # This updates fields like derived_initiative, derived_total_ep etc.

        # 4. Calculate total spent Character Power Points (uses the now final costs on each power object)
        recalc_state['spentPowerPoints'] = self.calculate_all_costs(recalc_state)
        
        # 5. Perform ALL validations
        recalc_state['validationErrors'] = self.validate_all(recalc_state)
        
        print(f"Recalculation cycle complete. Final PP: {recalc_state['spentPowerPoints']}. Errors: {len(recalc_state['validationErrors'])}")
        return recalc_state

    # --- Helper methods for deriving final range, duration, action (NEW & COMPLEX) ---
    def _derive_final_duration(self, base_duration: str, modifiers_config: List[Dict]) -> str:
        # DHH p.139 (Increased Duration), p.146 (Decreased Duration)
        # Progression: Instant -> Concentration -> Sustained -> Continuous -> Permanent
        # This needs careful logic to track current duration state as modifiers are applied.
        # Modifiers like 'mod_duration_continuous' should have 'appliesToDuration': ['Sustained']
        # and 'changesDurationTo': 'Continuous'.
        current_duration = base_duration
        # Sort modifiers if order matters (unlikely for duration, but possible for others)
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf.get('id')), None)
            if mod_rule and mod_rule.get('appliesToDuration') and current_duration in mod_rule.get('appliesToDuration'):
                current_duration = mod_rule.get('changesDurationTo', current_duration)
            elif mod_rule and mod_rule.get('id') == 'mod_permanent_duration_extra': # Example for a direct Permanent extra if defined
                current_duration = "Permanent"
        return current_duration

    def _derive_final_range(self, base_range: str, modifiers_config: List[Dict], power_rank: int, base_effect_rule: Dict) -> str:
        # DHH p.155 (Increased Range), p.150 (Reduced Range / Diminished Range)
        # Progression: Personal -> Touch (Close) -> Ranged -> Perception
        # This also needs careful state tracking.
        current_range = base_range
        # Modifiers like 'mod_increased_range_ranged' (makes Close to Ranged)
        # Modifiers like 'mod_perception_range' (makes Ranged to Perception)
        # These would have fields like 'changesRangeTo': 'Ranged'
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf.get('id')), None)
            if mod_rule and mod_rule.get('modifiesProperty') == 'range':
                current_range = mod_rule.get('newValue', current_range) # e.g. "Ranged", "Perception"
        
        # If final range is "Ranged" or "Perception" (rank-based distance), add measurement
        if current_range.lower() == "ranged":
            # Standard Ranged: Short (Rank*25), Med (Rank*50), Long (Rank*100 feet)
            # This isn't a single measurement, but implies these bands.
            # For display, usually just "Ranged" is fine, or we can show max range.
            max_range_val = self.get_measurement_by_rank(power_rank + 6, 'distance') # Rank*100 ft is roughly Distance Rank + 6
            return f"Ranged (up to {max_range_val})"
        if current_range.lower() == "perception":
            # Perception range effects are often Perception (Sense Type) like Visual, Auditory
            perception_type_mod = next((mc for mc in modifiers_config if mc.get('id') == 'mod_area_perception'), None) # Example ID
            if perception_type_mod and perception_type_mod.get('userInput'):
                return f"Perception ({perception_type_mod['userInput']})"
            return "Perception"
            
        return current_range.capitalize()


    def _derive_final_action(self, base_action: str, modifiers_config: List[Dict]) -> str:
        # DHH p.147 (Action Modifier Extra/Flaw)
        # Progression: Full -> Standard -> Move -> Free -> Reaction
        current_action = base_action
        # Modifiers like 'mod_action_free', 'mod_reaction_std'
        # These would have 'changesActionTo': 'Free'
        for mod_conf in modifiers_config:
            mod_rule = next((m for m in self.rule_data.get('power_modifiers', []) if m['id'] == mod_conf.get('id')), None)
            if mod_rule and mod_rule.get('changesActionTo'):
                current_action = mod_rule.get('changesActionTo') # Assumes only one action mod or last one wins
        return current_action.capitalize()
        
    # Ensure HQs/Vehicles use detailed costing based on their DHH feature costs
    def calculate_hq_cost(self, hq_definition: Dict[str, Any]) -> int:
        # ... (Full implementation from previous response using DHH p.178 for size/toughness
        #      and summing EP costs for all features listed in hq_definition['features']
        #      based on rules in `rules/hq_features.json`) ...
        cost = 0
        size_id = hq_definition.get('size_id', 'hq_size_medium')
        size_rule = next((f for f in self.rule_data.get('hq_features',[]) if f['id'] == size_id), None)
        if size_rule: cost += size_rule.get('ep_cost',0)
        
        bought_toughness = hq_definition.get('bought_toughness_ranks',0)
        cost += bought_toughness # 1 EP per +1 Toughness

        for feat_entry in hq_definition.get('features',[]):
            feat_rule = next((f for f in self.rule_data.get('hq_features',[]) if f['id'] == feat_entry['id']), None)
            if feat_rule:
                if feat_rule.get('ranked'): cost += feat_rule.get('ep_cost_per_rank',1) * feat_entry.get('rank',1)
                else: cost += feat_rule.get('ep_cost',1)
        return cost

    def calculate_vehicle_cost(self, vehicle_definition: Dict[str, Any]) -> int:
        # ... (Full implementation from previous response using DHH p.182 for base stats/cost
        #      from Vehicle Size Rank, then summing EP costs for all features from
        #      `rules/vehicle_features.json`) ...
        cost = 0
        size_rank_val = vehicle_definition.get('size_rank', 0)
        size_stats_rule = next((s for s in self.rule_data.get('vehicle_size_stats',[]) if s.get('size_rank') == size_rank_val), None)
        if size_stats_rule:
            cost += size_stats_rule.get('base_ep_cost',0)
            # Store derived base stats on vehicle_definition if not already there
            vehicle_definition['derived_str'] = size_stats_rule.get('str',0)
            vehicle_definition['derived_spd'] = size_stats_rule.get('spd',0)
            vehicle_definition['derived_def'] = size_stats_rule.get('def',0)
            vehicle_definition['derived_tou'] = size_stats_rule.get('tou',0)

        for feat_entry in vehicle_definition.get('features',[]):
            feat_rule = next((f for f in self.rule_data.get('vehicle_features',[]) if f['id'] == feat_entry['id']), None)
            if feat_rule:
                if feat_rule.get('ranked'): cost += feat_rule.get('ep_cost_per_rank',1) * feat_entry.get('rank',1)
                else: cost += feat_rule.get('ep_cost',1)
        return cost