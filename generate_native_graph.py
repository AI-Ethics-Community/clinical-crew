"""
Generate diagram using LangGraph's native visualization capabilities.

LangGraph provides built-in methods for visualization:
- get_graph().draw_mermaid() - Returns Mermaid diagram as text
- get_graph().draw_mermaid_png() - Returns PNG image (requires pygraphviz)
- get_graph().draw_ascii() - Returns ASCII representation
"""

import asyncio
from app.agents.graph import medical_consultation_workflow, medical_consultation_workflow_from_evaluation


def generate_mermaid_text():
    """Generate Mermaid diagram text using LangGraph's native method."""
    print("Generating Mermaid diagram text...")

    # Get the compiled graph
    graph = medical_consultation_workflow

    # Generate Mermaid text
    mermaid_text = graph.get_graph().draw_mermaid()

    return mermaid_text


def generate_ascii_diagram():
    """Generate ASCII representation of the graph."""
    print("Generating ASCII diagram...")

    graph = medical_consultation_workflow

    # Generate ASCII text
    ascii_text = graph.get_graph().draw_ascii()

    return ascii_text


def generate_mermaid_png():
    """Generate PNG image using LangGraph's native method."""
    print("Generating PNG using LangGraph native method...")

    try:
        graph = medical_consultation_workflow

        # Generate PNG
        png_data = graph.get_graph().draw_mermaid_png()

        return png_data
    except Exception as e:
        print(f"Error generating PNG: {e}")
        print("Note: This requires pygraphviz to be installed")
        print("Install with: pip install pygraphviz")
        return None


def save_diagrams():
    """Save all diagram formats."""

    # 1. Save Mermaid text
    print("\n1. Generating Mermaid diagram...")
    mermaid_text = generate_mermaid_text()

    with open('graph_native_mermaid.md', 'w') as f:
        f.write("# Clinical Crew - LangGraph Native Visualization\n\n")
        f.write("## Main Workflow (with Interrogation)\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_text)
        f.write("\n```\n\n")

    print("   ✓ Saved to: graph_native_mermaid.md")

    # 2. Save ASCII diagram
    print("\n2. Generating ASCII diagram...")
    try:
        ascii_text = generate_ascii_diagram()

        with open('graph_native_ascii.txt', 'w') as f:
            f.write("Clinical Crew - LangGraph ASCII Visualization\n")
            f.write("=" * 60 + "\n\n")
            f.write(ascii_text)

        print("   ✓ Saved to: graph_native_ascii.txt")
    except ImportError as e:
        print(f"   ⚠ ASCII generation skipped: {e}")
        print("   ℹ Install with: pip install grandalf")

    # 3. Try to save PNG
    print("\n3. Attempting to generate PNG with native LangGraph method...")
    png_data = generate_mermaid_png()

    if png_data:
        with open('graph_native.png', 'wb') as f:
            f.write(png_data)
        print("   ✓ Saved to: graph_native.png")
    else:
        print("   ⚠ PNG generation skipped (requires pygraphviz)")

    # 4. Generate workflow from evaluation (without interrogation)
    print("\n4. Generating alternative workflow (from evaluation)...")
    graph_from_eval = medical_consultation_workflow_from_evaluation
    mermaid_from_eval = graph_from_eval.get_graph().draw_mermaid()

    with open('graph_native_mermaid.md', 'a') as f:
        f.write("\n## Alternative Workflow (from Evaluation)\n\n")
        f.write("This workflow starts directly from the evaluation phase (after interrogation is complete).\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_from_eval)
        f.write("\n```\n")

    print("   ✓ Appended to: graph_native_mermaid.md")

    # 5. Display graph info
    print("\n5. Graph Information:")
    graph = medical_consultation_workflow
    graph_info = graph.get_graph()

    print(f"   • Nodes: {len(graph_info.nodes)}")
    print(f"   • Edges: {len(graph_info.edges)}")
    print(f"\n   Node list:")
    for node in graph_info.nodes:
        print(f"     - {node}")

    print("\n✅ All native LangGraph diagrams generated!")
    print("\nFiles created:")
    print("  - graph_native_mermaid.md (Mermaid format - both workflows)")
    print("  - graph_native_ascii.txt (ASCII text representation)")
    if png_data:
        print("  - graph_native.png (PNG image)")

    print("\n📝 Note: The Mermaid diagrams can be viewed on:")
    print("  - GitHub (automatic rendering)")
    print("  - https://mermaid.live/ (paste the code)")
    print("  - VS Code with Mermaid extension")


if __name__ == '__main__':
    save_diagrams()
