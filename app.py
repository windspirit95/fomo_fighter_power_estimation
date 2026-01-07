import streamlit as st
import pandas as pd

# Page config
st.set_page_config(page_title="Clan Manager", layout="wide")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
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

# Login credentials
ADMIN_ID = "admin"
ADMIN_PIN = "919399"

# Bias value
BIAS_VALUE = 0.84

def calculate_power(race, base_power, mode):
    """Calculate actual power based on race and mode (ATK/DEF)"""
    if race == "Frog":
        return base_power * 1.5
    elif race == "Cat":
        if mode == "ATK":
            return base_power * 5.2
        else:
            return base_power * 2.5
    elif race == "Dog":
        if mode == "ATK":
            return base_power * 2.5
        else:
            return base_power * 5.2
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
    for member in members:
        if member['race'] == major_race:
            total += calculate_power(member['race'], member['power'], mode)
    return total

def calculate_total_power_lite(members, mode, clan_total_power):
    """Calculate total clan power for Lite mode"""
    major_power = calculate_major_race_power(members, mode)
    remaining_power = (clan_total_power - major_power) * 1.8
    return (major_power + remaining_power) * BIAS_VALUE

# Login page
if not st.session_state.logged_in:
    st.title("🛡️ Clan Manager - Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Please Login")
        user_id = st.text_input("User ID", key="login_id")
        user_pin = st.text_input("PIN Code", type="password", max_chars=6, key="login_pin")
        
        if st.button("Login", use_container_width=True):
            if user_id == ADMIN_ID and user_pin == ADMIN_PIN:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials!")

