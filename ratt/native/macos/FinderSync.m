/*
 * RATT macOS Finder Right-Click Shell Extension (FIFinderSync)
 *
 * Adds cascading "RATT > Copy to Slot N / Cut to Slot N / Paste from Slot N"
 * menus to macOS Finder context menus and forwards validated file URLs
 * (`NSPasteboardTypeFileURL`) to RATT (Premium & Enterprise only).
 */

#import <Cocoa/Cocoa.h>
#import <FinderSync/FinderSync.h>

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

static BOOL isSafeFinderPath(NSString *path) {
    if (!path || path.length == 0 || path.length > 4096) return NO;
    if ([path containsString:@".."] || [path hasPrefix:@"//"] || [path hasPrefix:@"\\\\"]) return NO;
    return YES;
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
        @"files": paths,
        @"uid": @(getuid())
    };
    [[NSDistributedNotificationCenter defaultCenter] postNotificationName:@"com.cybrox.ratt.FinderAction"
                                                                   object:@"com.cybrox.ratt.FinderSync"
                                                                 userInfo:info
                                                       deliverImmediately:NO];
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
        @"folder": folder,
        @"uid": @(getuid())
    };
    [[NSDistributedNotificationCenter defaultCenter] postNotificationName:@"com.cybrox.ratt.FinderAction"
                                                                   object:@"com.cybrox.ratt.FinderSync"
                                                                 userInfo:info
                                                       deliverImmediately:NO];
}

@end
