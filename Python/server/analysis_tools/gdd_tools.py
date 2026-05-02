from pathlib import Path
from server.core import mcp

# Simple in-memory cache for GDDs during the session
# In a robust system this might be SQLite or an external vector DB
_GDD_CACHE = {}

@mcp.tool()
async def upload_gdd(file_path: str, document_id: str = "default") -> str:
    """
    Loads a Game Design Document (GDD) from a local file path into the session memory.
    This allows the AI to maintain context about the game's design over time.

    Args:
        file_path: Path to the GDD file (Markdown, TXT, or JSON).
        document_id: An identifier for this document to reference later.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: GDD file not found at {file_path}"

    try:
        content = path.read_text(encoding='utf-8')
        _GDD_CACHE[document_id] = content
        return f"Successfully loaded GDD '{document_id}' ({len(content)} characters)."
    except Exception as e:
        return f"Failed to load GDD file: {str(e)}"

@mcp.tool()
async def query_gdd(query: str, document_id: str = "default") -> str:
    """
    Queries the loaded GDD for specific context or keywords.
    Since this is a simple text lookup, try to provide specific keywords.

    Args:
        query: The term or concept to search for in the GDD.
        document_id: The identifier of the GDD to search in.
    """
    if document_id not in _GDD_CACHE:
        return f"Error: No GDD loaded with ID '{document_id}'. Please use upload_gdd first."

    content = _GDD_CACHE[document_id]

    # Simple primitive search: extract paragraphs containing the query term
    results = []
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    query_lower = query.lower()
    for p in paragraphs:
        if query_lower in p.lower():
            results.append(p)

    if not results:
        return f"No matches found for '{query}' in GDD '{document_id}'."

    output = f"### Query Results for '{query}' in '{document_id}':\n\n"
    for r in results[:5]: # limit to 5 matching blocks
        output += f"- {r}\n"

    if len(results) > 5:
        output += f"\n*(Showing 5 of {len(results)} matches...)*"

    return output
