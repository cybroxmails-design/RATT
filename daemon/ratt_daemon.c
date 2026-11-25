/*
 * RATT helper ("daemon") - the always-on, input-side half of RATT.
 * A DLL hosted by rundll32.exe (Windows runs signed system binaries only; this way the
 * helper needs no executable of its own).
 *
 * The Python app (UI, slots, payments, translation) stays in charge of everything that is
 * slow-changing; this small native process takes over what must be instant and must not
 * look like a keylogger:
 *
 *   - global hotkeys through RegisterHotKey (no low-level keyboard hook):
 *       Ctrl+C / Ctrl+X / Ctrl+V followed by a slot number, and Ctrl+Shift+R (popup)
 *   - key injection (the Ctrl+C / Ctrl+V sent to the document in front)
 *   - the receiving end of the right-click menu: the menu's shell extension posts an action
 *     ("copy 3") to this helper's window, which relays it to the app in milliseconds
 *     instead of starting a Python runtime per click
 *
 * Talking to the app:
 *   app -> daemon   WM_COPYDATA to the hidden window "RATTDaemonWnd", one text command:
 *                     STATE login=1 max=10 paste=1000 gap=500 chord=2000 filled=1,3,7
 *                     KEYS ctrl+v | ctrl+c | ctrl+x | v
 *                     ACTION <action> [arg] [arg]      SHOW      QUIT
 *   daemon -> app   named pipe \\.\pipe\RATT.events.<app pid>, one line per event:
 *                     HK copy 3 | HK cut 3 | HK paste 3 | POPUP | SHOW | ACTION ... | ERR ...
 *
 * The daemon exits when the app process ends (--parent <pid>).
 *
 * Build:  gcc -shared -O2 -s -municode -static -o ratt_daemon.dll ratt_daemon.c -luser32 -ladvapi32
 */
#define WIN32_LEAN_AND_MEAN
#define COBJMACROS
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <ole2.h>
#include <oleauto.h>
#include <shlobj.h>
#include <sddl.h>
#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WND_CLASS      L"RATTDaemonWnd"
#define COPYDATA_MAGIC 0x52415454u           /* "RATT" */
#define MAX_SLOT_LIMIT 100000
#define EVENT_QUEUE    32

enum { ID_COPY = 1, ID_CUT, ID_PASTE, ID_POPUP, ID_TOGGLE_PAUSE, ID_TOGGLE_PAUSE_ALT, ID_MAX_STATIC = ID_TOGGLE_PAUSE_ALT, ID_DIGIT_BASE = 100 };
enum { TIMER_CHORD = 1, TIMER_GAP, TIMER_REARM };
enum { ACT_NONE, ACT_COPY, ACT_CUT, ACT_PASTE };
enum { WM_PIPE_READY = WM_APP + 1 };

/* ---------- state ---------- */

static HWND   g_wnd;
static HANDLE g_pipe = INVALID_HANDLE_VALUE;   /* written by the main thread only */
static int    g_dry_run;
static DWORD  g_parent_pid;

static struct {
    int login, enabled, max_slots, paste_ms, gap_ms, chord_ms;
    unsigned char *filled;                     /* filled[n] != 0: slot n holds data */
    int filled_count;
} g_cfg = { 0, 1, 10, 1000, 500, 2500, NULL, 0 };

static int  g_action = ACT_NONE;               /* chord waiting for a slot number */
static char g_digits[8];
static int  g_digit_count;
static int  g_digit_hotkeys;                   /* digit hotkeys currently registered */
static int  g_rearm_pending;                   /* Ctrl hotkeys paused while we inject keys */
static int  g_registered[ID_MAX_STATIC + 1];
static int  g_reported[ID_MAX_STATIC + 1];     /* "hotkey in use" already told to the app */

static char g_queue[EVENT_QUEUE][64];          /* events produced before the app connected */
static int  g_queued;

/* ---------- logging ---------- */

static void data_path(wchar_t *out, size_t n, const wchar_t *file)
{
    wchar_t base[MAX_PATH];
    DWORD len = GetEnvironmentVariableW(L"APPDATA", base, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) wcscpy(base, L".");
    _snwprintf(out, n, L"%ls\\RATT\\%ls", base, file);
    out[n - 1] = 0;
}

static void log_line(const char *fmt, ...)
{
    wchar_t path[MAX_PATH * 2];
    data_path(path, MAX_PATH * 2, L"daemon.log");
    HANDLE h = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    DWORD sz = GetFileSize(h, NULL);
    if (sz != INVALID_FILE_SIZE && sz > 1024 * 1024) {
        SetFilePointer(h, 0, NULL, FILE_BEGIN);
        SetEndOfFile(h);
    } else {
        SetFilePointer(h, 0, NULL, FILE_END);
    }
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf) - 2, fmt, ap);
    va_end(ap);
    if (n > 0) {
        buf[n++] = '\n';
        DWORD wrote;
        WriteFile(h, buf, (DWORD)n, &wrote, NULL);
    }
    CloseHandle(h);
}

