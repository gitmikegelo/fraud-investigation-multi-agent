"""
Ring visualization using PyVis.
Generates interactive HTML visualizations of fraud rings.
"""

from pyvis.network import Network
from typing import List, Dict
import os


def visualize_ring(
    ring_data: Dict,
    output_path: str = "ring.html",
    height: str = "750px",
    width: str = "100%"
) -> str:
    """
    Create an interactive network visualization of a fraud ring.
    
    Args:
        ring_data: Dict with:
            - entities: List of {entity_id, entity_type, anomaly_score}
            - edges: List of {src, dst, relationship, weight, total_amount}
        output_path: Where to save the HTML file
        height: Visualization height
        width: Visualization width
    
    Returns:
        Path to generated HTML file
    """
    
    # Create network
    net = Network(
        height=height,
        width=width,
        bgcolor="#0a0a0a",
        font_color="white",
        directed=True
    )
    
    # Physics settings for better layout
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {"iterations": 150}
        },
        "nodes": {
            "font": {"size": 14, "color": "white"}
        },
        "edges": {
            "color": {"inherit": true},
            "smooth": {"type": "continuous"}
        }
    }
    """)
    
    # Color scheme by entity type
    colors = {
        'provider': '#e74c3c',   # Red
        'member': '#3498db',     # Blue
        'facility': '#2ecc71',   # Green
    }
    
    # Add nodes
    entities = ring_data.get('entities', [])
    for entity in entities:
        entity_id = entity['entity_id']
        entity_type = entity.get('entity_type', 'unknown')
        anomaly_score = entity.get('anomaly_score', 0)
        
        # Size based on anomaly score (min 20, max 50)
        size = 20 + (anomaly_score * 30)
        
        # Color based on type
        color = colors.get(entity_type, '#95a5a6')
        
        # Label
        label = entity_id
        title = f"""
        <b>{entity_id}</b><br>
        Type: {entity_type}<br>
        Anomaly Score: {anomaly_score:.2f}
        """
        
        net.add_node(
            entity_id,
            label=label,
            title=title,
            color=color,
            size=size,
            borderWidth=2,
            borderWidthSelected=4
        )
    
    # Add edges
    edges = ring_data.get('edges', [])
    for edge in edges:
        src = edge['src']
        dst = edge['dst']
        relationship = edge.get('relationship', 'CONNECTED')
        weight = edge.get('weight', 1)
        total_amount = edge.get('total_amount', 0)
        
        # Edge width based on weight
        edge_width = min(1 + (weight / 10), 8)
        
        # Edge color based on relationship
        edge_colors = {
            'BILLED_FOR': '#e74c3c',
            'REFERRED_TO': '#f39c12',
            'OPERATES_AT': '#9b59b6',
        }
        edge_color = edge_colors.get(relationship, '#95a5a6')
        
        # Label for edge
        if total_amount > 0:
            title = f"{relationship}<br>Claims: {weight}<br>Amount: ${total_amount:,.0f}"
        else:
            title = f"{relationship}<br>Count: {weight}"
        
        net.add_edge(
            src,
            dst,
            title=title,
            width=edge_width,
            color=edge_color,
            arrows='to'
        )
    
    # Save
    net.save_graph(output_path)
    
    return output_path


def visualize_entity_network(
    entity_id: str,
    connections: Dict,
    edges: List[Dict],
    output_path: str = None
) -> str:
    """
    Visualize an entity and its connections.
    
    Args:
        entity_id: Central entity
        connections: Result from find_connections()
        edges: Edge data for the subgraph
        output_path: Where to save (default: {entity_id}_network.html)
    
    Returns:
        Path to generated HTML file
    """
    
    if output_path is None:
        safe_id = entity_id.replace('-', '_')
        output_path = f"{safe_id}_network.html"
    
    # Build ring_data format
    entities = [{'entity_id': entity_id, 'entity_type': 'provider', 'anomaly_score': 1.0}]
    
    for conn in connections.get('connected_entities', []):
        entities.append({
            'entity_id': conn['entity_id'],
            'entity_type': conn['entity_type'],
            'anomaly_score': conn.get('anomaly_score', 0)
        })
    
    ring_data = {
        'entities': entities,
        'edges': edges
    }
    
    return visualize_ring(ring_data, output_path)


def create_legend_html() -> str:
    """Create HTML legend for the visualization."""
    return """
    <div style="position: fixed; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); 
                padding: 15px; border-radius: 8px; color: white; font-family: sans-serif;">
        <h4 style="margin: 0 0 10px 0;">Legend</h4>
        <div><span style="color: #e74c3c;">●</span> Provider</div>
        <div><span style="color: #3498db;">●</span> Member</div>
        <div><span style="color: #2ecc71;">●</span> Facility</div>
        <hr style="border-color: #555;">
        <div style="font-size: 12px;">
            <div><span style="color: #e74c3c;">—</span> Billed For</div>
            <div><span style="color: #f39c12;">—</span> Referred To</div>
            <div><span style="color: #9b59b6;">—</span> Operates At</div>
        </div>
        <hr style="border-color: #555;">
        <div style="font-size: 11px;">Node size = anomaly score</div>
    </div>
    """


if __name__ == "__main__":
    # Test visualization
    test_ring = {
        'entities': [
            {'entity_id': 'P-6610', 'entity_type': 'provider', 'anomaly_score': 0.72},
            {'entity_id': 'P-6620', 'entity_type': 'provider', 'anomaly_score': 0.55},
            {'entity_id': 'P-6630', 'entity_type': 'provider', 'anomaly_score': 0.52},
            {'entity_id': 'P-6640', 'entity_type': 'provider', 'anomaly_score': 0.65},
            {'entity_id': 'P-6650', 'entity_type': 'provider', 'anomaly_score': 0.51},
            {'entity_id': 'M-NET-01', 'entity_type': 'member', 'anomaly_score': 0.40},
            {'entity_id': 'M-NET-02', 'entity_type': 'member', 'anomaly_score': 0.38},
            {'entity_id': 'F-8801', 'entity_type': 'facility', 'anomaly_score': 0.45},
        ],
        'edges': [
            {'src': 'P-6620', 'dst': 'P-6610', 'relationship': 'REFERRED_TO', 'weight': 10, 'total_amount': 0},
            {'src': 'P-6630', 'dst': 'P-6610', 'relationship': 'REFERRED_TO', 'weight': 8, 'total_amount': 0},
            {'src': 'P-6650', 'dst': 'P-6610', 'relationship': 'REFERRED_TO', 'weight': 6, 'total_amount': 0},
            {'src': 'P-6640', 'dst': 'P-6610', 'relationship': 'REFERRED_TO', 'weight': 5, 'total_amount': 0},
            {'src': 'P-6610', 'dst': 'M-NET-01', 'relationship': 'BILLED_FOR', 'weight': 4, 'total_amount': 75000},
            {'src': 'P-6610', 'dst': 'M-NET-02', 'relationship': 'BILLED_FOR', 'weight': 3, 'total_amount': 58000},
            {'src': 'P-6610', 'dst': 'F-8801', 'relationship': 'OPERATES_AT', 'weight': 30, 'total_amount': 0},
        ]
    }
    
    output = visualize_ring(test_ring, 'test_ring.html')
    print(f"Visualization saved to: {output}")
