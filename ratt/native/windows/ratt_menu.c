/*
 * RATT right-click menu - Explorer shell extension (IContextMenu).
 *
 * Why a DLL: a menu made only of registry entries is limited by Windows to 16 entries in
 * total, which cannot hold "Copy / Cut / Paste / Translate" with 10+ slots.  A shell
 * extension builds the menu in code, so everything cascades under one "RATT" entry.
 *
 * The menu content is read from %APPDATA%\RATT\menu_state.txt, written by the RATT app
 * (ratt/context_menu_updater.py) whenever slots / plan change.  Each line (UTF-8, tabs):
 *
 *   LAUNCH <exe> <argument-prefix>        how to start RATT when it is not running (the item
 *                                         arguments are appended); a running RATT is reached
 *                                         through its helper window instead
 *   LOGO   <raw file>                     4-byte width, 4-byte height, premultiplied BGRA
 *   ITEM   <depth> <kind> <color|-> <args|-> <label>
 *            depth 0 = directly under "RATT"; kind M = submenu, I = item, D = disabled item
 *            color = RRGGBB for the slot dot
 *
 * Build:  gcc -shared -O2 -s -o ratt_menu.dll ratt_menu.c -lole32 -luuid -lshell32 -lgdi32 -luser32 -static
 */
#define WIN32_LEAN_AND_MEAN
#define COBJMACROS
#include <windows.h>
#include <shlobj.h>
#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <math.h>
#include <shellapi.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

/* {B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21} */
static const CLSID CLSID_RattMenu =
    {0xB2D6C4A1, 0x3E7F, 0x4C59, {0x9A, 0x18, 0x5D, 0x0E, 0x7F, 0x6A, 0x4B, 0x21}};

#define MAX_BMPS 600
#define MAX_ARGS 1200
#define MAX_DEPTH 8

static LONG g_objects = 0;
static LONG g_locks = 0;
static HINSTANCE g_module = NULL;

typedef struct Ext {
    const IContextMenuVtbl *lpVtbl;
    const IShellExtInitVtbl *lpInitVtbl;
    LONG ref;
    HBITMAP bmps[MAX_BMPS];
    int nbmps;
    wchar_t *args[MAX_ARGS];
    int nargs;
    wchar_t launcher[MAX_PATH * 2];
    wchar_t prefix[MAX_PATH * 2];
    wchar_t folder_path[MAX_PATH * 2];
    wchar_t *sel_files[256];
    int nsel_files;
} Ext;

static Ext *from_init(IShellExtInit *p) { return (Ext *)((char *)p - offsetof(Ext, lpInitVtbl)); }

/* ---------- small helpers ---------- */

static wchar_t *utf8_to_w(const char *s, int len)
{
    int n = MultiByteToWideChar(CP_UTF8, 0, s, len, NULL, 0);
    wchar_t *w = (wchar_t *)calloc((size_t)n + 1, sizeof(wchar_t));
    if (w) MultiByteToWideChar(CP_UTF8, 0, s, len, w, n);
    return w;
}

static char *read_file(const wchar_t *path, DWORD *size)
{
    if (!path || !path[0]) return NULL;
    /* Block UNC paths (\\server\share) and device/pipe paths (\\.\pipe\...) */
    if (path[0] == L'\\' && path[1] == L'\\') return NULL;
    HANDLE h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                           OPEN_EXISTING,
                           FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN | SECURITY_SQOS_PRESENT | SECURITY_ANONYMOUS,
                           NULL);
    if (h == INVALID_HANDLE_VALUE) return NULL;
    if (GetFileType(h) != FILE_TYPE_DISK) { CloseHandle(h); return NULL; }
    DWORD sz = GetFileSize(h, NULL), got = 0;
    if (sz == INVALID_FILE_SIZE || sz > 4 * 1024 * 1024) { CloseHandle(h); return NULL; }
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { CloseHandle(h); return NULL; }
    if (!ReadFile(h, buf, sz, &got, NULL)) got = 0;
    CloseHandle(h);
    buf[got] = 0;
    *size = got;
    return buf;
}

