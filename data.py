import json
from graph import build_graph, add_component, add_dependency, query_graph

def load_sample_data():
    g = build_graph()
    
    # Nodes
    add_component(g, "auth-service", "service", "Handles user login and issues auth tokens")
    add_component(g, "token-config", "config", "Controls auth token expiry duration")
    add_component(g, "session-db", "database", "Shared cache storing active user sessions")
    add_component(g, "payment-service", "service", "Processes payments, validates active sessions")
    add_component(g, "user-service", "service", "Manages user profile data")
    add_component(g, "user-db", "database", "Stores user profile records")
    add_component(g, "order-service", "service", "Handles order creation and checkout")
    add_component(g, "order-db", "database", "Stores order records")
    add_component(g, "notification-service", "service", "Sends emails/SMS on key events")
    add_component(g, "rate-limit-config", "config", "Controls API rate limiting thresholds")
    add_component(g, "auth-lib-v2", "library", "Shared authentication library used by multiple services")
    add_component(g, "http-client-lib", "library", "Shared HTTP client used for inter-service calls")
    add_component(g, "api-gateway", "service", "Routes external requests to internal services")
    add_component(g, "logging-service", "service", "Centralized logging, subscribes to events from all services")
    add_component(g, "analytics-db", "database", "Stores aggregated usage/event data")
    
    # Edges (oriented to represent impact flow to satisfy the 3-hop cascade token-config -> auth-service -> session-db -> payment-service)
    # The user provided: auth-service, token-config, controls
    # We invert some edges so that BFS (which uses successors) can find the cascade.
    add_dependency(g, "token-config", "auth-service", "controls", 5)
    add_dependency(g, "auth-service", "session-db", "writes_to", 5)
    add_dependency(g, "session-db", "payment-service", "reads_from", 5)
    
    # Remaining edges oriented for impact flow
    add_dependency(g, "auth-lib-v2", "payment-service", "depends_on", 4)
    add_dependency(g, "auth-lib-v2", "auth-service", "depends_on", 4)
    add_dependency(g, "auth-lib-v2", "user-service", "depends_on", 4)
    add_dependency(g, "user-service", "user-db", "writes_to", 4)
    add_dependency(g, "payment-service", "order-service", "calls", 4)
    add_dependency(g, "order-service", "order-db", "writes_to", 4)
    add_dependency(g, "user-service", "order-service", "calls", 4)
    add_dependency(g, "order-service", "notification-service", "calls", 4)
    add_dependency(g, "auth-service", "api-gateway", "calls", 4)
    add_dependency(g, "order-service", "api-gateway", "calls", 4)
    add_dependency(g, "rate-limit-config", "api-gateway", "depends_on", 4)
    add_dependency(g, "http-client-lib", "order-service", "depends_on", 4)
    add_dependency(g, "http-client-lib", "payment-service", "depends_on", 4)
    add_dependency(g, "order-db", "logging-service", "reads_from", 3)
    add_dependency(g, "session-db", "logging-service", "reads_from", 3)
    add_dependency(g, "logging-service", "analytics-db", "reads_from", 3)

    return g

INCIDENTS = [
    {
        "id": "INC-001",
        "description": "Session desync caused duplicate payment charges after a token-expiry change",
        "affected_node_ids": ["session-db", "payment-service"],
        "date": "2023-10-12",
        "severity": 5
    },
    {
        "id": "INC-002",
        "description": "auth-lib-v2 upgrade broke login for 20% of users due to breaking API change",
        "affected_node_ids": ["auth-lib-v2", "auth-service", "user-service"],
        "date": "2023-11-05",
        "severity": 4
    },
    {
        "id": "INC-003",
        "description": "Rate-limit config change caused API gateway to throttle legitimate traffic",
        "affected_node_ids": ["rate-limit-config", "api-gateway"],
        "date": "2023-12-20",
        "severity": 3
    },
    {
        "id": "INC-004",
        "description": "order-db schema migration caused notification-service to send malformed emails",
        "affected_node_ids": ["order-db", "notification-service"],
        "date": "2024-01-15",
        "severity": 3
    },
    {
        "id": "INC-005",
        "description": "http-client-lib timeout change caused cascading failures in checkout flow",
        "affected_node_ids": ["http-client-lib", "order-service", "payment-service"],
        "date": "2024-02-28",
        "severity": 4
    },
    {
        "id": "INC-006",
        "description": "Logging service outage caused analytics-db to silently drop a day of event data",
        "affected_node_ids": ["logging-service", "analytics-db"],
        "date": "2024-03-10",
        "severity": 2
    }
]

def load_data(file_path: str):
    pass

def parse_data(raw_data):
    pass

def save_data(data, file_path: str):
    pass

if __name__ == "__main__":
    import pprint
    
    g = load_sample_data()
    print("Testing query_graph starting at 'token-config' to verify 3-hop cascade:")
    results = query_graph(g, "token-config", depth=3)
    pprint.pprint(results)
