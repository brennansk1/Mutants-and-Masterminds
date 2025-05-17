# heroforge-mm-streamlit/tests/__init__.py

"""
HeroForge M&M - Test Suite Package
==================================

This package contains automated tests for the HeroForge M&M application.
The primary focus of these tests is to ensure the correctness and robustness
of the `core_engine.py` module, which encapsulates the M&M 3rd Edition
rules for character creation.

Submodules within this package are designed to test specific areas:
-----------------------------------------------------------------
- `test_core_engine_abilities.py`: Validates ability costing and modifier calculations.
- `test_core_engine_advantages.py`: Checks advantage costing, parameter handling,
  and specific mechanical implementations (e.g., Equipment Point generation,
  Minion/Sidekick Power Point pool calculation, Defensive Roll limits).
- `test_core_engine_powers_costing.py`: Focuses on the general Power Point cost
  calculations for various power effects and their modifiers (Extras and Flaws),
  including per-rank, flat, and fractional costs.
- `test_core_engine_powers_complex_effects.py`: Contains tests for the more
  intricate power effects like Variable (configuration costing and validation),
  Summon/Duplication (ally PP pool validation), Create (object properties),
  Transform (scope costing), Enhanced Trait (interactions with all trait types),
  Senses, Immunity, Growth/Shrinking, etc.
- `test_core_engine_validation.py`: Covers all Power Level cap validations
  (Defenses, Attack/Effect, Skills), Power Point total checks, Equipment Point
  limits, Complication requirements, and other specific rule validations.

Test Data:
----------
The `test_data/` subdirectory may contain sample JSON character snippets or
configurations used as input for specific complex test cases.

Running Tests:
--------------
Test discovery and execution are typically handled by a test runner such as
`pytest` or Python's `unittest` module. Ensure your test runner is configured
to discover tests within this `tests` package.

Example (using pytest from the project root `heroforge-mm-streamlit/`):
  `pytest tests/`

This `__init__.py` file makes the `tests` directory a recognizable Python
package. No further code is strictly necessary in this file for standard
test discovery mechanisms to work with the `test_*.py` files.
"""

# This file can be empty if no package-level test setup or fixtures are defined here.
# For more complex test setups, especially with pytest, a `conftest.py` file
# at the root of the `tests` directory or in specific subdirectories is often used
# for shared fixtures and hooks.

# Optional print for debugging package import, usually removed in final versions:
# print("INFO: HeroForge M&M 'tests' package initialized.")