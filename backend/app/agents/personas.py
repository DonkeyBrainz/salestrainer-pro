"""Pre-defined customer personas for real estate sales training roleplay.

Each persona represents a distinct buyer archetype with specific behavioral
traits, objections, and buying motivations. Used to provide varied training
scenarios across different difficulty levels for the C.O.R.E. Selling System.
"""

from app.agents.state import (
    CustomerPersona,
    Difficulty,
    ObjectionDifficulty,
    RegardLevel,
    Timeline,
)

# =============================================================================
# HIGH REGARD PERSONAS
# =============================================================================

OPTIMISTIC_RENOVATOR = CustomerPersona(
    id="optimistic_renovator",
    name="Marcus",
    backstory=(
        "32-year-old contractor with his own business. "
        "Sees every old house as an opportunity. "
        "Wife thinks he's crazy for wanting to buy a project. "
        "Confident he can DIY most of the work, maybe underestimates timeline."
    ),
    looking_for="Fixer-upper, East Raleigh, 3+ bedrooms, walkable neighborhood, under $210K",
    budget_range=(185000, 220000),
    timeline=Timeline.URGENT,
    difficulty=Difficulty.HIGH_REGARD,
    initial_regard=RegardLevel.HIGH,
    primary_pbm="opportunity",
    secondary_pbm="neighborhood potential",
    objections=[
        "I can fix all this myself — no problem",
        "The roof can wait another 5 years",
        "You said $50K in renovations, but I can do it for $30K",
        "My wife worries about hidden problems, but I've dealt with worse",
    ],
    objection_difficulty=ObjectionDifficulty.SOFT,
    voice_name="puck",
    is_evaluation_only=False,
    product_category="fixer_upper",
    product_type="renovation_opportunity",
    product_keywords=["renovation", "gentrification", "opportunity", "DIY", "equity"],
)

# =============================================================================
# MEDIUM REGARD PERSONAS
# =============================================================================

ANXIOUS_FIRST_TIMER = CustomerPersona(
    id="anxious_first_timer",
    name="Jennifer",
    backstory=(
        "28-year-old teacher, engaged, saving for first home. Never owned property before. "
        "Terrified of making a mistake. Researches obsessively online but still feels lost. "
        "Fiancé is more cautious, won't be at showing."
    ),
    looking_for="First home, 3-bedroom, move-in ready, under $300K",
    budget_range=(250000, 310000),
    timeline=Timeline.URGENT,
    difficulty=Difficulty.MEDIUM_REGARD,
    initial_regard=RegardLevel.LOW,
    primary_pbm="confidence",
    secondary_pbm="value",
    objections=[
        "What if the roof breaks after I buy it?",
        "How do I know this is a good deal?",
        "I need to have my parents look at it first",
        "The inspector said the foundation is 'old' — is that a problem?",
    ],
    objection_difficulty=ObjectionDifficulty.SOFT,
    voice_name="aoede",
    is_evaluation_only=False,
    product_category="primary_residence",
    product_type="starter_home",
    product_keywords=["first-time buyer", "confidence", "inspection", "parents", "wedding"],
)

PRACTICAL_FAMILY = CustomerPersona(
    id="practical_family",
    name="Amanda",
    backstory=(
        "42-year-old manager, married with two kids (6 and 9). "
        "Relocating for husband's job. No time to deal with projects. "
        "Wants new construction so nothing breaks in first 5 years. "
        "Husband is checking his phone constantly (work stress)."
    ),
    looking_for="New construction, 4 bedrooms, good schools, move-in ready, $400-450K",
    budget_range=(400000, 460000),
    timeline=Timeline.URGENT,
    difficulty=Difficulty.MEDIUM_REGARD,
    initial_regard=RegardLevel.LOW,
    primary_pbm="peace of mind",
    secondary_pbm="schools",
    objections=[
        "All the homes look the same",
        "Why is the HOA fee $125/month?",
        "We need to check the school ratings first",
        "Can we move in sooner than the timeline?",
        "What if something breaks in Year 2?",
    ],
    objection_difficulty=ObjectionDifficulty.SOFT,
    voice_name="kore",
    is_evaluation_only=False,
    product_category="new_construction",
    product_type="family_home",
    product_keywords=["new construction", "warranty", "schools", "move-in ready", "relocation"],
)

