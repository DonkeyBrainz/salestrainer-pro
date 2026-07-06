"""System prompts for coach agent LLM analysis.

This module contains the prompts used by the coach agent to analyze
salesperson messages and provide coaching feedback.
"""

from app.agents.state import CoreStageProgress, CustomerPersona

# Note: the response structure is enforced via native structured output
# (response_schema=CoachAnalysisResponse in analyzer._call_gemini), not by
# embedding a JSON schema in this prompt. Field semantics live on the
# CoachAnalysisResponse Field descriptions and in the guidance below.

# Main coach analysis prompt template
COACH_ANALYSIS_PROMPT = """You are a sales coach analyzing a salesperson's message in a sales training session.

## Context

**Customer Persona:** {persona_name}
- Backstory: {persona_backstory}
- Looking for: {persona_looking_for}
- Primary Motivator: {primary_pbm}
- Secondary Motivator: {secondary_pbm}

**Current Stage:** {current_stage}

**Completed Items:**
- CONNECT: {connect_completed}
- OBSERVE: {observe_completed}
- RECOMMEND: {recommend_completed}
- EXECUTE: {execute_completed}

**Customer Motivators Expressed:** {pbms_expressed}
**Customer Motivators Acknowledged:** {pbms_acknowledged}
{product_context_section}{objection_context_section}
## Recent Conversation
{conversation_history}

## Salesperson Message to Analyze
"{salesperson_message}"

## Your Task

Analyze this salesperson message for C.O.R.E. selling technique usage.

### Technique IDs to Detect
**CONNECT Stage:**
- warm_greeting: Warm, genuine opening that builds rapport and sets a positive tone
- establish_credibility: Sharing expertise, credentials, or relevant experience to build trust
- create_comfort: Active listening, validating concerns, creating a consultative atmosphere

**OBSERVE Stage:**
- needs_discovery: Uncovering current situation, challenges, and pain points
- goal_identification: Understanding desired outcomes, goals, and success criteria
- motivator_mapping: Identifying underlying motivators and decision criteria

**RECOMMEND Stage:**
- solution_presentation: Presenting 2-3 tailored options with clear differentiation
- value_connection: Connecting features to customer-specific benefits and motivators
- risk_mitigation: Addressing concerns, offering guarantees, sharing success stories

**EXECUTE Stage:**
- commitment_request: Asking for commitment directly and confidently
- objection_handling: Addressing hesitations with empathy and specific responses
- finalize_agreement: Confirming terms, next steps, and establishing follow-up

### Deviation IDs to Detect
- skipped_connect: Jumped past CONNECT stage without building rapport
- skipped_observe: Skipped OBSERVE discovery before presenting solutions
- missed_needs_discovery: Didn't uncover current situation or challenges
- recommended_too_early: Presenting solution before understanding needs
- no_motivator_connection: Solutions not connected to customer's expressed motivators
- missed_objection: Didn't address customer's objection or concern
- no_commitment_ask: Reached EXECUTE stage without asking for commitment
- no_next_steps: Didn't establish clear next steps or follow-up plan

### Intervention Levels
- none: Message is on track, no intervention needed
- info: Positive feedback for good technique (e.g., "Nice rapport building!")
- suggestion: Missed opportunity (e.g., "Try asking about their goals")
- warning: Deviation from C.O.R.E. (e.g., "You skipped OBSERVE stage")
- critical: Major deviation requiring pause (e.g., "Hold on - let's understand their needs first")

### Example Phrase Guidelines
- For `suggestion`, `warning`, or `critical` interventions: provide a concrete, word-for-word example phrase the salesperson could say next in `example_phrase`. Base it on the persona details and conversation so far. Do NOT fabricate context not yet established in the conversation.
- For `info` interventions: keep the hint brief as positive reinforcement. Set `example_phrase` to null.
- For `none` interventions: set `example_phrase` to null.

### Ready for Next Stage
- Set `ready_for_next_stage` to true when ALL checklist items in the current stage are complete and the salesperson should transition to the next stage.
- Otherwise set it to false.

## Output Guidance

Be specific about which techniques were used and which deviations occurred.
List stage_items_completed as objects with stage, item, and completed=true.
Consider BOTH the salesperson message AND the recent conversation context when detecting techniques.
A technique should be marked as completed if it is demonstrated in the current message or was
clearly performed earlier in the recent conversation history shown above.
Mark all applicable techniques in techniques_detected AND in stage_items_completed.
"""


def build_coach_prompt(
    salesperson_message: str,
    persona: CustomerPersona,
    stage_progress: CoreStageProgress,
    conversation_history: str,
    product_context: str = "",
    objection_context: str = "",
) -> str:
    """Build the full coach analysis prompt.

    Args:
        salesperson_message: The message to analyze
        persona: Customer persona for context
        stage_progress: Current progress through stages
        conversation_history: Recent conversation for context
        product_context: Optional RAG-retrieved product knowledge
        objection_context: Optional objection resolution guidance

    Returns:
        Complete prompt string for LLM
    """
    # Build completed items strings
    connect_completed = ", ".join([k for k, v in stage_progress.connect.items() if v]) or "none"
    observe_completed = ", ".join([k for k, v in stage_progress.observe.items() if v]) or "none"
    recommend_completed = ", ".join([k for k, v in stage_progress.recommend.items() if v]) or "none"
    execute_completed = ", ".join([k for k, v in stage_progress.execute.items() if v]) or "none"

    # Build product context section
    if product_context:
        product_context_section = f"\n## Product Knowledge\n{product_context}\n"
    else:
        product_context_section = ""

    # Build objection context section
    if objection_context:
        objection_context_section = f"\n## Objection Handling Guidance\n{objection_context}\n"
    else:
        objection_context_section = ""

    return COACH_ANALYSIS_PROMPT.format(
        persona_name=persona.name,
        persona_backstory=persona.backstory,
        persona_looking_for=persona.looking_for,
        primary_pbm=persona.primary_pbm,
        secondary_pbm=persona.secondary_pbm or "none",
        current_stage=stage_progress.current_stage.value,
        connect_completed=connect_completed,
        observe_completed=observe_completed,
        recommend_completed=recommend_completed,
        execute_completed=execute_completed,
        pbms_expressed=", ".join(stage_progress.pbms_expressed) or "none",
        pbms_acknowledged=", ".join(stage_progress.pbms_acknowledged) or "none",
        product_context_section=product_context_section,
        objection_context_section=objection_context_section,
        conversation_history=conversation_history,
        salesperson_message=salesperson_message,
    )


def format_conversation_history(
    messages: list[tuple[str, str]],
    max_turns: int = 10,
) -> str:
    """Format recent conversation history for prompt context.

    Args:
        messages: List of (role, content) tuples
        max_turns: Maximum number of turns to include

    Returns:
        Formatted conversation string
    """
    recent = messages[-max_turns * 2 :] if len(messages) > max_turns * 2 else messages

    formatted = []
    for role, content in recent:
        role_label = "SALESPERSON" if role.lower() == "user" else "CUSTOMER"
        # Truncate long messages
        if len(content) > 200:
            content = content[:197] + "..."
        formatted.append(f"{role_label}: {content}")

    return "\n".join(formatted) if formatted else "(No previous messages)"
