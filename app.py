import streamlit as st
import json
import os
import re
from groq import Groq
from duckduckgo_search import DDGS # The Web Browser

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Sekai-Hub", page_icon="🌐", layout="wide", initial_sidebar_state="expanded")

if "game_active" not in st.session_state: st.session_state.game_active = False
if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "model_name" not in st.session_state: st.session_state.model_name = "llama-3.3-70b-versatile"
if "current_stats" not in st.session_state: st.session_state.current_stats = "Initializing..."
if "socials" not in st.session_state: st.session_state.socials = {}
if "event_log" not in st.session_state: st.session_state.event_log = []
if "world_context" not in st.session_state: st.session_state.world_context = "" # Live Web Data
if "director_log" not in st.session_state: st.session_state.director_log = "" # AI Thoughts

# Ensure Folders
if not os.path.exists('saves'): os.makedirs('saves')
if not os.path.exists('presets'): os.makedirs('presets')

# --- 2. THE WEB SEARCH ENGINE ---
def search_the_web(query):
    """Real-time Wiki Lookup"""
    try:
        with DDGS() as ddgs:
            # Search for text
            results = list(ddgs.text(query, max_results=3))
            if results:
                summary = "\n".join([f"- {r['body']}" for r in results])
                return summary
    except Exception as e:
        return f"Offline Mode (Search failed: {e})"
    return "No info found."

def play_sound(trigger_text):
    trigger_text = trigger_text.lower()
    sounds = {
        "boom": "https://www.myinstants.com/media/sounds/vine-boom.mp3",
        "punch": "https://www.myinstants.com/media/sounds/punch-sound-effect.mp3",
        "flash": "https://www.myinstants.com/media/sounds/flash-sound-effect.mp3"
    }
    for key, url in sounds.items():
        if key in trigger_text:
            st.markdown(f'<audio autoplay style="display:none;"><source src="{url}" type="audio/mp3"></audio>', unsafe_allow_html=True)
            break

