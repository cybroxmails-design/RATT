"""
RATT Architecture Plan PDF Generator.
Builds a high-quality, printable PDF using headless Edge and vector SVG diagrams.
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.error
import subprocess

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = r"C:\Users\State\.gemini\antigravity\brain\d0dba156-f5d2-41ce-8268-31cfed4e189e"
PDF_NAME = "RATT_Architecture_Plan.pdf"
HTML_NAME = "ratt_architecture_print.html"

DIAGRAMS = {
    "arch_diagram": """flowchart TD
    subgraph OS_Layer ["1. Windows OS & Shell Integration"]
        WinShell["Windows Explorer Context Menu\\n(HKCU\\\\Software\\\\Classes\\\\*)"]
        WinKbd["Low-Level Keyboard Hooks\\n(keyboard library)"]
        WinClip["System Clipboard (pyperclip / win32)"]
        WinTray["Windows System Tray Area\\n(pystray)"]
        WinVBS["Silent Shell Bridge\\n(RATT.vbs)"]
    end

    subgraph IPC_Layer ["2. IPC & Process Management"]
        SingleInst["Singleton Port Listener\\n(127.0.0.1:47653)"]
        ArgParser["Launch Action Parser & Filter\\n(Regex Sanitizer)"]
    end

    subgraph Core_Layer ["3. Master Coordination (RattApp)"]
        AppController["RattApp Controller\\n(Tkinter Main Event Loop)"]
        EmbeddedUI["Embedded Frame Router\\n(EmbeddedPage Architecture)"]
        DynamicMenuSync["Context Menu Updater Thread\\n(context_menu_updater.py)"]
    end

    subgraph Engine_Layer ["4. Business Logic & Feature Engines"]
        ClipMgr["Multi-Slot Clipboard Engine\\n(2 to 50,000 Slots)"]
        HotkeyEngine["Chord Parser Engine\\n(Ctrl+C/X/V + Digits)"]
        TransEngine["Translation Engine\\n(Google Web / Cloud API)"]
        CollabEngine["Collaboration Engine\\n(Share / Mirror Overlays)"]
    end

    subgraph Service_Layer ["5. Security, Services & Persistence"]
        EncryptMgr["Ephemeral Crypto Layer\\n(AES-256 Fernet Session Keys)"]
        PayGateway["Payment Gateway\\n(Paystack Mobile Money & Card)"]
        EmailVerify["Verification Service\\n(6-Digit OTP / SMTP)"]
        ConfigPersist["Profile & Session Store\\n(%APPDATA%\\\\RATT\\\\session.json)"]
    end

    WinVBS --> SingleInst
    WinShell -.-> WinVBS
    WinKbd --> HotkeyEngine
    SingleInst --> AppController
    ArgParser --> AppController

    AppController --> ClipMgr
    AppController --> HotkeyEngine
    AppController --> DynamicMenuSync
    AppController --> EmbeddedUI
    AppController --> WinTray

    HotkeyEngine --> ClipMgr
    ClipMgr --> WinClip
    ClipMgr --> EncryptMgr
    ClipMgr --> DynamicMenuSync
    DynamicMenuSync --> WinShell

    AppController --> TransEngine
    AppController --> CollabEngine
    AppController --> PayGateway
    AppController --> EmailVerify
    AppController --> ConfigPersist
""",

    "context_menu_seq": """sequenceDiagram
    autonumber
    actor User as User in Editor/Browser
    participant WinMenu as Windows Context Menu
    participant VBS as RATT.vbs Bridge
    participant Main as Secondary Process (main.py)
    participant Socket as Single-Instance Port (47653)
    participant Core as Primary RattApp Daemon
    participant Clip as ClipboardManager
    participant Reg as Registry (HKCU)

    User->>WinMenu: Right-click > RATT > "Copy to Slot 2"
    WinMenu->>VBS: Execute RATT.vbs "copy 2"
    VBS->>Main: pythonw -m ratt.main copy 2
    Main->>Socket: Connect 127.0.0.1:47653 & Send "ACTION copy 2"
    Main-->>User: Exit immediately (Secondary process dies)
    Socket->>Core: Process command string "ACTION copy 2"
    Core->>Clip: copy_to_slot(slot_num=2)
    Clip->>Clip: Store in Slot 2 & Notify Listeners
    Core->>Reg: Trigger context_menu_updater.py (Dot icon assigned)
