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
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RedTeamApp")

# Set page configuration with custom theme
st.set_page_config(
    page_title="AI Security Red Team Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
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

# Get current theme colors
theme = themes[st.session_state.current_theme]

# CSS styles
def load_css():
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
    </style>
    """

# Apply CSS
st.markdown(load_css(), unsafe_allow_html=True)

# Custom components
def card(title, content, card_type="default"):
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

def metric_card(label, value, description="", prefix="", suffix=""):
    return f"""
    <div class="card hover-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{prefix}{value}{suffix}</div>
        <div style="font-size: 14px; opacity: 0.7;">{description}</div>
    </div>
    """

# Logo and header
def render_header():
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

# Sidebar navigation
def sidebar_navigation():
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
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    for option in navigation_options:
        active_class = "active" if st.session_state.current_page == option["name"] else ""
        if st.sidebar.markdown(f"""
        <div class="nav-item {active_class}">
            {option["icon"]} {option["name"]}
        </div>
        """, unsafe_allow_html=True):
            st.session_state.current_page = option["name"]
            st.experimental_rerun()
    
    # Theme toggle
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="sidebar-title">🎨 Appearance</div>', unsafe_allow_html=True)
    if st.sidebar.button("🔄 Toggle Theme"):
        st.session_state.current_theme = "light" if st.session_state.current_theme == "dark" else "dark"
        st.experimental_rerun()
    
    # System status
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="sidebar-title">📡 System Status</div>', unsafe_allow_html=True)
    if st.session_state.running_test:
        st.sidebar.markdown(f"""
        <div class="status-badge active">⚡ Test Running</div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f"""
        <div class="status-badge inactive">⏸️ Idle</div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"🎯 Targets: {len(st.session_state.targets)}")
    
    # Add version info
    st.sidebar.markdown("---")
    st.sidebar.markdown("v1.0.0 | © 2025", unsafe_allow_html=True)

# Mock data functions (in a real implementation, these would interact with actual testing logic)
def get_mock_test_vectors():
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

def run_mock_test(target, test_vectors, duration=30):
    """Simulate running a test in the background"""
    # Initialize progress
    st.session_state.progress = 0
    st.session_state.vulnerabilities_found = 0
    st.session_state.running_test = True
    
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
    
    # Complete the test results
    results["summary"]["total_tests"] = len(test_vectors) * 10  # Assume 10 variations per vector
    results["timestamp"] = datetime.now().isoformat()
    results["target"] = target["name"]
    
    # Set the results in session state
    st.session_state.test_results = results
    st.session_state.running_test = False

# Page renderers
def render_dashboard():
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
                        "low": theme["text"],
                        "medium": theme["warning"],
                        "high": theme["warning"],
                        "critical": theme["error"]
                    }.get(vuln["severity"], theme["text"])
                    
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
                    <div style="height: 10px; width: {st.session_state.progress*100}%; background-color: {theme["primary"]}; border-radius: 5px;"></div>
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
    test_vectors = get_mock_test_vectors()
    categories = list(set(tv["category"] for tv in test_vectors))
    
    # Count test vectors by category
    category_counts = {}
    for cat in categories:
        category_counts[cat] = sum(1 for tv in test_vectors if tv["category"] == cat)
    
    # Create the data for the radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=list(category_counts.values()),
        theta=list(category_counts.keys()),
        fill='toself',
        fillcolor=f'rgba({int(theme["primary"][1:3], 16)}, {int(theme["primary"][3:5], 16)}, {int(theme["primary"][5:7], 16)}, 0.3)',
        line=dict(color=theme["primary"]),
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
        font=dict(color=theme["text"])
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Quick actions
    st.markdown("<h3>Quick Actions</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Add New Target", use_container_width=True):
            st.session_state.current_page = "Target Management"
            st.experimental_rerun()
    
    with col2:
        if st.button("🧪 Run Assessment", use_container_width=True):
            st.session_state.current_page = "Run Assessment"
            st.experimental_rerun()
    
    with col3:
        if st.button("📊 View Results", use_container_width=True):
            st.session_state.current_page = "Results Analyzer"
            st.experimental_rerun()

def render_target_management():
    st.markdown("""
    <h2>Target Management</h2>
    <p>Add and configure AI models to test</p>
    """, unsafe_allow_html=True)
    
    # Show existing targets
    if st.session_state.targets:
        st.markdown("<h3>Your Targets</h3>", unsafe_allow_html=True)
        
        cols = st.columns(3)
        for i, target in enumerate(st.session_state.targets):
            col = cols[i % 3]
            with col:
                st.markdown(f"""
                <div class="target-card hover-card">
                    <div class="card-title">{target["name"]}</div>
                    <div>Endpoint: {target["endpoint"]}</div>
                    <div>Type: {target.get("type", "Unknown")}</div>
                    <div style="margin-top: 10px;">
                        <button class="status-badge active">Edit</button>
                        <button class="status-badge inactive">Delete</button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
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
                st.experimental_rerun()
    
    # Import/Export
    st.markdown("<h3>Import/Export Targets</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        st.file_uploader("Import Targets", type=["json"])
    
    with col2:
        if st.session_state.targets:
            targets_json = json.dumps(st.session_state.targets, indent=2)
            st.download_button(
                label="Export Targets",
                data=targets_json,
                file_name="targets.json",
                mime="application/json"
            )
        else:
            st.button("Export Targets", disabled=True)

def render_test_configuration():
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
    tabs = st.tabs(list(categories.keys()))
    
    for i, (category, tab) in enumerate(zip(categories.keys(), tabs)):
        with tab:
            st.markdown(f"<h3>{category.upper()} Test Vectors</h3>", unsafe_allow_html=True)
            
            # Show test vectors in this category
            for tv in categories[category]:
                severity_color = {
                    "low": theme["text"],
                    "medium": theme["warning"],
                    "high": theme["warning"],
                    "critical": theme["error"]
                }.get(tv["severity"], theme["text"])
                
                st.markdown(f"""
                <div class="card hover-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div class="card-title">{tv["name"]}</div>
                        <div style="color: {severity_color}; font-weight: bold; text-transform: uppercase; font-size: 12px;">
                            {tv["severity"]}
                        </div>
                    </div>
                    <div>
                        <span class="tag {tv['category']}">
                            {tv['category'].upper()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Advanced configuration
    st.markdown("<h3>Advanced Configuration</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.slider("Maximum Test Duration (minutes)", 5, 120, 30)
        st.number_input("Test Variations per Vector", 1, 1000, 10)
        st.slider("Concurrency Level", 1, 16, 4)
    
    with col2:
        st.selectbox("Test Profile", ["Standard", "Thorough", "Extreme", "Custom"])
        st.radio("Focus Area", ["General Security", "AI Safety", "Compliance", "All"])
        st.checkbox("Save Detailed Results")
    
    # Save configuration
    st.button("Save Configuration")
    
    # Show configuration summary
    st.markdown("<h3>Configuration Summary</h3>", unsafe_allow_html=True)
    
    st.markdown(card("Test Parameters", """
    <ul>
        <li><strong>Total Test Vectors:</strong> 9</li>
        <li><strong>Estimated Duration:</strong> 30 minutes</li>
        <li><strong>Total Test Cases:</strong> 90 (9 vectors × 10 variations)</li>
    </ul>
    """), unsafe_allow_html=True)

def render_run_assessment():
    st.markdown("""
    <h2>Run Assessment</h2>
    <p>Execute security tests against your targets</p>
    """, unsafe_allow_html=True)
    
    # Check if targets exist
    if not st.session_state.targets:
        st.warning("No targets configured. Please add a target first.")
        if st.button("Add Target"):
            st.session_state.current_page = "Target Management"
            st.experimental_rerun()
        return
    
    # Check if a test is already running
    if st.session_state.running_test:
        st.markdown(card("Test in Progress", f"""
        <div style="margin-bottom: 10px;">
            <div style="margin-bottom: 5px;">Progress:</div>
            <div style="height: 20px; background-color: rgba(255,255,255,0.1); border-radius: 10px;">
                <div style="height: 20px; width: {st.session_state.progress*100}%; background-color: {theme["primary"]}; border-radius: 10px;"></div>
            </div>
            <div style="text-align: right; font-size: 14px; margin-top: 5px;">{int(st.session_state.progress*100)}%</div>
        </div>
        <div style="margin-top: 15px; font-size: 16px;">
            <span style="color: {theme["primary"]}; font-weight: bold;">{st.session_state.vulnerabilities_found}</span> vulnerabilities found so far
        </div>
        """, "warning"), unsafe_allow_html=True)
        
        if st.button("Stop Test"):
            st.session_state.running_test = False
            st.experimental_rerun()
    else:
        # Test configuration
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<h3>Select Target</h3>", unsafe_allow_html=True)
            target_options = [t["name"] for t in st.session_state.targets]
            selected_target = st.selectbox("Target", target_options)
        
        with col2:
            st.markdown("<h3>Test Parameters</h3>", unsafe_allow_html=True)
            test_duration = st.slider("Test Duration (seconds)", 5, 60, 30, help="For demonstration purposes, we're using seconds. In a real system, this would be minutes.")
        
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
        cols = st.columns(len(categories))
        
        selected_vectors = []
        for i, (category, col) in enumerate(zip(categories.keys(), cols)):
            with col:
                st.markdown(f"<div style='text-align: center; text-transform: uppercase; font-weight: bold; margin-bottom: 10px;'>{category}</div>", unsafe_allow_html=True)
                
                for tv in categories[category]:
                    if st.checkbox(tv["name"], value=True, key=f"tv_{tv['id']}"):
                        selected_vectors.append(tv)
        
        # Run test button
        if st.button("Run Assessment", use_container_width=True, type="primary"):
            if not selected_vectors:
                st.error("Please select at least one test vector")
            else:
                # Find the selected target object
                target = next((t for t in st.session_state.targets if t["name"] == selected_target), None)
                
                if target:
                    # Create a thread to run the mock test
                    test_thread = threading.Thread(
                        target=run_mock_test,
                        args=(target, selected_vectors, test_duration)
                    )
                    test_thread.daemon = True
                    test_thread.start()
                    
                    st.session_state.running_test = True
                    st.experimental_rerun()

def render_results_analyzer():
    st.markdown("""
    <h2>Results Analyzer</h2>
    <p>Explore and analyze security assessment results</p>
    """, unsafe_allow_html=True)
    
    # Check if there are results to display
    if not st.session_state.test_results:
        st.markdown(card("No Results Available", """
        <p>Run an assessment to generate results that will appear here.</p>
        <button style="background-color: transparent; border: 1px solid; border-radius: 5px; padding: 8px 16px; cursor: pointer;">
            Go to Run Assessment
        </button>
        """, "warning"), unsafe_allow_html=True)
        
        if st.button("Go to Run Assessment"):
            st.session_state.current_page = "Run Assessment"
            st.experimental_rerun()
        return
    
    # Results summary
    results = st.session_state.test_results
    vulnerabilities = results.get("vulnerabilities", [])
    summary = results.get("summary", {})
    
    # Create header with summary metrics
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h3>Assessment Results: {results.get("target", "Unknown Target")}</h3>
            <div style="opacity: 0.7;">Completed: {results.get("timestamp", "Unknown")}</div>
        </div>
        <div style="display: flex; gap: 20px;">
            <div style="text-align: center;">
                <div style="font-size: 24px; font-weight: bold;">{summary.get("total_tests", 0)}</div>
                <div style="font-size: 14px; opacity: 0.7;">Tests Run</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: {theme["error"]};">{summary.get("vulnerabilities_found", 0)}</div>
                <div style="font-size: 14px; opacity: 0.7;">Vulnerabilities</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: {theme["warning"]};">{summary.get("risk_score", 0)}</div>
                <div style="font-size: 14px; opacity: 0.7;">Risk Score</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Visualizations
    st.markdown("<h3>Vulnerability Overview</h3>", unsafe_allow_html=True)
    
    # Prepare data for charts
    if vulnerabilities:
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
            
            color_map = [colors.get(label, "gray") for label in labels]
            
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
                font=dict(color=theme["text"])
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Create bar chart for test vector distribution
            fig = px.bar(
                x=list(vector_counts.keys()),
                y=list(vector_counts.values()),
                title="Vulnerabilities by Test Vector",
                labels={"x": "Test Vector", "y": "Vulnerabilities"},
                color_discrete_sequence=[theme["primary"]]
            )
            
            fig.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=theme["text"])
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed vulnerability listing
    st.markdown("<h3>Detailed Findings</h3>", unsafe_allow_html=True)
    
    if vulnerabilities:
        # Create tabs for different severity levels
        severities = list(set(vuln["severity"] for vuln in vulnerabilities if "severity" in vuln))
        severities.sort(key=lambda s: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(s, 4))
        
        # Add "All" tab at the beginning
        tabs = st.tabs(["All"] + severities)
        
        with tabs[0]:  # "All" tab
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "unknown")
                severity_color = {
                    "low": "green",
                    "medium": theme["warning"],
                    "high": theme["warning"],
                    "critical": theme["error"],
                    "unknown": "gray"
                }.get(severity, "gray")
                
                st.markdown(f"""
                <div class="card hover-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div class="card-title">{vuln.get("id", "Unknown")}: {vuln.get("test_name", "Unknown Test")}</div>
                        <div style="color: {severity_color}; font-weight: bold; text-transform: uppercase; font-size: 12px;">
                            {severity}
                        </div>
                    </div>
                    <p>{vuln.get("details", "No details available.")}</p>
                    <div style="font-size: 12px; opacity: 0.7;">Found: {vuln.get("timestamp", "Unknown")}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Create content for each severity tab
        for i, severity in enumerate(severities):
            with tabs[i+1]:  # +1 because "All" is the first tab
                severity_vulns = [v for v in vulnerabilities if v.get("severity") == severity]
                
                for vuln in severity_vulns:
                    severity_color = {
                        "low": "green",
                        "medium": theme["warning"],
                        "high": theme["warning"],
                        "critical": theme["error"],
                        "unknown": "gray"
                    }.get(severity, "gray")
                    
                    st.markdown(f"""
                    <div class="card hover-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div class="card-title">{vuln.get("id", "Unknown")}: {vuln.get("test_name", "Unknown Test")}</div>
                            <div style="color: {severity_color}; font-weight: bold; text-transform: uppercase; font-size: 12px;">
                                {severity}
                            </div>
                        </div>
                        <p>{vuln.get("details", "No details available.")}</p>
                        <div style="font-size: 12px; opacity: 0.7;">Found: {vuln.get("timestamp", "Unknown")}</div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No vulnerabilities were found in this assessment.")
    
    # Export results
    st.markdown("<h3>Export Results</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download JSON Report",
            data=json.dumps(results, indent=2),
            file_name=f"security_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        st.download_button(
            label="Download CSV Vulnerabilities",
            data=pd.DataFrame(vulnerabilities).to_csv(index=False) if vulnerabilities else "",
            file_name=f"vulnerabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            disabled=not vulnerabilities
        )

def render_ethical_ai_testing():
    st.markdown("""
    <h2>Ethical AI Testing</h2>
    <p>Comprehensive assessment of AI systems against OWASP, NIST, and ethical guidelines</p>
    """, unsafe_allow_html=True)
    
    # Check if targets exist
    if not st.session_state.targets:
        st.warning("No targets configured. Please add a target first.")
        if st.button("Add Target"):
            st.session_state.current_page = "Target Management"
            st.experimental_rerun()
        return
    
    # Ethical AI testing sections
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
        
        st.button("Run OWASP LLM Tests", key="run_owasp")
    
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
        
        st.button("Run NIST Framework Assessment", key="run_nist")
    
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
        
        st.button("Run Fairness Assessment", key="run_fairness")
    
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
        
        st.button("Run Privacy Assessment", key="run_privacy")
    
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
        
        st.button("Run Extreme Testing", key="run_extreme")

def render_high_volume_testing():
    st.markdown("""
    <h2>High-Volume Testing</h2>
    <p>Autonomous, high-throughput testing for AI systems</p>
    """, unsafe_allow_html=True)
    
    # Check if targets exist
    if not st.session_state.targets:
        st.warning("No targets configured. Please add a target first.")
        if st.button("Add Target"):
            st.session_state.current_page = "Target Management"
            st.experimental_rerun()
        return
    
    # Configuration section
    st.markdown("<h3>Testing Configuration</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_options = [t["name"] for t in st.session_state.targets]
        st.selectbox("Select Target", target_options)
        
        st.slider("Total Tests (thousands)", 10, 1000, 100)
        
        st.number_input("Max Runtime (hours)", 1, 24, 3)
    
    with col2:
        st.multiselect("Test Vectors", [
            "Prompt Injection",
            "Jailbreaking",
            "Data Extraction",
            "Input Manipulation",
            "Boundary Testing"
        ], default=["Prompt Injection", "Jailbreaking"])
        
        st.selectbox("Parallelism", ["Low (4 workers)", "Medium (8 workers)", "High (16 workers)", "Extreme (32 workers)"])
        
        st.checkbox("Save Only Vulnerabilities", value=True)
    
    # Resource monitoring
    st.markdown("<h3>Resource Monitoring</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(metric_card("Max Workers", "16", "Parallel execution threads"), unsafe_allow_html=True)
    
    with col2:
        st.markdown(metric_card("Rate Limit", "100", suffix=" req/sec", description="Maximum request rate"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(metric_card("Memory Limit", "8", suffix=" GB", description="Maximum memory usage"), unsafe_allow_html=True)
    
    # Start testing button
    if st.button("Start High-Volume Testing", type="primary", use_container_width=True):
        st.success("High-volume testing started! This would typically run for several hours in a production environment.")
        
        # Show a sample progress bar and metrics for demonstration
        progress_placeholder = st.empty()
        metrics_placeholder = st.empty()
        
        # Simulate progress updates
        for i in range(101):
            progress_placeholder.progress(i / 100)
            
            # Update metrics every 10%
            if i % 10 == 0:
                with metrics_placeholder.container():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tests Completed", f"{i * 1000:,}")
                    with col2:
                        vulnerabilities = int(i * 1000 * 0.02)  # 2% find rate
                        st.metric("Vulnerabilities", f"{vulnerabilities:,}")
                    with col3:
                        st.metric("Tests/Second", f"{random.randint(80, 120):,}")
            
            time.sleep(0.05)  # Just for demonstration
        
        progress_placeholder.empty()
        metrics_placeholder.empty()
        
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
            font=dict(color=theme["text"])
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_settings():
    st.markdown("""
    <h2>Settings</h2>
    <p>Configure application settings and preferences</p>
    """, unsafe_allow_html=True)
    
    # Theme settings
    st.markdown("<h3>Theme Settings</h3>", unsafe_allow_html=True)
    
    theme_option = st.radio("Theme", ["Dark", "Light"], index=0 if st.session_state.current_theme == "dark" else 1)
    if theme_option == "Dark" and st.session_state.current_theme != "dark":
        st.session_state.current_theme = "dark"
        st.experimental_rerun()
    elif theme_option == "Light" and st.session_state.current_theme != "light":
        st.session_state.current_theme = "light"
        st.experimental_rerun()
    
    # API settings
    st.markdown("<h3>API Settings</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("API Base URL", "https://api.example.com/v1", key="api_base_url")
    
    with col2:
        st.text_input("Default API Key", type="password", key="default_api_key")
    
    # Testing settings
    st.markdown("<h3>Testing Settings</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Default Test Duration (minutes)", 5, 120, 30, key="default_duration")
        st.number_input("Request Timeout (seconds)", 1, 60, 10, key="request_timeout")
    
    with col2:
        st.number_input("Maximum Concurrent Tests", 1, 32, 4, key="max_concurrent_tests")
        st.checkbox("Save Detailed Logs", value=True, key="save_detailed_logs")
    
    # Notifications
    st.markdown("<h3>Notifications</h3>", unsafe_allow_html=True)
    
    st.checkbox("Email Notifications", value=False, key="email_notifications")
    
    if st.session_state.get("email_notifications", False):
        st.text_input("Email Address", key="notification_email")
        st.multiselect("Notify On", ["Test Completion", "Critical Vulnerability", "Error"], default=["Test Completion", "Critical Vulnerability"], key="notification_events")
    
    # Save settings
    if st.button("Save Settings", type="primary"):
        st.success("Settings saved successfully!")

# Main application
def main():
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

if __name__ == "__main__":
    main()