/* ---------- events to the app ---------- */

typedef void (CALLBACK *EventCallbackFn)(const char *line);
static EventCallbackFn g_event_cb = NULL;

__declspec(dllexport) void CALLBACK SetEventCallback(EventCallbackFn cb)
{
    g_event_cb = cb;
}

static void write_event(const char *line)
{
    char buf[80];
    int n = snprintf(buf, sizeof(buf), "%s\n", line);
    DWORD wrote;
    if (!WriteFile(g_pipe, buf, (DWORD)n, &wrote, NULL)) {
        CloseHandle(g_pipe);
        g_pipe = INVALID_HANDLE_VALUE;
    }
}

static void emit(const char *line)
{
    if (g_dry_run) log_line("EVENT %s", line);
    if (g_event_cb) {
        g_event_cb(line);
    }
    if (g_pipe != INVALID_HANDLE_VALUE) {
        write_event(line);
    } else if (!g_event_cb && g_queued < EVENT_QUEUE) {
        snprintf(g_queue[g_queued++], sizeof(g_queue[0]), "%s", line);
    }
}

static void flush_queue(void)
{
    for (int i = 0; i < g_queued && g_pipe != INVALID_HANDLE_VALUE; i++) write_event(g_queue[i]);
    g_queued = 0;
}

/* ---------- hotkeys ---------- */

static void register_one(int id, UINT mods, UINT vk, const char *name)
{
    if (id <= ID_MAX_STATIC && g_registered[id]) return;
    if (RegisterHotKey(g_wnd, id, mods | MOD_NOREPEAT, vk)) {
        if (id <= ID_MAX_STATIC) g_registered[id] = 1;
    } else if (id <= ID_POPUP && !g_reported[id]) {
        char msg[64];
        g_reported[id] = 1;
        snprintf(msg, sizeof(msg), "ERR %s %s",
                 GetLastError() == ERROR_HOTKEY_ALREADY_REGISTERED ? "hotkey-in-use" : "hotkey-failed", name);
        emit(msg);
    }
}

static void unregister_one(int id)
{
    if (id <= ID_MAX_STATIC) {
        if (!g_registered[id]) return;
        g_registered[id] = 0;
    }
    UnregisterHotKey(g_wnd, id);
}

/* Register exactly the hotkeys the current state needs.
 * Emergency toggle hotkeys (Ctrl+Alt+P and Win+Shift+Pause) stay available so gamers
 * and full-screen users can toggle RATT ON/OFF without opening any window. */
static void apply_hotkeys(void)
{
    int active = g_cfg.login && g_cfg.enabled;
    int want_ctrl = active && !g_rearm_pending;
    if (want_ctrl) {
        register_one(ID_COPY, MOD_CONTROL, 'C', "Ctrl+C");
        register_one(ID_CUT, MOD_CONTROL, 'X', "Ctrl+X");
    } else {
        unregister_one(ID_COPY);
        unregister_one(ID_CUT);
    }
    /* Ctrl+V is only held back when there is a slot to choose from */
    if (want_ctrl && g_cfg.filled_count > 0) register_one(ID_PASTE, MOD_CONTROL, 'V', "Ctrl+V");
    else unregister_one(ID_PASTE);

    if (active) register_one(ID_POPUP, MOD_CONTROL | MOD_SHIFT, 'R', "Ctrl+Shift+R");
    else unregister_one(ID_POPUP);

    /* Universal Emergency Toggle Hotkeys: Ctrl+Alt+P and Win+Shift+Pause */
    register_one(ID_TOGGLE_PAUSE, MOD_CONTROL | MOD_ALT, 'P', "Ctrl+Alt+P");
    register_one(ID_TOGGLE_PAUSE_ALT, MOD_WIN | MOD_SHIFT, VK_PAUSE, "Win+Shift+Pause");
}

/* Slot-number hotkeys exist only while a chord is waiting: 0-9 and numpad 0-9, with or
 * without Ctrl still held. */
static void digit_hotkeys(int on)
{
    if (on == g_digit_hotkeys) return;
    for (int d = 0; d < 10; d++) {
        UINT vks[2] = { (UINT)('0' + d), (UINT)(VK_NUMPAD0 + d) };
        for (int k = 0; k < 2; k++)
            for (int c = 0; c < 2; c++) {
                int id = ID_DIGIT_BASE + d * 4 + k * 2 + c;
                if (on) RegisterHotKey(g_wnd, id, (c ? MOD_CONTROL : 0) | MOD_NOREPEAT, vks[k]);
                else UnregisterHotKey(g_wnd, id);
            }
    }
    g_digit_hotkeys = on;
}

/* ---------- key injection ---------- */

