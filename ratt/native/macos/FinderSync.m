/*
 * RATT macOS Finder Right-Click Shell Extension (FIFinderSync)
 *
 * Adds cascading "RATT > Copy to Slot N / Cut to Slot N / Paste from Slot N"
 * menus to macOS Finder context menus and forwards validated file URLs
 * (`NSPasteboardTypeFileURL`) to RATT (Premium & Enterprise only).
 */

#import <Cocoa/Cocoa.h>
#import <FinderSync/FinderSync.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>

@interface RattFinderSync : FIFinderSync
@end

@implementation RattFinderSync

- (instancetype)init {
    self = [super init];
    if (self) {
        NSURL *home = [NSURL fileURLWithPath:NSHomeDirectory()];
        [FIFinderSyncController defaultController].directoryURLs = [NSSet setWithObject:home];
    }
    return self;
}

/* MAC-01: Canonicalize with realpath() and block macOS/cross-platform executable extensions */
static BOOL isSafeFinderPath(NSString *path) {
    if (!path || path.length == 0 || path.length > 4096) return NO;
    if ([path containsString:@".."] || [path hasPrefix:@"//"] || [path hasPrefix:@"\\\\"]) return NO;
    char resolved[PATH_MAX];
    if (!realpath([path fileSystemRepresentation], resolved)) return NO;
    NSString *canon = [NSString stringWithUTF8String:resolved];
    if (!canon || [canon hasPrefix:@"//"]) return NO;
    static NSSet<NSString *> *blockedExts = nil;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        blockedExts = [NSSet setWithObjects:
            @"app", @"command", @"sh", @"zsh", @"bash", @"pkg", @"dmg", @"workflow",
            @"scpt", @"applescript", @"exe", @"dll", @"bat", @"cmd", @"ps1", @"vbs", @"js", nil];
    });
    NSArray<NSString *> *parts = [[canon.lastPathComponent lowercaseString] componentsSeparatedByString:@"."];
    if (parts.count > 1) {
        for (NSUInteger i = 1; i < parts.count; i++) {
            if ([blockedExts containsObject:parts[i]]) return NO;
        }
    }
    return YES;
}

/* MAC-01: Private 0600 Unix domain socket IPC inside user App Group / Application Support
 * instead of session-wide NSDistributedNotificationCenter broadcast */
static void sendPrivateFinderIPC(NSDictionary *payload) {
    NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:0 error:nil];
    if (!json || json.length == 0) return;
    NSString *sockPath = [NSHomeDirectory() stringByAppendingPathComponent:
        @"Library/Application Support/RATT/finder_ipc.sock"];
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (strlen(sockPath.fileSystemRepresentation) >= sizeof(addr.sun_path)) return;
    strncpy(addr.sun_path, sockPath.fileSystemRepresentation, sizeof(addr.sun_path) - 1);
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) return;
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == 0) {
        (void)write(fd, json.bytes, json.length);
        (void)write(fd, "\n", 1);
    }
    close(fd);
}

- (NSMenu *)menuForMenuKind:(FIMenuKind)whichMenu {
    NSMenu *rootMenu = [[NSMenu alloc] initWithTitle:@"RATT v2"];
    NSMenuItem *rattItem = [[NSMenuItem alloc] initWithTitle:@"RATT v2" action:nil keyEquivalent:@""];
    NSMenu *subMenu = [[NSMenu alloc] initWithTitle:@"RATT v2"];

    NSMenuItem *copyItem = [[NSMenuItem alloc] initWithTitle:@"Copy to Slot" action:nil keyEquivalent:@""];
    NSMenu *copySub = [[NSMenu alloc] initWithTitle:@"Copy to Slot"];
    for (int i = 1; i <= 10; i++) {
        NSMenuItem *slot = [[NSMenuItem alloc] initWithTitle:[NSString stringWithFormat:@"Slot %d", i]
                                                      action:@selector(copySlotAction:)
                                               keyEquivalent:@""];
        slot.tag = i;
        [copySub addItem:slot];
    }
    [copyItem setSubmenu:copySub];
    [subMenu addItem:copyItem];

    NSMenuItem *cutItem = [[NSMenuItem alloc] initWithTitle:@"Cut to Slot" action:nil keyEquivalent:@""];
    NSMenu *cutSub = [[NSMenu alloc] initWithTitle:@"Cut to Slot"];
    for (int i = 1; i <= 10; i++) {
        NSMenuItem *slot = [[NSMenuItem alloc] initWithTitle:[NSString stringWithFormat:@"Slot %d", i]
                                                      action:@selector(cutSlotAction:)
                                               keyEquivalent:@""];
        slot.tag = i;
        [cutSub addItem:slot];
    }
    [cutItem setSubmenu:cutSub];
    [subMenu addItem:cutItem];

    NSMenuItem *pasteItem = [[NSMenuItem alloc] initWithTitle:@"Paste from Slot" action:nil keyEquivalent:@""];
    NSMenu *pasteSub = [[NSMenu alloc] initWithTitle:@"Paste from Slot"];
    for (int i = 1; i <= 10; i++) {
        NSMenuItem *slot = [[NSMenuItem alloc] initWithTitle:[NSString stringWithFormat:@"Slot %d", i]
                                                      action:@selector(pasteSlotAction:)
                                               keyEquivalent:@""];
        slot.tag = i;
        [pasteSub addItem:slot];
    }
    [pasteItem setSubmenu:pasteSub];
    [subMenu addItem:pasteItem];

    [rattItem setSubmenu:subMenu];
    [rootMenu addItem:rattItem];
    return rootMenu;
}

- (IBAction)copySlotAction:(id)sender {
    NSInteger slot = [(NSMenuItem *)sender tag];
    if (slot < 1 || slot > 10) return;
    NSArray<NSURL *> *items = [[FIFinderSyncController defaultController] selectedItemURLs];
    NSMutableArray<NSString *> *paths = [NSMutableArray array];
    for (NSURL *u in items) {
        if (u.isFileURL && isSafeFinderPath(u.path)) {
            [paths addObject:[u.path stringByStandardizingPath]];
        }
    }
    if (paths.count == 0) return;
    NSDictionary *info = @{
        @"action": @"copy",
        @"slot": @(slot),
        @"files": paths
    };
    sendPrivateFinderIPC(info);
}

- (IBAction)cutSlotAction:(id)sender {
    NSInteger slot = [(NSMenuItem *)sender tag];
    if (slot < 1 || slot > 10) return;
    NSArray<NSURL *> *items = [[FIFinderSyncController defaultController] selectedItemURLs];
    NSMutableArray<NSString *> *paths = [NSMutableArray array];
    for (NSURL *u in items) {
        if (u.isFileURL && isSafeFinderPath(u.path)) {
            [paths addObject:[u.path stringByStandardizingPath]];
        }
    }
    if (paths.count == 0) return;
    NSDictionary *info = @{
        @"action": @"cut",
        @"slot": @(slot),
        @"files": paths
    };
    sendPrivateFinderIPC(info);
}

- (IBAction)pasteSlotAction:(id)sender {
    NSInteger slot = [(NSMenuItem *)sender tag];
    if (slot < 1 || slot > 10) return;
    NSURL *target = [[FIFinderSyncController defaultController] targetedURL];
    NSString *folder = (target && target.isFileURL && isSafeFinderPath(target.path))
        ? [target.path stringByStandardizingPath]
        : @"";
    if (folder.length == 0) return;
    NSDictionary *info = @{
        @"action": @"paste",
        @"slot": @(slot),
        @"folder": folder
    };
    sendPrivateFinderIPC(info);
}

@end