static HBITMAP make_dib(int w, int h, void **bits)
{
    BITMAPINFO bi;
    memset(&bi, 0, sizeof(bi));
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = w;
    bi.bmiHeader.biHeight = -h;               /* top-down */
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    HDC dc = GetDC(NULL);
    HBITMAP bmp = CreateDIBSection(dc, &bi, DIB_RGB_COLORS, bits, NULL, 0);
    ReleaseDC(NULL, dc);
    return bmp;
}

static int icon_size(void)
{
    int s = GetSystemMetrics(SM_CXSMICON);
    return (s < 12 || s > 48) ? 16 : s;
}

static void keep(Ext *e, HBITMAP b) { if (b && e->nbmps < MAX_BMPS) e->bmps[e->nbmps++] = b; }

/* round coloured dot, anti-aliased, premultiplied alpha */
static HBITMAP dot_bitmap(Ext *e, unsigned rgb)
{
    int s = icon_size();
    DWORD *px = NULL;
    HBITMAP b = make_dib(s, s, (void **)&px);
    if (!b || !px) return NULL;
    double c = (s - 1) / 2.0, r = s * 0.34;
    unsigned R = (rgb >> 16) & 255, G = (rgb >> 8) & 255, B = rgb & 255;
    for (int y = 0; y < s; y++)
        for (int x = 0; x < s; x++) {
            double dx = x - c, dy = y - c, d = sqrt(dx * dx + dy * dy);
            double a = r + 0.5 - d;
            if (a < 0) a = 0;
            if (a > 1) a = 1;
            unsigned A = (unsigned)(a * 255.0 + 0.5);
            px[y * s + x] = (A << 24) | ((R * A / 255) << 16) | ((G * A / 255) << 8) | (B * A / 255);
        }
    keep(e, b);
    return b;
}

/* logo from raw premultiplied BGRA file, box-resampled to the menu icon size */
static HBITMAP logo_bitmap(Ext *e, const wchar_t *path)
{
    DWORD size = 0;
    unsigned char *raw = (unsigned char *)read_file(path, &size);
    if (!raw) return NULL;
    HBITMAP result = NULL;
    if (size >= 8) {
        unsigned sw = *(unsigned *)raw, sh = *(unsigned *)(raw + 4);
        if (sw > 0 && sh > 0 && sw <= 1024 && sh <= 1024 && size >= 8 + sw * sh * 4) {
            int s = icon_size();
            DWORD *px = NULL;
            HBITMAP b = make_dib(s, s, (void **)&px);
            if (b && px) {
                const unsigned char *src = raw + 8;
                for (int y = 0; y < s; y++)
                    for (int x = 0; x < s; x++) {
                        unsigned x0 = x * sw / s, x1 = (x + 1) * sw / s, y0 = y * sh / s, y1 = (y + 1) * sh / s;
                        if (x1 <= x0) x1 = x0 + 1;
                        if (y1 <= y0) y1 = y0 + 1;
                        unsigned long sum[4] = {0, 0, 0, 0}, n = 0;
                        for (unsigned yy = y0; yy < y1; yy++)
                            for (unsigned xx = x0; xx < x1; xx++) {
                                const unsigned char *p = src + (yy * sw + xx) * 4;
                                sum[0] += p[0]; sum[1] += p[1]; sum[2] += p[2]; sum[3] += p[3];
                                n++;
                            }
                        px[y * s + x] = ((DWORD)(sum[3] / n) << 24) | ((DWORD)(sum[2] / n) << 16) |
                                        ((DWORD)(sum[1] / n) << 8) | (DWORD)(sum[0] / n);
                    }
                keep(e, b);
                result = b;
            }
        }
    }
    free(raw);
    return result;
}

/* "&" in a label must be doubled or it becomes an accelerator */
static wchar_t *menu_label(const wchar_t *s)
{
    size_t n = wcslen(s), j = 0;
    wchar_t *o = (wchar_t *)calloc(n * 2 + 1, sizeof(wchar_t));
    if (!o) return NULL;
    for (size_t i = 0; i < n; i++) { if (s[i] == L'&') o[j++] = L'&'; o[j++] = s[i]; }
    return o;
}

/* ---------- menu construction ---------- */

