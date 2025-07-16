import streamlit as st
import sqlite3
import json
import datetime
import requests
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional

load_dotenv()

st.set_page_config(
    page_title="WorkZen - Christian Workplace Stress Assistant",
    page_icon="✝️",
    layout="wide"
)

DAILY_VERSES = [
    {
        "verse": "Matthew 11:28-30",
        "text": "Come to me, all you who are weary and burdened, and I will give you rest. Take my yoke upon you and learn from me, for I am gentle and humble in heart, and you will find rest for your souls. For my yoke is easy and my burden is light.",
        "theme": "Rest and Relief",
        "application": "When work feels overwhelming, remember that Christ invites you to find rest in Him."
    },
    {
        "verse": "Philippians 4:6-7",
        "text": "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus.",
        "theme": "Anxiety and Peace",
        "application": "Before that stressful meeting, take a moment to pray and surrender your worries to God."
    },
    {
        "verse": "Isaiah 40:31",
        "text": "But those who hope in the Lord will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint.",
        "theme": "Strength and Endurance",
        "application": "When you feel burned out, remember that God is your source of renewed strength."
    },
    {
        "verse": "1 Peter 5:7",
        "text": "Cast all your anxiety on him because he cares for you.",
        "theme": "Casting Burdens",
        "application": "Your workplace stress matters to God. He cares about your daily struggles."
    },
    {
        "verse": "Jeremiah 29:11",
        "text": "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, to give you hope and a future.",
        "theme": "Hope and Purpose",
        "application": "When career uncertainty causes stress, trust in God's good plans for your life."
    },
    {
        "verse": "2 Corinthians 12:9",
        "text": "But he said to me, 'My grace is sufficient for you, for my power is made perfect in weakness.' Therefore I will boast all the more gladly about my weaknesses, so that Christ's power may rest on me.",
        "theme": "Strength in Weakness",
        "application": "Your workplace challenges are opportunities for God's strength to shine through you."
    },
    {
        "verse": "Psalm 46:1-2",
        "text": "God is our refuge and strength, an ever-present help in trouble. Therefore we will not fear, though the earth give way and the mountains fall into the heart of the sea.",
        "theme": "God as Refuge",
        "application": "In workplace crises, God is your stable foundation when everything else feels uncertain."
    }
]

