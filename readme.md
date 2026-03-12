# Financial Investment Advisor

## Problem statement

Develop a multi-agent system where a group of agents collaborates to provide financial investment advice to a client. The system must include:

- A simulated **Client Agent** that provides a profile and evaluates recommendations.
- An **Advisor Agent** that is the only agent allowed to interact with the client and the analyst.
- An **Analyst Agent** with access to the internet and a knowledge store.

The agents should communicate effectively to reach a resolution and terminate once the client is satisfied.

## Architecture overview

The system is an advisor-led workflow. The Advisor Agent orchestrates the plan, delegates research to the Analyst Agent, and uses a simulated Client Agent to generate the profile and evaluate whether the recommendation resolves the query. The workflow enforces a single decision-maker and an explicit stop condition.

## Why the Advisor is the orchestrator

Only the Advisor sees the full state and decides when to call tools or sub-agents. This keeps research, task ordering, and recommendation drafting in one place, avoiding conflicting decisions between agents. The Advisor is the only agent that can decide:

- Which tasks are required.
- When to call the Analyst.
- How to synthesize sources.
- When to end the loop.

## Agent responsibilities

- **Advisor Agent**: Orchestrates the workflow, defines tasks, calls the analyst for research, and writes the final recommendation. Produces the `AdvisorRecommendation` JSON response.
- **Analyst Agent**: Retrieves KB and web sources based on the research mode and returns sourced findings with citations.
- **Client Agent**: Simulates a client by generating a profile and evaluating whether the recommendation is resolved or needs a follow-up concern.

## Sequence diagram / flow

```
Client Agent → Advisor Agent → Analyst Agent
Analyst Agent → Advisor Agent
Advisor Agent → Client Agent
Client Agent → accept / concern
Advisor Agent → final resolution
```

Detailed flow:

1. Client Agent generates a profile from the user query.
2. Advisor Agent creates a todo list and decides the research mode.
3. Analyst Agent retrieves KB and/or web sources and returns findings.
4. Advisor Agent drafts the recommendation.
5. Client Agent evaluates the recommendation for resolution or a follow-up concern.
6. If unresolved, the Advisor revises once, then re-checks resolution.

## State passed between agents

- `State.USER_QUERY`: Original user prompt.
- `State.CLIENT_PROFILE`: Simulated client profile (age, risk tolerance, goals, holdings).
- `State.ANALYST_FINDINGS`: Sourced findings from KB/web research.
- `State.ADVISOR_RECOMMENDATION`: Final recommendation object.
- `State.CLIENT_RESPONSE`: Client evaluation (`resolved` + `follow_up`).
- `State.TODO_LIST`: Task list created and completed by the Advisor.

## Knowledge store design

The KB is stored in LanceDB with curated markdown sources under knowledge_store/data. The knowledge store tool retrieves and reranks chunks for evergreen concepts and internal guidance. Each chunk is normalized into a structured search result with title, snippet, and category for easier synthesis.

## Internet retrieval design

The Advisor sets `State.ANALYST_RESEARCH_MODE` (KB, WEB, or both). The Analyst uses the KB search tool for evergreen concepts and the web search tool for time-sensitive or market-specific information. When both are selected, the Analyst performs one pass of each and synthesizes a single response.

## How resolution is determined

The Client Agent returns a `ClientResponse` with `resolved: true/false` and an optional follow-up concern. The Advisor can revise once when unresolved. A max review count prevents infinite loops. If analyst findings contain explicit gaps or assumptions, the client evaluation is encouraged to raise a focused follow-up.

## How to run

- End-to-end example: [examples/end_to_end_example.py](examples/end_to_end_example.py)

```bash
poetry run python -m examples.end_to_end_example
```

- Web UI (in-memory sessions to avoid local state serialization issues):

```bash
poetry run python -m google.adk.cli web .\agents --session_service_uri memory://
```

## Example output

```json
{
  "summary": "A moderate-risk retirement strategy that balances growth and income.",
  "recommendation": "Diversify across equities and fixed income, ladder bonds, and review annually.",
  "next_steps": [
    "Confirm target allocation",
    "Implement a bond ladder",
    "Rebalance quarterly"
  ]
}
```

## Assumptions and limitations

- The Client Agent is a simulated persona, not a live human. In production, this would be replaced by real user interaction.
- The first run incurs an initial delay while embedding and cross-encoder models load; models are not lazy-loaded per request.
- Web UI persistence can fail if complex objects are stored in session state; use in-memory sessions for the UI command above.
- External API keys are required for web search and LLM providers.