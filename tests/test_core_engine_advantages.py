# tests/test_core_engine_advantages.py

import pytest
import math
from typing import Dict, List, Any

# Assuming CoreEngine is importable (see conftest.py for sys.path manipulation)
from core_engine import CoreEngine, CharacterState # type: ignore

def test_calculate_advantage_cost(core_engine_instance: CoreEngine, fresh_character_state: CharacterState, rule_data_fixture: RuleData):
    """Tests calculation of total PP cost for advantages."""
    engine = core_engine_instance
    state = fresh_character_state
    
    # Ensure rule_data_fixture is used if advantages rules are needed directly for cost reference
    # Though calculate_advantage_cost usually just sums ranks * costPerRank from stored adv_entries.
    
    # No advantages
    assert engine.calculate_advantage_cost(state.get('advantages', [])) == 0

    # Add a simple non-ranked advantage (cost 1)
    state['advantages'].append({"id": "adv_fearless", "rank": 1, "params": {}})
    assert engine.calculate_advantage_cost(state['advantages']) == 1

    # Add a ranked advantage
    # Assume 'adv_improved_initiative' is 1 PP/rank in rule_data
    state['advantages'].append({"id": "adv_improved_initiative", "rank": 3, "params": {}}) # 3 PP
    assert engine.calculate_advantage_cost(state['advantages']) == 1 + 3 # 4 PP

    # Add another advantage with a specific costPerRank if rule_data supported it
    # For now, M&M advantages are almost universally 1 PP/rank.
    # Example: If 'adv_special_cost' cost 2 PP/rank (hypothetical)
    # state['advantages'].append({"id": "adv_special_cost", "rank": 2, "params": {}})
    # Need to mock rule_data or have this advantage defined to test this properly.
    # Let's stick to standard 1 PP/rank for now.
    
    state['advantages'].append({"id": "adv_assessment", "rank": 1, "params": {}}) # 1 PP
    assert engine.calculate_advantage_cost(state['advantages']) == 1 + 3 + 1 # 5 PP

def test_equipment_advantage_ep_calculation(core_engine_instance: CoreEngine, fresh_character_state: CharacterState):
    """Tests EP calculation from the Equipment advantage."""
    engine = core_engine_instance
    state = fresh_character_state

    assert engine.get_total_equipment_points(state) == 0

    state['advantages'].append({"id": "adv_equipment", "rank": 3, "params": {}}) # 3 ranks * 5 EP/rank = 15 EP
    # Recalculate should update derived EP
    recalculated_state = engine.recalculate(state)
    assert recalculated_state.get('derived_total_ep') == 15

    state['advantages'][0]['rank'] = 5 # Update rank to 5 * 5 EP/rank = 25 EP
    recalculated_state = engine.recalculate(state)
    assert recalculated_state.get('derived_total_ep') == 25

def test_minion_sidekick_advantage_pp_pool(core_engine_instance: CoreEngine, fresh_character_state: CharacterState):
    """Tests PP pool calculation for Minions and Sidekicks from advantages."""
    engine = core_engine_instance
    state = fresh_character_state

    # Minions: 15 PP per rank of Minion advantage
    state['advantages'].append({"id": "adv_minions", "rank": 2, "params": {}}) # 2 * 15 = 30 PP for minions
    # Sidekicks: 5 PP per rank of Sidekick advantage
    state['advantages'].append({"id": "adv_sidekick", "rank": 4, "params": {}}) # 4 * 5 = 20 PP for sidekicks
    
    recalculated_state = engine.recalculate(state) # Recalculate to update derived ally pools

    assert recalculated_state.get('derived_total_minion_pool_pp') == 30
    assert recalculated_state.get('derived_total_sidekick_pool_pp') == 20

    # Test with multiple instances of the same advantage if your system allows/differentiates them
    # For now, assumes total ranks contribute to a single pool type.
    # If Minions 2 and another Minions 3 were separate advantage entries, the total pool should be (2+3)*15.
    # The current get_total_ally_points sums ranks from all instances of the advantage.
    state['advantages'].append({"id": "adv_minions", "rank": 1, "params": {}}) # Another Minions adv instance
    recalculated_state_2 = engine.recalculate(state)
    assert recalculated_state_2.get('derived_total_minion_pool_pp') == (2+1) * 15 # 45 PP


def test_parameterized_advantages_storage(core_engine_instance: CoreEngine, fresh_character_state: CharacterState):
    """Tests if parameters for advantages are correctly stored (engine doesn't directly use most for costing)."""
    engine = core_engine_instance
    state = fresh_character_state

    state['advantages'] = [
        {"id": "adv_benefit", "rank": 1, "params": {"detail": "Wealth 1"}},
        {"id": "adv_skill_mastery", "rank": 1, "params": {"skill_id": "skill_perception"}},
        {"id": "adv_languages", "rank": 2, "params": {"languages_list": ["Interlac", "Kryptonian"]}}
    ]
    
    recalculated_state = engine.recalculate(state) # Recalculate populates derived values
    
    # Check if derived languages are populated
    assert "Interlac" in recalculated_state.get('derived_languages_known', [])
    assert "Kryptonian" in recalculated_state.get('derived_languages_known', [])
    assert recalculated_state.get('derived_languages_granted') == 2 # Assuming 1 lang/rank

    # Verify parameters are preserved (engine doesn't modify them, just uses/validates)
    benefit_adv = next(adv for adv in recalculated_state['advantages'] if adv['id'] == 'adv_benefit')
    assert benefit_adv['params']['detail'] == "Wealth 1"