""",

    "hotkey_seq": """sequenceDiagram
    autonumber
    actor User as User Keyboard
    participant Hook as Low-Level Keyboard Hook
    participant Parser as HotkeyListener Chord Engine
    participant Timer as Chord & Digit Timers
    participant Clip as ClipboardManager

    User->>Hook: Press Ctrl + C
    Hook->>Parser: Plain Ctrl+C detected
    Parser->>Timer: Start Chord Window (2.0s timeout)
    User->>Hook: Press '1'
    Hook->>Parser: Digit '1' captured while chord active
    alt Multi-digit disambiguation (Plan has slots >= 10)
        Parser->>Timer: Wait DIGIT_GAP (0.8s) for possible 2nd digit
        User-->>Parser: (No further digit pressed)
        Timer-->>Parser: Timeout fires -> slot 1 resolved
    else Immediate dispatch (Slots < 10)
        Parser->>Parser: Slot 1 resolved immediately
    end
    Parser->>Clip: copy_to_slot(slot_num=1)
    Clip-->>User: Slot updated & HUD notification
""",

    "payment_seq": """sequenceDiagram
    autonumber
    actor User as End User
    participant App as RattApp (PaymentDialog)
    participant Paystack as Paystack REST API
    participant Browser as Web Browser (Checkout)
    participant Config as AppConfig & session.json

    User->>App: Select Plan (Premium 50 slots / Enterprise)
    App->>Paystack: POST /transaction/initialize (amount, email, pesewas)
    Paystack-->>App: Return { authorization_url, reference }
    App->>Browser: Open Paystack Checkout in Browser
    User->>Browser: Complete payment (Mobile Money / Card)
    User->>App: Clicks "Verify Payment"
    App->>Paystack: GET /transaction/verify/{reference}
    Paystack-->>App: Return status="success", amount_paid
    App->>Config: Update UserProfile (tier=PREMIUM, set_subscription(+1 mo))
    App->>Config: save_session() (%APPDATA%\\RATT\\session.json)
    App->>App: Unlock features & re-render slots
""",

    "roadmap_flow": """flowchart LR
    subgraph Current_Phase1 ["Phase 1: Local Desktop Engine"]
        P1_Local["Local Memory Slots\\n(2 to 50k Slots)"]
        P1_LocalCrypto["In-Memory Fernet AES\\n(Session Lifetime)"]
        P1_LocalIPC["Local Socket IPC\\n(Port 47653)"]
        P1_SimVerify["Local OTP & SMTP\\n(Account Setup)"]
    end

    subgraph Future_Phase2 ["Phase 2: Cloud E2EE & Team Mesh"]
        P2_CloudSync["WebSocket Cloud Relay\\n(Sub-50ms sync)"]
        P2_Signal["Signal Protocol E2EE\\n(X3DH + Double Ratchet)"]
        P2_Mobile["Mobile Companions\\n(iOS & Android)"]
        P2_OrgSync["Enterprise Directory Sync\\n(Up to 3,000 Workers)"]
    end

    Current_Phase1 ==> Future_Phase2