static void key_event(INPUT *in, int *n, WORD vk, int up)
{
    memset(&in[*n], 0, sizeof(INPUT));
    in[*n].type = INPUT_KEYBOARD;
    in[*n].ki.wVk = vk;
    in[*n].ki.dwFlags = up ? KEYEVENTF_KEYUP : 0;
    (*n)++;
}

/* Send Ctrl+<vk> (or just <vk>) to the window in front. Our own Ctrl hotkeys are paused
 * for a moment so the keys we inject are not caught again. */
static void inject(WORD vk, int with_ctrl)
{
    if (g_dry_run) {
        log_line("KEYS %s%c", with_ctrl ? "ctrl+" : "", (char)(vk + 32));
        return;
    }
    g_rearm_pending = 1;
    apply_hotkeys();

    INPUT in[6];
    int n = 0;
    int ctrl_already_down = (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0;
    if (with_ctrl) key_event(in, &n, VK_CONTROL, 0);
    key_event(in, &n, vk, 0);
    key_event(in, &n, vk, 1);
    if (with_ctrl && (!ctrl_already_down || vk == 'V')) key_event(in, &n, VK_CONTROL, 1);
    SendInput((UINT)n, in, sizeof(INPUT));

    SetTimer(g_wnd, TIMER_REARM, 120, NULL);
}

static void inject_combo(const char *combo)
{
    if (strcmp(combo, "ctrl+c") == 0) inject('C', 1);
    else if (strcmp(combo, "ctrl+x") == 0) inject('X', 1);
    else if (strcmp(combo, "ctrl+v") == 0) inject('V', 1);
    else if (strcmp(combo, "v") == 0) inject('V', 0);
}

/* ---------- chords: Ctrl+C/X/V, then a slot number ---------- */

static void chord_end(void)
{
    KillTimer(g_wnd, TIMER_CHORD);
    KillTimer(g_wnd, TIMER_GAP);
    digit_hotkeys(0);
    g_action = ACT_NONE;
    g_digit_count = 0;
    g_digits[0] = 0;
}

static void chord_begin(int action, int timeout_ms)
{
    chord_end();
    g_action = action;
    digit_hotkeys(1);
    SetTimer(g_wnd, TIMER_CHORD, (UINT)timeout_ms, NULL);
}

static void chord_run(int slot)
{
    static const char *names[] = { "", "copy", "cut", "paste" };
    char line[48];
    snprintf(line, sizeof(line), "HK %s %d", names[g_action], slot);
    chord_end();
    emit(line);
}

/* The typed number is not a usable slot: a held-back paste is simply sent. */
static void chord_invalid(void)
{
    int was_paste = (g_action == ACT_PASTE);
    chord_end();
    if (was_paste) inject('V', 1);
}

/* Is there a filled slot whose number continues the digits typed so far (e.g. 10-19 after "1")? */
static int filled_slot_continues(int n)
{
    long scale = 10;                               /* each extra digit multiplies the range by 10 */
    for (int extra = 1; extra <= 5; extra++, scale *= 10) {
        long lo = (long)n * scale, hi = lo + scale - 1;
        if (lo > g_cfg.max_slots) break;
        if (hi > g_cfg.max_slots) hi = g_cfg.max_slots;
        for (long k = lo; k <= hi; k++)
            if (g_cfg.filled && g_cfg.filled[k]) return 1;
    }
    return 0;
}

static void on_digit(int d)
{
    if (g_action == ACT_NONE) return;
    KillTimer(g_wnd, TIMER_CHORD);
    KillTimer(g_wnd, TIMER_GAP);

    if (g_digit_count == 0 && d == 0) {          /* a lone 0 means slot 10 */
        if (g_cfg.max_slots >= 10) chord_run(10);
        else chord_invalid();
        return;
    }
    if (g_digit_count >= 6) { chord_invalid(); return; }
    g_digits[g_digit_count++] = (char)('0' + d);
    g_digits[g_digit_count] = 0;

    int n = atoi(g_digits);
    if (n < 1 || n > g_cfg.max_slots) { chord_invalid(); return; }

    char max_text[16];
    snprintf(max_text, sizeof(max_text), "%d", g_cfg.max_slots);
    int can_grow = (n * 10 <= g_cfg.max_slots) && (g_digit_count < (int)strlen(max_text));
    if (can_grow && g_action == ACT_PASTE)       /* only wait if a longer filled slot exists */
        can_grow = filled_slot_continues(n);

    if (can_grow) SetTimer(g_wnd, TIMER_GAP, (UINT)g_cfg.gap_ms, NULL);
    else chord_run(n);
}

/* ---------- commands from the app ---------- */

static int valid_token(const char *t)
{
    size_t n = strlen(t);
    if (n == 0 || n > 15) return 0;
    for (size_t i = 0; i < n; i++)
        if (!(isalnum((unsigned char)t[i]) || t[i] == '-')) return 0;
    return 1;
}

static int valid_action(const char *a)
{
    static const char *ok[] = {
        "open", "copy", "cut", "paste", "translate", "share", "mirror", "popup",
        "android", "android-copy", "android-cut", "android-paste",
        "ios", "ios-copy", "ios-cut", "ios-paste"
    };
    for (size_t i = 0; i < sizeof(ok) / sizeof(ok[0]); i++)
        if (strcmp(a, ok[i]) == 0) return 1;
    return 0;
}

static void set_filled(const char *list)
{
    if (!g_cfg.filled) g_cfg.filled = (unsigned char *)calloc(MAX_SLOT_LIMIT + 1, 1);
    if (!g_cfg.filled) return;
    memset(g_cfg.filled, 0, MAX_SLOT_LIMIT + 1);
    g_cfg.filled_count = 0;
    char *copy = _strdup(list), *save = NULL;
    for (char *t = strtok_s(copy, ",", &save); t; t = strtok_s(NULL, ",", &save)) {
        int n = atoi(t);
        if (n >= 1 && n <= MAX_SLOT_LIMIT && !g_cfg.filled[n]) { g_cfg.filled[n] = 1; g_cfg.filled_count++; }
    }
    free(copy);
}

static void cmd_state(char *args)
{
    char *save = NULL;
    for (char *t = strtok_s(args, " ", &save); t; t = strtok_s(NULL, " ", &save)) {
        char *eq = strchr(t, '=');
        if (!eq) continue;
        *eq = 0;
        const char *k = t, *v = eq + 1;
        if (strcmp(k, "login") == 0) g_cfg.login = atoi(v) != 0;
        else if (strcmp(k, "enabled") == 0) g_cfg.enabled = atoi(v) != 0;
        else if (strcmp(k, "max") == 0) g_cfg.max_slots = atoi(v) < 1 ? 1 : (atoi(v) > MAX_SLOT_LIMIT ? MAX_SLOT_LIMIT : atoi(v));
        else if (strcmp(k, "paste") == 0) g_cfg.paste_ms = atoi(v) < 100 ? 100 : atoi(v);
        else if (strcmp(k, "gap") == 0) g_cfg.gap_ms = atoi(v) < 50 ? 50 : atoi(v);
        else if (strcmp(k, "chord") == 0) g_cfg.chord_ms = atoi(v) < 200 ? 200 : atoi(v);
        else if (strcmp(k, "filled") == 0) set_filled(v);
    }
    if (!g_cfg.login || !g_cfg.enabled) chord_end();
    apply_hotkeys();
}

static void handle_command(char *text, int from_parent)
{
    char *args = strchr(text, ' ');
    if (args) *args++ = 0;
    else args = text + strlen(text);

    if (strcmp(text, "STATE") == 0) {
        if (from_parent) cmd_state(args);
    } else if (strcmp(text, "KEYS") == 0) {
        if (from_parent) inject_combo(args);
    } else if (strcmp(text, "SHOW") == 0) {
        emit("SHOW");
    } else if (strcmp(text, "ACTION") == 0 || valid_action(text)) {
        char line[64] = "ACTION", *save = NULL;
        int count = 0;
        if (strcmp(text, "ACTION") != 0) {
            strncat(line, " ", sizeof(line) - strlen(line) - 1);
            strncat(line, text, sizeof(line) - strlen(line) - 1);
            count = 1;
        }
        for (char *t = strtok_s(args, " ", &save); t && count < 3; t = strtok_s(NULL, " ", &save), count++) {
            if (!valid_token(t) || (count == 0 && !valid_action(t))) return;
            strncat(line, " ", sizeof(line) - strlen(line) - 1);
            strncat(line, t, sizeof(line) - strlen(line) - 1);
        }
        if (count > 0) emit(line);
    } else if (strcmp(text, "QUIT") == 0) {
        if (from_parent) PostQuitMessage(0);
    }
}

/* ---------- window ---------- */

/* SEC-R002-04: Verify whether sender_pid is Windows Explorer or a secondary RATT launch */
static int is_authorized_explorer(DWORD sender_pid)
{
    if (sender_pid == 0) return 0;
    HANDLE hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, sender_pid);
    if (!hProc) return 0;
    wchar_t exe_path[MAX_PATH * 2];
    DWORD sz = MAX_PATH * 2;
    BOOL ok = QueryFullProcessImageNameW(hProc, 0, exe_path, &sz);
    CloseHandle(hProc);
    if (!ok || sz == 0) return 0;
    const wchar_t *base = wcsrchr(exe_path, L'\\');
    base = base ? (base + 1) : exe_path;
    if (_wcsicmp(base, L"explorer.exe") == 0 ||
        _wcsicmp(base, L"RATT.exe") == 0 ||
        _wcsicmp(base, L"python.exe") == 0 ||
        _wcsicmp(base, L"pythonw.exe") == 0) {
        return 1;
    }
    return 0;
}

