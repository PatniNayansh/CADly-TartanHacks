"""Application configuration. All settings read from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UI_DIR = Path(__file__).resolve().parent / "ui"

# Fusion 360 Add-in HTTP Server
FUSION_HOST = os.getenv("FUSION_HOST", "localhost")
FUSION_PORT = int(os.getenv("FUSION_PORT", "5000"))
FUSION_BASE_URL = f"http://{FUSION_HOST}:{FUSION_PORT}"
FUSION_TIMEOUT = 20  # seconds
FUSION_RETRY_COUNT = 3
FUSION_RETRY_DELAY = 1.0  # seconds between retries

# FastAPI Server
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "3000"))

# Dedalus Labs (R3 only)
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY", "")
DEDALUS_MODEL = "anthropic/claude-sonnet-4-5-20250929"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Fix validation
FIX_VALIDATION_RETRIES = 3
FIX_VALIDATION_DELAY = 1.0  # seconds between validation polls

# Fusion 360 HTTP Endpoints
ENDPOINTS = {
    # Health
    "test_connection": "/test_connection",
    # Geometry queries
    "get_body_properties": "/get_body_properties",
    "get_faces_info": "/get_faces_info",
    "get_edges_info": "/get_edges_info",
    "analyze_walls": "/analyze_walls",
    "analyze_holes": "/analyze_holes",
    # Geometry modification
    "fillet_specific_edges": "/fillet_specific_edges",
    "execute_script": "/execute_script",
    "undo": "/undo",
    # CAD creation
    "box": "/Box",
    "cylinder": "/draw_cylinder",
    "circle": "/create_circle",
    "line": "/draw_one_line",
    "lines": "/draw_lines",
    "rectangle": "/draw_2d_rectangle",
    "arc": "/arc",
    "sphere": "/draw_sphere",
    "text": "/draw_text",
    "spline": "/spline",
    # Features
    "extrude": "/extrude_last_sketch",
    "cut_extrude": "/cut_extrude",
    "extrude_thin": "/extrude_thin",
    "revolve": "/revolve",
    "sweep": "/sweep",
    "loft": "/loft",
    "fillet_edges": "/fillet_edges",
    "shell_body": "/shell_body",
    "holes": "/holes",
    "thread": "/threaded",
    # Patterns
    "circular_pattern": "/circular_pattern",
    "rectangular_pattern": "/rectangular_pattern",
    # Operations
    "boolean_operation": "/boolean_operation",
    "move_body": "/move_body",
    "offset_plane": "/offsetplane",
    "set_parameter": "/set_parameter",
    "select_body": "/select_body",
    "select_sketch": "/select_sketch",
    # Parameters
    "count_parameters": "/count_parameters",
    "list_parameters": "/list_parameters",
    # Export
    "export_step": "/Export_STEP",
    "export_stl": "/Export_STL",
    # Scene management
    "delete_all": "/delete_everything",
}
