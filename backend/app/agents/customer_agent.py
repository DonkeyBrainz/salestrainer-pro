"""LangGraph customer agent for sales training roleplay.

This module implements a stateful customer agent using LangGraph. The agent
simulates a furniture store customer with dynamic mood, objections, and
realistic conversational behavior based on the selected persona.
"""

import random
import re
from typing import Any, Literal, cast

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.prompts import build_customer_prompt
from app.agents.state import (
    DIFFICULTY_CONFIG,
    CustomerAgentState,
    Mood,
    RegardLevel,
)
from app.config import Settings
from app.llm_providers import ChatMessage, ChatRole, GeminiProvider, LLMProvider

# Words/phrases that signal the salesperson is being disrespectful toward the
# customer. Single words are matched against the message's word set (so benign
# text like "hello" containing "hell", or "class" containing "ass", never trips
# the flag); phrases are matched as substrings.
_INSULT_WORDS: frozenset[str] = frozenset(
    {
        "stupid",
        "idiot",
        "idiotic",
        "idiots",
        "moron",
        "moronic",
        "dumb",
        "dumbass",
        "useless",
        "incompetent",
        "pathetic",
        "clueless",
        "loser",
        "jerk",
        "crap",
        "suck",
        "sucks",
        "sucked",
        "lame",
        "trash",
        "garbage",
        "asshole",
        "bitch",
        "bastard",
        "fuck",
        "fucking",
        "shit",
        "shitty",
        "bullshit",
        "wtf",
    }
)
_INSULT_PHRASES: tuple[str, ...] = (
    "shut up",
    "shut it",
    "waste of time",
    "wasting my time",
    "don't care what you think",
    "dont care what you think",
)


