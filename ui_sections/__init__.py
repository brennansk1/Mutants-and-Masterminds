# heroforge-mm-streamlit/ui_sections/__init__.py

"""
HeroForge M&M - UI Sections Package
===================================

This package contains modules that define UI rendering functions for different
parts of the Streamlit application. Organizing UI components into these
submodules helps to keep the main `app.py` file cleaner, more modular, and
easier to manage, especially given the complexity and number of features
in this character creator.

Modules within this package:
----------------------------
- `wizard_steps.py`:
    Contains functions responsible for rendering each distinct step of the
    Character Creation Wizard. This includes UI elements for basic character
    information, archetype selection, guided ability allocation, defense and
    skill suggestions, simplified power selection, and the final review and
    complication step. Each function aims to be beginner-friendly with ample
    help text.

- `advanced_mode_ui.py`:
    Houses functions for rendering the main sections of the Advanced Mode
    character creator. This includes detailed views and input forms for:
    Abilities, Defenses, Skills, Advantages (with full parameterization),
    Equipment (including EP tracking), Headquarters construction, Vehicle
    construction, Companions (Allies - Minions, Sidekicks, Summons, Duplicates
    with structured stat blocks), Complications, the Measurements Table reference,
    and the in-app Character Sheet View.

- `power_builder_ui.py`:
    Dedicated to the most complex UI component: the Power Builder.
    This module will contain functions to render the detailed form for adding and
    editing powers, including selection of any base Power Effect, rank,
    configuration of all Power Modifiers (Extras and Flaws) with their specific
    parameters (ranks, user input, selections), setup for Power Arrays (Static
    and Dynamic), and specialized UI sections for complex effects like Senses,
    Immunity, Variable (with its configuration "mini-builder"), Create, Healing,
    Nullify, Weaken, Teleport, Growth/Shrinking, etc.

How to Use from app.py:
-----------------------
Modules and functions from this package should be imported specifically in `app.py`
where needed. For example:

```python
# In app.py
# from ui_sections.wizard_steps import render_wizard_step1_basics, render_wizard_step2_archetype
# from ui_sections.advanced_mode_ui import render_abilities_section, render_advantages_section
# from ui_sections.power_builder_ui import render_power_builder_form
"""