static int add_entry(Ext *e, HMENU parent, UINT *nextId, UINT idFirst, int kind /*M,I,D*/,
                     HMENU *subOut, const wchar_t *label, HBITMAP bmp, const wchar_t *args)
{
    MENUITEMINFOW mi;
    memset(&mi, 0, sizeof(mi));
    mi.cbSize = sizeof(mi);
    wchar_t *lab = menu_label(label);
    if (!lab) return 0;
    mi.fMask = MIIM_STRING | MIIM_ID | MIIM_STATE;
    mi.dwTypeData = lab;
    mi.fState = (kind == 'D') ? (MFS_DISABLED | MFS_GRAYED) : MFS_ENABLED;
    if (bmp) { mi.fMask |= MIIM_BITMAP; mi.hbmpItem = bmp; }
    if (kind == 'M') {
        HMENU sub = CreatePopupMenu();
        if (!sub) { free(lab); return 0; }
        mi.fMask |= MIIM_SUBMENU;
        mi.hSubMenu = sub;
        *subOut = sub;
        mi.wID = *nextId; (*nextId)++;
    } else {
        mi.wID = *nextId;
        if (args && e->nargs < MAX_ARGS && (int)(*nextId - idFirst) == e->nargs) {
            e->args[e->nargs++] = _wcsdup(args);
        } else {
            while ((int)(*nextId - idFirst) > e->nargs && e->nargs < MAX_ARGS) e->args[e->nargs++] = NULL;
            if (e->nargs < MAX_ARGS) e->args[e->nargs++] = args ? _wcsdup(args) : NULL;
        }
        (*nextId)++;
    }
    BOOL ok = InsertMenuItemW(parent, (UINT)GetMenuItemCount(parent), TRUE, &mi);
    free(lab);
    return ok ? 1 : 0;
}

static HRESULT build_menu(Ext *e, HMENU hmenu, UINT index, UINT idFirst, UINT idLast)
{
    wchar_t path[MAX_PATH * 2];
    DWORD len = GetEnvironmentVariableW(L"APPDATA", path, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) return 0;
    wcscat(path, L"\\RATT\\menu_state.txt");
    DWORD size = 0;
    char *txt = read_file(path, &size);
    if (!txt) return 0;

    HMENU stack[MAX_DEPTH + 2];
    int top = 0;
    stack[0] = CreatePopupMenu();
    UINT next = idFirst;
    HBITMAP logo = NULL;
    int items = 0;

    e->launcher[0] = 0;
    e->prefix[0] = 0;

    char *p = txt;
    while (p && *p) {
        char *eol = strchr(p, '\n');
        size_t ll = eol ? (size_t)(eol - p) : strlen(p);
        char *line = (char *)malloc(ll + 1);
        if (!line) break;
        memcpy(line, p, ll);
        line[ll] = 0;
        if (ll && line[ll - 1] == '\r') line[ll - 1] = 0;
        p = eol ? eol + 1 : NULL;

        /* split on tabs (max 6 fields) */
        char *f[6] = {0};
        int nf = 0;
        char *q = line;
        while (nf < 6) {
            f[nf++] = q;
            char *t = strchr(q, '\t');
            if (!t || nf == 6) break;
            *t = 0;
            q = t + 1;
        }

        if (nf >= 2 && strcmp(f[0], "LAUNCH") == 0) {
            wchar_t *a = utf8_to_w(f[1], -1);
            if (a) { wcsncpy(e->launcher, a, MAX_PATH * 2 - 1); free(a); }
            if (nf >= 3) {
                wchar_t *b = utf8_to_w(f[2], -1);
                if (b) { wcsncpy(e->prefix, b, MAX_PATH * 2 - 1); free(b); }
            }
        } else if (nf >= 2 && strcmp(f[0], "LOGO") == 0) {
            wchar_t *a = utf8_to_w(f[1], -1);
            if (a) { logo = logo_bitmap(e, a); free(a); }
        } else if (nf >= 6 && strcmp(f[0], "ITEM") == 0 && next < idLast - 1) {
            int depth = atoi(f[1]);
            char kind = f[2][0];
            if (depth >= 0 && depth <= top && depth < MAX_DEPTH && (kind == 'M' || kind == 'I' || kind == 'D')) {
                top = depth;                                /* close deeper submenus */
                wchar_t *label = utf8_to_w(f[5], -1);
                wchar_t *args = (strcmp(f[4], "-") != 0) ? utf8_to_w(f[4], -1) : NULL;
                HBITMAP bmp = NULL;
                if (strcmp(f[3], "-") != 0) bmp = dot_bitmap(e, (unsigned)strtoul(f[3], NULL, 16));
                HMENU sub = NULL;
                if (label && add_entry(e, stack[depth], &next, idFirst, kind, &sub, label, bmp, args)) {
                    items++;
                    if (kind == 'M' && sub) { stack[depth + 1] = sub; top = depth + 1; }
                }
                free(label);
                free(args);
            }
        }
        free(line);
    }
    free(txt);

    if (items == 0 || e->launcher[0] == 0) {
        DestroyMenu(stack[0]);                              /* nothing to show */
        return 0;
    }

    MENUITEMINFOW mi;
    memset(&mi, 0, sizeof(mi));
    mi.cbSize = sizeof(mi);
    mi.fMask = MIIM_STRING | MIIM_SUBMENU | MIIM_ID;
    mi.dwTypeData = (LPWSTR)L"RATT";
    mi.hSubMenu = stack[0];
    mi.wID = next++;
    if (logo) { mi.fMask |= MIIM_BITMAP; mi.hbmpItem = logo; }
    if (!InsertMenuItemW(hmenu, index, TRUE, &mi)) {
        DestroyMenu(stack[0]);
        return 0;
    }
    return MAKE_HRESULT(SEVERITY_SUCCESS, FACILITY_NULL, next - idFirst);
}

