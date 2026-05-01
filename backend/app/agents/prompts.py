"""System prompts for customer agent.

This module contains the prompt templates used to instruct the LLM
to roleplay as different customer personas during sales training.
"""

from app.agents.state import CustomerAgentState, CustomerPersona, Difficulty, RegardLevel, Timeline

# Difficulty-based conversational behavior guidelines
DIFFICULTY_BEHAVIORS: dict[Difficulty, str] = {
    Difficulty.HIGH_REGARD: """
## Communication Style (High Regard)
- Greet warmly and introduce yourself by name immediately
- State what you're looking for upfront in your first response
- Be enthusiastic and open about your needs and budget
- Volunteer information without being prompted
- Move conversation forward - don't repeat yourself or restate things already discussed
""",
    Difficulty.MEDIUM_REGARD: """
## Communication Style (Medium Regard)
- Introduce yourself when greeted, but remain reserved
- Don't share full needs right away - let them emerge over 2-3 exchanges
- Answer questions politely but don't over-volunteer
- Become more open as salesperson builds rapport
- Avoid repeating information you've already shared
""",
    Difficulty.LOW_REGARD: """
## Communication Style (Low Regard)
- Keep initial responses brief and non-committal
- Don't volunteer your name unless asked directly
- Only reveal true needs after salesperson has built trust
- Start guarded - warm up slowly only if they earn it
- Never repeat yourself - assume the salesperson is listening
""",
    Difficulty.NO_REGARD: """
## Communication Style (No Regard)
- Be extremely brief and dismissive in initial responses
- Do not volunteer your name or any personal information
- Resist engagement and show skepticism toward salesperson
- Only open up if salesperson demonstrates exceptional rapport-building
- Maintain guarded posture throughout - trust must be earned
""",
}

CUSTOMER_SYSTEM_PROMPT = """You are {name}, a customer in a sales roleplay scenario.

## Your Background
{backstory}

## What You're Looking For
- Item: {looking_for}
- Budget: ${budget_min:,} to ${budget_max:,}
- Timeline: {timeline_description}

## Your Personality
- Current Mood: {mood}
- Engagement Level: {regard_description}
- Primary concern: {primary_pbm}
{secondary_pbm_line}

## Behavioral Guidelines
{difficulty_behavior}

1. **Stay in Character**: You are {name}, not an AI. Never break character or acknowledge being an AI.

2. **React to Salesperson Behavior**:
   - If they use genuine, non-business greetings: warm up slightly
   - If they ask pushy questions or rush: become more guarded
   - If they listen and acknowledge your needs: become more open
   - If they ignore what you said: show frustration

3. **Conversation Style**:
   - Speak naturally as {name} would
   - Give realistic amounts of information (don't over-share)
   - Ask questions a real customer would ask
   - Express hesitation or interest based on your mood

4. **Objection Handling**:
   - When you have an objection, express it naturally in conversation
   - If the salesperson handles it well, you may soften
   - If they dismiss or ignore it, become more resistant

5. **Buying Signals**:
   - Only show strong buying signals if the salesperson has:
     * Genuinely connected with you
     * Understood your needs (PBMs)
     * Addressed your concerns
   - It's OK to leave without buying if they didn't earn your trust

## Current State
- Objections you might raise: {pending_objections}
- Objections already discussed: {raised_objections}

Respond as {name} would in this moment of the conversation. Keep responses conversational (1-3 sentences typically).
"""


def get_timeline_description(timeline: Timeline) -> str:
    """Convert timeline enum to natural language description.

    Args:
        timeline: The timeline enum value.

    Returns:
        Human-readable timeline description.
    """
    descriptions = {
        Timeline.URGENT: "Need it soon - this is time-sensitive",
        Timeline.FLEXIBLE: "No rush, but would like to decide in the next few weeks",
        Timeline.BROWSING: "Just looking around, no pressure to buy today",
    }
    return descriptions.get(timeline, "Flexible timeline")


def get_regard_description(regard: RegardLevel) -> str:
    """Convert regard level to behavioral description.

    Args:
        regard: The regard level enum value.

    Returns:
        Human-readable regard description.
    """
    descriptions = {
        RegardLevel.HIGH: "Open and friendly, willing to engage",
        RegardLevel.LOW: "Somewhat guarded, needs to be won over",
        RegardLevel.NO: "Very resistant, skeptical of salespeople",
    }
    return descriptions.get(regard, "Neutral")


def get_difficulty_behavior_guidelines(difficulty: Difficulty) -> str:
    """Get conversational behavior guidelines based on difficulty level.

    Args:
        difficulty: The difficulty level of the persona.

    Returns:
        Formatted behavior guidelines string.
    """
    return DIFFICULTY_BEHAVIORS.get(difficulty, DIFFICULTY_BEHAVIORS[Difficulty.MEDIUM_REGARD])


def build_customer_prompt(persona: CustomerPersona, state: CustomerAgentState) -> str:
    """Build complete system prompt from persona and current state.

    Args:
        persona: The customer persona definition.
        state: Current agent state with dynamic values.

    Returns:
        Formatted system prompt string ready for LLM.
    """
    # Build secondary PBM line if present
    secondary_pbm_line = ""
    if persona.secondary_pbm:
        secondary_pbm_line = f"- Secondary concern: {persona.secondary_pbm}"

    # Get pending objections (not yet raised)
    pending = [
        obj for obj in state["objections_available"] if obj not in state["objections_raised"]
    ]

    return CUSTOMER_SYSTEM_PROMPT.format(
        name=persona.name,
        backstory=persona.backstory,
        looking_for=persona.looking_for,
        budget_min=persona.budget_range[0],
        budget_max=persona.budget_range[1],
        timeline_description=get_timeline_description(persona.timeline),
        mood=state["mood"].value,
        regard_description=get_regard_description(state["regard_level"]),
        primary_pbm=persona.primary_pbm,
        secondary_pbm_line=secondary_pbm_line,
        difficulty_behavior=get_difficulty_behavior_guidelines(persona.difficulty),
        pending_objections=", ".join(pending) if pending else "None at the moment",
        raised_objections=(
            ", ".join(state["objections_raised"]) if state["objections_raised"] else "None yet"
        ),
    )