static LRESULT CALLBACK wnd_proc(HWND h, UINT msg, WPARAM w, LPARAM l)
{
    switch (msg) {
    case WM_HOTKEY: {
        int id = (int)w;
        if (id == ID_TOGGLE_PAUSE || id == ID_TOGGLE_PAUSE_ALT) {
            g_cfg.enabled = !g_cfg.enabled;
            if (!g_cfg.enabled) chord_end();
            apply_hotkeys();
            emit("TOGGLE");
            return 0;
        }
        if (!g_cfg.enabled) return 0;
        if (id == ID_COPY) { inject('C', 1); chord_begin(ACT_COPY, g_cfg.chord_ms); }
        else if (id == ID_CUT) { inject('X', 1); chord_begin(ACT_CUT, g_cfg.chord_ms); }
        else if (id == ID_PASTE) chord_begin(ACT_PASTE, g_cfg.paste_ms);
        else if (id == ID_POPUP) emit("POPUP");
        else if (id >= ID_DIGIT_BASE && id < ID_DIGIT_BASE + 40) on_digit((id - ID_DIGIT_BASE) / 4);
        return 0;
    }
    case WM_TIMER:
        if (w == TIMER_CHORD) {
            int was_paste = (g_action == ACT_PASTE && g_digit_count == 0);
            chord_end();
            if (was_paste) inject('V', 1);          /* no slot number came: ordinary paste */
        } else if (w == TIMER_GAP) {
            KillTimer(h, TIMER_GAP);
            if (g_action != ACT_NONE && g_digit_count > 0) chord_run(atoi(g_digits));
        } else if (w == TIMER_REARM) {
            KillTimer(h, TIMER_REARM);
            g_rearm_pending = 0;
            apply_hotkeys();
        }
        return 0;
    case WM_COPYDATA: {
        HWND hSender = (HWND)w;
        DWORD sender_pid = 0;
        if (hSender) GetWindowThreadProcessId(hSender, &sender_pid);
        int from_parent = g_dry_run || (sender_pid != 0 && sender_pid == g_parent_pid) || (g_event_cb != NULL && sender_pid == GetCurrentProcessId());
        COPYDATASTRUCT *cd = (COPYDATASTRUCT *)l;
        if (!cd || cd->dwData != COPYDATA_MAGIC || !cd->lpData || cd->cbData == 0 || cd->cbData > 65536)
            return FALSE;
        char *text = (char *)malloc((size_t)cd->cbData + 1);
        if (!text) return FALSE;
        memcpy(text, cd->lpData, cd->cbData);
        text[cd->cbData] = 0;
        /* Privileged STATE/KEYS/QUIT commands require from_parent; ACTION/SHOW are strictly token-whitelisted */
        if (!from_parent && strncmp(text, "ACTION ", 7) != 0 && strcmp(text, "SHOW") != 0 && !is_authorized_explorer(sender_pid)) {
            free(text);
            return FALSE;
        }
        handle_command(text, from_parent);
        free(text);
        return TRUE;
    }
    case WM_PIPE_READY:
        g_pipe = (HANDLE)l;
        flush_queue();
        return 0;
    }
    return DefWindowProcW(h, msg, w, l);
}