/* ---------- IContextMenu ---------- */

static HRESULT STDMETHODCALLTYPE CM_QueryInterface(IContextMenu *This, REFIID riid, void **ppv)
{
    Ext *e = (Ext *)This;
    if (IsEqualIID(riid, &IID_IUnknown) || IsEqualIID(riid, &IID_IContextMenu)) {
        *ppv = &e->lpVtbl;
    } else if (IsEqualIID(riid, &IID_IShellExtInit)) {
        *ppv = &e->lpInitVtbl;
    } else {
        *ppv = NULL;
        return E_NOINTERFACE;
    }
    InterlockedIncrement(&e->ref);
    return S_OK;
}

static ULONG STDMETHODCALLTYPE CM_AddRef(IContextMenu *This)
{
    return (ULONG)InterlockedIncrement(&((Ext *)This)->ref);
}

static ULONG STDMETHODCALLTYPE CM_Release(IContextMenu *This)
{
    Ext *e = (Ext *)This;
    LONG r = InterlockedDecrement(&e->ref);
    if (r == 0) {
        for (int i = 0; i < e->nbmps; i++) DeleteObject(e->bmps[i]);
        for (int i = 0; i < e->nargs; i++) free(e->args[i]);
        for (int i = 0; i < e->nsel_files; i++) free(e->sel_files[i]);
        free(e);
        InterlockedDecrement(&g_objects);
    }
    return (ULONG)r;
}

static HRESULT STDMETHODCALLTYPE CM_Query(IContextMenu *This, HMENU hmenu, UINT index, UINT idFirst,
                                          UINT idLast, UINT flags)
{
    Ext *e = (Ext *)This;
    if (flags & CMF_DEFAULTONLY) return MAKE_HRESULT(SEVERITY_SUCCESS, FACILITY_NULL, 0);
    /* rebuild from scratch each time the menu opens */
    for (int i = 0; i < e->nbmps; i++) DeleteObject(e->bmps[i]);
    e->nbmps = 0;
    for (int i = 0; i < e->nargs; i++) { free(e->args[i]); e->args[i] = NULL; }
    e->nargs = 0;
    return build_menu(e, hmenu, index, idFirst, idLast);
}