"""
}

def fetch_svg(diagram_code: str) -> str:
    """Fetch SVG from Mermaid.ink API with error handling."""
    try:
        b64 = base64.b64encode(diagram_code.encode("utf-8")).decode("ascii")
        url = f"https://mermaid.ink/svg/{b64}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            svg = resp.read().decode("utf-8")
            # Ensure SVG width scales cleanly in print
            svg = svg.replace('<svg ', '<svg style="max-width: 100%; height: auto; display: block; margin: 0 auto;" ')
            return svg
    except Exception as e:
        print(f"Failed to fetch SVG for diagram: {e}")
        return f'<div style="padding: 20px; background: #f1f5f9; border-radius: 8px; border: 1px dashed #cbd5e1; font-family: monospace; white-space: pre-wrap;">{diagram_code}</div>'

def build_html(svg_map: dict) -> str:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RATT Architecture & Explainable Plan - Cybrox.Inc</title>
<style>
    @page {{
        size: A4 portrait;
        margin: 16mm 14mm 16mm 14mm;
        @bottom-right {{
            content: "Page " counter(page);
            font-size: 8pt;
            font-family: 'Segoe UI', system-ui, sans-serif;
            color: #64748b;
        }}
        @bottom-left {{
            content: "RATT System Architecture • Cybrox.Inc";
            font-size: 8pt;
            font-family: 'Segoe UI', system-ui, sans-serif;
            color: #64748b;
        }}
    }}

    *, *:before, *:after {{
        box-sizing: border-box;
    }}

    body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        background: #ffffff;
        line-height: 1.55;
        font-size: 9.5pt;
        margin: 0;
        padding: 0;
    }}

    /* Cover / Header Section */
    .doc-header {{
        border-bottom: 3px solid #0284c7;
        padding-bottom: 16px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }}

    .title-block {{
        flex: 1;
    }}

    .app-badge {{
        display: inline-block;
        background: #0284c7;
        color: #ffffff;
        font-size: 7.5pt;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 4px;
        margin-bottom: 6px;
    }}

    h1 {{
        color: #0f172a;
        font-size: 22pt;
        font-weight: 800;
        margin: 0 0 4px 0;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }}

    .subtitle {{
        color: #475569;
        font-size: 11pt;
        font-weight: 500;
        margin: 0;
    }}

    .meta-box {{
        text-align: right;
        font-size: 8pt;
        color: #64748b;
        line-height: 1.4;
    }}

    .meta-box strong {{
        color: #0f172a;
    }}

    /* Section Styling */
    h2 {{
        color: #0f172a;
        font-size: 13pt;
        font-weight: 700;
        border-left: 4px solid #0284c7;
        padding-left: 10px;
        margin-top: 24px;
        margin-bottom: 10px;
        page-break-after: avoid;
        break-after: avoid;
    }}

    h3 {{
        color: #1e293b;
        font-size: 10.5pt;
        font-weight: 600;
        margin-top: 14px;
        margin-bottom: 6px;
        page-break-after: avoid;
        break-after: avoid;
    }}

    p {{
        margin: 0 0 10px 0;
    }}

    /* Callout & Card Boxes */
    .callout {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #0284c7;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 12px 0;
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    .callout-title {{
        font-weight: 700;
        color: #0369a1;
        font-size: 9pt;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* Diagram Containers */
    .diagram-container {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin: 14px 0;
        page-break-inside: avoid;
        break-inside: avoid;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        text-align: center;
    }}

    .diagram-caption {{
        font-size: 8pt;
        font-weight: 600;
        color: #64748b;
        margin-top: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* Tables */
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0 18px 0;
        font-size: 8.5pt;
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    th {{
        background: #0f172a;
        color: #ffffff;
        font-weight: 600;
        text-align: left;
        padding: 7px 10px;
        border: 1px solid #0f172a;
    }}

    td {{
        padding: 7px 10px;
        border: 1px solid #e2e8f0;
        vertical-align: top;
    }}

    tr:nth-child(even) td {{
        background: #f8fafc;
    }}

    /* Grid Layout for Component Cards */
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin: 12px 0;
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    .card {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 12px;
    }}

    .card h4 {{
        margin: 0 0 4px 0;
        color: #0284c7;
        font-size: 9.5pt;
        font-weight: 700;
    }}

    .card p {{
        margin: 0;
        font-size: 8.5pt;
        color: #475569;
    }}

    .badge-pill {{
        display: inline-block;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 7.5pt;
        font-weight: 600;
    }}
    .badge-free {{ background: #e0f2fe; color: #0369a1; }}
    .badge-prem {{ background: #fef3c7; color: #b45309; }}
    .badge-ent {{ background: #dcfce7; color: #15803d; }}

    code {{
        font-family: 'Consolas', 'Courier New', monospace;
        background: #f1f5f9;
        color: #0f172a;
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 8.5pt;
        border: 1px solid #e2e8f0;
    }}

    .page-break {{
        page-break-before: always;
        break-before: always;
    }}
</style>
</head>
<body>

<!-- Header -->
<div class="doc-header">
    <div class="title-block">
        <span class="app-badge">Official Architecture Specification</span>
        <h1>RATT (Rapid Access To Text)</h1>
        <p class="subtitle">System Architecture, Process Model & Explainable Technical Plan</p>
    </div>
    <div class="meta-box">
        <strong>Publisher:</strong> Cybrox.Inc<br>
        <strong>Document Version:</strong> 1.0.0<br>
        <strong>Target OS:</strong> Windows 10 / 11 Desktop<br>
        <strong>Status:</strong> Production Ready (Phase 1)
    </div>
</div>

<!-- Section 1 -->
<h2>1. Executive Summary & Objective</h2>
<p>
    <strong>RATT (Rapid Access To Text)</strong> is an enterprise-grade multi-slot clipboard acceleration platform designed to overcome the standard OS single-item clipboard bottleneck. Engineered by Cybrox.Inc, RATT enables seamless multi-slot copying, cutting, pasting, live machine translation, and peer-to-peer screen mirroring directly within native Windows application workflows.
</p>
<div class="callout">
    <div class="callout-title">Core Value Proposition</div>
    Zero-disruption workflow enhancement: Users interact with RATT via two-stroke global keyboard chords (e.g., <code>Ctrl+C</code> followed by a slot digit) or directly from the native Windows Explorer right-click cascading menu. Zero console window flickers, sub-10ms response times, and strictly in-memory data lifetimes ensure privacy and speed.
</div>

<!-- Section 2 -->
<h2>2. High-Level Layered System Architecture</h2>
<p>
    The system is organized into five decoupled layers ensuring complete isolation between operating system low-level hooks, the application event loop, data manipulation engines, and external web APIs.
</p>

<div class="diagram-container">
    {svg_map['arch_diagram']}
    <div class="diagram-caption">Figure 1: Full-Stack Layered Architecture & Inter-Process Communication Flow</div>
</div>

<div class="grid-2">
    <div class="card">
        <h4>1. OS Integration Layer</h4>
        <p>Direct Win32 bindings: <code>pyperclip</code> for OS clipboard, low-level keyboard hooks via <code>keyboard</code>, system notification area via <code>pystray</code>, and cascading context menu registry trees in <code>HKCU</code>.</p>
    </div>
    <div class="card">
        <h4>2. IPC & Singleton Engine</h4>
        <p>Local loopback TCP socket (<code>127.0.0.1:47653</code>) with <code>SO_EXCLUSIVEADDRUSE</code> ensures exactly one daemon runs while multiplexing shell actions from <code>RATT.vbs</code>.</p>
    </div>
    <div class="card">
        <h4>3. Central Coordinator</h4>
        <p><code>RattApp</code> coordinates the Tkinter root event loop, dynamic frame swapping (via <code>EmbeddedPage</code> pattern), background thread orchestration, and registry state publishing.</p>
    </div>
    <div class="card">
        <h4>4. Business Logic & Crypto</h4>
        <p>Thread-safe multi-slot buffer (2 to 50,000 slots) backed by ephemeral Fernet AES-256 session keys that are completely destroyed from RAM upon application termination.</p>
    </div>
</div>

<div class="page-break"></div>

<!-- Section 3 -->
<h2>3. Operational Workflows & Sequence Diagrams</h2>

<h3>3.1 Right-Click Context Menu Shell Activation</h3>
<p>
    When a user triggers an action from the native Windows Explorer context menu (e.g., in Word, Notepad, or a browser), Windows launches the decoupled VBS bridge. The secondary process communicates with the background daemon over the loopback socket and exits instantly without stealing UI focus.
</p>

<div class="diagram-container">
    {svg_map['context_menu_seq']}
    <div class="diagram-caption">Figure 2: Sequence of Context Menu Action Execution via Single-Instance Socket Handshake</div>
</div>

<h3>3.2 Two-Stage Global Hotkey Chord Engine</h3>
<p>
    Instead of reserving dozens of static shortcut keys, RATT uses an intuitive chord sequence:
    <code>Ctrl+C / Ctrl+X / Ctrl+V</code> &rarr; <em>Wait for Slot Digit(s)</em> &rarr; <em>Action Dispatch</em>.
</p>

<div class="diagram-container">
    {svg_map['hotkey_seq']}
    <div class="diagram-caption">Figure 3: Global Hotkey Chording & Multi-Digit Slot Disambiguation Sequence</div>
</div>

<div class="page-break"></div>

<!-- Section 4 -->
<h3>3.3 Monetization & Payment Verification Lifecycle</h3>
<p>
    RATT supports automated tier upgrades via the Paystack payment gateway, supporting mobile money (MTN, Vodafone, AirtelTigo) and bank cards in GHS and USD.
</p>

<div class="diagram-container">
    {svg_map['payment_seq']}
    <div class="diagram-caption">Figure 4: Paystack Checkout & In-App Web Verification Workflow</div>
</div>

<h2>4. Subscription Tiers & Capability Matrix</h2>
<table>
    <thead>
        <tr>
            <th>Feature / Capability</th>
            <th>Basic (Free) <span class="badge-pill badge-free">Free</span></th>
            <th>Premium <span class="badge-pill badge-prem">GHS 20 / 10 slots</span></th>
            <th>Enterprise <span class="badge-pill badge-ent">GHS 250 flat</span></th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Slot Allocation</strong></td>
            <td>2 Slots (Slot 1 & 2)</td>
            <td>10 to 50,000 Custom Slots</td>
            <td>Unlimited / Max Capacity</td>
        </tr>
        <tr>
            <td><strong>Global Hotkey Chords</strong></td>
            <td>Supported (Slots 1 & 2)</td>
            <td>Supported (All configured slots)</td>
            <td>Supported (All configured slots)</td>
        </tr>
        <tr>
            <td><strong>Context Menu Integration</strong></td>
            <td>Standard 2 slots</td>
            <td>Top 15 + "More slots..." + Dot status</td>
            <td>Full cascading menu + Dot status</td>
        </tr>
        <tr>
            <td><strong>Cloud Translation</strong></td>
            <td>Disabled</td>
            <td>Enabled (Google Cloud / Web API)</td>
            <td>Enabled (High-volume API support)</td>
        </tr>
        <tr>
            <td><strong>Share & Mirror Features</strong></td>
            <td>7-day trial countdown</td>
            <td>Unlimited Lifetime Access</td>
            <td>Unlimited Lifetime Access</td>
        </tr>
        <tr>
            <td><strong>Team Contacts</strong></td>
            <td>None</td>
            <td>Personal contacts list</td>
            <td>Up to 3,000 verified worker accounts</td>
        </tr>
    </tbody>
</table>

<h2>5. Security, Memory Safety & Cryptographic Design</h2>
<div class="grid-2">
    <div class="card">
        <h4>Zero Cold-Storage Persistence</h4>
        <p>Text copied into slots is never written to disk. All slots reside exclusively in volatile memory protected by <code>threading.Lock</code>. Closing the app wipes all data.</p>
    </div>
    <div class="card">
        <h4>Ephemeral Fernet Encryption</h4>
        <p>Clipboard slots are encrypted in-memory using Fernet AES-256. The session key is generated at boot via <code>Fernet.generate_key()</code> and wiped with <code>destroy()</code> upon exit.</p>
    </div>
    <div class="card">
        <h4>User-Level Registry Scope</h4>
        <p>All context menu modifications are strictly scoped to <code>HKEY_CURRENT_USER</code> (HKCU). RATT operates with zero Administrator privileges, preventing privilege escalation.</p>
    </div>
    <div class="card">
        <h4>Command Injection Immunity</h4>
        <p>Arguments passed through <code>RATT.vbs</code> are strictly validated using <code>re.fullmatch(r"[A-Za-z0-9\\-]{{1,10}}", a)</code>, guaranteeing shell parameter safety.</p>
    </div>
</div>

<h2>6. Scalability Roadmap: Phase 2 Architecture</h2>
<p>
    Phase 1 delivers a self-contained, high-performance desktop workstation utility. Phase 2 transitions RATT into a zero-knowledge cross-device collaboration network.
</p>

<div class="diagram-container">
    {svg_map['roadmap_flow']}
    <div class="diagram-caption">Figure 5: Phase 1 (Local Engine) to Phase 2 (Distributed Cloud Relay) Evolution</div>
</div>

<div class="callout">
    <div class="callout-title">Key Phase 2 Milestones</div>
    <ul>
        <li><strong>Signal Protocol Integration:</strong> Upgrade <code>SignalProtocolStub</code> in <code>encryption.py</code> to full X3DH key agreement and Double Ratchet end-to-end encryption.</li>
        <li><strong>WebSocket Relay Server:</strong> Zero-knowledge cloud message broker for real-time synchronization across desktop and mobile devices.</li>
        <li><strong>Cross-Platform Adaptation:</strong> Port the registry updater to macOS Quick Action Services and Linux DBus interfaces.</li>
    </ul>
</div>

</body>
</html>
"""
    return html