def init_database():
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stress_checkins (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            date DATE,
            morning_stress INTEGER,
            evening_stress INTEGER,
            workload_rating INTEGER,
            energy_level INTEGER,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prayer_requests (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            request_text TEXT,
            category VARCHAR(50),
            is_answered BOOLEAN DEFAULT FALSE,
            answered_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            answered_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_daily_verse():
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    return DAILY_VERSES[day_of_year % len(DAILY_VERSES)]

def get_ai_response(user_message: str, context: Dict) -> str:
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return "I'm having trouble connecting right now. Please try again in a moment."
    
    crisis_keywords = ["suicide", "kill myself", "hopeless", "can't go on", "hurt myself", "end it all"]
    if any(keyword in user_message.lower() for keyword in crisis_keywords):
        return """I'm deeply concerned about what you're sharing. Please know that God loves you and your life has immense value. Please reach out for immediate support:

🆘 **Crisis Resources:**
- 988 Suicide & Crisis Lifeline: Call or text 988
- Crisis Text Line: Text HOME to 741741
- SAMHSA Helpline: 1-800-662-4357

**Christian Crisis Support:**
- Focus on the Family: 1-800-A-FAMILY
- New Life Ministries: 1-800-NEW-LIFE

**Remember God's Truth:**
"For I know the plans I have for you," declares the Lord, "plans to prosper you and not to harm you, to give you hope and a future." - Jeremiah 29:11

Please also connect with your pastor, a Christian counselor, or a trusted believer. You are not alone, and God has a purpose for your life."""

    system_prompt = """You are WorkZen, a Christian workplace stress assistant. You provide:

1. Biblical encouragement and wisdom for workplace challenges
2. Practical stress management techniques grounded in Christian faith
3. Prayer support and spiritual guidance
4. Compassionate listening and validation

Guidelines:
- Always integrate biblical wisdom naturally, not forced
- Include relevant Bible verses when appropriate
- Provide practical, actionable advice
- Be warm, encouraging, and empathetic
- Keep responses under 300 words
- End with a question to continue the conversation

Current context:"""
    
    if context.get('recent_stress_level'):
        system_prompt += f"\n- User's recent stress level: {context['recent_stress_level']}/10"
    
    if context.get('time_of_day'):
        hour = datetime.datetime.now().hour
        if hour < 10:
            system_prompt += "\n- Morning - focus on starting the day with God"
        elif hour > 17:
            system_prompt += "\n- Evening - focus on reflection and rest"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 400,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        elif response.status_code == 401:
            return "I'm having authentication issues with my API. Please check that your API key is valid."
        elif response.status_code == 429:
            return "I'm getting too many requests right now. Please wait a moment and try again."
        else:
            return f"I'm experiencing some technical difficulties (Error {response.status_code}). Please try again in a moment."
            
    except Exception as e:
        return "I'm having trouble connecting right now. Please try again in a moment."

def get_or_create_user(username: str) -> int:
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if user:
        user_id = user[0]
    else:
        cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
        user_id = cursor.lastrowid
        conn.commit()
    
    conn.close()
    return user_id

def save_conversation(user_id: int, message: str, response: str):
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO conversations (user_id, message, response)
        VALUES (?, ?, ?)
    ''', (user_id, message, response))
    
    conn.commit()
    conn.close()

def save_stress_checkin(user_id: int, stress_data: Dict):
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO stress_checkins 
        (user_id, date, morning_stress, evening_stress, workload_rating, energy_level, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        stress_data['date'],
        stress_data.get('morning_stress'),
        stress_data.get('evening_stress'),
        stress_data.get('workload_rating'),
        stress_data.get('energy_level'),
        stress_data.get('notes', '')
    ))
    
    conn.commit()
    conn.close()

def get_user_stress_history(user_id: int) -> pd.DataFrame:
    conn = sqlite3.connect('workzen.db')
    df = pd.read_sql_query('''
        SELECT date, morning_stress, evening_stress, workload_rating, energy_level
        FROM stress_checkins
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT 30
    ''', conn, params=(user_id,))
    conn.close()
    return df

def save_prayer_request(user_id: int, request_text: str, category: str = "work"):
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO prayer_requests (user_id, request_text, category)
        VALUES (?, ?, ?)
    ''', (user_id, request_text, category))
    
    conn.commit()
    conn.close()

def get_user_prayer_requests(user_id: int):
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, request_text, category, is_answered, answered_text, created_at, answered_at
        FROM prayer_requests
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    
    requests = cursor.fetchall()
    conn.close()
    return requests

def mark_prayer_answered(prayer_id: int, answered_text: str):
    conn = sqlite3.connect('workzen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE prayer_requests
        SET is_answered = TRUE, answered_text = ?, answered_at = ?
        WHERE id = ?
    ''', (answered_text, datetime.datetime.now(), prayer_id))
    
    conn.commit()
    conn.close()

def main():
    init_database()
    
    st.sidebar.title("✝️ WorkZen")
    st.sidebar.markdown("*Your Christian workplace stress companion*")
    
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if not st.session_state.username:
        st.sidebar.subheader("Welcome!")
        username = st.sidebar.text_input("Enter your name to start:")
        if st.sidebar.button("Start"):
            if username:
                st.session_state.username = username
                st.session_state.user_id = get_or_create_user(username)
                st.rerun()
    else:
        st.sidebar.success(f"Welcome back, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.username = None
            st.session_state.user_id = None
            st.rerun()
    
    if st.session_state.username:
        tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📊 Check-in", "🙏 Prayer", "📈 Progress"])
        
        with tab1:
            st.header("Chat with WorkZen")
            
            daily_verse = get_daily_verse()
            with st.expander("📖 Today's Encouraging Verse", expanded=False):
                st.markdown(f"**{daily_verse['verse']}**")
                st.markdown(f"*\"{daily_verse['text']}\"*")
                st.markdown(f"**Today's Application:** {daily_verse['application']}")
                st.markdown(f"**Theme:** {daily_verse['theme']}")
            
            if 'messages' not in st.session_state:
                st.session_state.messages = []
                welcome_msg = f"""👋 Welcome to WorkZen, {st.session_state.username}! I'm here to provide biblical encouragement and practical support for your workplace challenges.

Feel free to share:
• What's stressing you at work today
• Difficult situations you're facing  
• Prayer requests for your workplace
• Questions about faith and work

How can I support you today?"""
                st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
            
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            if prompt := st.chat_input("How can I pray for you and support you today?"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                context = {
                    "user_id": st.session_state.user_id,
                    "recent_stress_level": 5,
                    "time_of_day": datetime.datetime.now().hour
                }
                
                with st.spinner("🙏 Praying and thinking..."):
                    response = get_ai_response(prompt, context)
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                save_conversation(st.session_state.user_id, prompt, response)
                
                st.rerun()
        
        with tab2:
            st.header("Daily Stress Check-in")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Morning Check-in")
                morning_stress = st.slider("Morning stress level", 1, 10, 5, key="morning", 
                                         help="1 = Very peaceful, 10 = Extremely stressed")
                workload_rating = st.slider("Expected workload today", 1, 10, 5, key="workload",
                                          help="1 = Very light, 10 = Overwhelming")
                energy_level = st.slider("Energy level", 1, 10, 5, key="energy",
                                        help="1 = Exhausted, 10 = Energized")
            
            with col2:
                st.subheader("Evening Reflection")
                evening_stress = st.slider("Evening stress level", 1, 10, 5, key="evening",
                                         help="1 = Very peaceful, 10 = Extremely stressed")
                notes = st.text_area("Notes about your day", key="notes", 
                                    placeholder="What happened today? How did God show up?")
            
            if st.button("Save Check-in", type="primary"):
                stress_data = {
                    'date': datetime.date.today(),
                    'morning_stress': morning_stress,
                    'evening_stress': evening_stress,
                    'workload_rating': workload_rating,
                    'energy_level': energy_level,
                    'notes': notes
                }
                save_stress_checkin(st.session_state.user_id, stress_data)
                st.success("Check-in saved! 🎉 May God bless your day.")
        
        with tab3:
            st.header("🙏 Prayer Requests")
            
            tab3a, tab3b = st.tabs(["Submit Request", "My Prayers"])
            
            with tab3a:
                st.subheader("Submit a Prayer Request")
                
                with st.form("prayer_request_form"):
                    request_text = st.text_area("What would you like prayer for?", 
                                               placeholder="Share your workplace challenges, concerns, or gratitudes...")
                    category = st.selectbox("Category", 
                                          ["work", "relationships", "health", "finances", "family", "other"])
                    
                    submitted = st.form_submit_button("Submit Prayer Request", type="primary")
                    
                    if submitted and request_text:
                        save_prayer_request(st.session_state.user_id, request_text, category)
                        st.success("Prayer request submitted! 🙏")
                        st.balloons()
            
            with tab3b:
                st.subheader("My Prayer Requests")
                
                prayers = get_user_prayer_requests(st.session_state.user_id)
                
                if prayers:
                    for prayer in prayers:
                        prayer_id, text, category, is_answered, answered_text, created_at, answered_at = prayer
                        
                        with st.expander(f"{category.title()} - {created_at[:10]}"):
                            st.write(f"**Request:** {text}")
                            
                            if is_answered:
                                st.success("✅ Answered!")
                                st.write(f"**Testimony:** {answered_text}")
                                if answered_at:
                                    st.write(f"**Answered on:** {answered_at[:10]}")
                            else:
                                st.info("🤲 Still praying...")
                                answered_response = st.text_area("Mark as answered with testimony:", 
                                                                key=f"answer_{prayer_id}")
                                if st.button("Mark as Answered", key=f"btn_{prayer_id}"):
                                    if answered_response:
                                        mark_prayer_answered(prayer_id, answered_response)
                                        st.success("Praise God! Prayer marked as answered! 🙌")
                                        st.rerun()
                else:
                    st.info("No prayer requests yet. Submit your first request above!")
        
        with tab4:
            st.header("Your Spiritual & Wellness Journey")
            
            df = get_user_stress_history(st.session_state.user_id)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                
                fig = px.line(df, x='date', y=['morning_stress', 'evening_stress'],
                             title='Stress Levels Over Time',
                             labels={'value': 'Stress Level', 'date': 'Date'},
                             color_discrete_map={
                                 'morning_stress': '#ff6b6b',
                                 'evening_stress': '#4ecdc4'
                             })
                st.plotly_chart(fig, use_container_width=True)
                
                fig2 = px.scatter(df, x='workload_rating', y='energy_level',
                                 title='Workload vs Energy Level',
                                 labels={'workload_rating': 'Workload', 'energy_level': 'Energy'},
                                 color='morning_stress',
                                 color_continuous_scale='RdYlGn_r')
                st.plotly_chart(fig2, use_container_width=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_morning = df['morning_stress'].mean()
                    st.metric("Avg Morning Stress", f"{avg_morning:.1f}")
                with col2:
                    avg_evening = df['evening_stress'].mean()
                    st.metric("Avg Evening Stress", f"{avg_evening:.1f}")
                with col3:
                    improvement = avg_morning - avg_evening
                    st.metric("Daily Improvement", f"{improvement:+.1f}")
                with col4:
                    total_checkins = len(df)
                    st.metric("Total Check-ins", total_checkins)
                
                if improvement > 0:
                    st.success("🙌 Praise God! Your stress levels are improving throughout the day. You're learning to cast your burdens on Him!")
                elif improvement < -1:
                    st.info("💙 Your evenings show more stress than mornings. Consider ending your day with prayer and reflection.")
                else:
                    st.info("📊 Your stress levels are fairly consistent. Keep tracking to identify patterns and growth opportunities.")
                    
            else:
                st.info("Complete your first check-in to see your progress and God's faithfulness in your journey!")
                
                st.markdown("---")
                st.markdown("### 📖 While You Get Started")
                verse = get_daily_verse()
                st.markdown(f"**{verse['verse']}**")
                st.markdown(f"*\"{verse['text']}\"*")
    
    else:
        st.title("✝️ WorkZen - Christian Workplace Stress Assistant")
        st.markdown("""
        ### Transform workplace stress through faith and practical wisdom
        
        WorkZen combines biblical encouragement with evidence-based stress management techniques, helping Christian professionals find peace and purpose in their work.
        
        **Features:**
        - 🗣️ **Faith-Based AI Support**: Chat with biblical guidance for work challenges
        - 📖 **Daily Bible Verses**: Encouraging scriptures for stress and mental health
        - 📊 **Spiritual Progress Tracking**: Monitor stress patterns with prayer and reflection
        - 🙏 **Prayer Request System**: Submit and track your workplace prayer needs
        - 🛠️ **Biblical Coping Strategies**: God-honoring techniques for workplace stress
        
        **"Cast all your anxiety on him because he cares for you." - 1 Peter 5:7**
        
        **Enter your name in the sidebar to begin your journey!**
        """)
        
        st.subheader("How WorkZen supports Christian professionals:")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📖 Daily Scripture**")
            st.info("Start each day with verses specifically chosen for workplace stress and mental health")
        
        with col2:
            st.markdown("**🙏 Prayer-Centered Chat**")
            st.info("Get personalized support that integrates biblical wisdom with practical coping strategies")
        
        with col3:
            st.markdown("**✝️ Faith-Based Progress**")
            st.info("Track your spiritual and emotional growth with tools rooted in Christian principles")
        
        st.subheader("📖 Today's Encouraging Verse:")
        daily_verse = get_daily_verse()
        st.markdown(f"**{daily_verse['verse']}**")
        st.markdown(f"*\"{daily_verse['text']}\"*")
        st.markdown(f"**Application:** {daily_verse['application']}")

if __name__ == "__main__":
    main()