/* Validate menu action arguments against strict action/token whitelist */
static BOOL valid_menu_args(const wchar_t *wargs)
{
    if (!wargs || !wargs[0]) return FALSE;
    char buf[128];
    int n = WideCharToMultiByte(CP_UTF8, 0, wargs, -1, buf, sizeof(buf), NULL, NULL);
    if (n <= 0 || n >= (int)sizeof(buf)) return FALSE;

    static const char *ok_actions[] = {
        "open", "copy", "cut", "paste", "translate", "share", "mirror", "popup",
        "android", "android-copy", "android-cut", "android-paste",
        "ios", "ios-copy", "ios-cut", "ios-paste"
    };
    char *save = NULL;
    int count = 0;
    for (char *t = strtok_s(buf, " ", &save); t; t = strtok_s(NULL, " ", &save), count++) {
        if (count >= 3) return FALSE;
        size_t len = strlen(t);
        if (len == 0 || len > 15) return FALSE;
        for (size_t i = 0; i < len; i++) {
            if (!(isalnum((unsigned char)t[i]) || t[i] == '-')) return FALSE;
        }
        if (count == 0) {
            int action_ok = 0;
            for (size_t k = 0; k < sizeof(ok_actions) / sizeof(ok_actions[0]); k++) {
                if (strcmp(t, ok_actions[k]) == 0) { action_ok = 1; break; }
            }
            if (!action_ok) return FALSE;
        }
    }
    return count > 0;
}

static BOOL valid_launcher_path(const wchar_t *launcher, const wchar_t *prefix)
{
    if (!launcher || !launcher[0]) return FALSE;
    /* Block UNC paths, device namespaces, relative paths, and traversal tokens (WIN-02) */
    if (launcher[0] == L'\\' && launcher[1] == L'\\') return FALSE;
    if (wcsstr(launcher, L"..") != NULL) return FALSE;
    if (wcspbrk(launcher, L"&|;`$><\r\n\"'") != NULL) return FALSE;
    if (prefix && (wcsstr(prefix, L"..") != NULL || wcspbrk(prefix, L"&|;`$><\r\n") != NULL)) return FALSE;
    return TRUE;
}

/* Hand the chosen action to the running RATT helper window (instant). If RATT is not
 * running yet, start it with the action as its argument instead. */
static BOOL send_to_helper(const wchar_t *args)
{
    HWND helper = FindWindowExW(HWND_MESSAGE, NULL, L"RATTDaemonWnd", NULL);
    if (!helper) return FALSE;
    char text[160] = "ACTION ";
    WideCharToMultiByte(CP_UTF8, 0, args, -1, text + 7, (int)sizeof(text) - 8, NULL, NULL);
    COPYDATASTRUCT cd = { 0x52415454u, (DWORD)strlen(text), text };
    DWORD_PTR result;
    HWND sender = GetShellWindow();
    if (!sender) sender = GetDesktopWindow();
    return SendMessageTimeoutW(helper, WM_COPYDATA, (WPARAM)sender, (LPARAM)&cd, SMTO_ABORTIFHUNG, 1500, &result) != 0;
}

static void write_shell_context(Ext *e)
{
    wchar_t path[MAX_PATH * 2];
    DWORD len = GetEnvironmentVariableW(L"APPDATA", path, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) return;
    wcscat(path, L"\\RATT\\shell_context.txt");
    FILE *fp = _wfopen(path, L"wb");
    if (!fp) return;
    if (e->folder_path[0]) {
        char u8[MAX_PATH * 4];
        if (WideCharToMultiByte(CP_UTF8, 0, e->folder_path, -1, u8, sizeof(u8), NULL, NULL) > 0)
            fprintf(fp, "FOLDER\t%s\n", u8);
    }
    for (int i = 0; i < e->nsel_files; i++) {
        if (e->sel_files[i]) {
            char u8[MAX_PATH * 4];
            if (WideCharToMultiByte(CP_UTF8, 0, e->sel_files[i], -1, u8, sizeof(u8), NULL, NULL) > 0)
                fprintf(fp, "FILE\t%s\n", u8);
        }
    }
    fclose(fp);
}

