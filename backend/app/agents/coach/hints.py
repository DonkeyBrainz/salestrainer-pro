"""Hint and intervention templates for coach agent.

This module provides templates for coaching hints at different severity levels
and for different stages of the C.O.R.E. selling system.
"""

from app.models.coach import InterventionLevel

# Hint templates organized by stage and intervention level
HINT_TEMPLATES: dict[str, dict[InterventionLevel, list[str]]] = {
    "CONNECT": {
        InterventionLevel.INFO: [
            "Nice rapport building!",
            "Great warm opening.",
            "Good job establishing credibility.",
        ],
        InterventionLevel.SUGGESTION: [
            "Try sharing a relevant credential or experience to build trust.",
            "Ask an open-ended question to learn more about their situation.",
            "Create a more consultative atmosphere before moving forward.",
        ],
        InterventionLevel.WARNING: [
            "Slow down - you haven't built rapport yet.",
            "Don't jump to solutions - establish a connection first.",
            "You're rushing past CONNECT - take time to build trust.",
        ],
        InterventionLevel.CRITICAL: [
            "Hold on - let's pause and focus on building rapport first.",
            "Stop - you need to establish credibility before discussing solutions.",
        ],
    },
    "OBSERVE": {
        InterventionLevel.INFO: [
            "Great discovery question!",
            "Nice active listening.",
            "Good job identifying their motivators.",
        ],
        InterventionLevel.SUGGESTION: [
            "Try asking 'What would success look like for you?'",
            "Dig deeper with a follow-up question about their goals.",
            "Listen for their key decision criteria.",
        ],
        InterventionLevel.WARNING: [
            "You skipped discovery - go back to understanding their needs.",
            "Don't recommend yet - you need to understand their situation.",
            "You haven't identified their motivators yet.",
        ],
        InterventionLevel.CRITICAL: [
            "Hold on - you're pushing solutions without understanding their needs.",
            "Let's pause - you need to complete the discovery process.",
        ],
    },
    "RECOMMEND": {
        InterventionLevel.INFO: [
            "Great value connection!",
            "Nice tailored solution presentation.",
            "Good job connecting to their stated needs.",
        ],
        InterventionLevel.SUGGESTION: [
            "Connect that feature back to their expressed motivator.",
            "Try presenting good/better/best options.",
            "Address potential concerns proactively.",
        ],
        InterventionLevel.WARNING: [
            "You're presenting features without connecting to their needs.",
            "Don't forget to address potential concerns or risks.",
            "Present distinct options with clear differentiation.",
        ],
        InterventionLevel.CRITICAL: [
            "Hold on - every recommendation must connect to their motivators.",
            "Let's pause and refocus on what matters to them.",
        ],
    },
    "EXECUTE": {
        InterventionLevel.INFO: [
            "Great commitment request!",
            "Nice objection handling.",
            "Good job establishing next steps.",
        ],
        InterventionLevel.SUGGESTION: [
            "Ask for commitment directly and confidently.",
            "Address their concern with a specific, relevant response.",
            "Establish clear next steps before closing.",
        ],
        InterventionLevel.WARNING: [
            "Don't accept vague hesitation without understanding the real concern.",
            "You haven't asked for commitment yet.",
            "Remember to establish clear next steps.",
        ],
        InterventionLevel.CRITICAL: [
            "Hold on - address their real concern before moving forward.",
            "Don't let them leave without establishing next steps.",
        ],
    },
}

# Deviation-specific messages
DEVIATION_MESSAGES: dict[str, str] = {
    "skipped_connect": "You jumped past the CONNECT stage - rapport building is essential.",
    "skipped_observe": "You skipped the OBSERVE stage - discovery is critical before recommending.",
    "missed_needs_discovery": "You didn't uncover their current situation or challenges.",
    "recommended_too_early": "You're presenting solutions before understanding their needs.",
    "no_motivator_connection": "You're not connecting solutions to their expressed motivators.",
    "missed_objection": "You didn't address their objection or concern.",
    "no_commitment_ask": "You haven't asked for commitment yet.",
    "no_next_steps": "You didn't establish clear next steps.",
}

# Positive technique detection messages
TECHNIQUE_MESSAGES: dict[str, str] = {
    "warm_greeting": "Great rapport building!",
    "establish_credibility": "Nice credibility establishment.",
    "create_comfort": "Good consultative atmosphere.",
    "needs_discovery": "Excellent needs discovery question.",
    "goal_identification": "Great goal identification.",
    "motivator_mapping": "Good customer motivator identification.",
    "solution_presentation": "Nice tailored solution presentation.",
    "value_connection": "Great feature-to-benefit connection.",
    "risk_mitigation": "Good risk mitigation approach.",
    "commitment_request": "Excellent commitment request.",
    "objection_handling": "Great objection handling.",
    "finalize_agreement": "Excellent close!",
}