/* ---------- event pipe (server end; the app connects as a client) ---------- */

/* Security descriptor that lets only the current user open the pipe. */
static BOOL user_only_descriptor(SECURITY_ATTRIBUTES *sa)
{
    HANDLE token;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) return FALSE;
    BYTE buf[256];
    DWORD len = 0;
    wchar_t *sid_text = NULL;
    BOOL ok = GetTokenInformation(token, TokenUser, buf, sizeof(buf), &len)
           && ConvertSidToStringSidW(((TOKEN_USER *)buf)->User.Sid, &sid_text);
    CloseHandle(token);
    if (!ok) return FALSE;
    /* Restrict access strictly to the current user SID */
    wchar_t sddl[160];
    _snwprintf(sddl, 160, L"D:(A;;GA;;;%ls)", sid_text);
    sddl[159] = 0;
    LocalFree(sid_text);
    return ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1,
                                                                &sa->lpSecurityDescriptor, NULL);
}

static DWORD WINAPI pipe_thread(LPVOID param)
{
    DWORD expected_pid = (DWORD)(ULONG_PTR)param;
    wchar_t name[64];
    _snwprintf(name, 64, L"\\\\.\\pipe\\RATT.events.%lu", (unsigned long)expected_pid);

    SECURITY_ATTRIBUTES sa = { sizeof(sa), NULL, FALSE };
    if (!user_only_descriptor(&sa)) { log_line("pipe security failed: %lu", GetLastError()); return 1; }
    HANDLE p = CreateNamedPipeW(name, PIPE_ACCESS_OUTBOUND | FILE_FLAG_FIRST_PIPE_INSTANCE,
                                PIPE_TYPE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
                                1, 4096, 4096, 0, &sa);
    LocalFree(sa.lpSecurityDescriptor);
    if (p == INVALID_HANDLE_VALUE) { log_line("pipe create failed: %lu", GetLastError()); return 1; }
    for (int tries = 0; tries < 16; tries++) {
        if (ConnectNamedPipe(p, NULL) || GetLastError() == ERROR_PIPE_CONNECTED) {
            ULONG client_pid = 0;
            if (!g_dry_run && expected_pid != 0 &&
                GetNamedPipeClientProcessId(p, &client_pid) && client_pid != expected_pid) {
                DisconnectNamedPipe(p);
                continue;
            }
            PostMessageW(g_wnd, WM_PIPE_READY, 0, (LPARAM)p);
            return 0;
        }
        break;
    }
    CloseHandle(p);
    return 0;
}