static HRESULT STDMETHODCALLTYPE CM_Invoke(IContextMenu *This, CMINVOKECOMMANDINFO *ici)
{
    Ext *e = (Ext *)This;
    if (!ici || HIWORD((ULONG_PTR)ici->lpVerb) != 0) return E_INVALIDARG;
    UINT idx = LOWORD((ULONG_PTR)ici->lpVerb);
    if ((int)idx >= e->nargs || !e->args[idx] || e->launcher[0] == 0) return E_INVALIDARG;
    if (!valid_menu_args(e->args[idx]) || !valid_launcher_path(e->launcher, e->prefix)) return E_INVALIDARG;

    /* WIN-02: Canonicalize launcher via GetFullPathNameW and verify it resides in the
     * DLL's own trusted installation directory (or Program Files\RATT), never arbitrary AppData */
    wchar_t canon_launcher[MAX_PATH * 2];
    DWORD clen = GetFullPathNameW(e->launcher, MAX_PATH * 2, canon_launcher, NULL);
    if (clen == 0 || clen >= MAX_PATH * 2) return E_ACCESSDENIED;
    if (canon_launcher[0] == L'\\' && canon_launcher[1] == L'\\') return E_ACCESSDENIED;

    wchar_t trusted_dir[MAX_PATH * 2];
    if (!g_module || GetModuleFileNameW(g_module, trusted_dir, MAX_PATH * 2) == 0) {
        return E_ACCESSDENIED;
    }
    wchar_t *slash = wcsrchr(trusted_dir, L'\\');
    if (!slash) return E_ACCESSDENIED;
    *(slash + 1) = 0;

    /* Allow launcher strictly inside the DLL's own directory (or parent dir when DLL is in assets\) */
    BOOL trusted = (_wcsnicmp(canon_launcher, trusted_dir, wcslen(trusted_dir)) == 0);
    if (!trusted) {
        wchar_t parent_dir[MAX_PATH * 2];
        wcsncpy(parent_dir, trusted_dir, MAX_PATH * 2 - 1);
        parent_dir[MAX_PATH * 2 - 1] = 0;
        size_t plen = wcslen(parent_dir);
        if (plen > 1) {
            parent_dir[plen - 1] = 0; /* strip trailing backslash */
            wchar_t *pslash = wcsrchr(parent_dir, L'\\');
            if (pslash) {
                *(pslash + 1) = 0;
                if (_wcsnicmp(canon_launcher, parent_dir, wcslen(parent_dir)) == 0) {
                    trusted = TRUE;
                }
            }
        }
    }
    /* Restrict executable basename to RATT.exe only */
    const wchar_t *lbase = wcsrchr(canon_launcher, L'\\');
    lbase = lbase ? (lbase + 1) : canon_launcher;
    if (!trusted || _wcsicmp(lbase, L"RATT.exe") != 0) {
        return E_ACCESSDENIED;
    }

    write_shell_context(e);
    if (send_to_helper(e->args[idx])) return S_OK;

    /* WIN-02: Use CreateProcessW with explicit lpApplicationName instead of ShellExecuteW */
    wchar_t cmdline[MAX_PATH * 2 + 192];
    _snwprintf(cmdline, sizeof(cmdline) / sizeof(cmdline[0]) - 1, L"\"%ls\" %ls", canon_launcher, e->args[idx]);
    cmdline[sizeof(cmdline) / sizeof(cmdline[0]) - 1] = 0;
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    memset(&si, 0, sizeof(si));
    memset(&pi, 0, sizeof(pi));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    BOOL ok = CreateProcessW(canon_launcher, cmdline, NULL, NULL, FALSE,
                             CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    if (ok) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        return S_OK;
    }
    return E_FAIL;
}

static HRESULT STDMETHODCALLTYPE CM_GetCommandString(IContextMenu *This, UINT_PTR id, UINT type,
                                                     UINT *res, CHAR *name, UINT cch)
{
    (void)This; (void)id; (void)type; (void)res; (void)name; (void)cch;
    return E_NOTIMPL;
}

static const IContextMenuVtbl g_cmVtbl = {
    CM_QueryInterface, CM_AddRef, CM_Release, CM_Query, CM_Invoke, CM_GetCommandString
};

/* ---------- IShellExtInit ---------- */

