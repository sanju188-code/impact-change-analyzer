import openai
import os
import json
import math
import time
from dotenv import load_dotenv
from graph import query_graph

load_dotenv()

def get_related_incidents(node_id: str, incidents: list):
    """Filter INCIDENTS to only those where node_id appears in affected_node_ids."""
    return [inc for inc in incidents if node_id in inc["affected_node_ids"]]

def calculate_risk_score(hop_distance: int, incident_count: int, llm_severity: str) -> str:
    """Calculate a deterministic risk score combining hop distance, incident count, and LLM judgment."""
    severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    base_llm = severity_map.get(llm_severity.lower(), 1)
    
    # Fewer hops = higher weight (max 3)
    hop_weight = max(1, 4 - hop_distance) 
    
    # More incidents = higher weight (capped at 5)
    incident_weight = min(5, incident_count * 2)
    
    total_score = base_llm + hop_weight + incident_weight
    
    if total_score <= 4:
        return "Low"
    elif total_score <= 7:
        return "Medium"
    elif total_score <= 9:
        return "High"
    else:
        return "Critical"

RISK_LEVELS_FOR_MITIGATION = {"Medium", "High", "Critical"}
VALID_MITIGATION_TYPES = {
    "staged_rollout",
    "monitoring",
    "code_change",
    "config_adjustment",
    "testing",
}

# Initialize OpenAI-compatible client for the OpenRouter/OpenAI router.
OPENAI_ROUTER_BASE_URL = os.getenv(
    "OPENAI_ROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)
OPENAI_ROUTER_API_KEY = (
    os.getenv("OPENROUTER_API_KEY")
    or os.getenv("OPENAI_API_KEY", "")
)
OPENAI_ROUTER_MODEL = (
    os.getenv("OPENAI_ROUTER_MODEL")
    or os.getenv("OPENROUTER_MODEL")
    or "openai/gpt-4o-mini"
)

client = openai.OpenAI(
    base_url=OPENAI_ROUTER_BASE_URL,
    api_key=OPENAI_ROUTER_API_KEY,
)

def chat_followup(user_message, chat_history, current_analysis, graph, incidents):
    """Answer a follow-up using only the active analysis, graph, and incidents."""
    graph_nodes = [
        {
            "node_id": node_id,
            "type": node_data.get("type", ""),
            "description": node_data.get("description", ""),
        }
        for node_id, node_data in graph.nodes(data=True)
    ]
    graph_edges = [
        {
            "source": source,
            "target": target,
            "relation": edge_data.get("relation", ""),
            "criticality": edge_data.get("criticality", ""),
        }
        for source, target, edge_data in graph.edges(data=True)
    ]
    analysis_summary = {
        "targeted_node": current_analysis.get("targeted_node"),
        "affected_components": current_analysis.get("affected_components", []),
        "overall_recommendation": current_analysis.get("overall_recommendation", ""),
    }

    system_prompt = f"""
You are the follow-up assistant for a change impact analysis. Answer only from
the current analysis, graph, and incident data below. Be concise and explain
your reasoning by pointing to the relevant component, dependency, or incident
when available. Do not invent architecture details, dependencies, incidents,
metrics, or operational facts. If the answer cannot be supported by this data,
say exactly: "I don't have data on that."
For questions about a different node or a what-if scenario, use the query_graph
tool to inspect fresh downstream dependencies before answering.

Current analysis result:
{json.dumps(analysis_summary, indent=2)}

Graph structure (nodes):
{json.dumps(graph_nodes, indent=2)}

Graph structure (directed dependencies):
{json.dumps(graph_edges, indent=2)}

Historical incidents:
{json.dumps(incidents, indent=2)}
"""

    graph_query_tool = {
        "type": "function",
        "function": {
            "name": "query_graph",
            "description": (
                "Traverse downstream dependencies from a graph node. Use this for "
                "questions about a different node or a what-if scenario instead of "
                "guessing from the current analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "An exact node_id from the graph structure.",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Maximum downstream traversal depth (1-3).",
                        "minimum": 1,
                        "maximum": 3,
                    },
                },
                "required": ["node_id"],
                "additionalProperties": False,
            },
        },
    }

    messages = [{"role": "system", "content": system_prompt}]
    for message in chat_history:
        if (
            isinstance(message, dict)
            and message.get("role") in {"user", "assistant"}
            and isinstance(message.get("content"), str)
        ):
            messages.append({"role": message["role"], "content": message["content"]})
    messages.append({"role": "user", "content": user_message})

    for _ in range(3):
        response = client.chat.completions.create(
            model=OPENAI_ROUTER_MODEL,
            max_tokens=600,
            messages=messages,
            tools=[graph_query_tool],
        )
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []
        if not tool_calls:
            return (assistant_message.content or "I don't have data on that.").strip()

        messages.append(assistant_message.model_dump(exclude_none=True))
        for tool_call in tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments)
                node_id = arguments.get("node_id")
                depth = arguments.get("depth", 3)
                if not isinstance(depth, int) or isinstance(depth, bool):
                    depth = 3
                result = query_graph(graph, node_id, depth=max(1, min(depth, 3)))
                tool_result = {"node_id": node_id, "affected_components": result}
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                tool_result = {"error": f"Unable to query the graph: {error}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result),
            })

    return "I don't have data on that."

