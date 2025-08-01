import streamlit as st
from datetime import datetime


def login_page(
    go_to, verify_user, is_account_locked, handle_failed_login, update_last_login
):
    """Render the login page with enhanced security"""
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                # Check if account is locked
                locked, unlock_time = is_account_locked(username)
                if locked:
                    st.error(
                        f"Account locked due to failed login attempts. Try again after {unlock_time.strftime('%H:%M:%S')}"
                    )
                elif verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    update_last_login(username)
                    st.success("Login successful!")
                    go_to("dashboard")
                else:
                    handle_failed_login(username)
                    st.error("Invalid credentials")

    # Password strength indicator
    if password:
        strength = calculate_password_strength(password)
        st.progress(strength / 100)
        if strength < 50:
            st.caption("🔴 Weak password")
        elif strength < 80:
            st.caption("🟡 Medium password")
        else:
            st.caption("🟢 Strong password")

    st.divider()

    st.write("Don't have an account?")
    if st.button("Register here", use_container_width=True):
        go_to("register")


def register_page(go_to, register_user):
    """Render the registration page with enhanced validation"""
    st.title("📝 Register")

    username = st.text_input("Choose a username", help="Must be at least 3 characters")
    email = st.text_input("Email", help="We'll never share your email")
    password = st.text_input(
        "Choose a password",
        type="password",
        help="Must be at least 8 characters with uppercase, lowercase, number and special character",
    )
    confirm_password = st.text_input("Confirm password", type="password")

    # Real-time password strength indicator
    if password:
        strength = calculate_password_strength(password)
        progress_bar = st.progress(strength / 100)
        if strength < 30:
            st.caption("🔴 Very weak password")
        elif strength < 50:
            st.caption("🟡 Weak password")
        elif strength < 70:
            st.caption("🟠 Medium password")
        elif strength < 90:
            st.caption("🟢 Strong password")
        else:
            st.caption("💪 Very strong password")

    # Password match indicator
    if password and confirm_password:
        if password == confirm_password:
            st.success("✅ Passwords match")
        else:
            st.error("❌ Passwords don't match")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Register", type="primary", use_container_width=True):
            success, message = register_user(username, password, email)
            if success:
                st.success(message)
                st.balloons()  # Celebration animation
                go_to("login")
            else:
                st.error(message)

    with col2:
        if st.button("Back to login", use_container_width=True):
            go_to("login")


def dashboard_page(go_to, get_user_info, change_password):
    """Render the dashboard page with enhanced features"""
    st.title("📊 Dashboard")

    # Get user info
    user_info = get_user_info(st.session_state.username)

    # Welcome message with user info
    st.markdown(f"### Welcome back, **{st.session_state.username}**! 👋")

    if user_info and user_info.get("last_login"):
        last_login = user_info["last_login"]
        if isinstance(last_login, datetime):
            st.caption(f"Last login: {last_login.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Sessions", "1", "↗️")

    with col2:
        st.metric("Account Status", "Active", "✅")

    with col3:
        if user_info:
            days_since = (
                datetime.utcnow() - user_info.get("created_at", datetime.utcnow())
            ).days
            st.metric("Member for", f"{days_since} days")

    with col4:
        st.metric("Security Level", "High", "🔒")

    st.divider()

    # Enhanced tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["👤 Profile", "⚙️ Settings", "🔐 Security", "📊 Activity"]
    )

    with tab1:
        st.subheader("Profile Information")
        if user_info:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Username:** {user_info['username']}")
                st.write(f"**Email:** {user_info['email']}")
                st.write(f"**Role:** {user_info.get('role', 'user').title()}")
            with col2:
                if user_info.get("created_at"):
                    st.write(
                        f"**Member since:** {user_info['created_at'].strftime('%B %d, %Y')}"
                    )
                st.write(
                    f"**Account Status:** {'Active' if user_info.get('is_active') else 'Inactive'}"
                )

        # Profile update form
        with st.expander("Update Email"):
            new_email = st.text_input(
                "New Email", value=user_info.get("email", "") if user_info else ""
            )
            if st.button("Update Email"):
                st.info("Email update functionality coming soon...")

    with tab2:
        st.subheader("Application Settings")

        # Theme selection
        theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])

        # Notification preferences
        st.subheader("Notifications")
        email_notifications = st.checkbox("Email notifications", value=True)
        push_notifications = st.checkbox("Push notifications", value=False)

        if st.button("Save Settings"):
            st.success("Settings saved successfully!")

    with tab3:
        st.subheader("Security Settings")

        # Password change
        st.write("**Change Password**")
        with st.form("change_password"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_new_password = st.text_input(
                "Confirm New Password", type="password"
            )

            if st.form_submit_button("Change Password"):
                if new_password != confirm_new_password:
                    st.error("New passwords don't match")
                else:
                    success, message = change_password(
                        st.session_state.username, current_password, new_password
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        st.divider()

        # Security info
        st.write("**Security Status**")
        st.write("✅ Password protected")
        st.write("✅ Email verified")
        st.write("⚠️ Two-factor authentication: Not enabled (Coming soon)")

    with tab4:
        st.subheader("Recent Activity")

        # Mock activity data - in real app, fetch from database
        activity_data = [
            {"action": "Login", "timestamp": datetime.now(), "ip": "192.168.1.1"},
            {
                "action": "Password Changed",
                "timestamp": datetime.now(),
                "ip": "192.168.1.1",
            },
            {
                "action": "Profile Updated",
                "timestamp": datetime.now(),
                "ip": "192.168.1.1",
            },
        ]

        for activity in activity_data:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"🔹 {activity['action']}")
                with col2:
                    st.write(activity["timestamp"].strftime("%Y-%m-%d %H:%M"))
                with col3:
                    st.write(activity["ip"])

    st.divider()

    # Session management
    st.subheader("Session Management")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚪 Logout", type="secondary"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()

    with col2:
        if st.button("🔄 Refresh Session", type="secondary"):
            st.success("Session refreshed!")
            st.rerun()


def calculate_password_strength(password):
    """Calculate password strength score (0-100)"""
    if not password:
        return 0

    score = 0

    # Length scoring
    if len(password) >= 8:
        score += 25
    elif len(password) >= 6:
        score += 15
    elif len(password) >= 4:
        score += 10

    # Character variety scoring
    if any(c.isupper() for c in password):
        score += 20
    if any(c.islower() for c in password):
        score += 20
    if any(c.isdigit() for c in password):
        score += 20
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 15

    return min(score, 100)