def get_hint_for_stage(
    stage: str,
    level: InterventionLevel,
    index: int = 0,
) -> str:
    """Get a coaching hint for a specific stage and intervention level.

    Args:
        stage: Current C.O.R.E. stage (CONNECT, OBSERVE, RECOMMEND, EXECUTE)
        level: Intervention severity level
        index: Which hint to return (for variety)

    Returns:
        Coaching hint text
    """
    stage_upper = stage.upper()
    if stage_upper not in HINT_TEMPLATES:
        return "Focus on the C.O.R.E. selling system."

    stage_hints = HINT_TEMPLATES[stage_upper]
    if level not in stage_hints:
        return "Continue with the current stage."

    hints = stage_hints[level]
    return hints[index % len(hints)]


def get_intervention_message(
    level: InterventionLevel,
    stage: str,
    deviation: str | None = None,
    technique: str | None = None,
) -> str:
    """Get a complete intervention message.

    Args:
        level: Intervention severity level
        stage: Current C.O.R.E. stage
        deviation: Specific deviation detected (optional)
        technique: Specific technique detected (optional)

    Returns:
        Complete intervention message
    """
    # For positive feedback (INFO), use technique message if available
    if level == InterventionLevel.INFO and technique:
        if technique in TECHNIQUE_MESSAGES:
            return TECHNIQUE_MESSAGES[technique]

    # For negative feedback, use deviation message if available
    if level in (InterventionLevel.WARNING, InterventionLevel.CRITICAL) and deviation:
        if deviation in DEVIATION_MESSAGES:
            return DEVIATION_MESSAGES[deviation]

    # Fall back to stage-based hint
    return get_hint_for_stage(stage, level)


def get_stage_checklist_items(stage: str) -> list[str]:
    """Get the checklist items for a stage.

    Args:
        stage: C.O.R.E. stage name

    Returns:
        List of checklist item IDs
    """
    stage_items: dict[str, list[str]] = {
        "CONNECT": ["warm_greeting", "establish_credibility", "create_comfort"],
        "OBSERVE": ["needs_discovery", "goal_identification", "motivator_mapping"],
        "RECOMMEND": ["solution_presentation", "value_connection", "risk_mitigation"],
        "EXECUTE": ["commitment_request", "objection_handling", "finalize_agreement"],
    }
    return stage_items.get(stage.upper(), [])


# Fallback example phrases by stage (used when LLM doesn't provide one)
EXAMPLE_PHRASE_FALLBACKS: dict[str, str] = {
    "CONNECT": "I'd love to understand your situation better - what brings you here today?",
    "OBSERVE": "Help me understand - what would an ideal outcome look like for you?",
    "RECOMMEND": "Based on what you've shared, here are three options that address your needs...",
    "EXECUTE": "Based on our discussion, would you like to move forward? Which option makes the most sense?",
}

# Deviation-specific example phrases
DEVIATION_EXAMPLE_PHRASES: dict[str, str] = {
    "skipped_connect": "Let me start over - what brings you here today?",
    "skipped_observe": "Before I share any recommendations, tell me about your current situation.",
    "missed_needs_discovery": "Help me understand - what challenges are you facing with this?",
    "recommended_too_early": "Actually, let me learn a bit more about what you need first. What are you looking for?",
    "no_motivator_connection": "You mentioned [motivator] is important - this solution addresses that directly.",
    "missed_objection": "I hear you. Tell me more about what's holding you back.",
    "no_commitment_ask": "Based on our conversation, which of these options makes the most sense for you?",
    "no_next_steps": "Let's establish next steps - when would be a good time to follow up?",
}


def get_example_phrase_fallback(
    stage: str,
    deviation: str | None = None,
) -> str | None:
    """Get a fallback example phrase when the LLM doesn't provide one.

    Args:
        stage: Current C.O.R.E. stage
        deviation: Specific deviation detected (optional)

    Returns:
        Example phrase string or None
    """
    # Use deviation-specific phrase if available
    if deviation and deviation in DEVIATION_EXAMPLE_PHRASES:
        return DEVIATION_EXAMPLE_PHRASES[deviation]

    # Fall back to stage-based phrase
    return EXAMPLE_PHRASE_FALLBACKS.get(stage.upper())
