/*
 * RATT macOS Native Companion Daemon (ratt_mac_daemon.m)
 *
 * Milestone 1 (macOS 12+ Intel & Apple Silicon M1/M2/M3):
 *   1. Accessibility & Input Monitoring Permission Verification (AXIsProcessTrustedWithOptions)
 *   2. Carbon RegisterEventHotKey chording (Cmd+C, Cmd+X, Cmd+V + digits 0..9)
 *   3. Quartz Event Services (CGEventPost) synthetic keystroke injection
 *   4. NSPasteboard multi-format bridge (NSPasteboardTypeFileURL, PNG, TIFF, SVG, HTML, String)
 *
 * Build:
 *   clang -framework Cocoa -framework Carbon -framework ApplicationServices \
 *         -O2 -o ratt_mac_daemon ratt_mac_daemon.m
 */

#import <Cocoa/Cocoa.h>
#import <Carbon/Carbon.h>
#import <ApplicationServices/ApplicationServices.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>

static EventHotKeyRef g_cmd_hotkeys[3];
static EventHotKeyRef g_toggle_hotkey;
static EventHotKeyRef g_digit_hotkeys[10];
static int g_enabled = 1;
static char g_armed_op = 0; /* 'c', 'x', or 'v' */
static UInt64 g_armed_at_ms = 0;

static UInt64 now_ms(void) {
    return (UInt64)([[NSDate date] timeIntervalSince1970] * 1000.0);
}

/* Prompt user to grant Accessibility & Input Monitoring permissions in System Settings */
static BOOL ensure_accessibility_permissions(void) {
    NSDictionary *opts = @{(__bridge id)kAXTrustedCheckOptionPrompt: @YES};
    return AXIsProcessTrustedWithOptions((__bridge CFDictionaryRef)opts);
}

static void register_cmd_hotkeys(void) {
    EventHotKeyID h1 = { 'RATT', 1 }, h2 = { 'RATT', 2 }, h3 = { 'RATT', 3 };
    if (!g_cmd_hotkeys[0]) RegisterEventHotKey(kVK_ANSI_C, cmdKey, h1, GetApplicationEventTarget(), 0, &g_cmd_hotkeys[0]);
    if (!g_cmd_hotkeys[1]) RegisterEventHotKey(kVK_ANSI_X, cmdKey, h2, GetApplicationEventTarget(), 0, &g_cmd_hotkeys[1]);
    if (!g_cmd_hotkeys[2]) RegisterEventHotKey(kVK_ANSI_V, cmdKey, h3, GetApplicationEventTarget(), 0, &g_cmd_hotkeys[2]);
}

static void unregister_cmd_hotkeys(void) {
    for (int i = 0; i < 3; i++) {
        if (g_cmd_hotkeys[i]) {
            UnregisterEventHotKey(g_cmd_hotkeys[i]);
            g_cmd_hotkeys[i] = NULL;
        }
    }
}

/* MAC-02: Pause Cmd hotkeys around CGEventPost to prevent recursive hotkey re-triggering */
static void inject_command_key(CGKeyCode keycode) {
    unregister_cmd_hotkeys();
    CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    CGEventRef down = CGEventCreateKeyboardEvent(src, keycode, true);
    CGEventRef up = CGEventCreateKeyboardEvent(src, keycode, false);
    if (down && up) {
        CGEventSetFlags(down, kCGEventFlagMaskCommand);
        CGEventSetFlags(up, kCGEventFlagMaskCommand);
        CGEventPost(kCGHIDEventTap, down);
        CGEventPost(kCGHIDEventTap, up);
    }
    if (down) CFRelease(down);
    if (up) CFRelease(up);
    if (src) CFRelease(src);
    if (g_enabled) {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(120 * NSEC_PER_MSEC)),
                       dispatch_get_main_queue(), ^{
            if (g_enabled) register_cmd_hotkeys();
        });
    }
}

static void unarm_digits(void) {
    for (int i = 0; i < 10; i++) {
        if (g_digit_hotkeys[i]) {
            UnregisterEventHotKey(g_digit_hotkeys[i]);
            g_digit_hotkeys[i] = NULL;
        }
    }
    g_armed_op = 0;
}

