import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from google import genai
from google.genai import types

# Configuration
DATA_FILE = "members_data.json"
DELETE_SECRET_KEY = "your-secret-key-here"  # Change this to your own secret key

# Initialize Gemini client
def get_gemini_client():
    """Initialize Gemini client with API key from environment variable"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY environment variable not set!")
        st.info("Please set your Gemini API key: `export GEMINI_API_KEY='your-api-key'`")
        return None
    return genai.Client(api_key=api_key)

# Data management functions
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
                    if name_key:  # Only migrate if name exists
                        migrated_data[name_key] = member
                
                # Save migrated data
                if migrated_data:
                    save_members(migrated_data)
                return migrated_data
            
            # Already in dictionary format
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
    
    # Convert to string and normalize: strip, uppercase
    value_str = str(value_str).strip().upper()
    
    # Remove any spaces
    value_str = value_str.replace(' ', '')
    
    try:
        if 'M' in value_str:
            # Handle millions (e.g., 9M, 9.5M, 900M)
            number = float(value_str.replace('M', ''))
            return int(number * 1_000_000)
        elif 'K' in value_str:
            # Handle thousands (e.g., 500K, 1.5K)
            number = float(value_str.replace('K', ''))
            return int(number * 1_000)
        else:
            # Plain number
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
        
        # Parse the response
        response_text = response.text.strip()
        
        # Try to extract JSON from the response
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

# Streamlit UI
def main():
    st.set_page_config(page_title="Member Stats Manager", page_icon="⚔️", layout="wide")
    
    st.title("⚔️ Member Stats Manager")
    st.markdown("---")
    
    # Load existing members
    members = load_members()
    
    # Sidebar for totals
    with st.sidebar:
        st.header("📊 Total Stats")
        total_atk, total_def = calculate_totals(members)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total ATK", format_stat(total_atk))
        with col2:
            st.metric("Total DEF", format_stat(total_def))
        
        st.metric("Total Members", len(members))
        
        st.markdown("---")
        
        # Download button
        if members:
            json_str = json.dumps(members, indent=2)
            st.download_button(
                label="📥 Download Data (JSON)",
                data=json_str,
                file_name=f"members_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Download all member data as JSON file"
            )
        
        st.markdown("---")
        
        # Import/Export section
        st.header("📁 Import/Export")
        
        # Export button
        if members:
            export_data = json.dumps(members, indent=2)
            st.download_button(
                label="📥 Export Data (JSON)",
                data=export_data,
                file_name=f"clan_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Download all member data as JSON file"
            )
        else:
            st.info("No data to export")
        
        # Import button
        uploaded_json = st.file_uploader(
            "📤 Import Data (JSON)",
            type=['json'],
            help="Upload a JSON file to import clan data"
        )
        
        if uploaded_json is not None:
            try:
                # Read and parse the uploaded JSON
                import_data = json.load(uploaded_json)
                
                # Validate it's a dictionary
                if not isinstance(import_data, dict):
                    st.error("❌ Invalid format! JSON must be an object/dictionary.")
                else:
                    # Show preview
                    st.write("**Preview:**")
                    st.json(import_data)
                    
                    col_import, col_cancel = st.columns(2)
                    
                    with col_import:
                        if st.button("✅ Import Data", type="primary", key="import_btn"):
                            # Merge or replace based on user preference
                            st.session_state.import_data = import_data
                            st.session_state.show_import_options = True
                    
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
                ["Merge (keep existing + add new)", "Replace (overwrite all data)"],
                key="import_mode_radio"
            )
            
            col_confirm, col_cancel = st.columns(2)
            
            with col_confirm:
                if st.button("Confirm Import", type="primary", key="confirm_import_btn"):
                    if import_mode == "Replace (overwrite all data)":
                        members = st.session_state.import_data.copy()
                    else:  # Merge
                        members.update(st.session_state.import_data)
                    
                    save_members(members)
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
        
        # Clear all data button
        if st.button("🗑️ Clear All Data", type="secondary"):
            st.session_state.show_clear_dialog = True
        
        # Show clear all confirmation dialog
        if st.session_state.get('show_clear_dialog', False):
            st.warning("⚠️ This will delete ALL members!")
            
            clear_secret_input = st.text_input(
                "Enter secret key:", 
                type="password",
                key="clear_secret_input"
            )
            
            if st.button("Confirm Clear All", type="primary", key="confirm_clear_btn"):
                if clear_secret_input == DELETE_SECRET_KEY:
                    members = {}
                    save_members(members)
                    st.session_state.show_clear_dialog = False
                    st.success("✅ All data cleared")
                    st.rerun()
                else:
                    st.error("❌ Invalid secret key!")
            
            if st.button("Cancel", key="cancel_clear_btn"):
                st.session_state.show_clear_dialog = False
                st.rerun()
    
    # Main content - Add new member section
    st.subheader("➕ Add New Member")
    
    # Tab for different input methods
    tab1, tab2 = st.tabs(["📝 Manual Input", "🖼️ Upload Image"])
    
    with tab1:
        with st.form("manual_form"):
            name = st.text_input("Name", placeholder="Enter member name")
            
            col1, col2 = st.columns(2)
            with col1:
                atk_input = st.text_input("ATK", placeholder="e.g., 2M or 2000000", help="You can use M for millions (e.g., 2M = 2,000,000)")
            with col2:
                def_input = st.text_input("DEF", placeholder="e.g., 4.1M or 4100000", help="You can use M for millions (e.g., 4.1M = 4,100,000)")
            
            submit = st.form_submit_button("Add Member", type="primary")
            
            if submit:
                if name.strip():
                    atk = parse_stat_input(atk_input) if atk_input else 0
                    def_val = parse_stat_input(def_input) if def_input else 0
                    
                    # Use lowercase name as key
                    name_key = name.strip().lower()
                    
                    # Check if updating existing member
                    is_update = name_key in members
                    
                    members[name_key] = {
                        "name": name.strip(),  # Keep original capitalization for display
                        "atk": atk,
                        "def": def_val,
                        "updated_at": get_utc_timestamp()
                    }
                    save_members(members)
                    
                    if is_update:
                        st.success(f"✅ Updated {name} (ATK: {format_stat(atk)}, DEF: {format_stat(def_val)})")
                    else:
                        st.success(f"✅ Added {name} (ATK: {format_stat(atk)}, DEF: {format_stat(def_val)})")
                    st.rerun()
                else:
                    st.error("Please enter a name")
    
    with tab2:
        # Manual name input (outside form)
        img_name = st.text_input("Name", placeholder="Enter member name", key="img_name_input")
        
        uploaded_file = st.file_uploader(
            "Upload an image with ATK and DEF stats",
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="Upload an image containing ATK and DEF information"
        )
        
        # Display uploaded image
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        # Extract button (outside form)
        if st.button("🔍 Extract Stats from Image", type="primary", key="extract_btn"):
            if not img_name.strip():
                st.error("Please enter a name")
            elif uploaded_file is None:
                st.error("Please upload an image")
            else:
                with st.spinner("Analyzing image with Gemini..."):
                    # Read image bytes
                    uploaded_file.seek(0)  # Reset file pointer
                    image_bytes = uploaded_file.read()
                    mime_type = uploaded_file.type
                    
                    # Extract stats using Gemini
                    extracted_data = extract_stats_from_image(image_bytes, mime_type)
                    
                    if extracted_data:
                        # Store in session state for confirmation
                        st.session_state.extracted_data = extracted_data
                        st.session_state.extracted_name = img_name.strip()
                        st.session_state.show_confirmation = True
        
        # Show confirmation if extraction was successful
        if st.session_state.get('show_confirmation', False):
            st.success("✅ Stats extracted successfully!")
            st.write("**Review and Confirm:**")
            
            # Display extracted name (read-only)
            st.text_input("Name", value=st.session_state.extracted_name, disabled=True, key="confirm_name")
            
            # Editable stats
            col_atk, col_def = st.columns(2)
            with col_atk:
                ext_atk = st.number_input("ATK", min_value=0, value=int(st.session_state.extracted_data.get('atk', 0)), step=100000, key="confirm_atk")
            with col_def:
                ext_def = st.number_input("DEF", min_value=0, value=int(st.session_state.extracted_data.get('def', 0)), step=100000, key="confirm_def")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Confirm & Add", type="primary", key="confirm_add_btn"):
                    # Use lowercase name as key
                    name_key = st.session_state.extracted_name.lower()
                    
                    # Check if updating existing member
                    is_update = name_key in members
                    
                    members[name_key] = {
                        "name": st.session_state.extracted_name,  # Keep original capitalization
                        "atk": int(ext_atk),
                        "def": int(ext_def),
                        "updated_at": get_utc_timestamp()
                    }
                    save_members(members)
                    
                    # Clear session state
                    st.session_state.show_confirmation = False
                    st.session_state.pop('extracted_data', None)
                    st.session_state.pop('extracted_name', None)
                    
                    if is_update:
                        st.success(f"✅ Updated {st.session_state.extracted_name}!")
                    else:
                        st.success(f"✅ Added {st.session_state.extracted_name}!")
                    st.rerun()
            
            with col_b:
                if st.button("❌ Cancel", key="cancel_btn"):
                    st.session_state.show_confirmation = False
                    st.session_state.pop('extracted_data', None)
                    st.session_state.pop('extracted_name', None)
                    st.rerun()
    
    st.markdown("---")
    
    # Members list section (completely separate from forms)
    st.subheader("👥 Current Members")
    
    if not members:
        st.info("No members added yet. Add your first member!")
    else:
        # Display members in a table-like format
        # Sort by name for consistent display
        sorted_members = sorted(members.items())
        
        for name_key, member in sorted_members:
            cols = st.columns([3, 1, 1, 1])
            
            with cols[0]:
                st.write(f"**{member['name']}**")
                # Display timestamp if available
                if 'updated_at' in member:
                    st.caption(f"🕒 {member['updated_at']}")
                else:
                    st.caption("🕒 No timestamp")
            with cols[1]:
                st.write(f"⚔️ {format_stat(member['atk'])}")
            with cols[2]:
                st.write(f"🛡️ {format_stat(member['def'])}")
            with cols[3]:
                if st.button("❌", key=f"delete_{name_key}"):
                    # Store which member to delete in session state
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
                key="delete_secret_input"
            )
            
            col_confirm, col_cancel = st.columns(2)
            
            with col_confirm:
                if st.button("🗑️ Confirm Delete", type="primary", key="confirm_delete_btn"):
                    if secret_input == DELETE_SECRET_KEY:
                        deleted_name = members[st.session_state.delete_pending]['name']
                        del members[st.session_state.delete_pending]
                        save_members(members)
                        st.session_state.show_delete_dialog = False
                        st.session_state.pop('delete_pending', None)
                        st.success(f"✅ Deleted {deleted_name}")
                        st.rerun()
                    else:
                        st.error("❌ Invalid secret key!")
            
            with col_cancel:
                if st.button("❌ Cancel", key="cancel_delete_btn"):
                    st.session_state.show_delete_dialog = False
                    st.session_state.pop('delete_pending', None)
                    st.rerun()
    
    # Display JSON data at the bottom (optional, for debugging)
    with st.expander("📄 View Raw JSON Data"):
        st.json(members)

if __name__ == "__main__":
    main()