static int tokenize(wchar_t *cmd, wchar_t **argv, int max)
{
    int n = 0;
    wchar_t *p = cmd;
    while (*p && n < max) {
        while (*p == L' ' || *p == L'\t') p++;
        if (!*p) break;
        int quoted = (*p == L'"');
        if (quoted) p++;
        argv[n++] = p;
        while (*p && (quoted ? *p != L'"' : (*p != L' ' && *p != L'\t'))) p++;
        if (*p) *p++ = 0;
    }
    return n;
}

/* ---------- Explorer folder & file selection introspection (COM IDispatch) ---------- */

static HRESULT disp_invoke(IDispatch *disp, LPCOLESTR name, WORD flags, VARIANT *arg, VARIANT *ret)
{
    if (!disp || !ret) return E_INVALIDARG;
    VariantInit(ret);
    DISPID dispid = 0;
    LPOLESTR names[1] = { (LPOLESTR)name };
    HRESULT hr = IDispatch_GetIDsOfNames(disp, &IID_NULL, names, 1, LOCALE_USER_DEFAULT, &dispid);
    if (FAILED(hr)) return hr;
    DISPPARAMS dp = { arg, NULL, arg ? 1 : 0, 0 };
    return IDispatch_Invoke(disp, dispid, &IID_NULL, LOCALE_USER_DEFAULT, flags, &dp, ret, NULL, NULL);
}

static IDispatch *disp_get_obj(IDispatch *disp, LPCOLESTR name, VARIANT *arg)
{
    VARIANT v;
    if (SUCCEEDED(disp_invoke(disp, name, DISPATCH_PROPERTYGET | DISPATCH_METHOD, arg, &v))) {
        if (v.vt == VT_DISPATCH && v.pdispVal) return v.pdispVal;
        VariantClear(&v);
    }
    return NULL;
}

static long disp_get_long(IDispatch *disp, LPCOLESTR name, long def_val)
{
    VARIANT v;
    if (SUCCEEDED(disp_invoke(disp, name, DISPATCH_PROPERTYGET, NULL, &v))) {
        VARIANT conv;
        VariantInit(&conv);
        long res = def_val;
        if (SUCCEEDED(VariantChangeType(&conv, &v, 0, VT_I4))) res = conv.lVal;
        VariantClear(&conv);
        VariantClear(&v);
        return res;
    }
    return def_val;
}

static BOOL disp_get_bstr(IDispatch *disp, LPCOLESTR name, wchar_t *out, size_t max_cch)
{
    out[0] = 0;
    VARIANT v;
    if (SUCCEEDED(disp_invoke(disp, name, DISPATCH_PROPERTYGET, NULL, &v))) {
        BOOL ok = FALSE;
        if (v.vt == VT_BSTR && v.bstrVal && v.bstrVal[0]) {
            wcsncpy(out, v.bstrVal, max_cch - 1);
            out[max_cch - 1] = 0;
            ok = TRUE;
        }
        VariantClear(&v);
        return ok;
    }
    return FALSE;
}

static void append_line(wchar_t *out_buf, int max_chars, const wchar_t *prefix, const wchar_t *val)
{
    if (!val || !val[0]) return;
    size_t cur = wcslen(out_buf);
    size_t need = wcslen(prefix) + wcslen(val) + 2;
    if ((int)(cur + need) >= max_chars) return;
    wcscat(out_buf, prefix);
    wcscat(out_buf, val);
    wcscat(out_buf, L"\n");
}