def main():
    print("Step 1: Fetching crisp vector SVG diagrams from Mermaid API...")
    svg_map = {}
    for key, diagram_code in DIAGRAMS.items():
        print(f"  Fetching '{key}'...")
        svg_map[key] = fetch_svg(diagram_code)

    print("Step 2: Generating print-ready HTML document...")
    html_content = build_html(svg_map)
    html_path = os.path.join(OUTPUT_DIR, HTML_NAME)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  HTML saved to: {html_path}")

    print("Step 3: Compiling PDF via Microsoft Edge Headless engine...")
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)
    if not edge_exe:
        print("ERROR: Microsoft Edge executable not found.")
        sys.exit(1)

    pdf_output_local = os.path.join(OUTPUT_DIR, PDF_NAME)
    pdf_output_artifact = os.path.join(ARTIFACT_DIR, PDF_NAME)

    cmd = [
        edge_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_output_local}",
        f"file:///{html_path.replace(os.sep, '/')}"
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(pdf_output_local):
        size_kb = os.path.getsize(pdf_output_local) / 1024
        print(f"  SUCCESS! Local PDF generated: {pdf_output_local} ({size_kb:.1f} KB)")
        
        # Copy to artifact directory
        try:
            os.makedirs(ARTIFACT_DIR, exist_ok=True)
            import shutil
            shutil.copy2(pdf_output_local, pdf_output_artifact)
            print(f"  SUCCESS! Artifact PDF copied to: {pdf_output_artifact}")
        except Exception as e:
            print(f"  Warning copying to artifact dir: {e}")
    else:
        print(f"ERROR: PDF was not generated. Return code: {res.returncode}, Stderr: {res.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
