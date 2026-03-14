#!/usr/bin/env python3
"""
Test rapido integrazione admin
"""

import streamlit as st
import sys
import os

# Setup paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from admin_test_panel import render_admin_page

def main():
    st.set_page_config(page_title="Test Admin VerificAI", layout="wide")
    
    # Session state
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'login'
    
    # Login page
    if st.session_state.current_page == 'login':
        st.title("🔐 Login Admin VerificAI")
        
        with st.form("login_form"):
            password = st.text_input("Password Admin:", type="password")
            submitted = st.form_submit_button("🔐 Login")
            
            if submitted:
                if password == "admin123":
                    st.session_state.is_admin = True
                    st.session_state.current_page = 'admin'
                    st.success("✅ Accesso abilitato!")
                    st.rerun()
                else:
                    st.error("❌ Password errata!")
        
        st.info("Password di test: **admin123**")
    
    # Admin page
    elif st.session_state.current_page == 'admin':
        if st.session_state.is_admin:
            render_admin_page()
        else:
            st.session_state.current_page = 'login'
            st.rerun()

if __name__ == "__main__":
    main()