__declspec(dllexport) int WINAPI GetExplorerSelectionW(HWND target_hwnd, wchar_t *out_buf, int max_chars)
{
    if (!out_buf || max_chars <= 16) return 0;
    out_buf[0] = 0;

    HWND fg = target_hwnd ? target_hwnd : GetForegroundWindow();
    wchar_t cls[64] = {0};
    if (fg) GetClassNameW(fg, cls, 63);

    /* If the user is on the Windows Desktop, return the Desktop folder path */
    if (_wcsicmp(cls, L"Progman") == 0 || _wcsicmp(cls, L"WorkerW") == 0) {
        wchar_t desk[MAX_PATH] = {0};
        if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_DESKTOPDIRECTORY, NULL, 0, desk)) && desk[0]) {
            append_line(out_buf, max_chars, L"FOLDER\t", desk);
            return 1;
        }
    }

    int is_explorer = (_wcsicmp(cls, L"CabinetWClass") == 0 || _wcsicmp(cls, L"ExploreWClass") == 0);
    if (target_hwnd != NULL && !is_explorer) {
        return 0;
    }

    HRESULT hr_init = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    CLSID clsid;
    IDispatch *pShell = NULL;
    if (SUCCEEDED(CLSIDFromProgID(L"Shell.Application", &clsid)) &&
        SUCCEEDED(CoCreateInstance(&clsid, NULL, CLSCTX_INPROC_SERVER | CLSCTX_LOCAL_SERVER,
                                   &IID_IDispatch, (void **)&pShell)) && pShell) {
        IDispatch *pWins = disp_get_obj(pShell, L"Windows", NULL);
        if (pWins) {
            long count = disp_get_long(pWins, L"Count", 0);
            IDispatch *matchedWin = NULL;
            IDispatch *titleMatchedWin = NULL;
            IDispatch *fallbackWin = NULL;
            wchar_t fg_title[MAX_PATH] = {0};
            if (fg) GetWindowTextW(fg, fg_title, MAX_PATH - 1);

            for (long i = 0; i < count; i++) {
                VARIANT idx;
                VariantInit(&idx);
                idx.vt = VT_I4;
                idx.lVal = i;
                IDispatch *pWin = disp_get_obj(pWins, L"Item", &idx);
                if (!pWin) continue;
                long w_hwnd = disp_get_long(pWin, L"HWND", 0);
                if (fg && (HWND)(ULONG_PTR)w_hwnd == fg) {
                    /* On Windows 11 with Explorer tabs, multiple tabs share the same top HWND.
                     * Prefer the tab whose LocationName appears in the foreground window title. */
                    wchar_t loc_name[MAX_PATH] = {0};
                    disp_get_bstr(pWin, L"LocationName", loc_name, MAX_PATH);
                    if (loc_name[0] && fg_title[0] && wcsstr(fg_title, loc_name) != NULL) {
                        if (titleMatchedWin) IDispatch_Release(titleMatchedWin);
                        titleMatchedWin = pWin;
                        continue;
                    }
                    if (!matchedWin) {
                        matchedWin = pWin;
                        continue;
                    }
                }
                if (!fallbackWin && w_hwnd != 0) {
                    fallbackWin = pWin;
                } else {
                    IDispatch_Release(pWin);
                }
            }
            if (titleMatchedWin) {
                if (matchedWin) IDispatch_Release(matchedWin);
                matchedWin = titleMatchedWin;
            }
            IDispatch *useWin = matchedWin ? matchedWin : (target_hwnd == NULL ? fallbackWin : NULL);
            if (useWin) {
                IDispatch *pDoc = disp_get_obj(useWin, L"Document", NULL);
                if (pDoc) {
                    IDispatch *pFolder = disp_get_obj(pDoc, L"Folder", NULL);
                    if (pFolder) {
                        IDispatch *pSelf = disp_get_obj(pFolder, L"Self", NULL);
                        if (pSelf) {
                            wchar_t fpath[MAX_PATH * 2];
                            if (disp_get_bstr(pSelf, L"Path", fpath, MAX_PATH * 2) &&
                                GetFileAttributesW(fpath) != INVALID_FILE_ATTRIBUTES) {
                                append_line(out_buf, max_chars, L"FOLDER\t", fpath);
                            }
                            IDispatch_Release(pSelf);
                        }
                        IDispatch_Release(pFolder);
                    }
                    IDispatch *pSel = disp_get_obj(pDoc, L"SelectedItems", NULL);
                    if (pSel) {
                        long sel_count = disp_get_long(pSel, L"Count", 0);
                        if (sel_count > 256) sel_count = 256;
                        for (long j = 0; j < sel_count; j++) {
                            VARIANT jdx;
                            VariantInit(&jdx);
                            jdx.vt = VT_I4;
                            jdx.lVal = j;
                            IDispatch *pItem = disp_get_obj(pSel, L"Item", &jdx);
                            if (pItem) {
                                wchar_t ipath[MAX_PATH * 2];
                                if (disp_get_bstr(pItem, L"Path", ipath, MAX_PATH * 2) &&
                                    GetFileAttributesW(ipath) != INVALID_FILE_ATTRIBUTES) {
                                    append_line(out_buf, max_chars, L"FILE\t", ipath);
                                }
                                IDispatch_Release(pItem);
                            }
                        }
                        IDispatch_Release(pSel);
                    }
                    IDispatch_Release(pDoc);
                }
            }
            if (matchedWin && fallbackWin && matchedWin != fallbackWin) IDispatch_Release(fallbackWin);
            if (matchedWin) IDispatch_Release(matchedWin);
            else if (fallbackWin) IDispatch_Release(fallbackWin);
            IDispatch_Release(pWins);
        }
        IDispatch_Release(pShell);
    }
    if (SUCCEEDED(hr_init)) CoUninitialize();
    return out_buf[0] != 0 ? 1 : 0;
}

