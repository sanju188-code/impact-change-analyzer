import networkx as nx
from pyvis.network import Network

def build_graph():
    return nx.DiGraph()

def add_component(graph, node_id, type, description):
    graph.add_node(node_id, type=type, description=description)

def add_dependency(graph, source, target, relation, criticality):
    graph.add_edge(source, target, relation=relation, criticality=criticality)

def query_graph(graph, node_id, depth=3):
    if node_id not in graph:
        return []
        
    results = []
    queue = [(node_id, 0, [node_id])]
    visited = {node_id}
    
    while queue:
        current, current_depth, current_path = queue.pop(0)
        
        if current_depth >= depth:
            continue
            
        for neighbor in graph.successors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                traversal_path = current_path + [neighbor]
                queue.append((neighbor, current_depth + 1, traversal_path))
                
                edge_data = graph.get_edge_data(current, neighbor)
                node_data = graph.nodes[neighbor]
                
                results.append({
                    "node_id": neighbor,
                    "path": " → ".join(traversal_path),
                    "hop_distance": current_depth + 1,
                    "relation": edge_data.get("relation", ""),
                    "description": node_data.get("description", ""),
                    "type": node_data.get("type", "")
                })
                
    return results

def analyze_impact(graph, start_node):
    pass

def visualize_graph(graph):
    pass

if __name__ == "__main__":
    import pprint
    
    g = build_graph()
    
    add_component(g, "auth_service", "service", "Handles user authentication")
    add_component(g, "user_db", "database", "Stores user profiles")
    add_component(g, "payment_service", "service", "Processes transactions")
    add_component(g, "stripe_lib", "library", "External payment gateway library")
    add_component(g, "app_config", "config", "Global application settings")
    
    add_dependency(g, "auth_service", "user_db", "reads_from", 5)
    add_dependency(g, "auth_service", "app_config", "reads_from", 3)
    add_dependency(g, "payment_service", "auth_service", "depends_on", 5)
    add_dependency(g, "payment_service", "stripe_lib", "calls", 4)
    add_dependency(g, "payment_service", "app_config", "shares_config_with", 2)
    
    print("Querying graph from 'payment_service' (depth=2):")
    results = query_graph(g, "payment_service", depth=2)
    pprint.pprint(results)
