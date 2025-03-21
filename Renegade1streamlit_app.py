import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import time
import logging
import os
import threading
import asyncio
import random
import base64
import traceback
from datetime import datetime, timedelta
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("redteam_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RedTeamApp")

# Set page configuration with custom theme
st.set_page_config(
    page_title="AI Security Red Team Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state with error handling
def initialize_session_state():
    """Initialize all session state variables with proper error handling"""
    try:
        # Core session states
        if 'targets' not in st.session_state:
            st.session_state.targets = []

        if 'test_results' not in st.session_state:
            st.session_state.test_results = {}

        if 'running_test' not in st.session_state:
            st.session_state.running_test = False

        if 'progress' not in st.session_state:
            st.session_state.progress = 0

        if 'vulnerabilities_found' not in st.session_state:
            st.session_state.vulnerabilities_found = 0

        if 'current_theme' not in st.session_state:
            st.session_state.current_theme = "dark"  # Default to dark theme
            
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"
            
        # Thread management
        if 'active_threads' not in st.session_state:
            st.session_state.active_threads = []
            
        # Error handling
        if 'error_message' not in st.session_state:
            st.session_state.error_message = None
            
        logger.info("Session state initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing session state: {str(e)}")
        display_error(f"Failed to initialize application state: {str(e)}")

# Thread cleanup
def cleanup_threads():
    """Remove completed threads from session state"""
    try:
        if 'active_threads' in st.session_state:
            # Filter out completed threads
            active_threads = []
            for thread in st.session_state.active_threads:
                if thread.is_alive():
                    active_threads.append(thread)
            
            # Update session state with only active threads
            st.session_state.active_threads = active_threads
            
            if len(st.session_state.active_threads) > 0:
                logger.info(f"Active threads: {len(st.session_state.active_threads)}")
    except Exception as e:
        logger.error(f"Error cleaning up threads: {str(e)}")

# Define color schemes
themes = {
    "dark": {
        "bg_color": "#121212",
        "card_bg": "#1E1E1E",
        "primary": "#1DB954",    # Vibrant green
        "secondary": "#BB86FC",  # Purple
        "accent": "#03DAC6",     # Teal
        "warning": "#FF9800",    # Orange
        "error": "#CF6679",      # Red
        "text": "#FFFFFF"
    },
    "light": {
        "bg_color": "#F5F5F5",
        "card_bg": "#FFFFFF",
        "primary": "#1DB954",    # Vibrant green
        "secondary": "#7C4DFF",  # Deep purple
        "accent": "#00BCD4",     # Cyan
        "warning": "#FF9800",    # Orange
        "error": "#F44336",      # Red
        "text": "#212121"
    }
}

# Get current theme colors safely
def get_theme():
    """Get current theme with error handling"""
    try:
        return themes[st.session_state.current_theme]
    except Exception as e:
        logger.error(f"Error getting theme: {str(e)}")
        # Return dark theme as fallback
        return themes["dark"]

# CSS styles
def load_css():
    """Load CSS with the current theme"""
    try:
        theme = get_theme()
        
        return f"""
        <style>
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: {theme["primary"]};
        }}
        
        .stProgress > div > div > div > div {{
            background-color: {theme["primary"]};
        }}
        
        div[data-testid="stExpander"] {{
            border: none;
            border-radius: 8px;
            background-color: {theme["card_bg"]};
            margin-bottom: 1rem;
        }}
        
        div[data-testid="stVerticalBlock"] {{
            gap: 1.5rem;
        }}
        
        .card {{
            border-radius: 10px;
            background-color: {theme["card_bg"]};
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            border-left: 3px solid {theme["primary"]};
        }}
        
        .warning-card {{
            border-left: 3px solid {theme["warning"]};
        }}
        
        .error-card {{
            border-left: 3px solid {theme["error"]};
        }}
        
        .success-card {{
            border-left: 3px solid {theme["primary"]};
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: {theme["primary"]};
        }}
        
        .metric-label {{
            font-size: 14px;
            color: {theme["text"]};
            opacity: 0.7;
        }}
        
        .sidebar-title {{
            margin-left: 15px;
            font-size: 1.2rem;
            font-weight: bold;
            color: {theme["primary"]};
        }}
        
        .target-card {{
            border-radius: 8px;
            background-color: {theme["card_bg"]};
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 3px solid {theme["secondary"]};
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .status-badge.active {{
            background-color: {theme["primary"]};
            color: white;
        }}
        
        .status-badge.inactive {{
            background-color: gray;
            color: white;
        }}
        
        .hover-card:hover {{
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }}
        
        .card-title {{
            color: {theme["primary"]};
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .nav-item {{
            padding: 8px 15px;
            border-radius: 5px;
            margin-bottom: 5px;
            cursor: pointer;
        }}
        
        .nav-item:hover {{
            background-color: rgba(29, 185, 84, 0.1);
        }}
        
        .nav-item.active {{
            background-color: rgba(29, 185, 84, 0.2);
            font-weight: bold;
        }}
        
        .tag {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 5px;
            margin-bottom: 5px;
        }}
        
        .tag.owasp {{
            background-color: rgba(187, 134, 252, 0.2);
            color: {theme["secondary"]};
        }}
        
        .tag.nist {{
            background-color: rgba(3, 218, 198, 0.2);
            color: {theme["accent"]};
        }}
        
        .tag.fairness {{
            background-color: rgba(255, 152, 0, 0.2);
            color: {theme["warning"]};
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            border-radius: 5px 5px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {theme["card_bg"]};
            border-bottom: 3px solid {theme["primary"]};
        }}
        
        .error-message {{
            background-color: #CF6679;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        </style>
        """
    except Exception as e:
        logger.error(f"Error loading CSS: {str(e)}")
        # Return minimal CSS as fallback
        return "<style>.error-message { background-color: #CF6679; color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; }</style>"

# Helper function to set page
def set_page(page_name):
    """Set the current page safely"""
    try:
        st.session_state.current_page = page_name
        logger.info(f"Navigation: Switched to {page_name} page")
    except Exception as e:
        logger.error(f"Error setting page to {page_name}: {str(e)}")
        display_error(f"Failed to navigate to {page_name}")

# Safe rerun function
def safe_rerun():
    """Safely rerun the app, handling different Streamlit versions"""
    try:
        st.rerun()  # For newer Streamlit versions
    except Exception as e1:
        try:
            st.experimental_rerun()  # For older Streamlit versions
        except Exception as e2:
            logger.error(f"Failed to rerun app: {str(e1)} then {str(e2)}")
            # Do nothing - at this point we can't fix it

# Error handling
def display_error(message):
    """Display error message to the user"""
    try:
        st.session_state.error_message = message
        logger.error(f"UI Error: {message}")
    except Exception as e:
        logger.critical(f"Failed to display error message: {str(e)}")

# Custom components
def card(title, content, card_type="default"):
    """Generate HTML card with error handling"""
    try:
        card_class = "card"
        if card_type == "warning":
            card_class += " warning-card"
        elif card_type == "error":
            card_class += " error-card"
        elif card_type == "success":
            card_class += " success-card"
        
        return f"""
        <div class="{card_class} hover-card">
            <div class="card-title">{title}</div>
            {content}
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering card: {str(e)}")
        return f"""
        <div class="card error-card">
            <div class="card-title">Error Rendering Card</div>
            <p>Failed to render card content: {str(e)}</p>
        </div>
        """

def metric_card(label, value, description="", prefix="", suffix=""):
    """Generate HTML metric card with error handling"""
    try:
        return f"""
        <div class="card hover-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{prefix}{value}{suffix}</div>
            <div style="font-size: 14px; opacity: 0.7;">{description}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"Error rendering metric card: {str(e)}")
        return f"""
        <div class="card error-card">
            <div class="metric-label">Error</div>
            <div class="metric-value">N/A</div>
            <div style="font-size: 14px; opacity: 0.7;">Failed to render metric: {str(e)}</div>
        </div>
        """