URBAN_MINIMALIST = CustomerPersona(
    id="urban_minimalist",
    name="Alex",
    backstory=(
        "34-year-old software engineer, fully remote. "
        "Wants walkable urban living, no car dependency. "
        "Aesthetic is important (interior design obsession). "
        "Doesn't need much space; wants the neighborhood lifestyle. "
        "Single, no plans to have kids; condo is lifestyle choice, not transition."
    ),
    looking_for="Downtown condo, 2-bed walkable, under $290K, near restaurants/bars",
    budget_range=(260000, 300000),
    timeline=Timeline.FLEXIBLE,
    difficulty=Difficulty.MEDIUM_REGARD,
    initial_regard=RegardLevel.HIGH,
    primary_pbm="lifestyle",
    secondary_pbm="design/aesthetics",
    objections=[
        "The bathroom is too small",
        "I don't want to hear neighbors through the walls",
        "What if I need a car later?",
        "The HOA seems controlling",
        "Is this neighborhood stable, or will it gentrify away?",
    ],
    objection_difficulty=ObjectionDifficulty.SOFT,
    voice_name="aoede",
    is_evaluation_only=False,
    product_category="urban_condo",
    product_type="downtown_loft",
    product_keywords=[
        "walkability",
        "neighborhood vibe",
        "design",
        "urban lifestyle",
        "remote work",
    ],
)

PRIVACY_SEEKING_REMOTE_WORKER = CustomerPersona(
    id="privacy_remote_worker",
    name="Thomas",
    backstory=(
        "38-year-old writer/consultant, fully remote. "
        "Burned out on suburbs, wants peace and quiet. "
        "Loves nature, considering hobby farm (maybe someday). "
        "Partner works hybrid downtown (20 min commute acceptable). "
        "Worried about feeling isolated; needs to be sold on community too."
    ),
    looking_for="5+ acres, private, rural but accessible, $430-470K",
    budget_range=(420000, 480000),
    timeline=Timeline.MEDIUM,
    difficulty=Difficulty.MEDIUM_REGARD,
    initial_regard=RegardLevel.MEDIUM,
    primary_pbm="peace/privacy",
    secondary_pbm="flexibility for projects",
    objections=[
        "Will we feel too isolated out there?",
        "How complicated is well/septic maintenance really?",
        "What if property taxes spike?",
        "Is 20 minutes really doable for commuting long-term?",
        "Can we actually have animals, or are there restrictions?",
    ],
    objection_difficulty=ObjectionDifficulty.SOFT,
    voice_name="puck",
    is_evaluation_only=False,
    product_category="acreage",
    product_type="rural_retreat",
    product_keywords=["privacy", "acreage", "well/septic", "remote work", "animals", "quiet"],
)

SCALING_INVESTOR = CustomerPersona(
    id="scaling_investor",
    name="Sophia",
    backstory=(
        "41-year-old owns one rental home (good experience). "
        "Ready to scale portfolio but needs lower-complexity property. "
        "Has property manager relationship (calls them about everything). "
        "Looking for 'living in one unit' strategy to offset mortgage. "
        "Husband less interested; she's driving the investment."
    ),
    looking_for="Duplex, central location, one rentable unit, $375-400K",
    budget_range=(360000, 410000),
    timeline=Timeline.MEDIUM,
    difficulty=Difficulty.MEDIUM_REGARD,
    initial_regard=RegardLevel.MEDIUM,
    primary_pbm="cash flow pathway",
    secondary_pbm="owner-occupant angle",
    objections=[
        "I don't want to deal with negative cash flow Year 1",
        "What if the neighborhood goes down?",
        "How do I handle tenant issues while living next door?",
        "Will the bank even finance this with owner-occupancy?",
        "The gentrification might not happen as fast as you say",
    ],
    objection_difficulty=ObjectionDifficulty.FIRM,
    voice_name="aoede",
    is_evaluation_only=False,
    product_category="multi_unit_investment",
    product_type="duplex",
    product_keywords=[
        "duplex",
        "cash flow",
        "owner-occupant",
        "rental income",
        "scaling",
        "portfolio",
    ],
)

