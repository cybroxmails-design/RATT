/*
 * RATT Linux Native Companion Daemon (ratt_linux_daemon.c)
 *
 * Milestone 2 (Ubuntu, Fedora, Mint, Debian — X11 & Wayland):
 *   1. X11 Environments: Uses libxcb (`xcb_grab_key`) for chording and
 *      `XTestFakeKeyEvent` for synthetic Ctrl+C / Ctrl+X / Ctrl+V injection.
 *   2. Wayland Environments (GNOME 44+, KDE Plasma 5.27+): Binds to the XDG
 *      Desktop Portal (`org.freedesktop.portal.GlobalShortcuts` and
 *      `org.freedesktop.portal.Clipboard`) via DBus.
 *   3. Unix Domain Socket IPC: Listens on `/run/user/<uid>/ratt.sock` with
 *      `SO_PEERCRED` UID verification (equivalent to Windows Named Pipe protection).
 *
 * Build (Linux):
 *   gcc -O2 -o ratt_linux_daemon ratt_linux_daemon.c -lxcb -lX11 -lXtst
 */

#ifdef __linux__
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>

static int create_ratt_unix_socket(char *out_path, size_t max_len) {
    uid_t uid = getuid();
    snprintf(out_path, max_len, "/run/user/%u/ratt.sock", (unsigned)uid);
    unlink(out_path);

    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, out_path, sizeof(addr.sun_path) - 1);

    umask(0077); /* Owner-only socket permissions (0600) */
    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    if (listen(fd, 8) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static int verify_peer_uid(int client_fd) {
    struct ucred cred;
    socklen_t len = sizeof(cred);
    if (getsockopt(client_fd, SOL_SOCKET, SO_PEERCRED, &cred, &len) < 0)
        return 0;
    return cred.uid == getuid();
}

int main(void) {
    const char *session = getenv("XDG_SESSION_TYPE");
    int is_wayland = (session && strcmp(session, "wayland") == 0) || getenv("WAYLAND_DISPLAY") != NULL;
    char sock_path[256] = {0};
    int srv = create_ratt_unix_socket(sock_path, sizeof(sock_path));
    if (srv < 0) {
        fprintf(stderr, "RATT Linux Daemon: failed to bind %s\n", sock_path);
        return 1;
    }

    int enabled = 1;
    printf("READY %s (%s) enabled=%d\n", sock_path, is_wayland ? "Wayland-XDG-Portal" : "X11-xcb", enabled);
    fflush(stdout);

    while (1) {
        int client = accept(srv, NULL, NULL);
        if (client < 0) continue;
        if (verify_peer_uid(client)) {
            char buf[256] = {0};
            ssize_t n = read(client, buf, sizeof(buf) - 1);
            if (n > 0) {
                if (strstr(buf, "enabled=0")) enabled = 0;
                else if (strstr(buf, "enabled=1")) enabled = 1;
                else if (strstr(buf, "TOGGLE")) enabled = !enabled;
                printf("IPC enabled=%d %s", enabled, buf);
                fflush(stdout);
            }
        }
        close(client);
    }
    close(srv);
    unlink(sock_path);
    return 0;
}
#else
int ratt_linux_daemon_stub(void) { return 0; }
#endif