def apply_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400&display=swap');
        .stApp { background-color: #0a0a0f; color: #E0E0E0; font-family: 'Roboto', sans-serif; }
        
        .director-box {
            background-color: #1a1a2e; border-left: 4px solid #ffcc00;
            padding: 10px; margin-bottom: 10px; font-family: monospace; font-size: 0.85em; color: #aaa;
        }
        
        .user-bubble {
            background: linear-gradient(135deg, #1c4e80, #2a6fdb);
            color: white; padding: 15px; border-radius: 20px 20px 0px 20px;
            margin-bottom: 15px; text-align: right; max-width: 80%; margin-left: auto;
        }
        .ai-bubble {
            background: linear-gradient(135deg, #1a1a1a, #252525);
            color: #ff80ff; padding: 15px; border-radius: 20px 20px 20px 0px;
            margin-bottom: 15px; text-align: left; max-width: 80%; margin-right: auto;
            border-left: 4px solid #d500f9;
        }
        .stat-card { background: rgba(0, 255, 0, 0.05); border: 1px solid #00ff00; padding: 10px; border-radius: 8px; margin-bottom: 5px; color: #00ff00; font-family: 'Orbitron', monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA PROCESSING ---
def process_response(text):
    # EXTRACT DIRECTOR THOUGHTS [DIRECTOR]...[/DIRECTOR]
    director_match = re.search(r"\[DIRECTOR\](.*?)\[/DIRECTOR\]", text, flags=re.DOTALL)
    if director_match:
        thought = director_match.group(1).strip()
        st.session_state.director_log = thought # Save for display
        text = text.replace(director_match.group(0), "") # Remove from chat

    # EXTRACT STATS
    stat_match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    if stat_match:
        st.session_state.current_stats = stat_match.group(1).strip()

    # EXTRACT SOCIALS
    npc_matches = re.findall(r"\|\|\s*SOCIAL\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    for npc_data in npc_matches:
        parts = [p.strip() for p in npc_data.split('|') if p.strip()]
        name, rel, status, bio = "Unknown", "Unknown", "Unknown", "No info"
        for p in parts:
            if p.startswith("Name:"): name = p.replace("Name:", "").strip()
            elif p.startswith("Rel:"): rel = p.replace("Rel:", "").strip()
            elif p.startswith("Status:"): status = p.replace("Status:", "").strip()
            elif p.startswith("Bio:"): bio = p.replace("Bio:", "").strip()
        if name != "Unknown": st.session_state.socials[name] = {"rel": rel, "status": status, "bio": bio}

    # EXTRACT EVENTS
    event_matches = re.findall(r"\|\|\s*EVENT\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    for event_desc in event_matches:
        clean = event_desc.strip()
        if not st.session_state.event_log or st.session_state.event_log[-1] != clean: st.session_state.event_log.append(clean)

    # CLEAN UP
    if "||" in text: text = text.split("||")[0]
    text = re.sub(r'(".*?")', r'<span style="color:#00ffff; font-weight:bold;">\1</span>', text, flags=re.DOTALL)
    text = text.replace("*", "") 
    text = text.replace("\n", "<br>")
    
    play_sound(text)
    return text

def extract_stats(text):
    match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    return match.group(1).strip() if match else st.session_state.current_stats

def load_json_files(prefix):
    files = {}
    for filename in os.listdir('.'):
        if filename.startswith(prefix) and filename.endswith('.json'):
            with open(filename, 'r') as f:
                data = json.load(f)
                key = data.get('world_name', filename)
                files[key] = data
    return files

def autosave():
    if st.session_state.game_active:
        safe = "".join([c for c in st.session_state.character['name'] if c.isalpha() or c.isdigit()]).rstrip()
        data = {
            "character": st.session_state.character,
            "world": st.session_state.world,
            "history": st.session_state.messages,
            "stats": st.session_state.current_stats,
            "socials": st.session_state.socials,
            "events": st.session_state.event_log,
            "context": st.session_state.world_context
        }
        with open(f"saves/autosave_{safe}.json", 'w') as f: json.dump(data, f)

def generate_ai_response():
    client = Groq(api_key=st.session_state.api_key)
    
    # DYNAMIC SEARCH: Does the last user message ask for info?
    last_user_msg = st.session_state.messages[-1]['content'] if st.session_state.messages else ""
    live_search_data = ""
    
    # If the AI Director thinks we need info, we search (Simplified for speed)
    # We pass a strict instruction to the model to use [SEARCH: query] if it needs info
    # But for now, we rely on the pre-loaded context.
    
    with st.spinner("AI Director is searching & thinking..."):
        try:
            resp = client.chat.completions.create(
                model=st.session_state.model_name,
                messages=st.session_state.messages,
                temperature=0.8,
                max_tokens=1024
            )
            msg = resp.choices[0].message.content
            if not msg: return False
            
            st.session_state.messages.append({"role": "assistant", "content": msg})
            match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", msg, flags=re.DOTALL)
            if match: st.session_state.current_stats = match.group(1).strip()
            
            process_response(msg) 
            autosave()
            return True
        except Exception as e:
            st.error(f"AI Brain Error: {e}")
            return False

def reroll_callback():
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
    if generate_ai_response(): st.rerun()

def continue_callback():
    if generate_ai_response(): st.rerun()

apply_theme()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💠 SEKAI-HUB")
    if not st.session_state.api_key: st.session_state.api_key = st.text_input("Groq API Key", type="password")
    st.session_state.model_name = st.selectbox("🧠 Brain", ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile"])

    if st.session_state.game_active:
        t1, t2, t3, t4 = st.tabs(["📊 Status", "👥 Socials", "🌍 Lore", "🎬 Director"])
        with t1:
            for s in st.session_state.current_stats.split('|'): 
                if s.strip(): st.markdown(f'<div class="stat-card">{s.strip()}</div>', unsafe_allow_html=True)
            if st.button("💾 Save"): autosave(); st.toast("Saved")
        with t2:
            if not st.session_state.socials: st.info("None")
            for n, d in st.session_state.socials.items():
                with st.expander(f"{n} ({d['rel']})"):
                    st.markdown(f"**Status:** {d['status']}<br><small>{d['bio']}</small>", unsafe_allow_html=True)
        with t3:
            st.caption("Live Internet Data")
            st.text_area("Context", value=st.session_state.world_context, height=300, disabled=True)
        with t4:
            st.caption("AI Thought Process")
            st.markdown(f'<div class="director-box">{st.session_state.director_log}</div>', unsafe_allow_html=True)

    st.divider()
    if st.session_state.game_active and st.button("🛑 Exit"): st.session_state.game_active = False; st.rerun()

# --- MAIN MENU ---
if not st.session_state.api_key: st.warning("Enter API Key"); st.stop()
worlds = load_json_files('world_')

if not st.session_state.game_active:
    st.title("⚔️ Sekai-Hub: Auto-RPG")
    tab1, tab2, tab3 = st.tabs(["🆕 New", "👤 Preset", "📂 Load"])
    
    with tab2:
        presets = [f for f in os.listdir('presets') if f.endswith('.json')]
        sel_pre = st.selectbox("Preset", ["None"] + presets)
        pre_dat = json.load(open(f"presets/{sel_pre}")) if sel_pre != "None" else {}
    
    with tab1:
        sel_w = st.selectbox("World", list(worlds.keys()))
        if sel_w:
            w_dat = worlds[sel_w]
            st.info("📅 **World Timeline:**")
            arcs = w_dat.get('arcs', {})
            sorted_arcs = sorted(arcs.items(), key=lambda x: x[1])
            if sorted_arcs: st.caption(f"{sorted_arcs[0][0]} -> {sorted_arcs[-1][0]}")

            with st.form("new"):
                st.subheader("Identity")
                name = st.text_input("Name", value=pre_dat.get("name", ""))
                race = st.selectbox("Race", w_dat.get('races', ["Human"]))
                align = st.select_slider("Alignment", ["Heroic", "Neutral", "Evil"], value=pre_dat.get("align", "Neutral"))
                looks = st.text_area("Appearance", value=pre_dat.get("looks", ""))
                pers = st.text_area("Personality", value=pre_dat.get("personality", ""))
                backstory = st.text_area("Backstory", value=pre_dat.get("backstory", ""))
                
                st.subheader("Start")
                c1, c2 = st.columns(2)
                with c1:
                    t_arc = st.selectbox("Starting Arc", list(w_dat['arcs'].keys()))
                    t_age = st.number_input("Age", 1, 1000, 16)
                with c2:
                    mode = st.radio("Mode", ["Born as Baby", "Drop-in at Target Age"])
                    cust_p = st.text_input("Power", value=pre_dat.get("power", ""))
                
                save_pre = st.checkbox("Save Preset")

                if st.form_submit_button("Initializing... (This searches the web)"):
                    if save_pre:
                        with open(f"presets/{name}.json", 'w') as f: json.dump({"name": name, "looks": looks, "power": cust_p}, f)

                    # 1. CALCULATE TIME
                    start_year = w_dat['arcs'][t_arc]
                    if "Baby" in mode:
                        curr_year = start_year - t_age
                        age_d = 0
                        intro = "The player is being born."
                    else:
                        curr_year = start_year
                        age_d = t_age
                        intro = "The player enters the story."

                    # 2. PERFORM WEB SEARCH (THE MAGIC)
                    with st.spinner("🔍 Scanning the Multiverse (Searching Web)..."):
                        search_query = f"{w_dat['world_name']} factions power system summary key characters"
                        web_data = search_the_web(search_query)
                        st.session_state.world_context = web_data

                    # 3. BUILD PROMPT
                    sys_prompt = f"""
                    You are the Engine of an RPG in {w_dat['world_name']}.
                    
                    --- WEB KNOWLEDGE BASE ---
                    {web_data}
                    
                    --- SIMULATION DATA ---
                    Current Year: {curr_year}
                    Target Arc: {t_arc}
                    
                    --- PLAYER ---
                    Name: {name} | Race: {race} | Align: {align}
                    Age: {age_d} | Power: {cust_p}
                    Backstory: {backstory}
                    
                    --- DIRECTOR MODE (IMPORTANT) ---
                    Before writing the scene, you must output a hidden thought block:
                    [DIRECTOR]
                    1. Analyze the year {curr_year}. Who is the main villain right now?
                    2. Check the player's location.
                    3. Decide if a Canon Character or OC should appear.
                    [/DIRECTOR]
                    
                    --- DATA TAGS ---
                    || STATS | Age: {age_d} | Year: {curr_year} | Loc: [Place] ||
                    || SOCIAL | Name: [Name] | Rel: [Role] | Status: [Action] | Bio: [Lore] ||
                    || EVENT | [Major Event] ||
                    
                    Start simulation. Context: {intro}
                    """
                    
                    st.session_state.character = {"name": name, "race": race}
                    st.session_state.world = w_dat
                    st.session_state.messages = [{"role": "system", "content": sys_prompt}]
                    st.session_state.current_stats = f"Age: {age_d} | Year: {curr_year}"
                    st.session_state.socials = {}
                    st.session_state.event_log = []
                    
                    if generate_ai_response():
                        st.session_state.game_active = True
                        st.rerun()

    with tab3:
        saves = [f for f in os.listdir('saves') if f.endswith('.json')]
        if saves:
            if st.button("Load"):
                with open(f"saves/{st.selectbox('File', saves)}") as f: d = json.load(f)
                st.session_state.character = d['character']
                st.session_state.world = d['world']
                st.session_state.messages = d['history']
                st.session_state.current_stats = d.get('stats', "")
                st.session_state.socials = d.get('socials', {})
                st.session_state.event_log = d.get('events', [])
                st.session_state.world_context = d.get('context', "")
                st.session_state.game_active = True
                st.rerun()

else:
    st.markdown(f"### 🌍 {st.session_state.world['world_name']} | 👤 {st.session_state.character['name']}")
    
    with st.container():
        for m in st.session_state.messages:
            if m["role"]=="user": st.markdown(f'<div class="user-bubble">{m["content"]}</div>', unsafe_allow_html=True)
            elif m["role"]=="assistant": 
                # Process the Director tag out before showing
                html = process_response(m["content"])
                st.markdown(f'<div class="ai-bubble">{html}</div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 6])
    with c1: 
        if st.button("🎲 Reroll"): reroll_callback()
    with c2: 
        if st.button("⏩ Continue"): continue_callback()
    
    with st.form("act", clear_on_submit=True):
        c1, c2 = st.columns([6,1])
        with c1: inp = st.text_input("Act", placeholder="Action...", label_visibility="collapsed")
        with c2: sub = st.form_submit_button("➤")
        if sub and inp:
            st.session_state.messages.append({"role": "user", "content": inp})
            if generate_ai_response(): st.rerun()