/* ---------- entry points (hosted by rundll32.exe or in-process thread) ---------- */

static HINSTANCE g_module;

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) { g_module = h; DisableThreadLibraryCalls(h); }
    return TRUE;
}

/* rundll32 ratt_daemon.dll,RunDaemonW --parent <app pid>   - serve until the app ends */
__declspec(dllexport) void CALLBACK RunDaemonW(HWND w, HINSTANCE i, LPWSTR cmd, int show)
{
    (void)w; (void)i; (void)show;
    wchar_t *argv[8];
    wchar_t *copy = _wcsdup(cmd ? cmd : L"");
    if (!copy) return;
    int argc = tokenize(copy, argv, 8);

    DWORD parent_pid = 0;
    for (int k = 0; k + 1 < argc; k++)
        if (wcscmp(argv[k], L"--parent") == 0) parent_pid = (DWORD)_wtol(argv[k + 1]);
    free(copy);
    if (!parent_pid) parent_pid = GetCurrentProcessId();

    HANDLE parent = OpenProcess(SYNCHRONIZE, FALSE, parent_pid);
    if (!parent) return;
    g_parent_pid = parent_pid;

    /* Terminate any stale external daemon instances left over from earlier sessions */
    HWND old_wnd = NULL;
    while ((old_wnd = FindWindowExW(HWND_MESSAGE, old_wnd, WND_CLASS, NULL)) != NULL) {
        DWORD old_pid = 0;
        GetWindowThreadProcessId(old_wnd, &old_pid);
        if (old_pid && old_pid != GetCurrentProcessId()) {
            HANDLE old_proc = OpenProcess(PROCESS_TERMINATE | SYNCHRONIZE, FALSE, old_pid);
            if (old_proc) {
                TerminateProcess(old_proc, 0);
                WaitForSingleObject(old_proc, 1000);
                CloseHandle(old_proc);
            }
            old_wnd = NULL;
        }
    }

    SECURITY_ATTRIBUTES msa = { sizeof(msa), NULL, FALSE };
    BOOL have_msa = user_only_descriptor(&msa);
    HANDLE single = CreateMutexW(have_msa ? &msa : NULL, TRUE, L"Local\\RATT.Daemon.v2");
    if (have_msa) LocalFree(msa.lpSecurityDescriptor);
    if (!g_event_cb && (!single || GetLastError() == ERROR_ALREADY_EXISTS)) {
        if (single) CloseHandle(single);
        CloseHandle(parent);
        return;
    }

    wchar_t dry[8];
    g_dry_run = GetEnvironmentVariableW(L"RATT_DAEMON_DRYRUN", dry, 8) > 0;

    WNDCLASSW wc;
    memset(&wc, 0, sizeof(wc));
    wc.lpfnWndProc = wnd_proc;
    wc.hInstance = g_module;
    wc.lpszClassName = WND_CLASS;
    RegisterClassW(&wc);
    g_wnd = CreateWindowExW(0, WND_CLASS, L"RATT helper", 0, 0, 0, 0, 0, HWND_MESSAGE, NULL, g_module, NULL);
    if (!g_wnd) { CloseHandle(parent); CloseHandle(single); return; }

    if (!g_event_cb) {
        HANDLE t = CreateThread(NULL, 0, pipe_thread, (LPVOID)(ULONG_PTR)parent_pid, 0, NULL);
        if (t) CloseHandle(t);
    }

    for (;;) {
        DWORD r = MsgWaitForMultipleObjects(1, &parent, FALSE, INFINITE, QS_ALLINPUT);
        if (r == WAIT_OBJECT_0) break;               /* the app has ended */
        MSG m;
        int quit = 0;
        while (PeekMessageW(&m, NULL, 0, 0, PM_REMOVE)) {
            if (m.message == WM_QUIT) { quit = 1; break; }
            TranslateMessage(&m);
            DispatchMessageW(&m);
        }
        if (quit) break;
    }

    chord_end();
    for (int id = 1; id <= ID_MAX_STATIC; id++) UnregisterHotKey(g_wnd, id);
    if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe);
    DestroyWindow(g_wnd);
    CloseHandle(parent);
    CloseHandle(single);
}