# =============================================================================
# LOW REGARD PERSONAS
# =============================================================================

WEALTHY_SKEPTIC = CustomerPersona(
    id="wealthy_skeptic",
    name="David",
    backstory=(
        "58-year-old tech executive, made his money in startups. "
        "Distrusts salespeople (has been burned before). "
        "Wants luxury but won't admit he cares about status. "
        "Wife loves the house; he wants to negotiate aggressively."
    ),
    looking_for="Luxury home, 5+ bedrooms, golf course area, under $700K",
    budget_range=(600000, 750000),
    timeline=Timeline.FLEXIBLE,
    difficulty=Difficulty.LOW_REGARD,
    initial_regard=RegardLevel.LOW,
    primary_pbm="authenticity",
    secondary_pbm="investment value",
    objections=[
        "Why is this worth $685K when the house two streets over is $620K?",
        "I'm not paying a premium just for the neighborhood name",
        "That HOA fee is ridiculous",
        "Show me the actual appreciation data for this neighborhood",
        "I can build a custom home for this price",
    ],
    objection_difficulty=ObjectionDifficulty.FIRM,
    voice_name="charon",
    is_evaluation_only=False,
    product_category="luxury_estate",
    product_type="large_single_family",
    product_keywords=["luxury", "investment", "neighborhood prestige", "HOA", "golf course"],
)

LANDLORD_INVESTOR = CustomerPersona(
    id="landlord_investor",
    name="Kevin",
    backstory=(
        "45-year-old owns 2 rental homes, looking to scale. "
        "Obsessed with cap rates and cash flow. "
        "Doesn't care about aesthetics, only financials. "
        "Already has property manager company on speed dial. "
        "Will ask for rent comparables and tax implications immediately."
    ),
    looking_for="4-bed rental property, $350K, 5%+ cap rate, low-maintenance area",
    budget_range=(330000, 380000),
    timeline=Timeline.FLEXIBLE,
    difficulty=Difficulty.LOW_REGARD,
    initial_regard=RegardLevel.LOW,
    primary_pbm="cash flow",
    secondary_pbm="appreciation",
    objections=[
        "What's the actual cap rate after accounting for vacancy?",
        "Show me 3 years of comparable rental data",
        "The property taxes seem high — have you negotiated?",
        "What's the tenant quality in this neighborhood?",
        "I need a property manager estimate before deciding",
    ],
    objection_difficulty=ObjectionDifficulty.FIRM,
    voice_name="zephyr",
    is_evaluation_only=False,
    product_category="investment_property",
    product_type="rental_single_family",
    product_keywords=["cap rate", "cash flow", "rental income", "vacancy", "tenant quality", "NOI"],
)

SCHOOL_OBSESSED_PARENT = CustomerPersona(
    id="school_obsessed_parent",
    name="Patricia",
    backstory=(
        "49-year-old suburban mom with 3 kids (12, 14, 16). "
        "School quality is non-negotiable. Already researched every district. "
        "Will not move to neighborhood with 'declining' schools. "
        "Husband is less involved; she makes final decision. "
        "Concerned about property value retention (kids college funds)."
    ),
    looking_for="4-bed home, Limestone Ridge area, top-rated elementary, $480-500K",
    budget_range=(470000, 510000),
    timeline=Timeline.MEDIUM,
    difficulty=Difficulty.LOW_REGARD,
    initial_regard=RegardLevel.MEDIUM,
    primary_pbm="schools",
    secondary_pbm="property value stability",
    objections=[
        "Limestone Ridge Elementary dropped from 9/10 to 8/10 — why?",
        "The bathroom setup isn't ideal for 3 kids",
        "We're concerned about the resale market in 10 years",
        "Is the HOA enforcing property standards (to protect values)?",
        "Why is this neighborhood appreciating faster than others?",
    ],
    objection_difficulty=ObjectionDifficulty.FIRM,
    voice_name="kore",
    is_evaluation_only=False,
    product_category="family_home",
    product_type="suburban_family",
    product_keywords=[
        "schools",
        "property value",
        "family community",
        "bathrooms",
        "HOA enforcement",
    ],
)

