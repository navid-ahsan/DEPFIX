"""
Agent 1: Intent Analyzer
Parses user input to understand intent and extract tech stack hints
"""

import re
from typing import Set, Optional
from .base import BaseAgent, AgentContext, AgentContract, RetryPolicy, FallbackPolicy
import logging

logger = logging.getLogger(__name__)


class IntentAnalyzerAgent(BaseAgent):
    """
    Analyzes user query to:
    1. Classify intent (guidance vs. automatic fix)
    2. Extract tech stack hints (libraries mentioned)
    3. Categorize problem type
    """

    # Common library patterns
    LIBRARY_PATTERNS = {
        r'\btorch\b': 'torch',
        r'\btensorflow\b|\btf\b': 'tensorflow',
        r'\btransformers\b': 'transformers',
        r'\bnumpy\b': 'numpy',
        r'\bpandas\b': 'pandas',
        r'\bscikit-learn\b|\bsklearn\b': 'scikit-learn',
        r'\bflask\b': 'flask',
        r'\bfastapi\b': 'fastapi',
        r'\bdjango\b': 'django',
        r'\bmonai\b': 'monai',
        r'\bflower\b': 'flower',
        r'\bpytest\b': 'pytest',
        r'\brequests\b': 'requests',
        r'\bscipy\b': 'scipy',
    }

    ERROR_KEYWORDS = [
        'error', 'bug', 'exception', 'fail', 'crash', 'traceback',
        'issue', 'problem', 'doesn\'t work', 'not working', 'broken'
    ]

    def __init__(self):
        super().__init__(
            name="IntentAnalyzer",
            description="Analyzes user input intent and extracts tech stack hints",
            contract=AgentContract(
                input_schema={"user_intent": "str"},
                output_schema={
                    "metadata.intent_type": "str",
                    "metadata.problem_type": "str",
                    "detected_tech_stack": "dict[str, str]",
                },
                required_inputs=["user_intent"],
                success_criteria="Intent classified and metadata fields populated",
                retry_policy=RetryPolicy(max_attempts=1, backoff_ms=0),
                fallback_policy=FallbackPolicy(mode="fail"),
            ),
        )

    async def validate_input(self, context: AgentContext) -> bool:
        """Require user_intent to be set"""
        return bool(context.user_intent)

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Parse user intent and extract information
        """
        if not context.user_intent:
            self.log_message(context, "No user intent provided", level="warning")
            return context

        intent = context.user_intent.lower()
        self.log_message(context, f"Analyzing intent: {context.user_intent}")

        # Extract mentioned libraries
        mentioned_libraries = self._extract_libraries(intent)
        context.detected_tech_stack = {lib: "latest" for lib in mentioned_libraries}

        if mentioned_libraries:
            self.log_message(
                context,
                f"Detected libraries: {', '.join(mentioned_libraries)}"
            )

        # Classify intent
        intent_type = self._classify_intent(intent)
        context.metadata['intent_type'] = intent_type
        self.log_message(context, f"Intent type: {intent_type}")

        # Extract problem type
        problem_type = self._classify_problem(intent)
        context.metadata['problem_type'] = problem_type
        self.log_message(context, f"Problem type: {problem_type}")

        return context

    def _extract_libraries(self, text: str) -> Set[str]:
        """Extract mentioned libraries from text"""
        libraries = set()

        for pattern, lib_name in self.LIBRARY_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                libraries.add(lib_name)

        return libraries

    def _classify_intent(self, intent: str) -> str:
        """Classify user intent as 'guidance' or 'automatic_fix'"""
        fix_keywords = ['fix', 'auto', 'automatically', 'solve', 'change code', 'apply']
        guide_keywords = ['help', 'explain', 'how to', 'understand', 'debug', 'guide']

        intent_lower = intent.lower()

        # Check for fix intent
        for keyword in fix_keywords:
            if keyword in intent_lower:
                return "automatic_fix"

        # Check for guidance intent
        for keyword in guide_keywords:
            if keyword in intent_lower:
                return "guidance"

        # Default based on presence of error
        has_error = any(keyword in intent_lower for keyword in self.ERROR_KEYWORDS)
        return "guidance" if has_error else "unknown"

    def _classify_problem(self, intent: str) -> str:
        """Classify the type of problem"""
        intent_lower = intent.lower()

        problem_keywords = {
            'dependency': ['version', 'dependency', 'import', 'module not found', 'not installed'],
            'incompatibility': ['incompatible', 'conflict', 'mismatch', 'compatibility'],
            'configuration': ['config', 'setting', 'setup', 'environment'],
            'runtime': ['runtime', 'error', 'exception', 'crash', 'traceback'],
            'performance': ['slow', 'performance', 'memory', 'cpu', 'hang'],
        }

        for problem_type, keywords in problem_keywords.items():
            for keyword in keywords:
                if keyword in intent_lower:
                    return problem_type

        return 'unknown'
