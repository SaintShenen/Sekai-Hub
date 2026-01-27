import streamlit as st
import json
import os
import re
from groq import Groq

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Sekai-Hub", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

if "game_active" not in st.session_state: st.session_state.game_active = False
if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
# Default to a smaller model if 70b hits limits
if "model_name" not in st.session_state: st.session_state.model_name = "llama-3.3-70b-versatile"
if "current_stats" not in st.session_state: st.session_state.current_stats = "Initializing..."
if "socials" not in st.session_state: st.session_state.socials = {}
if "event_log" not in st.session_state: st.session_state.event_log = []

# Ensure Folders
if not os.path.exists('saves'): os.makedirs('saves')
if not os.path.exists('presets'): os.makedirs('presets')

# --- 2. AUDIO & STYLING ---
def play_sound(trigger_text):
    trigger_text = trigger_text.lower()
    sounds = {
        "boom": "https://www.myinstants.com/media/sounds/vine-boom.mp3",
        "explosion": "https://www.myinstants.com/media/sounds/explosion_1.mp3",
        "punch": "https://www.myinstants.com/media/sounds/punch-sound-effect.mp3",
        "slash": "https://www.myinstants.com/media/sounds/sword-slash.mp3",
        "teleport": "https://www.myinstants.com/media/sounds/dbz-teleport.mp3",
        "flash": "https://www.myinstants.com/media/sounds/flash-sound-effect.mp3"
    }
    for key, url in sounds.items():
        if key in trigger_text:
            st.markdown(f'<audio autoplay><source src="{url}" type="audio/mp3"></audio>', unsafe_allow_html=True)
            break

