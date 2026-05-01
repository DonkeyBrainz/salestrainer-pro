"""C.O.R.E. Selling System content.

This module contains the complete C.O.R.E. selling methodology used for
training sales representatives. Content is structured for:
- Full-text access (system prompts, fuzzy search)
- Structured stage lookups (validation, progress tracking)

C.O.R.E. = Connect, Observe, Recommend, Execute
"""

from typing import TypedDict


class StageRequirement(TypedDict):
    """A single requirement for completing a sales stage."""

    id: str
    description: str
    techniques: list[str]


class StageContent(TypedDict):
    """Complete content for a sales stage."""

    name: str
    purpose: str
    requirements: list[StageRequirement]
    key_phrases: list[str]
    do_list: list[str]
    dont_list: list[str]


# =============================================================================
# CUSTOMER MOTIVATORS (CMs)
# =============================================================================

CUSTOMER_MOTIVATORS: dict[str, str] = {
    "convenience": "Time-saving, easy process, hassle-free experience",
    "value": "Best price, good deal, cost-effective, ROI-focused",
    "quality": "Premium materials, reliability, long-lasting, investment",
    "status": "Prestige, reputation, impressive to others, exclusivity",
    "security": "Safety, protection, guarantee, risk mitigation",
    "growth": "Improvement, advancement, competitive advantage",
    "efficiency": "Productivity, streamlined process, optimization",
    "innovation": "Latest technology, cutting-edge, modern solutions",
}

# =============================================================================
# STAGE 1: CONNECT
# =============================================================================

CONNECT_CONTENT: StageContent = {
    "name": "CONNECT",
    "purpose": (
        "Build rapport and trust through genuine conversation, establish "
        "credibility, and create a comfortable environment for open dialogue "
        "about the customer's needs."
    ),
    "requirements": [
        {
            "id": "warm_greeting",
            "description": "Start with genuine, warm conversation to build rapport",
            "techniques": [
                "Use open-ended questions about their experience",
                "Show genuine interest in their responses",
                "Find common ground through shared experiences",
                "Maintain positive, professional energy",
            ],
        },
        {
            "id": "establish_credibility",
            "description": "Build trust through expertise and professionalism",
            "techniques": [
                "Share relevant experience or credentials",
                "Demonstrate knowledge of industry/market",
                "Use customer success stories or testimonials",
                "Show understanding of their business/situation",
            ],
        },
        {
            "id": "create_comfort",
            "description": "Ensure customer feels at ease and valued",
            "techniques": [
                "Active listening with full attention",
                "Validate their concerns and experiences",
                "Use their preferred communication style",
                "Respect their time and priorities",
            ],
        },
    ],
    "key_phrases": [
        "I'd love to understand your experience so far...",
        "What brings you here today?",
        "Tell me about your current situation...",
        "I'm here to help - what would be most valuable for you?",
        "Let's make sure this is the best use of your time...",
    ],
    "do_list": [
        "Ask open-ended questions to encourage dialogue",
        "Listen actively and respond thoughtfully",
        "Share relevant credentials or experience",
        "Establish mutual respect and understanding",
        "Create a consultative atmosphere",
    ],
    "dont_list": [
        "Launch into sales pitch immediately",
        "Make assumptions about their needs",
        "Focus on yourself or your company first",
        "Rush through relationship building",
        "Use overly formal or scripted language",
    ],
}

# =============================================================================
# STAGE 2: OBSERVE
# =============================================================================

OBSERVE_CONTENT: StageContent = {
    "name": "OBSERVE",
    "purpose": (
        "Discover customer needs, challenges, and motivators through strategic "
        "questioning and active listening. Understand their current situation and desired outcomes."
    ),
    "requirements": [
        {
            "id": "needs_discovery",
            "description": "Uncover current situation and challenges",
            "techniques": [
                "What's your current situation with [relevant area]?",
                "What challenges are you facing?",
                "What's working well and what isn't?",
                "How is this impacting your business/life?",
            ],
        },
        {
            "id": "goal_identification",
            "description": "Understand desired outcomes and objectives",
            "techniques": [
                "What would success look like for you?",
                "What are your main priorities?",
                "How do you envision this working ideally?",
                "What would need to change for this to be perfect?",
            ],
        },
        {
            "id": "motivator_mapping",
            "description": "Identify underlying motivators and decision criteria",
            "techniques": [
                "What's most important to you in a solution?",
                "How do you typically evaluate options?",
                "What would make you confident in moving forward?",
                "Who else is involved in this decision?",
            ],
        },
    ],
    "key_phrases": [
        "Help me understand your current situation...",
        "What's been your experience with [relevant area]?",
        "Walk me through how this typically works for you...",
        "What would ideal look like?",
        "How are you handling this today?",
        "What's driving this need right now?",
    ],
    "do_list": [
        "Ask open-ended, consultative questions",
        "Practice active listening - let customer talk 70% of the time",
        "Take notes on key points and requirements",
        "Identify at least 2 core motivators before recommending",
        "Confirm understanding by summarizing what you heard",
    ],
    "dont_list": [
        "Interrogate with rapid-fire questions",
        "Make assumptions about their needs",
        "Jump to solutions before understanding problems",
        "Interrupt or cut off their explanations",
        "Focus only on surface-level information",
    ],
}