def generate_mitigations(affected_components: list, change_description: str) -> dict:
    """Generate actionable mitigations for Medium+ risk affected components."""
    components_needing_mitigation = [
        {
            "node_id": comp["node_id"],
            "risk_level": comp["risk_level"],
            "explanation": comp.get("explanation", ""),
            "related_incidents": comp.get("related_incidents", []),
        }
        for comp in affected_components
        if comp.get("risk_level") in RISK_LEVELS_FOR_MITIGATION
    ]

    if not components_needing_mitigation:
        return {
            "mitigations": [],
            "overall_recommendation": (
                "All identified downstream impacts are low risk. Proceed with the change "
                "using your standard deployment checklist and baseline monitoring."
            ),
        }

    system_prompt = """
You are an expert site reliability engineer recommending concrete mitigations for a planned production change.

You will receive a proposed change and a list of affected components at Medium risk or higher.
Each component includes its risk level, explanation of why it is at risk, and any related historical incident IDs.

Guidance for suggestions:
- If related_incidents is non-empty: propose actions that would have prevented or quickly detected those specific past incidents.
- If related_incidents is empty: the risk is graph-inferred without historical precedent — favor monitoring, testing, or staged rollout mitigations.

Return your answer strictly in valid JSON format matching this structure:
{
  "mitigations": [
    {
      "node_id": "string",
      "suggestion": "string (1-2 concrete, actionable sentences)",
      "mitigation_type": "staged_rollout" | "monitoring" | "code_change" | "config_adjustment" | "testing"
    }
  ],
  "overall_recommendation": "string (1-2 sentences on how to approach the change safely overall, e.g. rollout order or sequencing)"
}

Provide exactly one mitigation entry per component in the input list.
Do not include any other text, markdown blocks, or explanations outside the JSON.
"""

    user_prompt = f"""
Proposed Change: {change_description}

Components requiring mitigation (Medium risk or higher):
{json.dumps(components_needing_mitigation, indent=2)}
"""

    response = client.chat.completions.create(
        model=OPENAI_ROUTER_MODEL,
        max_tokens=600,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    try:
        content = response.choices[0].message.content
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        mitigations = result.get("mitigations", [])
        expected_node_ids = {comp["node_id"] for comp in components_needing_mitigation}

        validated_mitigations = []
        for entry in mitigations:
            node_id = entry.get("node_id")
            mitigation_type = entry.get("mitigation_type", "")
            if node_id not in expected_node_ids:
                continue
            if mitigation_type not in VALID_MITIGATION_TYPES:
                mitigation_type = "monitoring"
            validated_mitigations.append({
                "node_id": node_id,
                "suggestion": entry.get("suggestion", ""),
                "mitigation_type": mitigation_type,
            })

        return {
            "mitigations": validated_mitigations,
            "overall_recommendation": result.get(
                "overall_recommendation",
                "Roll out the change incrementally and validate downstream dependencies before full promotion.",
            ),
        }
    except Exception as e:
        print(f"Failed to parse mitigation model response: {response.choices[0].message.content}")
        raise e

def analyze_change(change_text: str, graph, incidents: list):
    # Prepare node context for the LLM
    valid_node_ids = list(graph.nodes)
    node_context = []
    for node_id in valid_node_ids:
        desc = graph.nodes[node_id].get("description", "")
        node_context.append(f"- {node_id}: {desc}")
    node_context_str = "\n".join(node_context)

    # Step 1: Extract targeted node
    system_prompt_1 = f"""
You are an expert system architecture analyzer. 
Given a proposed change text, identify which component in the graph it most likely targets.

Available components:
{node_context_str}

Valid node_ids (the only values you may return):
{", ".join(valid_node_ids)}

You MUST return exactly one of the valid node_ids listed above. Never invent,
modify, or infer a new node_id. If the proposed change does not clearly apply
to one of these components, return {{"node_id": null, "confidence": 0}}.

Return your answer strictly in valid JSON format matching this structure:
{{"node_id": "one exact valid node_id or null", "confidence": 0.95}}
Do not include any other text, markdown blocks, or explanations outside the JSON.
"""
    
    target_identification_started = time.time()
    response_1 = client.chat.completions.create(
        model=OPENAI_ROUTER_MODEL,
        max_tokens=100,
        messages=[
            {"role": "system", "content": system_prompt_1},
            {"role": "user", "content": f"Proposed change: {change_text}"}
        ]
    )
    
    try:
        content_1 = response_1.choices[0].message.content
        content_1 = content_1.replace("```json", "").replace("```", "").strip()
        extracted = json.loads(content_1)
        targeted_node_id = extracted.get("node_id")
        try:
            confidence = float(extracted.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0
    except Exception as e:
        print(f"Failed to parse model response: {response_1.choices[0].message.content}")
        raise e

    if (
        targeted_node_id not in valid_node_ids
        or not math.isfinite(confidence)
        or confidence < 0.6
    ):
        print(f"Target identification: {time.time() - target_identification_started:.2f}s")
        return {
            "status": "unclear",
            "message": (
                "This change doesn't clearly map to a component in the system "
                "(auth-service, payment-service, session-db, etc.). Try referencing "
                "a specific service, config, or database."
            ),
        }

    print(f"Target identification: {time.time() - target_identification_started:.2f}s")

    # Step 2: Query graph
    graph_traversal_started = time.time()
    affected_nodes = query_graph(graph, targeted_node_id, depth=3)
    print(f"Graph traversal: {time.time() - graph_traversal_started:.2f}s")

    # Step 3: Match incidents
    incident_filtering_started = time.time()
    matched_incidents_info = []
    traversal_paths = {}
    for node_info in affected_nodes:
        nid = node_info["node_id"]
        traversal_paths[nid] = node_info.get("path", f"{targeted_node_id} → {nid}")
        # Use our dedicated Python function to guarantee only correctly associated incidents are passed
        related_incidents = get_related_incidents(nid, incidents)
        
        matched_incidents_info.append({
            "node_info": node_info,
            "related_incidents": related_incidents
        })
    print(f"Incident filtering: {time.time() - incident_filtering_started:.2f}s")

    # Step 4: Final Impact Analysis
    system_prompt_2 = """
You are an expert site reliability engineer. 
You will be provided with a proposed change, the initial targeted component, and a list of downstream components affected by this change.
For each downstream component, you will also receive a pre-filtered list of historical incidents that occurred on that specific node.

Analyze the risks of the proposed change on these downstream components.
When citing related incidents in your JSON output, YOU MUST ONLY select from the exact pre-filtered incidents provided for that specific component. Do not invent or loosely associate incidents from other components. If none of the provided incidents for a node are relevant to the proposed change (e.g. an incident about rate-limiting when the change is about token expiry), leave the list empty [].

Return your answer strictly in valid JSON format matching this structure:
{
  "affected_components": [
    {
      "node_id": "string",
      "hop_distance": 1,
      "risk_level": "Low" | "Medium" | "High" | "Critical",
      "explanation": "string (1-2 sentences explaining why)",
      "related_incidents": ["INC-001", "INC-002"],
      "evidence_strength": "confirmed" | "inferred"
    }
  ]
}
Do not include any other text, markdown blocks, or explanations outside the JSON.
"""

    user_prompt_2 = f"""
Proposed Change: {change_text}
Targeted Component: {targeted_node_id}

Downstream Affected Components and Incidents:
{json.dumps(matched_incidents_info, indent=2)}
"""

    explanation_generation_started = time.time()
    response_2 = client.chat.completions.create(
        model=OPENAI_ROUTER_MODEL,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": system_prompt_2},
            {"role": "user", "content": user_prompt_2}
        ]
    )

    try:
        content_2 = response_2.choices[0].message.content
        content_2 = content_2.replace("```json", "").replace("```", "").strip()
        final_analysis = json.loads(content_2)
        
        # Override risk_level using deterministic scoring
        for comp in final_analysis.get("affected_components", []):
            node_id = comp.get("node_id")
            # The traversal route and evidence classification are determined from
            # graph and incident data rather than model-generated text.
            comp["path"] = traversal_paths.get(node_id, targeted_node_id)
            comp["evidence_strength"] = (
                "confirmed" if comp.get("related_incidents") else "inferred"
            )
            llm_risk = comp.get("risk_level", "Low")
            comp["llm_risk_level"] = llm_risk
            
            comp["risk_level"] = calculate_risk_score(
                hop_distance=comp.get("hop_distance", 3),
                incident_count=len(comp.get("related_incidents", [])),
                llm_severity=llm_risk
            )

        print(f"Explanation generation: {time.time() - explanation_generation_started:.2f}s")
            
        final_analysis["targeted_node"] = targeted_node_id
        final_analysis.update(
            generate_mitigations(
                final_analysis.get("affected_components", []),
                change_text,
            )
        )
        return final_analysis
    except Exception as e:
        print(f"Failed to parse final model response: {response_2.choices[0].message.content}")
        raise e

def generate_impact_summary(changes):
    pass

def query_agent(prompt: str):
    pass

if __name__ == "__main__":
    import pprint
    from data import load_sample_data, INCIDENTS
    
    g = load_sample_data()
    print("Running analyze_change test...")
    try:
        result = analyze_change("increasing auth token expiry to 24 hours", g, INCIDENTS)
        pprint.pprint(result)
        print("\n--- Mitigations ---")
        pprint.pprint(result.get("mitigations", []))
        print("\nOverall recommendation:")
        print(result.get("overall_recommendation", ""))
    except Exception as e:
        print(f"Error during test: {e}")
