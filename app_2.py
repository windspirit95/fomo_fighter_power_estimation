import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from google import genai
from google.genai import types

# Page config
st.set_page_config(page_title="Clan Manager", layout="wide")

# ============================================================================
# TAB 1: CLAN POWER CALCULATOR - Configuration and Functions
# ============================================================================

# Bias value for power calculation
BIAS_VALUE = 0.84

def calculate_power(race, base_power, mode):
    """Calculate actual power based on race and mode (ATK/DEF)"""
    if race == "Frog":
        return base_power * 2.5
    elif race == "Cat":
        if mode == "ATK":
            return base_power * 5
        else:
            return base_power * 2.5
    elif race == "Dog":
        if mode == "ATK":
            return base_power * 2.5
        else:
            return base_power * 5
    return base_power

def calculate_total_power_full(members, mode):
    """Calculate total clan power with bias for Full mode"""
    total = 0
    for member in members:
        total += calculate_power(member['race'], member['power'], mode)
    return total * BIAS_VALUE

def calculate_major_race_power(members, mode):
    """Calculate power for major race (Dog for DEF, Cat for ATK)"""
    major_race = "Dog" if mode == "DEF" else "Cat"
    total = 0
    total_power = 0
    for member in members:
        if member['race'] == major_race:
            total += calculate_power(member['race'], member['power'], mode)
            total_power += member['power']
    return total, total_power

def calculate_total_power_lite(members, mode, clan_total_power):
    """Calculate total clan power for Lite mode"""
    major_power, major_power_raw = calculate_major_race_power(members, mode)
    remaining_power = (clan_total_power - major_power_raw) * 1.8
    return (major_power + remaining_power) * BIAS_VALUE

# ============================================================================
# TAB 2: MEMBER STATS MANAGER - Configuration and Functions
# ============================================================================

DATA_FILE = "members_data.json"
CLANS_FILE = "clans_data.json"
SECRET_KEY = "windissupervippro"  # Universal secret key for all operations

def get_gemini_client():
    """Initialize Gemini client with API key from environment variable"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY environment variable not set!")
        st.info("Please set your Gemini API key: `export GEMINI_API_KEY='your-api-key'`")
        return None
    return genai.Client(api_key=api_key)

def load_clans():
    """Load clans data from JSON file"""
    if Path(CLANS_FILE).exists():
        with open(CLANS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_clans(clans):
    """Save clans data to JSON file"""
    with open(CLANS_FILE, 'w') as f:
        json.dump(clans, f, indent=2)

def load_members():
    """Load members data from JSON file"""
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
            # Migration: Convert old array format to new dictionary format
            if isinstance(data, list):
                migrated_data = {}
                for member in data:
                    name_key = member.get('name', '').lower()
                    if name_key:
                        migrated_data[name_key] = member
                
                if migrated_data:
                    save_members(migrated_data)
                return migrated_data
            
            return data
    return {}

def save_members(members):
    """Save members data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(members, f, indent=2)

def calculate_totals(members):
    """Calculate total ATK and DEF from all members"""
    total_atk = sum(member.get('atk', 0) for member in members.values())
    total_def = sum(member.get('def', 0) for member in members.values())
    return total_atk, total_def

def format_stat(value):
    """Format stat value - show in millions (M) if >= 1 million"""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)

def parse_stat_input(value_str):
    """Parse stat input - supports formats like '2M', '4.1M', '500K', or plain numbers"""
    if isinstance(value_str, (int, float)):
        return int(value_str)
    
    value_str = str(value_str).strip().upper()
    value_str = value_str.replace(' ', '')
    
    try:
        if 'M' in value_str:
            number = float(value_str.replace('M', ''))
            return int(number * 1_000_000)
        elif 'K' in value_str:
            number = float(value_str.replace('K', ''))
            return int(number * 1_000)
        else:
            return int(float(value_str))
    except (ValueError, AttributeError):
        return 0