def apply_theme():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400&display=swap');
        .stApp {{ background-color: #0a0a0f; color: #E0E0E0; font-family: 'Roboto', sans-serif; }}
        h1, h2, h3 {{ font-family: 'Orbitron', sans-serif; color: #00e5ff; }}
        
        /* BUBBLES */
        .user-bubble {{
            background: linear-gradient(135deg, #1c4e80, #2a6fdb);
            color: white; padding: 15px; border-radius: 20px 20px 0px 20px;
            margin-bottom: 15px; text-align: right; max-width: 80%; margin-left: auto;
            border: 1px solid #4da6ff;
        }}
        .ai-bubble {{
            background: linear-gradient(135deg, #1a1a1a, #252525);
            color: #ff80ff; padding: 15px; border-radius: 20px 20px 20px 0px;
            margin-bottom: 15px; text-align: left; max-width: 80%; margin-right: auto;
            border-left: 4px solid #d500f9;
        }}
        .dialog-text {{ color: #00ffff; font-weight: bold; font-family: "Courier New", monospace; }}
        .stat-card {{ background: rgba(0, 255, 0, 0.05); border: 1px solid #00ff00; padding: 10px; border-radius: 8px; margin-bottom: 5px; color: #00ff00; font-family: 'Orbitron', monospace; }}
        
        /* ARC TRACKER */
        .arc-past {{ color: #555; border-left: 3px solid #555; padding-left: 5px; }}
        .arc-current {{ color: #00ffff; font-weight: bold; border-left: 3px solid #00ffff; padding-left: 5px; background: rgba(0,255,255,0.05); }}
        .arc-future {{ color: #333; border-left: 3px solid #333; padding-left: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIC ---
def format_lore(world_data):
    lore_obj = world_data.get('lore', {})
    text_block = ""
    if isinstance(lore_obj, dict):
        if "history" in lore_obj: text_block += f"HISTORY:\n{lore_obj['history']}\n\n"
        if "factions" in lore_obj: text_block += f"FACTIONS:\n" + "\n".join([f"- {f}" for f in lore_obj['factions']]) + "\n\n"
        if "key_concepts" in lore_obj: text_block += f"CONCEPTS:\n" + "\n".join([f"- {c}" for c in lore_obj['key_concepts']]) + "\n\n"
    return text_block

def format_characters(world_data):
    chars = world_data.get('key_characters', [])
    text_block = ""
    for c in chars:
        if isinstance(c, dict):
            text_block += f"Name: {c.get('name')}\nApp: {c.get('appearance')}\nPers: {c.get('personality')}\nLore: {c.get('backstory')}\nPower: {c.get('power')}\n---\n"
    return text_block

def process_response(text):
    text = re.sub(r"---.*?---", "", text) 
    text = re.sub(r"###.*?DATA", "", text)
    
    # Event Capture
    event_matches = re.findall(r"\|\|\s*EVENT\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    for event_desc in event_matches:
        clean = event_desc.strip()
        if not st.session_state.event_log or st.session_state.event_log[-1] != clean: st.session_state.event_log.append(clean)
    text = re.sub(r"\|\|\s*EVENT\s*\|(.*?)\|\|", "", text, flags=re.DOTALL)

    # Stats Capture
    stat_match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    if stat_match:
        st.session_state.current_stats = stat_match.group(1).strip()
        text = text.replace(stat_match.group(0), "")

    # Socials Capture
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
    text = re.sub(r"\|\|\s*SOCIAL\s*\|(.*?)\|\|", "", text, flags=re.DOTALL)

    # Formatting
    text = re.sub(r'(".*?")', r'<span class="dialog-text">\1</span>', text, flags=re.DOTALL)
    text = text.replace("*", "") 
    text = text.replace("\n", "<br>")
    
    play_sound(text)
    return text

def extract_stats(text):
    match = re.search(r"\|\|\s*STATS\s*\|(.*?)\|\|", text, flags=re.DOTALL)
    return match.group(1).strip() if match else st.session_state.current_stats

def get_current_year():
    try:
        match = re.search(r"(?:Year|Age):\s*(\d+)", st.session_state.current_stats)
        if match: return int(match.group(1))
    except: pass
    return -9999

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
            "events": st.session_state.event_log
        }
        with open(f"saves/autosave_{safe}.json", 'w') as f: json.dump(data, f)

def generate_ai_response():
    client = Groq(api_key=st.session_state.api_key)
    try:
        resp = client.chat.completions.create(
            model=st.session_state.model_name,
            messages=st.session_state.messages,
            temperature=0.8
        )
        msg = resp.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.session_state.current_stats = extract_stats(msg)
        autosave()
    except Exception as e:
        st.error(f"AI Error (Likely Rate Limit): {e}")
        st.info("Try switching the Model in the sidebar to 'llama-3.1-8b'!")

# --- CALLBACKS FOR NEW BUTTONS ---
def reroll_callback():
    # Remove last AI message
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
    generate_ai_response()

def continue_callback():
    # Force AI to generate again without user input
    generate_ai_response()

apply_theme()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💠 HUB SYSTEM")
    if not st.session_state.api_key: st.session_state.api_key = st.text_input("Groq API Key", type="password")
    
    # MODEL SWITCHER
    st.session_state.model_name = st.selectbox(
        "🧠 AI Brain", 
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        help="Switch if you hit a Token Limit error."
    )

    if st.session_state.game_active:
        t1, t2, t3, t4 = st.tabs(["📊 Stats", "👥 Socials", "📜 Arcs", "✏️ Edit"])
        
        with t1:
            for s in st.session_state.current_stats.split('|'): 
                if s.strip(): st.markdown(f'<div class="stat-card">{s.strip()}</div>', unsafe_allow_html=True)
            if st.button("💾 Save State"): autosave(); st.toast("Saved")
        
        with t2:
            if not st.session_state.socials: st.info("None")
            for n, d in st.session_state.socials.items():
                with st.expander(f"{n} ({d['rel']})"):
                    st.markdown(f"**Status:** {d['status']}<br><small>{d['bio']}</small>", unsafe_allow_html=True)
        
        with t3:
            st.caption("Timeline Status")
            current_year = get_current_year()
            arcs = st.session_state.world.get('arcs', {})
            for an, ay in sorted(arcs.items(), key=lambda x: x[1]):
                if current_year > ay + 1: st.markdown(f'<div class="arc-past">✅ {an}</div>', unsafe_allow_html=True)
                elif current_year >= ay: st.markdown(f'<div class="arc-current">🔵 {an}</div>', unsafe_allow_html=True)
                else: st.markdown(f'<div class="arc-future">⚪ {an}</div>', unsafe_allow_html=True)

        with t4:
            st.caption("History Editor (God Mode)")
            # Slider to pick message
            msg_len = len(st.session_state.messages)
            if msg_len > 0:
                msg_idx = st.number_input("Message Index", 0, msg_len-1, value=msg_len-1)
                selected_msg = st.session_state.messages[msg_idx]
                
                new_text = st.text_area("Edit Content", value=selected_msg["content"], height=200)
                if st.button("Update Message"):
                    st.session_state.messages[msg_idx]["content"] = new_text
                    st.toast("History Updated!")
                    st.rerun()
            else:
                st.info("No messages yet.")

    st.divider()
    if st.session_state.game_active and st.button("🛑 Exit Simulation"): st.session_state.game_active = False; st.rerun()

# --- GAME ---
if not st.session_state.api_key: st.warning("Enter API Key"); st.stop()
worlds = load_json_files('world_')

if not st.session_state.game_active:
    st.title("⚔️ Sekai-Hub: Simulation")
    tab1, tab2, tab3 = st.tabs(["🆕 New", "👤 Preset", "📂 Load"])
    
    with tab2:
        presets = [f for f in os.listdir('presets') if f.endswith('.json')]
        sel_pre = st.selectbox("Preset", ["None"] + presets)
        pre_dat = {}
        if sel_pre != "None":
            try: with open(f"presets/{sel_pre}") as f: pre_dat = json.load(f)
            except: st.error("Error loading preset.")
    
    with tab1:
        sel_w = st.selectbox("World", list(worlds.keys()))
        if sel_w:
            w_dat = worlds[sel_w]
            st.info("📅 **World Timeline Preview:**")
            arcs = w_dat.get('arcs', {})
            sorted_arcs = sorted(arcs.items(), key=lambda x: x[1])
            if sorted_arcs:
                timeline_str = f"{sorted_arcs[0][1]} ({sorted_arcs[0][0]})  --->  {sorted_arcs[-1][1]} ({sorted_arcs[-1][0]})"
                st.caption(timeline_str)

            with st.form("new"):
                st.subheader("Identity")
                name = st.text_input("Name", value=pre_dat.get("name", ""))
                race = st.selectbox("Race", w_dat['races'])
                looks = st.text_area("Appearance", value=pre_dat.get("looks", ""), placeholder="Describe hair, eyes, clothes...")
                def_align = pre_dat.get("align", "Neutral")
                align = st.select_slider("Alignment", ["Heroic", "Neutral", "Evil"], value=def_align)
                pers = st.text_area("Personality", value=pre_dat.get("personality", ""))
                st.subheader("Origins")
                backstory = st.text_area("Character Backstory", value=pre_dat.get("backstory", ""), placeholder="Where were you born? Who were your parents?")
                st.subheader("Timeline Start")
                c1, c2 = st.columns(2)
                with c1:
                    t_arc = st.selectbox("Target Arc", list(w_dat['arcs'].keys()))
                    t_age = st.number_input("Age at Start", 1, 1000, 7)
                with c2:
                    mode = st.radio("Mode", ["Born as Baby", "Drop-in at Target Age"])
                    p_mode = st.radio("Power", ["Manual", "Random"])
                    cust_p = st.text_input("Custom Power", value=pre_dat.get("power", ""))
                
                save_preset_box = st.checkbox("Save New Preset")

                if st.form_submit_button("Launch"):
                    if save_preset_box and name:
                        p_data = {
                            "name": name, "align": align, "personality": pers, 
                            "power": cust_p, "looks": looks, "backstory": backstory
                        }
                        with open(f"presets/{name}.json", 'w') as f: json.dump(p_data, f)
                        st.toast("Preset Saved!")

                    start_year = w_dat['arcs'][t_arc]
                    if "Baby" in mode:
                        curr_year = start_year - t_age
                        age_d = 0
                        intro = "The player is being born."
                    else:
                        curr_year = start_year
                        age_d = t_age
                        intro = "The player enters the story at this age."

                    # Logic Gates
                    canon_start_year = min(w_dat['arcs'].values()) + 15
                    timeline_instruction = ""
                    if curr_year < canon_start_year:
                        timeline_instruction = f"CRITICAL WARNING: Year {curr_year}. BEFORE main plot. Canon characters are CHILDREN/UNBORN."
                    elif curr_year > canon_start_year + 5:
                        timeline_instruction = f"CRITICAL WARNING: Year {curr_year}. LATE timeline."

                    formatted_lore = format_lore(w_dat)
                    formatted_chars = format_characters(w_dat)

                    sys_prompt = f"""
                    You are the Engine of an RPG in {w_dat['world_name']}.
                    --- WORLD KNOWLEDGE ---
                    Calendar: {w_dat.get('calendar_system', 'Year')}
                    CURRENT YEAR: {curr_year}
                    {formatted_lore}
                    --- PLAYER ---
                    Name: {name} | Race: {race} | Align: {align}
                    Age: {age_d}
                    Appearance: {looks}
                    Personality: {pers}
                    Backstory: {backstory}
                    --- LOGIC GATES ---
                    1. **TIMELINE CHECK:** {timeline_instruction}
                    2. **ANTI-PUPPETING:** Never write the user's thoughts/actions.
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
                    generate_ai_response()
                    st.session_state.game_active = True
                    st.rerun()

    with tab3:
        saves = [f for f in os.listdir('saves') if f.endswith('.json')]
        if saves:
            sel_file = st.selectbox("File", saves)
            if st.button("Load"):
                try:
                    with open(f"saves/{sel_file}") as f: d = json.load(f)
                    st.session_state.character = d.get('character', {})
                    st.session_state.world = d.get('world', {})
                    st.session_state.messages = d.get('history', [])
                    st.session_state.current_stats = d.get('stats', "Stats: N/A")
                    st.session_state.socials = d.get('socials', {})
                    st.session_state.event_log = d.get('events', [])
                    st.session_state.game_active = True
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

else:
    st.markdown(f"### 🌍 {st.session_state.world['world_name']} | 👤 {st.session_state.character['name']}")
    with st.container():
        for m in st.session_state.messages:
            if m["role"]=="user": st.markdown(f'<div class="user-bubble">{m["content"]}</div>', unsafe_allow_html=True)
            elif m["role"]=="assistant": st.markdown(f'<div class="ai-bubble">{process_response(m["content"])}</div>', unsafe_allow_html=True)
    
    # CONTROL BUTTONS
    c1, c2, c3 = st.columns([1, 1, 6])
    with c1:
        if st.button("🎲 Reroll"): reroll_callback(); st.rerun()
    with c2:
        if st.button("⏩ Continue"): continue_callback(); st.rerun()
    
    with st.form("act", clear_on_submit=True):
        col_in, col_btn = st.columns([6,1])
        with col_in: inp = st.text_input("Act", placeholder="Action...", label_visibility="collapsed")
        with col_btn: sub = st.form_submit_button("➤")
        if sub and inp:
            st.session_state.messages.append({"role": "user", "content": inp})
            generate_ai_response()
            st.rerun()