static HRESULT STDMETHODCALLTYPE SI_QueryInterface(IShellExtInit *This, REFIID riid, void **ppv)
{
    return CM_QueryInterface((IContextMenu *)from_init(This), riid, ppv);
}
static ULONG STDMETHODCALLTYPE SI_AddRef(IShellExtInit *This) { return CM_AddRef((IContextMenu *)from_init(This)); }
static ULONG STDMETHODCALLTYPE SI_Release(IShellExtInit *This) { return CM_Release((IContextMenu *)from_init(This)); }
static HRESULT STDMETHODCALLTYPE SI_Initialize(IShellExtInit *This, PCIDLIST_ABSOLUTE f, IDataObject *d, HKEY k)
{
    (void)k;
    Ext *e = from_init(This);
    for (int i = 0; i < e->nsel_files; i++) { free(e->sel_files[i]); e->sel_files[i] = NULL; }
    e->nsel_files = 0;
    e->folder_path[0] = 0;

    if (f) {
        SHGetPathFromIDListW(f, e->folder_path);
    }
    if (d) {
        FORMATETC fmt = { CF_HDROP, NULL, DVASPECT_CONTENT, -1, TYMED_HGLOBAL };
        STGMEDIUM stg;
        memset(&stg, 0, sizeof(stg));
        if (SUCCEEDED(IDataObject_GetData(d, &fmt, &stg))) {
            HDROP hdrop = (HDROP)GlobalLock(stg.hGlobal);
            if (hdrop) {
                UINT count = DragQueryFileW(hdrop, 0xFFFFFFFF, NULL, 0);
                if (count > 256) count = 256;
                for (UINT i = 0; i < count; i++) {
                    wchar_t buf[MAX_PATH * 2];
                    if (DragQueryFileW(hdrop, i, buf, MAX_PATH * 2 - 1) > 0) {
                        e->sel_files[e->nsel_files++] = _wcsdup(buf);
                        if (count == 1 && e->folder_path[0] == 0) {
                            DWORD attr = GetFileAttributesW(buf);
                            if (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY)) {
                                wcsncpy(e->folder_path, buf, MAX_PATH * 2 - 1);
                            }
                        }
                    }
                }
                GlobalUnlock(stg.hGlobal);
            }
            ReleaseStgMedium(&stg);
        }
    }
    return S_OK;
}
static const IShellExtInitVtbl g_siVtbl = { SI_QueryInterface, SI_AddRef, SI_Release, SI_Initialize };

/* ---------- class factory ---------- */

typedef struct { const IClassFactoryVtbl *lpVtbl; } Factory;

static HRESULT STDMETHODCALLTYPE CF_QueryInterface(IClassFactory *This, REFIID riid, void **ppv)
{
    if (IsEqualIID(riid, &IID_IUnknown) || IsEqualIID(riid, &IID_IClassFactory)) {
        *ppv = This;
        return S_OK;
    }
    *ppv = NULL;
    return E_NOINTERFACE;
}
static ULONG STDMETHODCALLTYPE CF_AddRef(IClassFactory *This) { (void)This; return 2; }
static ULONG STDMETHODCALLTYPE CF_Release(IClassFactory *This) { (void)This; return 1; }
static HRESULT STDMETHODCALLTYPE CF_CreateInstance(IClassFactory *This, IUnknown *outer, REFIID riid, void **ppv)
{
    (void)This;
    *ppv = NULL;
    if (outer) return CLASS_E_NOAGGREGATION;
    Ext *e = (Ext *)calloc(1, sizeof(Ext));
    if (!e) return E_OUTOFMEMORY;
    e->lpVtbl = &g_cmVtbl;
    e->lpInitVtbl = &g_siVtbl;
    e->ref = 1;
    InterlockedIncrement(&g_objects);
    HRESULT hr = CM_QueryInterface((IContextMenu *)e, riid, ppv);
    CM_Release((IContextMenu *)e);
    return hr;
}
static HRESULT STDMETHODCALLTYPE CF_LockServer(IClassFactory *This, BOOL lock)
{
    (void)This;
    if (lock) InterlockedIncrement(&g_locks); else InterlockedDecrement(&g_locks);
    return S_OK;
}
static const IClassFactoryVtbl g_cfVtbl = { CF_QueryInterface, CF_AddRef, CF_Release, CF_CreateInstance, CF_LockServer };
static Factory g_factory = { &g_cfVtbl };

__declspec(dllexport) HRESULT STDAPICALLTYPE DllGetClassObject(REFCLSID rclsid, REFIID riid, void **ppv)
{
    if (!IsEqualCLSID(rclsid, &CLSID_RattMenu)) { *ppv = NULL; return CLASS_E_CLASSNOTAVAILABLE; }
    return CF_QueryInterface((IClassFactory *)&g_factory, riid, ppv);
}

__declspec(dllexport) HRESULT STDAPICALLTYPE DllCanUnloadNow(void)
{
    return (g_objects == 0 && g_locks == 0) ? S_OK : S_FALSE;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) { g_module = h; DisableThreadLibraryCalls(h); }
    return TRUE;
}