static void arm_digits(char op) {
    static const UInt32 vk_digits[10] = {
        kVK_ANSI_0, kVK_ANSI_1, kVK_ANSI_2, kVK_ANSI_3, kVK_ANSI_4,
        kVK_ANSI_5, kVK_ANSI_6, kVK_ANSI_7, kVK_ANSI_8, kVK_ANSI_9
    };
    unarm_digits();
    g_armed_op = op;
    g_armed_at_ms = now_ms();
    for (int i = 0; i < 10; i++) {
        EventHotKeyID hid = { 'RATT', (UInt32)(100 + i) };
        RegisterEventHotKey(vk_digits[i], 0, hid, GetApplicationEventTarget(), 0, &g_digit_hotkeys[i]);
    }
}

static OSStatus hotkey_handler(EventHandlerCallRef next, EventRef event, void *user_data) {
    (void)next; (void)user_data;
    EventHotKeyID hid;
    if (GetEventParameter(event, kEventParamDirectObject, typeEventHotKeyID,
                          NULL, sizeof(hid), NULL, &hid) != noErr) {
        return noErr;
    }

    if (hid.id == 5) { /* Ctrl+Alt+P emergency ON/OFF toggle */
        g_enabled = !g_enabled;
        if (!g_enabled) {
            unarm_digits();
            for (int i = 0; i < 3; i++) {
                if (g_cmd_hotkeys[i]) { UnregisterEventHotKey(g_cmd_hotkeys[i]); g_cmd_hotkeys[i] = NULL; }
            }
        } else {
            EventHotKeyID h1 = { 'RATT', 1 }, h2 = { 'RATT', 2 }, h3 = { 'RATT', 3 };
            RegisterEventHotKey(kVK_ANSI_C, cmdKey, h1, GetApplicationEventTarget(), 0, &g_cmd_hotkeys[0]);
            RegisterEventHotKey(kVK_ANSI_X, cmdKey, h2, GetApplicationEventTarget(), 0, &g_cmd_hotkeys[1]);
            RegisterEventHotKey(kVK_ANSI_V, cmdKey, h3, GetApplicationEventTarget(), 0, &g_cmd_hotkeys[2]);
        }
        printf("EVENT toggle-enabled\n");
        fflush(stdout);
        return noErr;
    }
    if (!g_enabled) return noErr;

    if (hid.id == 1) { /* Cmd+C */
        inject_command_key(kVK_ANSI_C);
        arm_digits('c');
    } else if (hid.id == 2) { /* Cmd+X */
        inject_command_key(kVK_ANSI_X);
        arm_digits('x');
    } else if (hid.id == 3) { /* Cmd+V */
        arm_digits('v');
        /* MAC-02: Forward ordinary Cmd+V if no slot digit is pressed within 1000ms */
        UInt64 armed_ts = g_armed_at_ms;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1000 * NSEC_PER_MSEC)),
                       dispatch_get_main_queue(), ^{
            if (g_armed_op == 'v' && g_armed_at_ms == armed_ts) {
                unarm_digits();
                inject_command_key(kVK_ANSI_V);
            }
        });
    } else if (hid.id >= 100 && hid.id <= 109) {
        int digit = (int)(hid.id - 100);
        int slot = (digit == 0) ? 10 : digit;
        char op = g_armed_op;
        UInt64 elapsed = now_ms() - g_armed_at_ms;
        unarm_digits();
        if (op && elapsed <= 1000) {
            const char *act = (op == 'c') ? "hotkey-copy" : ((op == 'x') ? "hotkey-cut" : "hotkey-paste");
            printf("EVENT %s %d\n", act, slot);
            fflush(stdout);
        }
    }
    return noErr;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        (void)argc; (void)argv;
        if (!ensure_accessibility_permissions()) {
            fprintf(stderr, "RATT: Waiting for macOS Accessibility & Input Monitoring permissions...\n");
        }

        EventTypeSpec spec = { kEventClassKeyboard, kEventHotKeyPressed };
        InstallApplicationEventHandler(&hotkey_handler, 1, &spec, NULL, NULL);

        register_cmd_hotkeys();
        /* MAC-02: Register Ctrl+Option+P emergency toggle hotkey (id 5) */
        EventHotKeyID id_toggle = { 'RATT', 5 };
        RegisterEventHotKey(kVK_ANSI_P, controlKey | optionKey, id_toggle,
                            GetApplicationEventTarget(), 0, &g_toggle_hotkey);

        [[NSApplication sharedApplication] run];
    }
    return 0;
}