# Logo and header
def render_header():
    """Render the application header safely"""
    try:
        logo_html = """
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <div style="margin-right: 10px; font-size: 2.5rem;">🛡️</div>
            <div>
                <h1 style="margin-bottom: 0;">Synthetic Red Team Testing Agent</h1>
                <p style="opacity: 0.7;">Advanced Security Testing for AI Systems</p>
            </div>
        </div>
        """
        st.markdown(logo_html, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering header: {str(e)}")
        st.markdown("# 🛡️ Synthetic Red Team Testing Agent")

# Sidebar navigation - Fixed implementation
def sidebar_navigation():
    """Render the sidebar navigation with proper Streamlit buttons"""
    try:
        st.sidebar.markdown('<div class="sidebar-title">🧭 Navigation</div>', unsafe_allow_html=True)
        
        navigation_options = [
            {"icon": "🏠", "name": "Dashboard"},
            {"icon": "🎯", "name": "Target Management"},
            {"icon": "🧪", "name": "Test Configuration"},
            {"icon": "▶️", "name": "Run Assessment"},
            {"icon": "📊", "name": "Results Analyzer"},
            {"icon": "🔍", "name": "Ethical AI Testing"},
            {"icon": "🚀", "name": "High-Volume Testing"},
            {"icon": "⚙️", "name": "Settings"}
        ]
        
        for option in navigation_options:
            # Create a button for each navigation option
            if st.sidebar.button(
                f"{option['icon']} {option['name']}", 
                key=f"nav_{option['name']}",
                use_container_width=True,
                type="secondary" if st.session_state.current_page != option["name"] else "primary"
            ):
                set_page(option["name"])
                safe_rerun()
        
        # Theme toggle
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="sidebar-title">🎨 Appearance</div>', unsafe_allow_html=True)
        if st.sidebar.button("🔄 Toggle Theme", key="toggle_theme", use_container_width=True):
            st.session_state.current_theme = "light" if st.session_state.current_theme == "dark" else "dark"
            logger.info(f"Theme toggled to {st.session_state.current_theme}")
            safe_rerun()
        
        # System status
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="sidebar-title">📡 System Status</div>', unsafe_allow_html=True)
        
        if st.session_state.running_test:
            st.sidebar.success("⚡ Test Running")
        else:
            st.sidebar.info("⏸️ Idle")
        
        st.sidebar.markdown(f"🎯 Targets: {len(st.session_state.targets)}")
        
        # Active threads info
        if len(st.session_state.active_threads) > 0:
            st.sidebar.markdown(f"🧵 Active threads: {len(st.session_state.active_threads)}")
        
        # Add version info
        st.sidebar.markdown("---")
        st.sidebar.markdown("v1.0.0 | © 2025", unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering sidebar: {str(e)}")
        st.sidebar.error("Navigation Error")
        st.sidebar.markdown(f"Error: {str(e)}")

# Mock data functions with error handling
def get_mock_test_vectors():
    """Get mock test vector data with error handling"""
    try:
        return [
            {
                "id": "sql_injection",
                "name": "SQL Injection",
                "category": "owasp",
                "severity": "high"
            },
            {
                "id": "xss",
                "name": "Cross-Site Scripting",
                "category": "owasp",
                "severity": "medium"
            },
            {
                "id": "prompt_injection",
                "name": "Prompt Injection",
                "category": "owasp",
                "severity": "critical"
            },
            {
                "id": "insecure_output",
                "name": "Insecure Output Handling",
                "category": "owasp",
                "severity": "high"
            },
            {
                "id": "nist_governance",
                "name": "AI Governance",
                "category": "nist",
                "severity": "medium"
            },
            {
                "id": "nist_transparency",
                "name": "Transparency",
                "category": "nist",
                "severity": "medium"
            },
            {
                "id": "fairness_demographic",
                "name": "Demographic Parity",
                "category": "fairness",
                "severity": "high"
            },
            {
                "id": "privacy_gdpr",
                "name": "GDPR Compliance",
                "category": "privacy",
                "severity": "critical"
            },
            {
                "id": "jailbreaking",
                "name": "Jailbreaking Resistance",
                "category": "exploit",
                "severity": "critical"
            }
        ]
    except Exception as e:
        logger.error(f"Error getting mock test vectors: {str(e)}")
        display_error("Failed to load test vectors")
        return []  # Return empty list as fallback

def run_mock_test(target, test_vectors, duration=30):
    """Simulate running a test in the background with proper error handling"""
    try:
        # Initialize progress
        st.session_state.progress = 0
        st.session_state.vulnerabilities_found = 0
        st.session_state.running_test = True
        
        logger.info(f"Starting mock test against {target['name']} with {len(test_vectors)} test vectors")
        
        # Create mock results data structure
        results = {
            "summary": {
                "total_tests": 0,
                "vulnerabilities_found": 0,
                "risk_score": 0
            },
            "vulnerabilities": [],
            "test_details": {}
        }
        
        # Simulate test execution
        total_steps = 100
        step_sleep = duration / total_steps
        
        for i in range(total_steps):
            # Check if we should stop (for handling cancellations)
            if not st.session_state.running_test:
                logger.info("Test was cancelled")
                break
                
            time.sleep(step_sleep)
            st.session_state.progress = (i + 1) / total_steps
            
            # Occasionally "find" a vulnerability
            if random.random() < 0.2:  # 20% chance each step
                vector = random.choice(test_vectors)
                severity_weight = {"low": 1, "medium": 2, "high": 3, "critical": 5}
                weight = severity_weight.get(vector["severity"], 1)
                
                # Add vulnerability to results
                vulnerability = {
                    "id": f"VULN-{len(results['vulnerabilities']) + 1}",
                    "test_vector": vector["id"],
                    "test_name": vector["name"],
                    "severity": vector["severity"],
                    "details": f"Mock vulnerability found in {target['name']} using {vector['name']} test vector.",
                    "timestamp": datetime.now().isoformat()
                }
                results["vulnerabilities"].append(vulnerability)
                
                # Update counters
                st.session_state.vulnerabilities_found += 1
                results["summary"]["vulnerabilities_found"] += 1
                results["summary"]["risk_score"] += weight
                
                logger.info(f"Found vulnerability: {vulnerability['id']} ({vulnerability['severity']})")
        
        # Complete the test results
        results["summary"]["total_tests"] = len(test_vectors) * 10  # Assume 10 variations per vector
        results["timestamp"] = datetime.now().isoformat()
        results["target"] = target["name"]
        
        logger.info(f"Test completed: {results['summary']['vulnerabilities_found']} vulnerabilities found")
        
        # Set the results in session state
        st.session_state.test_results = results
        return results
    
    except Exception as e:
        error_details = {
            "error": True,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        logger.error(f"Error in test execution: {str(e)}")
        logger.debug(traceback.format_exc())
        
        # Create error result
        st.session_state.error_message = f"Test execution failed: {str(e)}"
        return error_details
    
    finally:
        # Always ensure we reset the running state
        st.session_state.running_test = False

# Page renderers
def render_dashboard():
    """Render the dashboard page safely"""
    try:
        st.markdown("""
        <h2>Dashboard</h2>
        <p>Overview of your AI security testing environment</p>
        """, unsafe_allow_html=True)
        
        # Quick stats in a row of cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(metric_card("Targets", len(st.session_state.targets), "Configured AI models"), unsafe_allow_html=True)
        
        with col2:
            st.markdown(metric_card("Test Vectors", "9", "Available security tests"), unsafe_allow_html=True)
        
        with col3:
            vuln_count = len(st.session_state.test_results.get("vulnerabilities", [])) if st.session_state.test_results else 0
            st.markdown(metric_card("Vulnerabilities", vuln_count, "Identified issues"), unsafe_allow_html=True)
        
        with col4:
            risk_score = st.session_state.test_results.get("summary", {}).get("risk_score", 0) if st.session_state.test_results else 0
            st.markdown(metric_card("Risk Score", risk_score, "Overall security risk"), unsafe_allow_html=True)
        
        # Recent activity and status
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("<h3>Recent Activity</h3>", unsafe_allow_html=True)
            
            if not st.session_state.test_results:
                st.markdown(card("No Recent Activity", "Run your first assessment to generate results.", "warning"), unsafe_allow_html=True)
            else:
                # Show the most recent vulnerabilities
                vulnerabilities = st.session_state.test_results.get("vulnerabilities", [])
                if vulnerabilities:
                    for vuln in vulnerabilities[:3]:  # Show top 3
                        severity_color = {
                            "low": get_theme()["text"],
                            "medium": get_theme()["warning"],
                            "high": get_theme()["warning"],
                            "critical": get_theme()["error"]
                        }.get(vuln["severity"], get_theme()["text"])
                        
                        st.markdown(f"""
                        <div class="card hover-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div class="card-title">{vuln["id"]}: {vuln["test_name"]}</div>
                                <div style="color: {severity_color}; font-weight: bold; text-transform: uppercase; font-size: 12px;">
                                    {vuln["severity"]}
                                </div>
                            </div>
                            <p>{vuln["details"]}</p>
                            <div style="font-size: 12px; opacity: 0.7;">Found in: {vuln["timestamp"]}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("<h3>System Status</h3>", unsafe_allow_html=True)
            
            if st.session_state.running_test:
                st.markdown(card("Test in Progress", f"""
                <div style="margin-bottom: 10px;">
                    <div style="margin-bottom: 5px;">Progress:</div>
                    <div style="height: 10px; background-color: rgba(255,255,255,0.1); border-radius: 5px;">
                        <div style="height: 10px; width: {st.session_state.progress*100}%; background-color: {get_theme()["primary"]}; border-radius: 5px;"></div>
                    </div>
                    <div style="text-align: right; font-size: 12px; margin-top: 5px;">{int(st.session_state.progress*100)}%</div>
                </div>
                <div>Vulnerabilities found: {st.session_state.vulnerabilities_found}</div>
                """, "warning"), unsafe_allow_html=True)
            else:
                st.markdown(card("System Ready", """
                <p>All systems operational and ready to run assessments.</p>
                <div style="display: flex; align-items: center;">
                    <div style="width: 10px; height: 10px; background-color: #4CAF50; border-radius: 50%; margin-right: 5px;"></div>
                    <div>API Connection: Active</div>
                </div>
                """, "success"), unsafe_allow_html=True)
        
        # Test vector overview
        st.markdown("<h3>Test Vector Overview</h3>", unsafe_allow_html=True)
        
        # Create a radar chart for test coverage
        try:
            test_vectors = get_mock_test_vectors()
            categories = list(set(tv["category"] for tv in test_vectors))
            
            # Count test vectors by category
            category_counts = {}
            for cat in categories:
                category_counts[cat] = sum(1 for tv in test_vectors if tv["category"] == cat)
            
            # Create the data for the radar chart
            fig = go.Figure()
            
            primary_color = get_theme()["primary"]
            r_value = int(primary_color[1:3], 16) if len(primary_color) >= 7 else 29
            g_value = int(primary_color[3:5], 16) if len(primary_color) >= 7 else 185
            b_value = int(primary_color[5:7], 16) if len(primary_color) >= 7 else 84
            
            fig.add_trace(go.Scatterpolar(
                r=list(category_counts.values()),
                theta=list(category_counts.keys()),
                fill='toself',
                fillcolor=f'rgba({r_value}, {g_value}, {b_value}, 0.3)',
                line=dict(color=primary_color),
                name='Test Coverage'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(category_counts.values()) + 1]
                    )
                ),
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=get_theme()["text"])
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logger.error(f"Error rendering radar chart: {str(e)}")
            st.error("Failed to render radar chart")
        
        # Quick actions with Streamlit buttons
        st.markdown("<h3>Quick Actions</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ Add New Target", use_container_width=True, key="dashboard_add_target"):
                set_page("Target Management")
                safe_rerun()
        
        with col2:
            if st.button("🧪 Run Assessment", use_container_width=True, key="dashboard_run_assessment"):
                set_page("Run Assessment")
                safe_rerun()
        
        with col3:
            if st.button("📊 View Results", use_container_width=True, key="dashboard_view_results"):
                set_page("Results Analyzer")
                safe_rerun()
                
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error rendering dashboard: {str(e)}")

def render_target_management():
    """Render the target management page safely"""
    try:
        st.markdown("""
        <h2>Target Management</h2>
        <p>Add and configure AI models to test</p>
        """, unsafe_allow_html=True)
        
        # Show existing targets
        if st.session_state.targets:
            st.markdown("<h3>Your Targets</h3>", unsafe_allow_html=True)
            
            # Use columns for better layout
            cols = st.columns(3)
            for i, target in enumerate(st.session_state.targets):
                col = cols[i % 3]
                with col:
                    with st.container():
                        st.markdown(f"### {target['name']}")
                        st.markdown(f"**Endpoint:** {target['endpoint']}")
                        st.markdown(f"**Type:** {target.get('type', 'Unknown')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Edit", key=f"edit_target_{i}", use_container_width=True):
                                # In a real app, this would open an edit dialog
                                st.info("Edit functionality would open here")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_target_{i}", use_container_width=True):
                                # Remove the target
                                st.session_state.targets.pop(i)
                                st.success(f"Target '{target['name']}' deleted")
                                safe_rerun()
        
        # Add new target form
        st.markdown("<h3>Add New Target</h3>", unsafe_allow_html=True)
        
        with st.form("add_target_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                target_name = st.text_input("Target Name")
                target_endpoint = st.text_input("API Endpoint URL")
                target_type = st.selectbox("Model Type", ["LLM", "Content Filter", "Embedding", "Classification", "Other"])
            
            with col2:
                api_key = st.text_input("API Key", type="password")
                target_description = st.text_area("Description")
            
            submit_button = st.form_submit_button("Add Target")
            
            if submit_button:
                try:
                    if not target_name or not target_endpoint:
                        st.error("Name and endpoint are required")
                    else:
                        new_target = {
                            "name": target_name,
                            "endpoint": target_endpoint,
                            "type": target_type,
                            "api_key": api_key,
                            "description": target_description
                        }
                        st.session_state.targets.append(new_target)
                        st.success(f"Target '{target_name}' added successfully!")
                        logger.info(f"Added new target: {target_name}")
                        safe_rerun()
                except Exception as e:
                    logger.error(f"Error adding target: {str(e)}")
                    st.error(f"Failed to add target: {str(e)}")
        
        # Import/Export
        st.markdown("<h3>Import/Export Targets</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file = st.file_uploader("Import Targets", type=["json"], key="target_import")
            
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read()
                    imported_targets = json.loads(content)
                    
                    if isinstance(imported_targets, list):
                        # Validate the imported targets
                        valid_targets = []
                        for target in imported_targets:
                            if isinstance(target, dict) and "name" in target and "endpoint" in target:
                                valid_targets.append(target)
                        
                        if valid_targets:
                            st.session_state.targets.extend(valid_targets)
                            st.success(f"Successfully imported {len(valid_targets)} targets")
                            logger.info(f"Imported {len(valid_targets)} targets")
                            safe_rerun()
                        else:
                            st.error("No valid targets found in the imported file")
                    else:
                        st.error("Invalid JSON format. Expected a list of targets.")
                except Exception as e:
                    logger.error(f"Error importing targets: {str(e)}")
                    st.error(f"Failed to import targets: {str(e)}")
        
        with col2:
            if st.session_state.targets:
                try:
                    targets_json = json.dumps(st.session_state.targets, indent=2)
                    st.download_button(
                        label="Export Targets",
                        data=targets_json,
                        file_name=f"targets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key="target_export"
                    )
                except Exception as e:
                    logger.error(f"Error exporting targets: {str(e)}")
                    st.error(f"Failed to export targets: {str(e)}")
            else:
                st.button("Export Targets", disabled=True, key="export_disabled")
    
    except Exception as e:
        logger.error(f"Error rendering target management: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in target management: {str(e)}")

def render_test_configuration():
    """Render the test configuration page safely"""
    try:
        st.markdown("""
        <h2>Test Configuration</h2>
        <p>Customize your security assessment</p>
        """, unsafe_allow_html=True)
        
        # Test vector selection
        test_vectors = get_mock_test_vectors()
        
        # Group by category
        categories = {}
        for tv in test_vectors:
            if tv["category"] not in categories:
                categories[tv["category"]] = []
            categories[tv["category"]].append(tv)
        
        # Create tabs for each category
        try:
            tabs = st.tabs(list(categories.keys()))
            
            for i, (category, tab) in enumerate(zip(categories.keys(), tabs)):
                with tab:
                    st.markdown(f"<h3>{category.upper()} Test Vectors</h3>", unsafe_allow_html=True)
                    
                    # Create a list of test vectors
                    for j, tv in enumerate(categories[category]):
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            
                            with col1:
                                st.markdown(f"### {tv['name']}")
                                st.markdown(f"**Severity:** {tv['severity'].upper()}")
                                st.markdown(f"**Category:** {tv['category'].upper()}")
                            
                            with col2:
                                # Use a checkbox to enable/disable
                                is_enabled = st.checkbox("Enable", value=True, key=f"enable_{tv['id']}")
        except Exception as e:
            logger.error(f"Error rendering test vector tabs: {str(e)}")
            st.error(f"Failed to render test vectors: {str(e)}")
            
            # Fallback: Show test vectors in a simple list
            st.markdown("### Test Vectors")
            for tv in test_vectors:
                st.markdown(f"- **{tv['name']}** ({tv['category']}, {tv['severity']})")
        
        # Advanced configuration
        st.markdown("<h3>Advanced Configuration</h3>", unsafe_allow_html=True)
        
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                test_duration = st.slider("Maximum Test Duration (minutes)", 5, 120, 30, key="test_duration")
                test_variations = st.number_input("Test Variations per Vector", 1, 1000, 10, key="test_variations")
                concurrency = st.slider("Concurrency Level", 1, 16, 4, key="concurrency")
            
            with col2:
                test_profile = st.selectbox("Test Profile", ["Standard", "Thorough", "Extreme", "Custom"], key="test_profile")
                focus_area = st.radio("Focus Area", ["General Security", "AI Safety", "Compliance", "All"], key="focus_area")
                save_detailed = st.checkbox("Save Detailed Results", value=True, key="save_detailed")
        except Exception as e:
            logger.error(f"Error rendering advanced configuration: {str(e)}")
            st.error(f"Failed to render advanced configuration: {str(e)}")
        
        # Save configuration button
        if st.button("Save Configuration", key="save_test_config"):
            st.success("Test configuration saved successfully!")
            logger.info("Test configuration saved")
        
        # Show configuration summary
        st.markdown("<h3>Configuration Summary</h3>", unsafe_allow_html=True)
        
        try:
            # Count enabled test vectors
            enabled_count = sum(1 for tv in test_vectors if st.session_state.get(f"enable_{tv['id']}", True))
            
            st.markdown(card("Test Parameters", f"""
            <ul>
                <li><strong>Enabled Test Vectors:</strong> {enabled_count} of {len(test_vectors)}</li>
                <li><strong>Estimated Duration:</strong> {test_duration} minutes</li>
                <li><strong>Total Test Cases:</strong> {enabled_count * test_variations} ({enabled_count} vectors × {test_variations} variations)</li>
                <li><strong>Profile:</strong> {test_profile}</li>
                <li><strong>Focus Area:</strong> {focus_area}</li>
            </ul>
            """), unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error rendering configuration summary: {str(e)}")
            st.error(f"Failed to render configuration summary: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering test configuration: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in test configuration: {str(e)}")

def render_run_assessment():
    """Render the run assessment page safely"""
    try:
        st.markdown("""
        <h2>Run Assessment</h2>
        <p>Execute security tests against your targets</p>
        """, unsafe_allow_html=True)
        
        # Check if targets exist
        if not st.session_state.targets:
            st.warning("No targets configured. Please add a target first.")
            if st.button("Add Target", key="run_add_target"):
                set_page("Target Management")
                safe_rerun()
            return
        
        # Check if a test is already running
        if st.session_state.running_test:
            # Show progress
            progress_placeholder = st.empty()
            with progress_placeholder.container():
                progress_bar = st.progress(st.session_state.progress)
                st.markdown(f"**Progress:** {int(st.session_state.progress*100)}%")
                st.markdown(f"**Vulnerabilities found:** {st.session_state.vulnerabilities_found}")
            
            # Stop button
            if st.button("Stop Test", key="stop_test"):
                st.session_state.running_test = False
                logger.info("Test stopped by user")
                st.warning("Test stopped by user")
                safe_rerun()
        else:
            # Test configuration
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h3>Select Target</h3>", unsafe_allow_html=True)
                target_options = [t["name"] for t in st.session_state.targets]
                selected_target = st.selectbox("Target", target_options, key="run_target")
            
            with col2:
                st.markdown("<h3>Test Parameters</h3>", unsafe_allow_html=True)
                test_duration = st.slider("Test Duration (seconds)", 5, 60, 30, key="run_duration", 
                                         help="For demonstration purposes, we're using seconds. In a real system, this would be minutes.")
            
            # Get test vectors
            test_vectors = get_mock_test_vectors()
            
            # Show test vector selection
            st.markdown("<h3>Select Test Vectors</h3>", unsafe_allow_html=True)
            
            # Group by category
            categories = {}
            for tv in test_vectors:
                if tv["category"] not in categories:
                    categories[tv["category"]] = []
                categories[tv["category"]].append(tv)
            
            # Create columns for each category
            try:
                cols = st.columns(len(categories))
                
                selected_vectors = []
                for i, (category, col) in enumerate(zip(categories.keys(), cols)):
                    with col:
                        st.markdown(f"<div style='text-align: center; text-transform: uppercase; font-weight: bold; margin-bottom: 10px;'>{category}</div>", unsafe_allow_html=True)
                        
                        for tv in categories[category]:
                            if st.checkbox(tv["name"], value=True, key=f"run_tv_{tv['id']}"):
                                selected_vectors.append(tv)
            except Exception as e:
                logger.error(f"Error rendering test vector selection: {str(e)}")
                st.error(f"Failed to render test vector selection: {str(e)}")
                
                # Fallback: Use multiselect
                st.markdown("### Select Test Vectors")
                vector_names = [tv["name"] for tv in test_vectors]
                selected_names = st.multiselect("Test Vectors", vector_names, default=vector_names, key="fallback_vectors")
                selected_vectors = [tv for tv in test_vectors if tv["name"] in selected_names]
            
            # Run test button
            if st.button("Run Assessment", use_container_width=True, type="primary", key="start_assessment"):
                try:
                    if not selected_vectors:
                        st.error("Please select at least one test vector")
                    else:
                        # Find the selected target object
                        target = next((t for t in st.session_state.targets if t["name"] == selected_target), None)
                        
                        if target:
                            # Start the test in a background thread
                            test_thread = threading.Thread(
                                target=run_mock_test,
                                args=(target, selected_vectors, test_duration)
                            )
                            test_thread.daemon = True
                            test_thread.start()
                            
                            # Track the thread
                            st.session_state.active_threads.append(test_thread)
                            
                            st.session_state.running_test = True
                            logger.info(f"Started test against {target['name']} with {len(selected_vectors)} vectors")
                            st.success("Test started!")
                            safe_rerun()
                        else:
                            st.error("Selected target not found")
                except Exception as e:
                    logger.error(f"Error starting test: {str(e)}")
                    st.error(f"Failed to start test: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering run assessment: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in run assessment: {str(e)}")

def render_results_analyzer():
    """Render the results analyzer page safely"""
    try:
        st.markdown("""
        <h2>Results Analyzer</h2>
        <p>Explore and analyze security assessment results</p>
        """, unsafe_allow_html=True)
        
        # Check if there are results to display
        if not st.session_state.test_results:
            st.warning("No Results Available - Run an assessment to generate results.")
            
            if st.button("Go to Run Assessment", key="results_goto_run"):
                set_page("Run Assessment")
                safe_rerun()
            return
        
        # Results summary
        results = st.session_state.test_results
        
        # Check if results contains an error
        if results.get("error", False):
            st.error(f"The last test resulted in an error: {results.get('error_message', 'Unknown error')}")
            if st.button("Clear Error and Run New Test", key="clear_error"):
                st.session_state.test_results = {}
                set_page("Run Assessment")
                safe_rerun()
            return
        
        vulnerabilities = results.get("vulnerabilities", [])
        summary = results.get("summary", {})
        
        # Create header with summary metrics
        st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <h3>Assessment Results: {results.get("target", "Unknown Target")}</h3>
            <div style="opacity: 0.7;">Completed: {results.get("timestamp", "Unknown")}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Tests Run", summary.get("total_tests", 0))
        
        with col2:
            st.metric("Vulnerabilities", summary.get("vulnerabilities_found", 0))
        
        with col3:
            st.metric("Risk Score", summary.get("risk_score", 0))
        
        # Visualizations
        st.markdown("<h3>Vulnerability Overview</h3>", unsafe_allow_html=True)
        
        # Prepare data for charts
        if vulnerabilities:
            try:
                # Count vulnerabilities by severity
                severity_counts = {}
                for vuln in vulnerabilities:
                    severity = vuln.get("severity", "unknown")
                    if severity not in severity_counts:
                        severity_counts[severity] = 0
                    severity_counts[severity] += 1
                
                # Count vulnerabilities by test vector
                vector_counts = {}
                for vuln in vulnerabilities:
                    vector = vuln.get("test_name", "unknown")
                    if vector not in vector_counts:
                        vector_counts[vector] = 0
                    vector_counts[vector] += 1
                
                # Create two columns for charts
                col1, col2 = st.columns(2)
                
                with col1:
                    # Create pie chart for severity distribution
                    labels = list(severity_counts.keys())
                    values = list(severity_counts.values())
                    
                    colors = {
                        "low": "green",
                        "medium": "yellow",
                        "high": "orange",
                        "critical": "red",
                        "unknown": "gray"
                    }
                    
                    fig = px.pie(
                        names=labels,
                        values=values,
                        title="Vulnerabilities by Severity",
                        color=labels,
                        color_discrete_map={label: colors.get(label, "gray") for label in labels}
                    )
                    
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color=get_theme()["text"])
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Create bar chart for test vector distribution
                    fig = px.bar(
                        x=list(vector_counts.keys()),
                        y=list(vector_counts.values()),
                        title="Vulnerabilities by Test Vector",
                        labels={"x": "Test Vector", "y": "Vulnerabilities"},
                        color_discrete_sequence=[get_theme()["primary"]]
                    )
                    
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color=get_theme()["text"])
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                logger.error(f"Error rendering charts: {str(e)}")
                st.error(f"Failed to render charts: {str(e)}")
        
        # Detailed vulnerability listing
        st.markdown("<h3>Detailed Findings</h3>", unsafe_allow_html=True)
        
        if vulnerabilities:
            try:
                # Create tabs for different severity levels
                severities = list(set(vuln["severity"] for vuln in vulnerabilities if "severity" in vuln))
                severities.sort(key=lambda s: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(s, 4))
                
                # Add "All" tab at the beginning
                tabs = st.tabs(["All"] + severities)
                
                with tabs[0]:  # "All" tab
                    for i, vuln in enumerate(vulnerabilities):
                        severity = vuln.get("severity", "unknown")
                        severity_emoji = {
                            "low": "🟢",
                            "medium": "🟡",
                            "high": "🟠",
                            "critical": "🔴",
                            "unknown": "⚪"
                        }.get(severity, "⚪")
                        
                        with st.expander(f"{severity_emoji} {vuln.get('id', 'Unknown')}: {vuln.get('test_name', 'Unknown Test')}"):
                            st.markdown(f"**Severity:** {severity.upper()}")
                            st.markdown(f"**Details:** {vuln.get('details', 'No details available.')}")
                            st.markdown(f"**Found:** {vuln.get('timestamp', 'Unknown')}")
                
                # Create content for each severity tab
                for i, severity in enumerate(severities):
                    with tabs[i+1]:  # +1 because "All" is the first tab
                        severity_vulns = [v for v in vulnerabilities if v.get("severity") == severity]
                        
                        for j, vuln in enumerate(severity_vulns):
                            severity_emoji = {
                                "low": "🟢",
                                "medium": "🟡",
                                "high": "🟠",
                                "critical": "🔴",
                                "unknown": "⚪"
                            }.get(severity, "⚪")
                            
                            with st.expander(f"{severity_emoji} {vuln.get('id', 'Unknown')}: {vuln.get('test_name', 'Unknown Test')}"):
                                st.markdown(f"**Severity:** {severity.upper()}")
                                st.markdown(f"**Details:** {vuln.get('details', 'No details available.')}")
                                st.markdown(f"**Found:** {vuln.get('timestamp', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error rendering vulnerability details: {str(e)}")
                st.error(f"Failed to render vulnerability details: {str(e)}")
                
                # Fallback: Simple list of vulnerabilities
                for vuln in vulnerabilities:
                    st.markdown(f"- **{vuln.get('id', 'Unknown')}**: {vuln.get('details', 'No details')}")
        else:
            st.info("No vulnerabilities were found in this assessment.")
        
        # Export results
        st.markdown("<h3>Export Results</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                st.download_button(
                    label="Download JSON Report",
                    data=json.dumps(results, indent=2),
                    file_name=f"security_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_json"
                )
            except Exception as e:
                logger.error(f"Error preparing JSON download: {str(e)}")
                st.error(f"Failed to prepare JSON download: {str(e)}")
        
        with col2:
            try:
                if vulnerabilities:
                    # Convert vulnerabilities to DataFrame
                    df = pd.DataFrame(vulnerabilities)
                    csv = df.to_csv(index=False)
                    
                    st.download_button(
                        label="Download CSV Vulnerabilities",
                        data=csv,
                        file_name=f"vulnerabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
                else:
                    st.button("Download CSV Vulnerabilities", disabled=True, key="download_csv_disabled")
            except Exception as e:
                logger.error(f"Error preparing CSV download: {str(e)}")
                st.error(f"Failed to prepare CSV download: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering results analyzer: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in results analyzer: {str(e)}")

def render_ethical_ai_testing():
    """Render the ethical AI testing page safely"""
    try:
        st.markdown("""
        <h2>Ethical AI Testing</h2>
        <p>Comprehensive assessment of AI systems against OWASP, NIST, and ethical guidelines</p>
        """, unsafe_allow_html=True)
        
        # Check if targets exist
        if not st.session_state.targets:
            st.warning("No targets configured. Please add a target first.")
            if st.button("Add Target", key="ethical_add_target"):
                set_page("Target Management")
                safe_rerun()
            return
        
        # Create tabs for different testing frameworks
        try:
            tabs = st.tabs(["OWASP LLM", "NIST Framework", "Fairness & Bias", "Privacy Compliance", "Synthetic Extreme"])
            
            with tabs[0]:
                st.markdown("<h3>OWASP LLM Top 10 Testing</h3>", unsafe_allow_html=True)
                
                st.markdown("""
                This module tests AI systems against the OWASP Top 10 for Large Language Model Applications:
                
                - Prompt Injection
                - Insecure Output Handling
                - Training Data Poisoning
                - Model Denial of Service
                - Supply Chain Vulnerabilities
                - Sensitive Information Disclosure
                - Insecure Plugin Design
                - Excessive Agency
                - Overreliance
                - Model Theft
                """)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    target_options = [t["name"] for t in st.session_state.targets]
                    st.selectbox("Select Target", target_options, key="owasp_target")
                
                with col2:
                    st.multiselect("Select Tests", [
                        "Prompt Injection",
                        "Insecure Output Handling",
                        "Sensitive Information Disclosure",
                        "Excessive Agency"
                    ], default=["Prompt Injection", "Insecure Output Handling"], key="owasp_tests")
                
                if st.button("Run OWASP LLM Tests", key="run_owasp"):
                    st.info("OWASP LLM testing would start here")
                    # In a real implementation, this would start the tests
            
            with tabs[1]:
                st.markdown("<h3>NIST AI Risk Management Framework</h3>", unsafe_allow_html=True)
                
                st.markdown("""
                This module evaluates AI systems against the NIST AI Risk Management Framework:
                
                - Governance
                - Mapping
                - Measurement
                - Management
                """)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    target_options = [t["name"] for t in st.session_state.targets]
                    st.selectbox("Select Target", target_options, key="nist_target")
                
                with col2:
                    st.multiselect("Select Framework Components", [
                        "Governance",
                        "Mapping",
                        "Measurement",
                        "Management"
                    ], default=["Governance", "Management"], key="nist_components")
                
                if st.button("Run NIST Framework Assessment", key="run_nist"):
                    st.info("NIST Framework assessment would start here")
            
            with tabs[2]:
                st.markdown("<h3>Fairness & Bias Testing</h3>", unsafe_allow_html=True)
                
                st.markdown("""
                This module tests AI systems for fairness and bias issues:
                
                - Demographic Parity
                - Equal Opportunity
                - Disparate Impact
                - Representation Bias
                """)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    target_options = [t["name"] for t in st.session_state.targets]
                    st.selectbox("Select Target", target_options, key="fairness_target")
                
                with col2:
                    st.multiselect("Select Fairness Metrics", [
                        "Demographic Parity",
                        "Equal Opportunity",
                        "Disparate Impact",
                        "Representation Bias"
                    ], default=["Demographic Parity"], key="fairness_metrics")
                
                st.text_area("Demographic Groups (one per line)", "Group A\nGroup B\nGroup C\nGroup D", key="demographic_groups")
                
                if st.button("Run Fairness Assessment", key="run_fairness"):
                    st.info("Fairness assessment would start here")
            
            with tabs[3]:
                st.markdown("<h3>Privacy Compliance Testing</h3>", unsafe_allow_html=True)
                
                st.markdown("""
                This module tests AI systems for compliance with privacy regulations:
                
                - GDPR
                - CCPA
                - HIPAA
                - PIPEDA
                """)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    target_options = [t["name"] for t in st.session_state.targets]
                    st.selectbox("Select Target", target_options, key="privacy_target")
                
                with col2:
                    st.multiselect("Select Regulations", [
                        "GDPR",
                        "CCPA",
                        "HIPAA",
                        "PIPEDA"
                    ], default=["GDPR"], key="privacy_regulations")
                
                if st.button("Run Privacy Assessment", key="run_privacy"):
                    st.info("Privacy assessment would start here")
            
            with tabs[4]:
                st.markdown("<h3>Synthetic Extreme Testing</h3>", unsafe_allow_html=True)
                
                st.markdown("""
                This module performs rigorous synthetic testing focusing on AI-specific vulnerabilities:
                
                - Jailbreaking
                - Advanced Prompt Injection
                - Data Extraction
                - Boundary Testing
                """)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    target_options = [t["name"] for t in st.session_state.targets]
                    st.selectbox("Select Target", target_options, key="extreme_target")
                
                with col2:
                    st.multiselect("Select Techniques", [
                        "Jailbreaking",
                        "Advanced Prompt Injection",
                        "Data Extraction",
                        "Boundary Testing"
                    ], default=["Jailbreaking"], key="extreme_techniques")
                
                st.slider("Testing Intensity", 1, 10, 5, key="testing_intensity")
                
                if st.button("Run Extreme Testing", key="run_extreme"):
                    st.info("Synthetic extreme testing would start here")
        
        except Exception as e:
            logger.error(f"Error rendering ethical AI tabs: {str(e)}")
            st.error(f"Failed to render ethical AI testing interface: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering ethical AI testing: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in ethical AI testing: {str(e)}")

def render_high_volume_testing():
    """Render the high-volume testing page safely"""
    try:
        st.markdown("""
        <h2>High-Volume Testing</h2>
        <p>Autonomous, high-throughput testing for AI systems</p>
        """, unsafe_allow_html=True)
        
        # Check if targets exist
        if not st.session_state.targets:
            st.warning("No targets configured. Please add a target first.")
            if st.button("Add Target", key="highvol_add_target"):
                set_page("Target Management")
                safe_rerun()
            return
        
        # Configuration section
        st.markdown("<h3>Testing Configuration</h3>", unsafe_allow_html=True)
        
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                target_options = [t["name"] for t in st.session_state.targets]
                st.selectbox("Select Target", target_options, key="highvol_target")
                
                total_tests = st.slider("Total Tests (thousands)", 10, 1000, 100, key="highvol_tests")
                
                max_runtime = st.number_input("Max Runtime (hours)", 1, 24, 3, key="highvol_runtime")
            
            with col2:
                st.multiselect("Test Vectors", [
                    "Prompt Injection",
                    "Jailbreaking",
                    "Data Extraction",
                    "Input Manipulation",
                    "Boundary Testing"
                ], default=["Prompt Injection", "Jailbreaking"], key="highvol_vectors")
                
                parallelism = st.selectbox("Parallelism", ["Low (4 workers)", "Medium (8 workers)", "High (16 workers)", "Extreme (32 workers)"], key="highvol_parallel")
                
                save_only_vulns = st.checkbox("Save Only Vulnerabilities", value=True, key="highvol_save_vulns")
        except Exception as e:
            logger.error(f"Error rendering high-volume configuration: {str(e)}")
            st.error(f"Failed to render high-volume testing configuration: {str(e)}")
        
        # Resource monitoring
        st.markdown("<h3>Resource Monitoring</h3>", unsafe_allow_html=True)
        
        try:
            col1, col2, col3 = st.columns(3)
            
            worker_count = {"Low (4 workers)": 4, "Medium (8 workers)": 8, "High (16 workers)": 16, "Extreme (32 workers)": 32}
            selected_workers = worker_count.get(st.session_state.get("highvol_parallel", "Medium (8 workers)"), 8)
            
            with col1:
                st.metric("Max Workers", selected_workers)
            
            with col2:
                st.metric("Rate Limit", "100 req/sec")
            
            with col3:
                st.metric("Memory Limit", "8 GB")
        except Exception as e:
            logger.error(f"Error rendering resource monitoring: {str(e)}")
            st.error(f"Failed to render resource monitoring: {str(e)}")
        
        # Start testing button
        if st.button("Start High-Volume Testing", type="primary", use_container_width=True, key="start_highvol"):
            try:
                st.success("High-volume testing started! This would typically run for several hours in a production environment.")
                
                # Create placeholders for progress updates
                progress_placeholder = st.empty()
                metrics_placeholder = st.empty()
                
                # Simulate progress updates
                for i in range(101):
                    # Check if the page has been navigated away from
                    if st.session_state.current_page != "High-Volume Testing":
                        break
                    
                    with progress_placeholder:
                        st.progress(i / 100)
                    
                    # Update metrics every 10%
                    if i % 10 == 0:
                        with metrics_placeholder:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Tests Completed", f"{i * 1000:,}")
                            with col2:
                                vulnerabilities = int(i * 1000 * 0.02)  # 2% find rate
                                st.metric("Vulnerabilities", f"{vulnerabilities:,}")
                            with col3:
                                st.metric("Tests/Second", f"{random.randint(80, 120):,}")
                    
                    time.sleep(0.05)  # Just for demonstration
                
                # Remove progress indicators
                progress_placeholder.empty()
                
                # Show completion message
                st.success("Testing completed! 100,000 tests executed, 2,000 vulnerabilities identified.")
                
                # Sample results visualization
                st.markdown("<h3>Results Overview</h3>", unsafe_allow_html=True)
                
                # Generate some mock data
                vector_names = ["Prompt Injection", "Jailbreaking", "Data Extraction", "Input Manipulation", "Boundary Testing"]
                vulnerability_counts = [random.randint(200, 600) for _ in range(5)]
                
                # Create bar chart
                fig = px.bar(
                    x=vector_names,
                    y=vulnerability_counts,
                    labels={"x": "Test Vector", "y": "Vulnerabilities Found"},
                    color=vulnerability_counts,
                    color_continuous_scale="Viridis"
                )
                
                fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=get_theme()["text"])
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                logger.error(f"Error in high-volume testing simulation: {str(e)}")
                st.error(f"Error in high-volume testing: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering high-volume testing: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in high-volume testing: {str(e)}")

def render_settings():
    """Render the settings page safely"""
    try:
        st.markdown("""
        <h2>Settings</h2>
        <p>Configure application settings and preferences</p>
        """, unsafe_allow_html=True)
        
        # Theme settings
        st.markdown("<h3>Theme Settings</h3>", unsafe_allow_html=True)
        
        theme_option = st.radio("Theme", ["Dark", "Light"], index=0 if st.session_state.current_theme == "dark" else 1, key="settings_theme")
        if theme_option == "Dark" and st.session_state.current_theme != "dark":
            st.session_state.current_theme = "dark"
            logger.info("Theme set to dark")
            safe_rerun()
        elif theme_option == "Light" and st.session_state.current_theme != "light":
            st.session_state.current_theme = "light"
            logger.info("Theme set to light")
            safe_rerun()
        
        # API settings
        st.markdown("<h3>API Settings</h3>", unsafe_allow_html=True)
        
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                api_base_url = st.text_input("API Base URL", "https://api.example.com/v1", key="api_base_url")
            
            with col2:
                default_api_key = st.text_input("Default API Key", type="password", key="default_api_key")
            
            # Save API settings
            if st.button("Save API Settings", key="save_api"):
                st.success("API settings saved successfully!")
                logger.info("API settings updated")
        except Exception as e:
            logger.error(f"Error rendering API settings: {str(e)}")
            st.error(f"Failed to render API settings: {str(e)}")
        
        # Testing settings
        st.markdown("<h3>Testing Settings</h3>", unsafe_allow_html=True)
        
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                default_duration = st.number_input("Default Test Duration (minutes)", 5, 120, 30, key="default_duration")
                request_timeout = st.number_input("Request Timeout (seconds)", 1, 60, 10, key="request_timeout")
            
            with col2:
                max_concurrent = st.number_input("Maximum Concurrent Tests", 1, 32, 4, key="max_concurrent_tests")
                save_logs = st.checkbox("Save Detailed Logs", value=True, key="save_detailed_logs")
            
            # Save testing settings
            if st.button("Save Testing Settings", key="save_testing"):
                st.success("Testing settings saved successfully!")
                logger.info("Testing settings updated")
        except Exception as e:
            logger.error(f"Error rendering testing settings: {str(e)}")
            st.error(f"Failed to render testing settings: {str(e)}")
        
        # Notifications
        st.markdown("<h3>Notifications</h3>", unsafe_allow_html=True)
        
        try:
            email_notifications = st.checkbox("Email Notifications", value=False, key="email_notifications")
            
            if email_notifications:
                email_address = st.text_input("Email Address", key="notification_email")
                notification_events = st.multiselect("Notify On", ["Test Completion", "Critical Vulnerability", "Error"], default=["Test Completion", "Critical Vulnerability"], key="notification_events")
            
            # Save notification settings
            if st.button("Save Notification Settings", key="save_notifications"):
                st.success("Notification settings saved successfully!")
                logger.info("Notification settings updated")
        except Exception as e:
            logger.error(f"Error rendering notification settings: {str(e)}")
            st.error(f"Failed to render notification settings: {str(e)}")
        
        # System information
        st.markdown("<h3>System Information</h3>", unsafe_allow_html=True)
        
        try:
            # Get system info
            import platform
            
            system_info = f"""
            - Python Version: {platform.python_version()}
            - Operating System: {platform.system()} {platform.release()}
            - Streamlit Version: {st.__version__}
            - Application Version: 1.0.0
            """
            
            st.code(system_info)
        except Exception as e:
            logger.error(f"Error rendering system information: {str(e)}")
            st.error(f"Failed to render system information: {str(e)}")
        
        # Clear data button (with confirmation)
        st.markdown("<h3>Data Management</h3>", unsafe_allow_html=True)
        
        if st.button("Clear All Application Data", key="clear_data"):
            # Confirmation
            if st.checkbox("I understand this will reset all targets, results, and settings", key="confirm_clear"):
                try:
                    # Reset all session state (except current page and theme)
                    current_page = st.session_state.current_page
                    current_theme = st.session_state.current_theme
                    
                    for key in list(st.session_state.keys()):
                        if key not in ['current_page', 'current_theme']:
                            del st.session_state[key]
                    
                    # Restore page and theme
                    st.session_state.current_page = current_page
                    st.session_state.current_theme = current_theme
                    
                    # Reinitialize session state
                    initialize_session_state()
                    
                    st.success("All application data has been cleared!")
                    logger.info("Application data cleared")
                    safe_rerun()
                except Exception as e:
                    logger.error(f"Error clearing application data: {str(e)}")
                    st.error(f"Failed to clear application data: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error rendering settings: {str(e)}")
        logger.debug(traceback.format_exc())
        st.error(f"Error in settings: {str(e)}")

# Main application
def main():
    """Main application entry point with error handling"""
    try:
        # Initialize session state
        initialize_session_state()
        
        # Clean up threads
        cleanup_threads()
        
        # Apply CSS
        st.markdown(load_css(), unsafe_allow_html=True)
        
        # Show error message if exists
        if st.session_state.error_message:
            st.markdown(f"""
            <div class="error-message">
                <strong>Error:</strong> {st.session_state.error_message}
            </div>
            """, unsafe_allow_html=True)
            
            # Add button to clear error
            if st.button("Clear Error"):
                st.session_state.error_message = None
                safe_rerun()
        
        # Render sidebar
        sidebar_navigation()
        
        # Render header
        render_header()
        
        # Render content based on current page
        if st.session_state.current_page == "Dashboard":
            render_dashboard()
        elif st.session_state.current_page == "Target Management":
            render_target_management()
        elif st.session_state.current_page == "Test Configuration":
            render_test_configuration()
        elif st.session_state.current_page == "Run Assessment":
            render_run_assessment()
        elif st.session_state.current_page == "Results Analyzer":
            render_results_analyzer()
        elif st.session_state.current_page == "Ethical AI Testing":
            render_ethical_ai_testing()
        elif st.session_state.current_page == "High-Volume Testing":
            render_high_volume_testing()
        elif st.session_state.current_page == "Settings":
            render_settings()
        else:
            # Default to dashboard if invalid page
            logger.warning(f"Invalid page requested: {st.session_state.current_page}")
            st.session_state.current_page = "Dashboard"
            render_dashboard()
    
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}")
        logger.critical(traceback.format_exc())
        st.error(f"Critical application error: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