# =============================================================================
# STAGE 3: RECOMMEND
# =============================================================================

RECOMMEND_CONTENT: StageContent = {
    "name": "RECOMMEND",
    "purpose": (
        "Present tailored solutions that directly address discovered needs. "
        "Connect features to benefits and demonstrate clear value proposition."
    ),
    "requirements": [
        {
            "id": "solution_presentation",
            "description": "Present 2-3 tailored options with clear differentiation",
            "techniques": [
                "Start with a brief summary of their needs",
                "Present good/better/best options with distinct value props",
                "Explain why each option fits their specific situation",
                "Use visual aids, demos, or examples when possible",
            ],
        },
        {
            "id": "value_connection",
            "description": "Connect features to customer-specific benefits",
            "techniques": [
                "Use 'This means for you...' to personalize benefits",
                "Reference their stated challenges and goals",
                "Quantify impact where possible (time saved, cost reduction)",
                "Address their primary decision criteria",
            ],
        },
        {
            "id": "risk_mitigation",
            "description": "Address concerns and provide reassurance",
            "techniques": [
                "Offer guarantees, warranties, or trial periods",
                "Share relevant success stories or testimonials",
                "Explain support and implementation process",
                "Clarify terms and next steps clearly",
            ],
        },
    ],
    "key_phrases": [
        "Based on what you've shared, I recommend...",
        "Here are three options that address your needs...",
        "This solves your challenge with [specific issue]...",
        "For your situation, this means...",
        "Let me show you exactly how this works...",
        "Other clients in similar situations have found...",
    ],
    "do_list": [
        "Present 2-3 distinct options with clear differentiation",
        "Connect each feature to their specific needs",
        "Provide social proof and credibility indicators",
        "Address potential objections proactively",
        "Gauge their reaction and adjust approach accordingly",
    ],
    "dont_list": [
        "Present generic solutions without customization",
        "Focus on features without explaining benefits",
        "Overwhelm with too many options",
        "Push the most expensive option without justification",
        "Ignore their budget or timeline constraints",
    ],
}

# =============================================================================
# STAGE 4: EXECUTE
# =============================================================================

EXECUTE_CONTENT: StageContent = {
    "name": "EXECUTE",
    "purpose": (
        "Secure commitment and agreement. Handle objections, finalize terms, "
        "and establish clear next steps for implementation."
    ),
    "requirements": [
        {
            "id": "commitment_request",
            "description": "Ask for commitment using appropriate closing technique",
            "techniques": [
                "Summarize value and ask for the business",
                "Offer choice between options rather than yes/no",
                "Use urgency only when genuine (deadlines, availability)",
                "Confirm they have everything needed to decide",
            ],
        },
        {
            "id": "objection_handling",
            "description": "Address hesitations and concerns directly",
            "techniques": [
                "LISTEN: Understand the real concern behind objections",
                "CLARIFY: Ask questions to isolate specific issues",
                "RESPOND: Address concerns with relevant information",
                "CONFIRM: Ensure the concern has been resolved",
            ],
        },
        {
            "id": "finalize_agreement",
            "description": "Complete the transaction and set expectations",
            "techniques": [
                "Confirm all terms and details clearly",
                "Establish timeline and next steps",
                "Gather necessary contact information",
                "Set up follow-up schedule and accountability",
            ],
        },
    ],
    "key_phrases": [
        "Based on our discussion, would you like to move forward?",
        "What questions do you still have before deciding?",
        "Which option makes the most sense for your situation?",
        "What would need to happen for this to be a perfect fit?",
        "Let's get this started - what are the next steps?",
        "I'm confident this will solve your challenge...",
    ],
    "do_list": [
        "Ask for the commitment directly and confidently",
        "Listen carefully to any objections or concerns",
        "Address objections with specific, relevant responses",
        "Confirm all terms and next steps clearly",
        "Establish ongoing relationship and follow-up plan",
    ],
    "dont_list": [
        "Accept vague objections without understanding the real concern",
        "Pressure or push when genuine concerns exist",
        "Leave terms or next steps unclear",
        "End conversation without establishing follow-up",
        "Miss opportunities to add value or expand the relationship",
    ],
}