def get_utc_timestamp():
    """Get current UTC timestamp as ISO format string"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def extract_stats_from_image(image_bytes, mime_type):
    """Use Gemini API to extract ATK and DEF from image"""
    client = get_gemini_client()
    if not client:
        return None
    
    try:
        prompt = """Analyze this image and extract the following information if present:
- ATK (attack value - may have M for millions, e.g., "2M" = 2000000)
- DEF (defense value - may have M for millions, e.g., "4.1M" = 4100000)

Convert any values with M suffix to actual numbers (multiply by 1,000,000).
Look for icons or symbols that typically represent attack (swords, red) and defense (shields, gray/black).

Please respond in this exact JSON format with converted numeric values:
{
  "atk": numeric_value_or_0,
  "def": numeric_value_or_0
}

Examples:
- "2M" should become 2000000
- "4.1M" should become 4100000
- "2.2M" should become 2200000

If you cannot find specific values, use 0 as default."""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                prompt
            ]
        )
        
        response_text = response.text.strip()
        
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        data = json.loads(response_text)
        return data
    
    except Exception as e:
        st.error(f"Error processing image with Gemini: {str(e)}")
        return None

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'clan1_members' not in st.session_state:
    st.session_state.clan1_members = []
if 'clan2_members' not in st.session_state:
    st.session_state.clan2_members = []
if 'clan1_mode' not in st.session_state:
    st.session_state.clan1_mode = 'ATK'
if 'calc_mode' not in st.session_state:
    st.session_state.calc_mode = 'Full'
if 'clan1_total_power' not in st.session_state:
    st.session_state.clan1_total_power = 0
if 'clan2_total_power' not in st.session_state:
    st.session_state.clan2_total_power = 0
if 'current_clan_pin' not in st.session_state:
    st.session_state.current_clan_pin = None
if 'authenticated_clans' not in st.session_state:
    st.session_state.authenticated_clans = set()

# ============================================================================
# TAB 1: CLAN POWER CALCULATOR UI
# ============================================================================

def render_clan_calculator():
    """Render the clan power calculator interface"""
    # Mode toggle and calculation mode
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        if st.toggle("Lite Mode", value=(st.session_state.calc_mode == 'Lite'), key="calc_mode_toggle_tab1"):
            st.session_state.calc_mode = 'Lite'
        else:
            st.session_state.calc_mode = 'Full'
    
    with col2:
        if st.toggle("Switch ATK/DEF", value=(st.session_state.clan1_mode == 'DEF'), key="atk_def_toggle_tab1"):
            st.session_state.clan1_mode = 'DEF'
        else:
            st.session_state.clan1_mode = 'ATK'
    
    clan2_mode = 'DEF' if st.session_state.clan1_mode == 'ATK' else 'ATK'
    
    # Two panel layout
    col1, col2 = st.columns(2)
    
    # Clan 1 Panel
    with col1:
        color = "#dc3545" if st.session_state.clan1_mode == 'ATK' else "#000080"
        
        if st.session_state.calc_mode == 'Full':
            total_power_1 = calculate_total_power_full(st.session_state.clan1_members, st.session_state.clan1_mode)
        else:
            total_power_1 = calculate_total_power_lite(st.session_state.clan1_members, st.session_state.clan1_mode, st.session_state.clan1_total_power)
        
        # Header with clear button
        h_col1, h_col2 = st.columns([3, 1])
        with h_col1:
            st.markdown(f"<h2 style='color: {color};'>Clan 1 - {st.session_state.clan1_mode} | Total: {total_power_1:.1f}</h2>", 
                        unsafe_allow_html=True)
        with h_col2:
            if len(st.session_state.clan1_members) > 0:
                st.write("")
                if st.button("🗑️ Clear All", use_container_width=True, key="clear_top_1_tab1"):
                    st.session_state.clan1_members = []
                    st.rerun()
        
        # Lite mode: Total power input
        if st.session_state.calc_mode == 'Lite':
            st.number_input(
                "Total Clan Power", 
                min_value=0, 
                value=st.session_state.clan1_total_power,
                key="clan1_total_input_tab1",
                on_change=lambda: setattr(st.session_state, 'clan1_total_power', st.session_state.clan1_total_input_tab1)
            )
        
        # Add member form
        with st.expander("➕ Add New Member"):
            if st.session_state.calc_mode == 'Full':
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    race1 = st.selectbox("Race", ["Dog", "Cat", "Frog"], key="race1_tab1")
                with c2:
                    power1 = st.number_input("Power", min_value=1, value=100, key="power1_tab1")
                with c3:
                    level1 = st.number_input("Level", min_value=1, value=1, key="level1_tab1")
                with c4:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add1_tab1"):
                        st.session_state.clan1_members.append({
                            'race': race1,
                            'power': power1,
                            'level': level1
                        })
                        st.rerun()
            else:
                # Lite mode: only major race
                major_race = "Cat" if st.session_state.clan1_mode == 'ATK' else "Dog"
                c1, c2 = st.columns([2, 1])
                with c1:
                    power1_lite = st.number_input("Power", min_value=1, value=100, key="power1_lite_tab1")
                with c2:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add1_lite_tab1"):
                        st.session_state.clan1_members.append({
                            'race': major_race,
                            'power': power1_lite
                        })
                        st.rerun()
        
        # Display members table
        if st.session_state.clan1_members:
            st.markdown("#### Members")
            
            if st.session_state.calc_mode == 'Full':
                for idx, member in enumerate(st.session_state.clan1_members):
                    actual_power = calculate_power(member['race'], member['power'], 
                                                  st.session_state.clan1_mode)
                    
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.5, 0.7])
                    
                    with c1:
                        new_race = st.selectbox("", ["Dog", "Cat", "Frog"], 
                                               index=["Dog", "Cat", "Frog"].index(member['race']),
                                               key=f"race1_{idx}_tab1",
                                               label_visibility="collapsed")
                    with c2:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power1_{idx}_tab1",
                                                   label_visibility="collapsed")
                    with c3:
                        new_level = st.number_input("", min_value=1, 
                                                   value=member['level'],
                                                   key=f"level1_{idx}_tab1",
                                                   label_visibility="collapsed")
                    with c4:
                        st.markdown(f"<div style='padding-top: 8px;'>{st.session_state.clan1_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c5:
                        if st.button("🗑️", key=f"delete1_{idx}_tab1", use_container_width=True):
                            st.session_state.clan1_members.pop(idx)
                            st.rerun()
                    
                    if (new_race != member['race'] or new_power != member['power'] or 
                        new_level != member['level']):
                        st.session_state.clan1_members[idx] = {
                            'race': new_race,
                            'power': new_power,
                            'level': new_level
                        }
            else:
                major_race = "Cat" if st.session_state.clan1_mode == 'ATK' else "Dog"
                for idx, member in enumerate(st.session_state.clan1_members):
                    actual_power = calculate_power(member['race'], member['power'], 
                                                  st.session_state.clan1_mode)
                    
                    c1, c2, c3 = st.columns([2, 1.5, 0.7])
                    
                    with c1:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power1_lite_{idx}_tab1",
                                                   label_visibility="collapsed")
                    with c2:
                        st.markdown(f"<div style='padding-top: 8px;'>{major_race} - {st.session_state.clan1_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c3:
                        if st.button("🗑️", key=f"delete1_lite_{idx}_tab1", use_container_width=True):
                            st.session_state.clan1_members.pop(idx)
                            st.rerun()
                    
                    if new_power != member['power']:
                        st.session_state.clan1_members[idx] = {
                            'race': major_race,
                            'power': new_power
                        }
            
        else:
            st.info("No members yet. Add members using the form above.")
    
    # Clan 2 Panel
    with col2:
        color = "#dc3545" if clan2_mode == 'ATK' else "#000080"
        
        if st.session_state.calc_mode == 'Full':
            total_power_2 = calculate_total_power_full(st.session_state.clan2_members, clan2_mode)
        else:
            total_power_2 = calculate_total_power_lite(st.session_state.clan2_members, clan2_mode, st.session_state.clan2_total_power)
        
        # Header with clear button
        h_col1, h_col2 = st.columns([3, 1])
        with h_col1:
            st.markdown(f"<h2 style='color: {color};'>Clan 2 - {clan2_mode} | Total: {total_power_2:.1f}</h2>", 
                        unsafe_allow_html=True)
        with h_col2:
            if len(st.session_state.clan2_members) > 0:
                st.write("")
                if st.button("🗑️ Clear All", use_container_width=True, key="clear_top_2_tab1"):
                    st.session_state.clan2_members = []
                    st.rerun()
        
        # Lite mode: Total power input
        if st.session_state.calc_mode == 'Lite':
            st.number_input(
                "Total Clan Power", 
                min_value=0, 
                value=st.session_state.clan2_total_power,
                key="clan2_total_input_tab1",
                on_change=lambda: setattr(st.session_state, 'clan2_total_power', st.session_state.clan2_total_input_tab1)
            )
        
        # Add member form
        with st.expander("➕ Add New Member"):
            if st.session_state.calc_mode == 'Full':
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    race2 = st.selectbox("Race", ["Dog", "Cat", "Frog"], key="race2_tab1")
                with c2:
                    power2 = st.number_input("Power", min_value=1, value=100, key="power2_tab1")
                with c3:
                    level2 = st.number_input("Level", min_value=1, value=1, key="level2_tab1")
                with c4:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add2_tab1"):
                        st.session_state.clan2_members.append({
                            'race': race2,
                            'power': power2,
                            'level': level2
                        })
                        st.rerun()
            else:
                major_race = "Cat" if clan2_mode == 'ATK' else "Dog"
                c1, c2 = st.columns([2, 1])
                with c1:
                    power2_lite = st.number_input("Power", min_value=1, value=100, key="power2_lite_tab1")
                with c2:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add2_lite_tab1"):
                        st.session_state.clan2_members.append({
                            'race': major_race,
                            'power': power2_lite
                        })
                        st.rerun()
        
        # Display members table
        if st.session_state.clan2_members:
            st.markdown("#### Members")
            
            if st.session_state.calc_mode == 'Full':
                for idx, member in enumerate(st.session_state.clan2_members):
                    actual_power = calculate_power(member['race'], member['power'], clan2_mode)
                    
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.5, 0.7])
                    
                    with c1:
                        new_race = st.selectbox("", ["Dog", "Cat", "Frog"], 
                                               index=["Dog", "Cat", "Frog"].index(member['race']),
                                               key=f"race2_{idx}_tab1",
                                               label_visibility="collapsed")
                    with c2:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power2_{idx}_tab1",
                                                   label_visibility="collapsed")
                    with c3:
                        new_level = st.number_input("", min_value=1, 
                                                   value=member['level'],
                                                   key=f"level2_{idx}_tab1",
                                                   label_visibility="collapsed")
                    with c4:
                        st.markdown(f"<div style='padding-top: 8px;'>{clan2_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c5:
                        if st.button("🗑️", key=f"delete2_{idx}_tab1", use_container_width=True):
                            st.session_state.clan2_members.pop(idx)
                            st.rerun()
                    
                    if (new_race != member['race'] or new_power != member['power'] or 
                        new_level != member['level']):
                        st.session_state.clan2_members[idx] = {
                            'race': new_race,
                            'power': new_power,
                            'level': new_level
                        }
            else:
                major_race = "Cat" if clan2_mode == 'ATK' else "Dog"
                for idx, member in enumerate(st.session_state.clan2_members):
                    actual_power = calculate_power(member['race'], member['power'], clan2_mode)
                    
                    c1, c2, c3 = st.columns([2, 1.5, 0.7])
                    
                    with c1:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power2_lite_{idx}_tab1",
                                                   label_visibility="collapsed")
                    with c2:
                        st.markdown(f"<div style='padding-top: 8px;'>{major_race} - {clan2_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c3:
                        if st.button("🗑️", key=f"delete2_lite_{idx}_tab1", use_container_width=True):
                            st.session_state.clan2_members.pop(idx)
                            st.rerun()
                    
                    if new_power != member['power']:
                        st.session_state.clan2_members[idx] = {
                            'race': major_race,
                            'power': new_power
                        }
            
        else:
            st.info("No members yet. Add members using the form above.")

# ============================================================================
# TAB 2: MEMBER STATS MANAGER UI (MULTI-CLAN)
# ============================================================================

def render_member_stats():
    """Render the member stats manager interface with multi-clan support"""
    
    # Load clans data
    clans = load_clans()
    
    # Sidebar for clan selection and authentication
    with st.sidebar:
        st.header("🏰 Clan Management")
        
        # Create new clan section
        with st.expander("➕ Create New Clan"):
            new_clan_name = st.text_input("Clan Name", key="new_clan_name", placeholder="Enter clan name")
            new_clan_pin = st.text_input("PIN Code (4-8 digits)", key="new_clan_pin", type="password", placeholder="e.g., 1234")
            
            if st.button("Create Clan", type="primary", key="create_clan_btn"):
                if not new_clan_name.strip():
                    st.error("Please enter a clan name")
                elif not new_clan_pin.strip():
                    st.error("Please enter a PIN code")
                elif len(new_clan_pin) < 4 or len(new_clan_pin) > 8:
                    st.error("PIN must be 4-8 digits")
                elif not new_clan_pin.isdigit():
                    st.error("PIN must contain only numbers")
                else:
                    clan_key = new_clan_name.strip().lower()
                    if clan_key in clans:
                        st.error("Clan name already exists!")
                    else:
                        clans[clan_key] = {
                            "name": new_clan_name.strip(),
                            "pin": new_clan_pin,
                            "members": {},
                            "created_at": get_utc_timestamp()
                        }
                        save_clans(clans)
                        st.success(f"✅ Clan '{new_clan_name}' created!")
                        st.rerun()
        
        st.markdown("---")
        
        # Clan selection and authentication
        if clans:
            st.subheader("🔐 Select & Unlock Clan")
            
            clan_options = {clan_data['name']: clan_key for clan_key, clan_data in clans.items()}
            selected_clan_name = st.selectbox(
                "Choose Clan",
                options=list(clan_options.keys()),
                key="selected_clan_dropdown"
            )
            
            selected_clan_key = clan_options[selected_clan_name]
            
            # Check if already authenticated
            if selected_clan_key in st.session_state.authenticated_clans:
                st.success(f"🔓 Unlocked: {selected_clan_name}")
                st.session_state.current_clan_pin = selected_clan_key
                
                if st.button("🔒 Lock Clan", key="lock_clan_btn"):
                    st.session_state.authenticated_clans.discard(selected_clan_key)
                    if st.session_state.current_clan_pin == selected_clan_key:
                        st.session_state.current_clan_pin = None
                    st.rerun()
            else:
                pin_input = st.text_input(
                    "Enter PIN to unlock",
                    type="password",
                    key="pin_input_unlock"
                )
                
                if st.button("🔓 Unlock", type="primary", key="unlock_btn"):
                    if pin_input == clans[selected_clan_key]['pin']:
                        st.session_state.authenticated_clans.add(selected_clan_key)
                        st.session_state.current_clan_pin = selected_clan_key
                        st.success(f"✅ Unlocked {selected_clan_name}!")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect PIN!")
            
            st.markdown("---")
            
            # Show stats for authenticated clan
            if st.session_state.current_clan_pin and st.session_state.current_clan_pin in clans:
                current_clan = clans[st.session_state.current_clan_pin]
                st.header(f"📊 {current_clan['name']} Stats")
                
                members = current_clan.get('members', {})
                total_atk, total_def = calculate_totals(members)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total ATK", format_stat(total_atk))
                with col2:
                    st.metric("Total DEF", format_stat(total_def))
                
                st.metric("Total Members", len(members))
                
                st.markdown("---")
                
                # Import/Export section
                st.header("📁 Import/Export")
                
                # Export button
                if members:
                    export_data = json.dumps(members, indent=2)
                    st.download_button(
                        label="📥 Export Clan Data",
                        data=export_data,
                        file_name=f"{current_clan['name']}_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        help="Download this clan's member data as JSON file"
                    )
                else:
                    st.info("No members to export")
                
                # Import button
                uploaded_json = st.file_uploader(
                    "📤 Import Clan Data",
                    type=['json'],
                    help="Upload a JSON file to import members into this clan",
                    key="upload_clan_json"
                )
                
                if uploaded_json is not None:
                    try:
                        import_data = json.load(uploaded_json)
                        
                        if not isinstance(import_data, dict):
                            st.error("❌ Invalid format! JSON must be an object/dictionary.")
                        else:
                            st.write("**Preview:**")
                            st.json(import_data)
                            
                            import_secret = st.text_input(
                                "Enter secret key to import:",
                                type="password",
                                key="import_secret_input"
                            )
                            
                            col_import, col_cancel = st.columns(2)
                            
                            with col_import:
                                if st.button("✅ Import Data", type="primary", key="import_btn"):
                                    if import_secret == SECRET_KEY:
                                        st.session_state.import_data = import_data
                                        st.session_state.show_import_options = True
                                    else:
                                        st.error("❌ Invalid secret key!")
                            
                            with col_cancel:
                                if st.button("❌ Cancel Import", key="cancel_import_btn"):
                                    st.rerun()
                    
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON file: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Error reading file: {str(e)}")
                
                # Show import options dialog
                if st.session_state.get('show_import_options', False):
                    st.markdown("---")
                    st.subheader("Import Options")
                    
                    import_mode = st.radio(
                        "How would you like to import?",
                        ["Merge (keep existing + add new)", "Replace (overwrite all members)"],
                        key="import_mode_radio"
                    )
                    
                    col_confirm, col_cancel = st.columns(2)
                    
                    with col_confirm:
                        if st.button("Confirm Import", type="primary", key="confirm_import_btn"):
                            if import_mode == "Replace (overwrite all members)":
                                members = st.session_state.import_data.copy()
                            else:
                                members.update(st.session_state.import_data)
                            
                            current_clan['members'] = members
                            save_clans(clans)
                            st.session_state.show_import_options = False
                            st.session_state.pop('import_data', None)
                            st.success(f"✅ Data imported successfully! ({len(st.session_state.import_data)} members)")
                            st.rerun()
                    
                    with col_cancel:
                        if st.button("Cancel", key="cancel_import_options_btn"):
                            st.session_state.show_import_options = False
                            st.session_state.pop('import_data', None)
                            st.rerun()
                
                st.markdown("---")
                
                # Delete clan section
                with st.expander("🗑️ Delete Clan"):
                    st.warning(f"⚠️ This will permanently delete '{current_clan['name']}' and all its members!")
                    delete_secret = st.text_input(
                        "Enter secret key to delete clan:",
                        type="password",
                        key="delete_clan_secret"
                    )
                    
                    if st.button("Confirm Delete Clan", type="primary", key="confirm_delete_clan"):
                        if delete_secret == SECRET_KEY:
                            clan_name = current_clan['name']
                            del clans[st.session_state.current_clan_pin]
                            save_clans(clans)
                            st.session_state.authenticated_clans.discard(st.session_state.current_clan_pin)
                            st.session_state.current_clan_pin = None
                            st.success(f"✅ Deleted clan '{clan_name}'")
                            st.rerun()
                        else:
                            st.error("❌ Invalid secret key!")
        else:
            st.info("No clans yet. Create your first clan!")
    
    # Main content
    if not st.session_state.current_clan_pin:
        st.info("👈 Please select and unlock a clan from the sidebar to manage members")
        return
    
    if st.session_state.current_clan_pin not in clans:
        st.error("Selected clan not found!")
        st.session_state.current_clan_pin = None
        return
    
    current_clan = clans[st.session_state.current_clan_pin]
    members = current_clan.get('members', {})
    
    st.header(f"⚔️ {current_clan['name']} - Member Management")
    
    # Add new member section
    st.subheader("➕ Add New Member")
    
    # Tab for different input methods
    input_tab1, input_tab2 = st.tabs(["📝 Manual Input", "🖼️ Upload Image"])
    
    with input_tab1:
        with st.form("manual_form_tab2"):
            name = st.text_input("Name", placeholder="Enter member name", key="name_input_tab2")
            
            col1, col2 = st.columns(2)
            with col1:
                atk_input = st.text_input("ATK", placeholder="e.g., 2M or 2000000", help="You can use M for millions (e.g., 2M = 2,000,000)", key="atk_input_tab2")
            with col2:
                def_input = st.text_input("DEF", placeholder="e.g., 4.1M or 4100000", help="You can use M for millions (e.g., 4.1M = 4,100,000)", key="def_input_tab2")
            
            submit = st.form_submit_button("Add Member", type="primary")
            
            if submit:
                if name.strip():
                    atk = parse_stat_input(atk_input) if atk_input else 0
                    def_val = parse_stat_input(def_input) if def_input else 0
                    
                    name_key = name.strip().lower()
                    is_update = name_key in members
                    
                    members[name_key] = {
                        "name": name.strip(),
                        "atk": atk,
                        "def": def_val,
                        "updated_at": get_utc_timestamp()
                    }
                    
                    current_clan['members'] = members
                    save_clans(clans)
                    
                    if is_update:
                        st.success(f"✅ Updated {name} (ATK: {format_stat(atk)}, DEF: {format_stat(def_val)})")
                    else:
                        st.success(f"✅ Added {name} (ATK: {format_stat(atk)}, DEF: {format_stat(def_val)})")
                    st.rerun()
                else:
                    st.error("Please enter a name")
    
    with input_tab2:
        img_name = st.text_input("Name", placeholder="Enter member name", key="img_name_input_tab2")
        
        uploaded_file = st.file_uploader(
            "Upload an image with ATK and DEF stats",
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="Upload an image containing ATK and DEF information",
            key="upload_image_tab2"
        )
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        if st.button("🔍 Extract Stats from Image", type="primary", key="extract_btn_tab2"):
            if not img_name.strip():
                st.error("Please enter a name")
            elif uploaded_file is None:
                st.error("Please upload an image")
            else:
                with st.spinner("Analyzing image with Gemini..."):
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()
                    mime_type = uploaded_file.type
                    
                    extracted_data = extract_stats_from_image(image_bytes, mime_type)
                    
                    if extracted_data:
                        st.session_state.extracted_data = extracted_data
                        st.session_state.extracted_name = img_name.strip()
                        st.session_state.show_confirmation = True
        
        if st.session_state.get('show_confirmation', False):
            st.success("✅ Stats extracted successfully!")
            st.write("**Review and Confirm:**")
            
            st.text_input("Name", value=st.session_state.extracted_name, disabled=True, key="confirm_name_tab2")
            
            col_atk, col_def = st.columns(2)
            with col_atk:
                ext_atk = st.number_input("ATK", min_value=0, value=int(st.session_state.extracted_data.get('atk', 0)), step=100000, key="confirm_atk_tab2")
            with col_def:
                ext_def = st.number_input("DEF", min_value=0, value=int(st.session_state.extracted_data.get('def', 0)), step=100000, key="confirm_def_tab2")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Confirm & Add", type="primary", key="confirm_add_btn_tab2"):
                    name_key = st.session_state.extracted_name.lower()
                    is_update = name_key in members
                    
                    members[name_key] = {
                        "name": st.session_state.extracted_name,
                        "atk": int(ext_atk),
                        "def": int(ext_def),
                        "updated_at": get_utc_timestamp()
                    }
                    
                    current_clan['members'] = members
                    save_clans(clans)
                    
                    st.session_state.show_confirmation = False
                    st.session_state.pop('extracted_data', None)
                    st.session_state.pop('extracted_name', None)
                    
                    if is_update:
                        st.success(f"✅ Updated {st.session_state.extracted_name}!")
                    else:
                        st.success(f"✅ Added {st.session_state.extracted_name}!")
                    st.rerun()
            
            with col_b:
                if st.button("❌ Cancel", key="cancel_btn_tab2"):
                    st.session_state.show_confirmation = False
                    st.session_state.pop('extracted_data', None)
                    st.session_state.pop('extracted_name', None)
                    st.rerun()
    
    st.markdown("---")
    
    # Members list section
    st.subheader("👥 Current Members")
    
    if not members:
        st.info("No members added yet. Add your first member!")
    else:
        sorted_members = sorted(members.items())
        
        for name_key, member in sorted_members:
            cols = st.columns([3, 1, 1, 1])
            
            with cols[0]:
                st.write(f"**{member['name']}**")
                if 'updated_at' in member:
                    st.caption(f"🕒 {member['updated_at']}")
                else:
                    st.caption("🕒 No timestamp")
            with cols[1]:
                st.write(f"⚔️ {format_stat(member['atk'])}")
            with cols[2]:
                st.write(f"🛡️ {format_stat(member['def'])}")
            with cols[3]:
                if st.button("❌", key=f"delete_{name_key}_tab2"):
                    st.session_state.delete_pending = name_key
                    st.session_state.show_delete_dialog = True
            
            st.markdown("---")
        
        # Show delete confirmation dialog
        if st.session_state.get('show_delete_dialog', False):
            st.markdown("---")
            st.warning(f"⚠️ Confirm deletion of **{members[st.session_state.delete_pending]['name']}**")
            
            secret_input = st.text_input(
                "Enter secret key to delete:", 
                type="password",
                key="delete_secret_input_tab2"
            )
            
            col_confirm, col_cancel = st.columns(2)
            
            with col_confirm:
                if st.button("🗑️ Confirm Delete", type="primary", key="confirm_delete_btn_tab2"):
                    if secret_input == SECRET_KEY:
                        deleted_name = members[st.session_state.delete_pending]['name']
                        del members[st.session_state.delete_pending]
                        current_clan['members'] = members
                        save_clans(clans)
                        st.session_state.show_delete_dialog = False
                        st.session_state.pop('delete_pending', None)
                        st.success(f"✅ Deleted {deleted_name}")
                        st.rerun()
                    else:
                        st.error("❌ Invalid secret key!")
            
            with col_cancel:
                if st.button("❌ Cancel", key="cancel_delete_btn_tab2"):
                    st.session_state.show_delete_dialog = False
                    st.session_state.pop('delete_pending', None)
                    st.rerun()
    
    # Display JSON data at the bottom
    with st.expander("📄 View Raw JSON Data"):
        st.json(members)

# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.title("⚔️ Clan Manager")

# Create tabs
tab1, tab2 = st.tabs(["🎯 Power Calculator", "📊 Member Stats (Multi-Clan)"])

with tab1:
    render_clan_calculator()

with tab2:
    render_member_stats()
