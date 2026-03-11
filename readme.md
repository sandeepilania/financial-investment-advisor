# Financial Investment Advisor

## Objective

Develop a multi-agent system where a group of agents collaborates to provide financial investment advice to a client.

## Agents

- **Client Agent**: A simulated client with a profile that includes attributes such as age, risk aversion, assets, and investments. You can use any dummy LLM-generated client profile.
- **Advisor Agent**: The sole agent permitted to interact with the client and the analyst. This agent is responsible for defining tasks for the analyst.
- **Analyst Agent**: An agent with access to:
  - The internet
  - A knowledge store (you may define any that makes sense)

  This agent fetches information for the advisor to tailor responses to the client.

## Goal

The agents should communicate effectively to achieve a common goal, concluding the conversation when a resolution is reached.

## Assumption

You may use any framework that suits your approach.