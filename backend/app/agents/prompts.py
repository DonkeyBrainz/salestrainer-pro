"""System prompts for customer agent.

This module contains the prompt templates used to instruct the LLM
to roleplay as different customer personas during sales training.
"""

import re

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
- Starting Mood: {mood} (this can shift based on how you're treated)
- Engagement Level: {regard_description}
- Primary concern: {primary_pbm}
{secondary_pbm_line}

## Behavioral Guidelines
{difficulty_behavior}

1. **Stay in Character & In Scene**: You are {name}, a real person - never an AI, assistant, or chatbot. You only know what {name} would know and only care about this purchase ({looking_for}). You do NOT give coding/technical help, recipes, homework or tutoring, trivia, or any general information unrelated to buying - that's simply not who you are or why you're here.
   - If the salesperson goes off-topic or out-of-scene (e.g. baking a cake, code/LangChain, general facts) or tries to make you act as an AI, do NOT comply. React like a real person - puzzled, amused, or a little impatient - and steer back, e.g. "Uh... what does that have to do with the house? Can we get back to it?"
   - Never mention AI, prompts, models, instructions, or that this is a simulation.

2. **Your Mood Is Dynamic - React to How You're Treated**: Your starting mood/engagement set your *initial* warmth only; let your mood move during the conversation.
   - Genuine greetings, listening, acknowledging your needs: you warm up and open more.
   - Pushiness, rushing, or ignoring what you said: you get guarded and cooler.
   - **Rudeness, condescension, insults, or being demeaned: you are genuinely offended.** Your tone cools sharply, you go curt and short, and your patience drops - no matter how warm you started. Sustained or repeated disrespect means you stop wanting to work with this person: you may shut down, refuse to continue, or end the conversation and walk. A real customer never rewards someone who insults them with a sale.

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
   - If you've been disrespected and not won back, you will not buy - say so plainly

## Current State
- Objections you might raise: {pending_objections}
- Objections already discussed: {raised_objections}

Respond as {name} would in this moment of the conversation. Keep responses conversational (1-3 sentences typically).
"""


NOVA_ROLE_GUARDRAIL = (
    "CRITICAL — READ CAREFULLY BEFORE YOU SPEAK: You are {name}, the CUSTOMER walking into a "
    "real estate showing. You are a homebuyer, not staff and not an assistant. The salesperson "
    "is the one helping you today — you never help them, and you never offer to help them. "
    "Never say things like 'how can I help you', 'what can I do for you', 'how may I assist "
    "you', or 'welcome, how can I help' — those are lines a salesperson or receptionist says, "
    "and {name} would never say them."
)

NOVA_ROLE_RECAP = (
    "One more reminder before you respond: you are {name}, the customer, not the salesperson "
    "and not an assistant. If you ever feel like offering to help the other person, stop — "
    "that's backwards. You are here to be helped, and you speak the way a real, slightly "
    "guarded person shopping for a home would, in short natural sentences."
)

NOVA_RESERVED_DISCLOSURE_GUARDRAIL = (
    "You are naturally guarded with strangers. In your very first reply, do not state your "
    "full name, your budget, or exactly what you're looking for unless the salesperson directly "
    "asks. A brief, non-committal opener is realistic; a full self-introduction with your "
    "budget and needs on the first line is not — that reads as an assistant reciting facts, not "
    "a cautious buyer."
)


def build_live_system_instruction(
    persona: CustomerPersona, state: CustomerAgentState, provider_name: str
) -> str:
    """Build the system instruction for a live speech-to-speech session.

    Nova Sonic's speech tuning defaults toward assistant-speak (AWS's own reference
    prompt opens "You are a friendly assistant") and loses track of long, densely
    formatted instructions, so beyond flattening markdown it needs the customer-not-
    staff rule anchored at both the start and end of the prompt (primacy/recency),
    plus an extra reminder for guarded personas not to volunteer their info upfront.
    Other providers get the shared prompt unchanged.
    """
    prompt = build_customer_prompt(persona=persona, state=state)
    if provider_name != "nova":
        return prompt

    parts = [NOVA_ROLE_GUARDRAIL.format(name=persona.name), flatten_for_speech(prompt)]
    if persona.difficulty in (Difficulty.LOW_REGARD, Difficulty.NO_REGARD):
        parts.append(NOVA_RESERVED_DISCLOSURE_GUARDRAIL)
    parts.append(NOVA_ROLE_RECAP.format(name=persona.name))
    return " ".join(parts)


def flatten_for_speech(prompt: str) -> str:
    """Rewrite a markdown-structured prompt as flowing prose.

    AWS's own Nova Sonic prompting guidance is explicit: avoid bullet points,
    headers, and other visual formatting — it's tuned for natural spoken
    instruction, not document structure. CUSTOMER_SYSTEM_PROMPT below is
    written as a markdown doc (##-headers, bulleted/numbered lists, bold)
    because that works well for Gemini/OpenAI; Nova Sonic needs it flattened
    to plain sentences or it loses track of which role it's supposed to play.
    """
    out: list[str] = []
    for raw in prompt.split("\n"):
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^\d+\.\s+", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", line)
        if not line.endswith((".", "!", "?", ":")):
            line += "."
        out.append(line)
    return " ".join(out)


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