# Main app
else:
    # Header with logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("⚔️ Clan Manager")
    with col2:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Mode toggle and calculation mode
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        if st.toggle("Lite Mode", value=(st.session_state.calc_mode == 'Lite'), key="calc_mode_toggle"):
            st.session_state.calc_mode = 'Lite'
        else:
            st.session_state.calc_mode = 'Full'
    
    with col2:
        if st.toggle("Switch ATK/DEF", value=(st.session_state.clan1_mode == 'DEF')):
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
                if st.button("🗑️ Clear All", use_container_width=True, key="clear_top_1"):
                    st.session_state.clan1_members = []
                    st.rerun()
        
        # Lite mode: Total power input
        if st.session_state.calc_mode == 'Lite':
            st.number_input(
                "Total Clan Power", 
                min_value=0, 
                value=st.session_state.clan1_total_power,
                key="clan1_total_input",
                on_change=lambda: setattr(st.session_state, 'clan1_total_power', st.session_state.clan1_total_input)
            )
        
        # Add member form
        with st.expander("➕ Add New Member"):
            if st.session_state.calc_mode == 'Full':
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    race1 = st.selectbox("Race", ["Dog", "Cat", "Frog"], key="race1")
                with c2:
                    power1 = st.number_input("Power", min_value=1, value=100, key="power1")
                with c3:
                    level1 = st.number_input("Level", min_value=1, value=1, key="level1")
                with c4:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add1"):
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
                    power1_lite = st.number_input("Power", min_value=1, value=100, key="power1_lite")
                with c2:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add1_lite"):
                        st.session_state.clan1_members.append({
                            'race': major_race,
                            'power': power1_lite
                        })
                        st.rerun()
        
        # Display members table
        if st.session_state.clan1_members:
            st.markdown("#### Members")
            
            if st.session_state.calc_mode == 'Full':
                # Full mode table
                for idx, member in enumerate(st.session_state.clan1_members):
                    actual_power = calculate_power(member['race'], member['power'], 
                                                  st.session_state.clan1_mode)
                    
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.5, 0.7])
                    
                    with c1:
                        new_race = st.selectbox("", ["Dog", "Cat", "Frog"], 
                                               index=["Dog", "Cat", "Frog"].index(member['race']),
                                               key=f"race1_{idx}",
                                               label_visibility="collapsed")
                    with c2:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power1_{idx}",
                                                   label_visibility="collapsed")
                    with c3:
                        new_level = st.number_input("", min_value=1, 
                                                   value=member['level'],
                                                   key=f"level1_{idx}",
                                                   label_visibility="collapsed")
                    with c4:
                        st.markdown(f"<div style='padding-top: 8px;'>{st.session_state.clan1_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c5:
                        if st.button("🗑️", key=f"delete1_{idx}", use_container_width=True):
                            st.session_state.clan1_members.pop(idx)
                            st.rerun()
                    
                    # Update member if changed
                    if (new_race != member['race'] or new_power != member['power'] or 
                        new_level != member['level']):
                        st.session_state.clan1_members[idx] = {
                            'race': new_race,
                            'power': new_power,
                            'level': new_level
                        }
            else:
                # Lite mode table
                major_race = "Cat" if st.session_state.clan1_mode == 'ATK' else "Dog"
                for idx, member in enumerate(st.session_state.clan1_members):
                    actual_power = calculate_power(member['race'], member['power'], 
                                                  st.session_state.clan1_mode)
                    
                    c1, c2, c3 = st.columns([2, 1.5, 0.7])
                    
                    with c1:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power1_lite_{idx}",
                                                   label_visibility="collapsed")
                    with c2:
                        st.markdown(f"<div style='padding-top: 8px;'>{major_race} - {st.session_state.clan1_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c3:
                        if st.button("🗑️", key=f"delete1_lite_{idx}", use_container_width=True):
                            st.session_state.clan1_members.pop(idx)
                            st.rerun()
                    
                    # Update member if changed
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
                if st.button("🗑️ Clear All", use_container_width=True, key="clear_top_2"):
                    st.session_state.clan2_members = []
                    st.rerun()
        
        # Lite mode: Total power input
        if st.session_state.calc_mode == 'Lite':
            st.number_input(
                "Total Clan Power", 
                min_value=0, 
                value=st.session_state.clan2_total_power,
                key="clan2_total_input",
                on_change=lambda: setattr(st.session_state, 'clan2_total_power', st.session_state.clan2_total_input)
            )
        
        # Add member form
        with st.expander("➕ Add New Member"):
            if st.session_state.calc_mode == 'Full':
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    race2 = st.selectbox("Race", ["Dog", "Cat", "Frog"], key="race2")
                with c2:
                    power2 = st.number_input("Power", min_value=1, value=100, key="power2")
                with c3:
                    level2 = st.number_input("Level", min_value=1, value=1, key="level2")
                with c4:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add2"):
                        st.session_state.clan2_members.append({
                            'race': race2,
                            'power': power2,
                            'level': level2
                        })
                        st.rerun()
            else:
                # Lite mode: only major race
                major_race = "Cat" if clan2_mode == 'ATK' else "Dog"
                c1, c2 = st.columns([2, 1])
                with c1:
                    power2_lite = st.number_input("Power", min_value=1, value=100, key="power2_lite")
                with c2:
                    st.write("")
                    st.write("")
                    if st.button("Add", use_container_width=True, key="add2_lite"):
                        st.session_state.clan2_members.append({
                            'race': major_race,
                            'power': power2_lite
                        })
                        st.rerun()
        
        # Display members table
        if st.session_state.clan2_members:
            st.markdown("#### Members")
            
            if st.session_state.calc_mode == 'Full':
                # Full mode table
                for idx, member in enumerate(st.session_state.clan2_members):
                    actual_power = calculate_power(member['race'], member['power'], clan2_mode)
                    
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.5, 0.7])
                    
                    with c1:
                        new_race = st.selectbox("", ["Dog", "Cat", "Frog"], 
                                               index=["Dog", "Cat", "Frog"].index(member['race']),
                                               key=f"race2_{idx}",
                                               label_visibility="collapsed")
                    with c2:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power2_{idx}",
                                                   label_visibility="collapsed")
                    with c3:
                        new_level = st.number_input("", min_value=1, 
                                                   value=member['level'],
                                                   key=f"level2_{idx}",
                                                   label_visibility="collapsed")
                    with c4:
                        st.markdown(f"<div style='padding-top: 8px;'>{clan2_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c5:
                        if st.button("🗑️", key=f"delete2_{idx}", use_container_width=True):
                            st.session_state.clan2_members.pop(idx)
                            st.rerun()
                    
                    # Update member if changed
                    if (new_race != member['race'] or new_power != member['power'] or 
                        new_level != member['level']):
                        st.session_state.clan2_members[idx] = {
                            'race': new_race,
                            'power': new_power,
                            'level': new_level
                        }
            else:
                # Lite mode table
                major_race = "Cat" if clan2_mode == 'ATK' else "Dog"
                for idx, member in enumerate(st.session_state.clan2_members):
                    actual_power = calculate_power(member['race'], member['power'], clan2_mode)
                    
                    c1, c2, c3 = st.columns([2, 1.5, 0.7])
                    
                    with c1:
                        new_power = st.number_input("", min_value=1, 
                                                   value=member['power'],
                                                   key=f"power2_lite_{idx}",
                                                   label_visibility="collapsed")
                    with c2:
                        st.markdown(f"<div style='padding-top: 8px;'>{major_race} - {clan2_mode} Power: <b>{actual_power:.1f}</b></div>", 
                                   unsafe_allow_html=True)
                    with c3:
                        if st.button("🗑️", key=f"delete2_lite_{idx}", use_container_width=True):
                            st.session_state.clan2_members.pop(idx)
                            st.rerun()
                    
                    # Update member if changed
                    if new_power != member['power']:
                        st.session_state.clan2_members[idx] = {
                            'race': major_race,
                            'power': new_power
                        }
            
        else:
            st.info("No members yet. Add members using the form above.")