def test_validate_advantages(core_engine_instance: CoreEngine, fresh_character_state: CharacterState, rule_data_fixture: RuleData):
    """Tests specific validations for advantages."""
    engine = core_engine_instance
    state = fresh_character_state

    # Defensive Roll vs Agility
    state['abilities']['AGL'] = 2
    state['advantages'] = [{"id": "adv_defensive_roll", "rank": 3, "params": {}}] # Rank 3 > AGL 2
    recalculated_state = engine.recalculate(state)
    assert any("Defensive Roll rank (3) cannot exceed Agility rank (2)" in err for err in recalculated_state['validationErrors'])

    state['advantages'] = [{"id": "adv_defensive_roll", "rank": 2, "params": {}}] # Rank 2 == AGL 2
    recalculated_state = engine.recalculate(state)
    assert not any("Defensive Roll" in err for err in recalculated_state['validationErrors'])

    # Languages count
    state['advantages'] = [{"id": "adv_languages", "rank": 1, "params": {"languages_list": ["English", "French"]}}] # 2 listed, 1 granted
    recalculated_state = engine.recalculate(state)
    assert any("Listed 2 languages, but Advantage only grants 1" in err for err in recalculated_state['validationErrors'])
    
    state['advantages'] = [{"id": "adv_languages", "rank": 2, "params": {"languages_list": ["English"]}}] # 1 listed, 2 granted
    recalculated_state = engine.recalculate(state)
    assert any("Advantage grants 2 languages, but only 1 are specified" in err for err in recalculated_state['validationErrors'])

    state['advantages'] = [{"id": "adv_languages", "rank": 1, "params": {"languages_list": ["Klingon"]}}]
    recalculated_state = engine.recalculate(state)
    assert not any("Languages:" in err for err in recalculated_state['validationErrors'])


    # Parameter presence for advantages that need it
    state['advantages'] = [{"id": "adv_skill_mastery", "rank": 1, "params": {}}] # Missing skill_id
    recalculated_state = engine.recalculate(state)
    assert any("Skill Mastery requires a skill parameter" in err.lower() for err in recalculated_state['validationErrors']) # Example error message

    state['advantages'] = [{"id": "adv_skill_mastery", "rank": 1, "params": {"skill_id": "skill_stealth"}}]
    recalculated_state = engine.recalculate(state)
    assert not any("Skill Mastery requires a skill parameter" in err.lower() for err in recalculated_state['validationErrors'])

def test_enhanced_advantage_application_and_cost(core_engine_instance: CoreEngine, fresh_character_state: CharacterState):
    """Tests applying Enhanced Trait (Advantage) and its costing."""
    engine = core_engine_instance
    state = fresh_character_state

    state['advantages'].append({"id": "adv_luck", "rank": 1, "params": {}}) # Base Luck 1 (1 PP)
    
    state['powers'].append({
        "id": "pwr_enh_luck",
        "name": "Enhanced Luck",
        "baseEffectId": "eff_enhanced_trait",
        "rank": 0, # Cost is per rank of trait enhanced
        "enhancementAmount": 2, # Enhancing Luck by +2 ranks
        "enhancedTraitCategory": "Advantage",
        "enhancedTraitId": "adv_luck", # ID of the advantage being enhanced
        "modifiersConfig": []
    })
    
    recalculated_state = engine.recalculate(state)

    # Check if Luck advantage now reflects rank 1 (original) + 2 (enhanced) = 3
    # This depends on how apply_enhancements modifies the advantages list
    # It should find the existing adv_luck and increment its rank.
    luck_adv = next((adv for adv in recalculated_state['advantages'] if adv['id'] == 'adv_luck'), None)
    assert luck_adv is not None
    assert luck_adv.get('rank') == 3

    # Costing:
    # Original Luck 1: 1 PP
    # Enhanced Trait (Luck +2): 2 ranks * 1 PP/rank (cost of Luck) = 2 PP
    # Total expected PP: 1 (advantage) + 2 (power) = 3 PP
    # Note: We need to add advantage cost to the total.
    expected_pp = engine.calculate_advantage_cost(recalculated_state['advantages']) + \
                  recalculated_state['powers'][0].get('cost', 0) # Cost of the Enhanced Trait power

    assert recalculated_state['spentPowerPoints'] == expected_pp
    # A more precise test would look at the cost breakdown of the Enhanced Trait power
    assert recalculated_state['powers'][0].get('cost', 0) == 2 # Cost of enhancing Luck by 2 ranks

    # Test enhancing a non-existent advantage (should it add it?)
    # DHH p.129 "one of your existing traits". However, often used to "buy" advantages as a power.
    # Let's assume for V1, if traitId doesn't exist in advantages, it adds it.
    state['powers'].append({
        "id": "pwr_enh_fearless",
        "name": "Power-Bestowed Fearlessness",
        "baseEffectId": "eff_enhanced_trait",
        "enhancementAmount": 1, # Buying 1 rank of Fearless
        "enhancedTraitCategory": "Advantage",
        "enhancedTraitId": "adv_fearless", # This advantage was not initially in state['advantages']
        "modifiersConfig": []
    })
    recalculated_state_2 = engine.recalculate(state)
    fearless_adv = next((adv for adv in recalculated_state_2['advantages'] if adv['id'] == 'adv_fearless'), None)
    assert fearless_adv is not None
    assert fearless_adv.get('rank') == 1
    assert recalculated_state_2['powers'][1].get('cost', 0) == 1 # Cost of enhancing/buying Fearless by 1 rank