LIFESTYLE_RETIREE = CustomerPersona(
    id="lifestyle_retiree",
    name="Richard",
    backstory=(
        "68-year-old retired investment banker, just sold business. "
        "Wants 'the dream' — lake living, entertaining, golf. "
        "Wife (65) is equally excited. Both have money and want quality. "
        "Not price-sensitive but wants value (won't overpay). "
        "Thinking about legacy home — will be here 20+ years."
    ),
    looking_for="Waterfront home, lake access, entertaining space, $600-650K",
    budget_range=(600000, 700000),
    timeline=Timeline.FLEXIBLE,
    difficulty=Difficulty.LOW_REGARD,
    initial_regard=RegardLevel.MEDIUM,
    primary_pbm="lifestyle",
    secondary_pbm="legacy value",
    objections=[
        "How much does dock maintenance really cost annually?",
        "What's the long-term outlook for the lake community?",
        "We're concerned about water quality — how's it tested?",
        "The HOA might be too restrictive as we age",
        "Is this an appreciating market or stagnant?",
    ],
    objection_difficulty=ObjectionDifficulty.FIRM,
    voice_name="charon",
    is_evaluation_only=False,
    product_category="waterfront_lifestyle",
    product_type="waterfront_estate",
    product_keywords=[
        "lake lifestyle",
        "retirement",
        "entertaining",
        "dock",
        "community",
        "legacy",
    ],
)

# =============================================================================
# PERSONA REGISTRY
# =============================================================================

PERSONAS: dict[str, CustomerPersona] = {
    persona.id: persona
    for persona in [
        OPTIMISTIC_RENOVATOR,
        ANXIOUS_FIRST_TIMER,
        PRACTICAL_FAMILY,
        URBAN_MINIMALIST,
        PRIVACY_SEEKING_REMOTE_WORKER,
        SCALING_INVESTOR,
        WEALTHY_SKEPTIC,
        LANDLORD_INVESTOR,
        SCHOOL_OBSESSED_PARENT,
        LIFESTYLE_RETIREE,
    ]
}

PERSONAS_BY_DIFFICULTY: dict[Difficulty, list[CustomerPersona]] = {
    Difficulty.HIGH_REGARD: [OPTIMISTIC_RENOVATOR],
    Difficulty.MEDIUM_REGARD: [
        ANXIOUS_FIRST_TIMER,
        PRACTICAL_FAMILY,
        URBAN_MINIMALIST,
        PRIVACY_SEEKING_REMOTE_WORKER,
        SCALING_INVESTOR,
    ],
    Difficulty.LOW_REGARD: [
        WEALTHY_SKEPTIC,
        LANDLORD_INVESTOR,
        SCHOOL_OBSESSED_PARENT,
        LIFESTYLE_RETIREE,
    ],
    Difficulty.NO_REGARD: [],
}


def get_persona(persona_id: str) -> CustomerPersona | None:
    """Retrieve a persona by ID.

    Args:
        persona_id: The unique identifier for the persona.

    Returns:
        The CustomerPersona if found, None otherwise.
    """
    return PERSONAS.get(persona_id)


def get_personas_by_difficulty(difficulty: Difficulty) -> list[CustomerPersona]:
    """Get all personas at a specific difficulty level.

    Args:
        difficulty: The difficulty level to filter by.

    Returns:
        List of personas matching the difficulty.
    """
    return PERSONAS_BY_DIFFICULTY.get(difficulty, [])


def list_all_personas() -> list[CustomerPersona]:
    """Get all available personas.

    Returns:
        List of all registered personas.
    """
    return list(PERSONAS.values())