# =============================================================================
# STAGE REGISTRY
# =============================================================================

CORE_STAGES: dict[str, StageContent] = {
    "CONNECT": CONNECT_CONTENT,
    "OBSERVE": OBSERVE_CONTENT,
    "RECOMMEND": RECOMMEND_CONTENT,
    "EXECUTE": EXECUTE_CONTENT,
}

# =============================================================================
# FULL CONTEXT FOR SYSTEM PROMPTS
# =============================================================================

CORE_FULL_CONTEXT = """
# C.O.R.E. Selling System

## Overview
The C.O.R.E. selling system is a proven sales methodology consisting of four sequential stages:
- C - Connect with Customer
- O - Observe and Discover
- R - Recommend Solutions
- E - Execute and Close

## Core Principles
1. Sequential Stage Progression: Follow CONNECT -> OBSERVE -> RECOMMEND -> EXECUTE in order
2. Customer Motivators Drive Everything: Connect all recommendations to discovered needs
3. No Fabrication: Only use provided information and honest representations
4. Natural Conversation Over Scripts: Adapt approach to customer's communication style
5. Consultative Approach: Focus on helping customer achieve their goals

## Stage 1: CONNECT
Purpose: Build rapport and trust through genuine conversation and credibility.
Key Actions:
- Warm, professional greeting focused on their experience
- Establish credibility through expertise and understanding
- Create comfortable environment for open dialogue
- Show genuine interest in their situation
- Build foundation for consultative relationship

## Stage 2: OBSERVE
Purpose: Discover customer needs, challenges, and motivators through strategic questioning.
Key Actions:
- Ask about their current situation and challenges
- Understand their goals and desired outcomes
- Identify decision criteria and priorities
- Practice active listening - customer talks 70% of the time
- Discover underlying motivators and constraints
- Map their requirements to potential solutions

## Stage 3: RECOMMEND
Purpose: Present tailored solutions that address discovered needs.
Key Actions:
- Summarize their situation and requirements
- Present 2-3 options with clear differentiation
- Connect features to customer-specific benefits
- Use relevant success stories and social proof
- Address potential concerns proactively
- Gauge reactions and adjust approach

## Stage 4: EXECUTE
Purpose: Secure commitment and establish implementation plan.
Key Actions:
- Ask for commitment directly and confidently
- Address objections with empathy and specific responses
- Clarify terms, timeline, and next steps
- Confirm mutual understanding and expectations
- Establish ongoing relationship and follow-up schedule
- Ensure successful implementation and satisfaction

## Customer Motivators (CMs)
Common categories to identify:
- Convenience: Time-saving, hassle-free experience
- Value: Cost-effective, good ROI, competitive pricing
- Quality: Premium materials, reliability, long-lasting
- Status: Prestige, reputation, exclusivity
- Security: Safety, protection, risk mitigation
- Growth: Improvement, competitive advantage
- Efficiency: Productivity, optimization
- Innovation: Latest technology, modern solutions
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_stage_content(stage: str) -> StageContent | None:
    """Get the full content for a specific stage.

    Args:
        stage: Stage name (CONNECT, OBSERVE, RECOMMEND, EXECUTE)

    Returns:
        StageContent if found, None otherwise.
    """
    return CORE_STAGES.get(stage.upper())


def get_stage_requirements(stage: str) -> list[StageRequirement]:
    """Get the requirements for a specific stage.

    Args:
        stage: Stage name (CONNECT, OBSERVE, RECOMMEND, EXECUTE)

    Returns:
        List of requirements for the stage, empty list if not found.
    """
    content = CORE_STAGES.get(stage.upper())
    if content:
        return content["requirements"]
    return []