class CustomerAgentGraph:
    """LangGraph-based customer agent for roleplay sessions.

    The graph processes each salesperson message through a series of nodes:
    1. analyze_input - Detect salesperson techniques
    2. update_mood - Adjust customer mood/regard
    3. check_objection - Decide if objection should be raised
    4. inject_objection (conditional) - Select objection to raise
    5. generate_response - Call LLM for customer response
    """

    def __init__(self, settings: Settings, provider: LLMProvider | None = None) -> None:
        """Initialize the customer agent graph.

        Args:
            settings: Application settings with Gemini configuration.
            provider: LLM provider for response generation. Defaults to
                Gemini; the eval harness injects alternatives here.
        """
        self.settings = settings
        self.llm_provider: LLMProvider = provider or GeminiProvider(settings)
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build and compile the customer agent graph.

        Returns:
            Compiled StateGraph ready for invocation.
        """
        workflow = StateGraph(CustomerAgentState)

        # Add nodes
        workflow.add_node("analyze_input", self._analyze_input)
        workflow.add_node("update_mood", self._update_mood)
        workflow.add_node("check_objection", self._check_objection)
        workflow.add_node("inject_objection", self._inject_objection)
        workflow.add_node("generate_response", self._generate_response)

        # Add edges
        workflow.add_edge(START, "analyze_input")
        workflow.add_edge("analyze_input", "update_mood")
        workflow.add_edge("update_mood", "check_objection")

        # Conditional routing from check_objection
        workflow.add_conditional_edges(
            "check_objection",
            self._route_objection,
            {
                "inject": "inject_objection",
                "respond": "generate_response",
            },
        )

        workflow.add_edge("inject_objection", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile(checkpointer=self.checkpointer)

    # --- Node implementations ---

    def _analyze_input(self, state: CustomerAgentState) -> dict[str, Any]:
        """Analyze the salesperson's latest message for techniques used.

        Detects:
        - Non-business greetings (good ENGAGE technique)
        - Questions (discovery behavior)
        - Pushy sales language (negative)
        - Acknowledgment of customer concerns (positive)

        Args:
            state: Current agent state.

        Returns:
            Analysis results stored in _analysis key.
        """
        # Always overwrite _analysis: it is checkpointed between invocations,
        # so a stale analysis from the previous turn must never leak forward.
        messages = state["messages"]
        if not messages:
            return {"_analysis": {}}

        last_msg = messages[-1]
        if not isinstance(last_msg, HumanMessage):
            return {"_analysis": {}}

        content = last_msg.content.lower() if isinstance(last_msg.content, str) else ""
        # Whole-word set for insult matching (avoids substring false positives).
        words = set(re.findall(r"[a-z']+", content))

        # Simple keyword-based analysis
        analysis = {
            "has_greeting": any(
                g in content for g in ["hi", "hello", "how are you", "nice to", "good morning"]
            ),
            "has_question": "?" in content,
            "is_pushy": any(
                p in content for p in ["buy now", "today only", "special deal", "limited time"]
            ),
            "acknowledges_concern": any(
                a in content
                for a in ["understand", "hear you", "makes sense", "i see", "that's fair"]
            ),
            "is_disrespectful": bool(words & _INSULT_WORDS)
            or any(p in content for p in _INSULT_PHRASES),
        }

        return {"_analysis": analysis}

    def _update_mood(self, state: CustomerAgentState) -> dict[str, Any]:
        """Update customer mood and regard based on salesperson behavior.

        Args:
            state: Current agent state with _analysis from previous node.

        Returns:
            Updated mood and regard_level.
        """
        # _analysis is a runtime key added by previous node, not in TypedDict
        analysis: dict[str, bool] = cast(Any, state).get("_analysis", {})
        current_mood = state["mood"]
        current_regard = state["regard_level"]
        difficulty = state["persona"].difficulty.value

        new_mood = current_mood
        new_regard = current_regard

        positive_action = False
        negative_action = False

        # Positive behavior improves mood/regard
        if analysis.get("acknowledges_concern"):
            positive_action = True
            new_mood = self._improve_mood(current_mood, difficulty)
            new_regard = self._improve_regard(current_regard)

        if analysis.get("has_greeting") and state["turn_count"] <= 2:
            positive_action = True
            new_regard = self._improve_regard(current_regard)

        # Disrespect/insults hit hardest and override baseline warmth and any
        # concurrent positive signal: a sharp two-step mood drop plus a regard
        # hit, so even a high-regard customer visibly sours when insulted.
        if analysis.get("is_disrespectful"):
            negative_action = True
            new_mood = self._worsen_mood(self._worsen_mood(current_mood, difficulty), difficulty)
            new_regard = self._worsen_regard(current_regard)

        # Pushiness is a milder negative
        elif analysis.get("is_pushy"):
            negative_action = True
            new_mood = self._worsen_mood(current_mood, difficulty)

        # Mood decay: if no positive/negative action detected, check for decay
        if not positive_action and not negative_action:
            new_mood = self._apply_mood_decay(current_mood, difficulty)

        return {"mood": new_mood, "regard_level": new_regard}

    def _check_objection(self, state: CustomerAgentState) -> dict[str, Any]:
        """Check conditions for raising an objection.

        This node doesn't modify state - routing logic is in _route_objection.

        Args:
            state: Current agent state.

        Returns:
            Empty dict (no state changes).
        """
        return {}

    def _route_objection(self, state: CustomerAgentState) -> Literal["inject", "respond"]:
        """Determine whether to inject an objection.

        Routing rules:
        1. No objections available -> respond
        2. All objections already raised -> respond
        3. Automatic: turns 2-4 for medium/low/no regard personas -> inject
        4. Behavior-responsive: difficulty-based chance if mood is negative -> inject

        Args:
            state: Current agent state.

        Returns:
            Routing decision: "inject" or "respond".
        """
        turn = state["turn_count"]
        available = state["objections_available"]
        raised = state["objections_raised"]
        persona = state["persona"]
        difficulty = persona.difficulty.value
        config = DIFFICULTY_CONFIG[difficulty]

        # No objections available
        if not available:
            return "respond"

        # All objections already raised
        pending = [o for o in available if o not in raised]
        if not pending:
            return "respond"

        # Automatic objection timing (early in conversation for medium/low/no regard)
        if difficulty in ("medium_regard", "low_regard", "no_regard"):
            if 2 <= turn <= 4 and len(raised) == 0:
                return "inject"

        # Behavior-responsive: if mood is skeptical/frustrated, difficulty-based chance
        if state["mood"] in (Mood.SKEPTICAL, Mood.FRUSTRATED):
            inject_chance = float(config["objection_inject_chance"])
            if random.random() < inject_chance:
                return "inject"

        return "respond"

    def _inject_objection(self, state: CustomerAgentState) -> dict[str, Any]:
        """Select and inject an objection to be raised.

        Args:
            state: Current agent state.

        Returns:
            Updated objections_raised and _injected_objection.
        """
        available = state["objections_available"]
        raised = list(state["objections_raised"])
        difficulty = state["persona"].difficulty.value

        pending = [o for o in available if o not in raised]
        if not pending:
            return {}

        # Select objection based on difficulty priority
        selected = self._select_objection(pending, difficulty)

        return {
            "objections_raised": raised + [selected],
            "_injected_objection": selected,
        }

    async def _generate_response(self, state: CustomerAgentState) -> dict[str, Any]:
        """Generate customer response using LLM.

        Args:
            state: Current agent state.

        Returns:
            New message appended to messages and incremented turn_count.
        """
        # Voice mode: the live Gemini session produces the customer's reply, so the
        # graph's text response would be discarded — skip the LLM call but keep
        # turn accounting intact (runtime key, not in TypedDict).
        if cast(Any, state).get("_skip_response"):
            return {
                "turn_count": state["turn_count"] + 1,
                "_injected_objection": None,
                "_last_usage": None,
            }

        persona = state["persona"]

        # Build system prompt
        system_prompt = build_customer_prompt(persona, state)

        # Prepare messages for LLM
        llm_messages: list[ChatMessage] = [ChatMessage(ChatRole.SYSTEM, system_prompt)]

        # Add conversation history
        for msg in state["messages"]:
            role = ChatRole.USER if isinstance(msg, HumanMessage) else ChatRole.ASSISTANT
            llm_messages.append(ChatMessage(role, str(msg.content)))

        # If objection was injected, add instruction (runtime key, not in TypedDict)
        injected: str | None = cast(Any, state).get("_injected_objection")
        if injected:
            instruction = f'\n[Naturally work this concern into your response: "{injected}"]'
            llm_messages.append(ChatMessage(ChatRole.SYSTEM, instruction))

        # Generate response. model=None lets the provider resolve its own
        # default (each LLMProvider impl knows its own model setting) so this
        # path works unmodified when a non-Gemini provider is injected.
        result = await self.llm_provider.complete(
            llm_messages,
            model=None,
            temperature=self.settings.gemini_temperature,
            max_output_tokens=self.settings.gemini_max_tokens,
        )

        return {
            "messages": [AIMessage(content=result.text)],
            "turn_count": state["turn_count"] + 1,
            # Consumed: clear so it can't be re-applied on the next turn.
            "_injected_objection": None,
            "_last_usage": result.usage,
        }

    # --- Helper methods ---

    def _improve_mood(self, mood: Mood, difficulty: str) -> Mood:
        """Move mood in positive direction with difficulty-based resistance.

        Lower regard personas resist improvement probabilistically.

        Args:
            mood: Current mood.
            difficulty: Persona difficulty level (high/medium/low/no regard).

        Returns:
            Improved mood (or same if resisted or already at max).
        """
        config = DIFFICULTY_CONFIG[difficulty]
        improve_chance = float(config["mood_improve_chance"])

        # Harder personas may resist mood improvement
        if random.random() > improve_chance:
            return mood

        progression = [
            Mood.FRUSTRATED,
            Mood.SKEPTICAL,
            Mood.NEUTRAL,
            Mood.INTERESTED,
            Mood.READY_TO_BUY,
        ]
        idx = progression.index(mood)
        return progression[min(idx + 1, len(progression) - 1)]

    def _worsen_mood(self, mood: Mood, difficulty: str) -> Mood:
        """Move mood in negative direction with difficulty-based severity.

        Lower regard personas may worsen more steps at once.

        Args:
            mood: Current mood.
            difficulty: Persona difficulty level (high/medium/low/no regard).

        Returns:
            Worsened mood (or same if already at min).
        """
        config = DIFFICULTY_CONFIG[difficulty]
        worsen_steps = int(config["mood_worsen_steps"])

        progression = [
            Mood.FRUSTRATED,
            Mood.SKEPTICAL,
            Mood.NEUTRAL,
            Mood.INTERESTED,
            Mood.READY_TO_BUY,
        ]
        idx = progression.index(mood)
        new_idx = max(idx - worsen_steps, 0)
        return progression[new_idx]

    def _apply_mood_decay(self, mood: Mood, difficulty: str) -> Mood:
        """Apply mood decay when no progress is made.

        Lower regard personas become frustrated without salesperson progress.

        Args:
            mood: Current mood.
            difficulty: Persona difficulty level (high/medium/low/no regard).

        Returns:
            Decayed mood or same if decay didn't trigger.
        """
        config = DIFFICULTY_CONFIG[difficulty]
        decay_chance = float(config["mood_decay_chance"])

        # Check if decay triggers
        if random.random() >= decay_chance:
            return mood

        # Apply single-step decay
        progression = [
            Mood.FRUSTRATED,
            Mood.SKEPTICAL,
            Mood.NEUTRAL,
            Mood.INTERESTED,
            Mood.READY_TO_BUY,
        ]
        idx = progression.index(mood)
        return progression[max(idx - 1, 0)]

    def _select_objection(self, pending: list[str], difficulty: str) -> str:
        """Select which objection to inject based on difficulty.

        Hard personas select the hardest (last) objection first.
        Other personas select the first available objection.

        Args:
            pending: List of pending objections.
            difficulty: Persona difficulty level.

        Returns:
            Selected objection string.
        """
        config = DIFFICULTY_CONFIG[difficulty]
        priority = str(config["objection_priority"])

        if priority == "hardest":
            # Hard personas pick the last (hardest) objection
            return pending[-1]
        else:
            # Default: pick first objection
            return pending[0]

    def _improve_regard(self, regard: RegardLevel) -> RegardLevel:
        """Move regard in positive direction.

        Args:
            regard: Current regard level.

        Returns:
            Improved regard (or same if already at max).
        """
        progression = [RegardLevel.NO, RegardLevel.LOW, RegardLevel.MEDIUM, RegardLevel.HIGH]
        idx = progression.index(regard)
        return progression[min(idx + 1, len(progression) - 1)]

    def _worsen_regard(self, regard: RegardLevel) -> RegardLevel:
        """Move regard in negative direction.

        Args:
            regard: Current regard level.

        Returns:
            Worsened regard (or same if already at min).
        """
        progression = [RegardLevel.NO, RegardLevel.LOW, RegardLevel.MEDIUM, RegardLevel.HIGH]
        idx = progression.index(regard)
        return progression[max(idx - 1, 0)]

    # --- Public API ---

    async def invoke(
        self,
        state: CustomerAgentState,
        thread_id: str,
    ) -> CustomerAgentState:
        """Invoke the graph with current state.

        Args:
            state: Current agent state.
            thread_id: Thread ID for checkpointing (usually session_id).

        Returns:
            Updated agent state after graph execution.
        """
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.graph.ainvoke(state, config)
        return cast(CustomerAgentState, result)

    def get_state(self, thread_id: str) -> CustomerAgentState | None:
        """Retrieve saved state for a thread.

        Args:
            thread_id: Thread ID to look up.

        Returns:
            Current state or None if not found.
        """
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = self.graph.get_state(config)
        if checkpoint is None:
            return None
        return cast(CustomerAgentState, checkpoint.values)
