import streamlit as st
import json
import os
import re
import time
from groq import Groq
from duckduckgo_search import DDGS

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Sekai-Hub", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

if "game_active" not in st.session_state: st.session_state.game_active = False
if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "model_name" not in st.session_state: st.session_state.model_name = "llama-3.3-70b-versatile"
if "current_stats" not in st.session_state: st.session_state.current_stats = "Initializing..."
if "socials" not in st.session_state: st.session_state.socials = {}
if "event_log" not in st.session_state: st.session_state.event_log = []
if "world_context" not in st.session_state: st.session_state.world_context = "" 
if "director_log" not in st.session_state: st.session_state.director_log = "" 

if not os.path.exists('saves'): os.makedirs('saves')
if not os.path.exists('presets'): os.makedirs('presets')

# --- 2. ROBUST SEARCH ENGINE ---
def search_the_web(query):
    """Robust Wiki Lookup with Fallback"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"- {r['body']}" for r in results])
    except Exception:
        pass # Fail silently so game doesn't crash
    return "No live internet data available. Relying on internal AI knowledge."

# --- 3. UI & AUDIO ---
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
        
        .director-box { background-color: #1a1a2e; border-left: 4px solid #ffcc00; padding: 10px; margin-bottom: 10px; font-family: monospace; font-size: 0.85em; color: #aaa; }
        .user-bubble { background: linear-gradient(135deg, #1c4e80, #2a6fdb); color: white; padding: 15px; border-radius: 20px 20px 0px 20px; margin-bottom: 15px; text-align: right; max-width: 80%; margin-left: auto; }
        .ai-bubble { background: linear-gradient(135deg, #1a1a1a, #252525); color: #ff80ff; padding: 15px; border-radius: 20px 20px 20px 0px; margin-bottom: 15px; text-align: left; max-width: 80%; margin-right: auto; border-left: 4px solid #d500f9; }
        .stat-card { background: rgba(0, 255, 0, 0.05); border: 1px solid #00ff00; padding: 10px; border-radius: 8px; margin-bottom: 5px; color: #00ff00; font-family: 'Orbitron', monospace; }
        .arc-current { color: #00ffff; font-weight: bold; border-left: 3px solid #00ffff; padding-left: 5px; background: rgba(0,255,255,0.05); }
        .arc-future { color: #333; border-left: 3px solid #333; padding-left: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA PROCESSING ---
def process_response(text):
    # EXTRACT HIDDEN DATA
    director_match = re.search(r"\[DIRECTOR\](.*?)\[/DIRECTOR\]", text, flags=re.DOTALL)
    if director_match:
        st.session_state.director_log = director_match.group(1).strip()
        text = text.replace(director_match.group(0), "")

    stat_match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    if stat_match: st.session_state.current_stats = stat_match.group(1).strip()

    event_matches = re.findall(r"\|\|\s*EVENT\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    for ev in event_matches:
        cl = ev.strip()
        if not st.session_state.event_log or st.session_state.event_log[-1] != cl: st.session_state.event_log.append(cl)

    npc_matches = re.findall(r"\|\|\s*SOCIAL\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    for npc in npc_matches:
        parts = [p.strip() for p in npc.split('|') if p.strip()]
        n, r, s, b = "Unknown", "?", "?", "?"
        for p in parts:
            if "Name:" in p: n = p.replace("Name:", "").strip()
            elif "Rel:" in p: r = p.replace("Rel:", "").strip()
            elif "Status:" in p: s = p.replace("Status:", "").strip()
            elif "Bio:" in p: b = p.replace("Bio:", "").strip()
        if n != "Unknown": st.session_state.socials[n] = {"rel":r, "status":s, "bio":b}

    # VISUAL CLEANUP
    if "||" in text: text = text.split("||")[0]
    text = re.sub(r'(".*?")', r'<span style="color:#00ffff; font-weight:bold;">\1</span>', text, flags=re.DOTALL)
    text = text.replace("*", "").replace("\n", "<br>")
    
    play_sound(text)
    return text

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
    with st.spinner("🧠 AI Director is creating the scene..."):
        try:
            resp = client.chat.completions.create(
                model=st.session_state.model_name,
                messages=st.session_state.messages,
                temperature=0.8
            )
            msg = resp.choices[0].message.content
            
            # BLANK MESSAGE FIX
            if not msg or not msg.strip():
                st.error("AI Error: Blank Response. Retrying...")
                time.sleep(1)
                return generate_ai_response() # Retry once
                
            st.session_state.messages.append({"role": "assistant", "content": msg})
            
            # Immediate Stat Update
            match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", msg, flags=re.DOTALL)
            if match: st.session_state.current_stats = match.group(1).strip()
            
            process_response(msg)
            autosave()
            return True
        except Exception as e:
            st.error(f"Critical AI Error: {e}")
            return False

def reroll_callback():
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
    if generate_ai_response(): st.rerun()

def continue_callback():
    if generate_ai_response(): st.rerun()

def load_json_files():
    files = {}
    for f in os.listdir('.'):
        if f.startswith('world_') and f.endswith('.json'):
            try: files[json.load(open(f))['world_name']] = json.load(open(f))
            except: pass
    return files

apply_theme()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💠 SEKAI-HUB")
    if not st.session_state.api_key: st.session_state.api_key = st.text_input("Groq API Key", type="password")
    st.session_state.model_name = st.selectbox("Brain", ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile"])

    if st.session_state.game_active:
        t1, t2, t3, t4 = st.tabs(["📊 Stats", "👥 Socials", "🌍 Lore", "🎬 Director"])
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
            st.text_area("Web Context", value=st.session_state.world_context, height=300, disabled=True)
        with t4:
            st.markdown(f'<div class="director-box">{st.session_state.director_log}</div>', unsafe_allow_html=True)

    st.divider()
    if st.session_state.game_active and st.button("🛑 Exit"): st.session_state.game_active = False; st.rerun()

# --- MAIN MENU ---
if not st.session_state.api_key: st.warning("Enter API Key"); st.stop()
worlds = load_json_files()

if not st.session_state.game_active:
    st.title("⚔️ Sekai-Hub: Auto-RPG")
    tab1, tab2, tab3 = st.tabs(["🆕 New", "👤 Preset", "📂 Load"])
    
    with tab2:
        presets = [f for f in os.listdir('presets') if f.endswith('.json')]
        sel_pre = st.selectbox("Preset", ["None"] + presets)
        pre_dat = json.load(open(f"presets/{sel_pre}")) if sel_pre != "None" else {}
    
    with tab1:
        if not worlds: st.error("No World JSONs found!"); st.stop()
        sel_w_name = st.selectbox("World", list(worlds.keys()))
        w_dat = worlds[sel_w_name]
        
        # --- NEW ARC SYSTEM ---
        arcs = w_dat.get('arcs', {})
        sorted_arcs = sorted(arcs.items(), key=lambda x: x[1])
        
        st.info("📅 **Timeline Selection**")
        c_arc, c_age = st.columns([2, 1])
        with c_arc:
            # User picks the Arc Name directly
            t_arc_name = st.selectbox("Start in which Arc?", list(w_dat['arcs'].keys()))
        with c_age:
            t_age = st.number_input("Your Age", 1, 1000, 16)
            
        with st.form("new"):
            st.subheader("Identity")
            name = st.text_input("Name", value=pre_dat.get("name", ""))
            race = st.selectbox("Race", w_dat.get('races', ["Human"]))
            align = st.select_slider("Alignment", ["Heroic", "Neutral", "Evil"], value=pre_dat.get("align", "Neutral"))
            looks = st.text_area("Appearance", value=pre_dat.get("looks", ""))
            pers = st.text_area("Personality", value=pre_dat.get("personality", ""))
            backstory = st.text_area("Backstory (Origin)", value=pre_dat.get("backstory", ""))
            cust_p = st.text_input("Power", value=pre_dat.get("power", ""))
            
            # TOGGLE FOR BIRTH SIMULATION
            start_as_baby = st.checkbox("Reincarnation Mode (Start as Baby 0 years old instead of selected Age)")
            save_pre = st.checkbox("Save Preset")

            if st.form_submit_button("Launch Simulation"):
                if save_pre:
                    with open(f"presets/{name}.json", 'w') as f: json.dump({"name": name, "looks": looks, "power": cust_p, "backstory":backstory}, f)

                # --- SIMPLIFIED MATH ---
                # Get the absolute year of the arc
                arc_year = w_dat['arcs'][t_arc_name]
                
                if start_as_baby:
                    # If born as baby, we must be in the past
                    # Example: Arc is 2000. Age is 16. Birth year is 1984.
                    current_year = arc_year - t_age
                    display_age = 0
                    intro_ctx = "The player is being born. Describe the parents."
                else:
                    # Direct Drop-in
                    current_year = arc_year
                    display_age = t_age
                    intro_ctx = f"The player starts at age {t_age}, right at the beginning of the {t_arc_name}."

                # SEARCH
                with st.spinner("🔍 AI Director is researching..."):
                    web_data = search_the_web(f"{w_dat.get('world_name')} {t_arc_name} summary factions power system")
                    st.session_state.world_context = web_data

                sys_prompt = f"""
                You are the Engine of an RPG in {w_dat.get('world_name')}.
                
                --- WEB KNOWLEDGE ---
                {web_data}
                
                --- TIMELINE ---
                Current Year: {current_year} (Calendar: {w_dat.get('calendar_system', 'Year')})
                Current Arc: {t_arc_name}
                
                --- PLAYER ---
                Name: {name} | Race: {race} | Align: {align}
                Age: {display_age} | Power: {cust_p}
                Appearance: {looks}
                Personality: {pers}
                Backstory: {backstory}
                
                --- DIRECTOR INSTRUCTIONS ---
                1. [DIRECTOR] Output a hidden thought block first. Decide where to spawn the player based on the Arc.
                2. Do not speak for the player.
                3. Introduce the setting vividly.
                
                --- DATA TAGS ---
                || STATS | Age: {display_age} | Year: {current_year} | Loc: [Place] ||
                || SOCIAL | Name: [Name] | Rel: [Role] | Status: [Action] | Bio: [Lore] ||
                || EVENT | [Major Event] ||
                
                Start simulation. Context: {intro_ctx}
                """
                
                st.session_state.character = {"name": name, "race": race}
                st.session_state.world = w_dat
                st.session_state.messages = [{"role": "system", "content": sys_prompt}]
                st.session_state.current_stats = f"Age: {display_age} | Year: {current_year}"
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
                html = process_response(m["content"])
                st.markdown(f'<div class="ai-bubble">{html}</div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 6])
    with c1: 
        if st.button("Reroll"): reroll_callback()
    with c2: 
        if st.button("Continue"): continue_callback()
    
    with st.form("act", clear_on_submit=True):
        c1, c2 = st.columns([6,1])
        with c1: inp = st.text_input("Act", placeholder="Action...", label_visibility="collapsed")
        with c2: sub = st.form_submit_button("➤")
        if sub and inp:
            st.session_state.messages.append({"role": "user", "content": inp})
            if generate_ai_response(): st.rerun()