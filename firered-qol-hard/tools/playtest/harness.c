// Minimal mGBA driver: run a ROM headless following a command script.
//   wait N | press KEYS [frames] | shot NAME | peek ADDR LEN | peekp PTR OFFSET LEN
// peek prints "PEEK <addr> <hex bytes>" so a test can check game state; peekp
// reads the pointer stored at PTR first (for the save blocks, which move).
// KEYS: letters A B s(elect) S(tart) R(ight) L(eft) U(p) D(own) r l, e.g. "AU"
#include <mgba/core/core.h>
#include <mgba/core/log.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void quiet(struct mLogger* l, int c, enum mLogLevel lv, const char* f, va_list a) { (void)l;(void)c;(void)lv;(void)f;(void)a; }
static struct mLogger logger = { .log = quiet };

static struct mCore* core; static color_t* buf; static unsigned W, H;

static void frames(int n, uint32_t keys) { core->setKeys(core, keys); while (n--) core->runFrame(core); }
static uint32_t keymask(const char* s) {
    uint32_t k = 0;
    for (; *s; s++) switch (*s) {
        case 'A': k |= 1; break; case 'B': k |= 2; break; case 's': k |= 4; break; case 'S': k |= 8; break;
        case 'R': k |= 16; break; case 'L': k |= 32; break; case 'U': k |= 64; break; case 'D': k |= 128; break;
        case 'r': k |= 256; break; case 'l': k |= 512; break; }
    return k;
}
static void shot(const char* name) {
    char path[256]; snprintf(path, sizeof path, "%s.ppm", name);
    FILE* f = fopen(path, "wb"); fprintf(f, "P6 %u %u 255\n", W, H);
    for (unsigned i = 0; i < W * H; i++) {
        uint32_t c = buf[i];
        unsigned char px[3] = { c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF };
        fwrite(px, 1, 3, f);
    }
    fclose(f);
}
int main(int argc, char** argv) {
    mLogSetDefaultLogger(&logger);
    core = mCoreFind(argv[1]); core->init(core); mCoreInitConfig(core, NULL);
    core->desiredVideoDimensions(core, &W, &H);
    buf = malloc(W * H * sizeof(color_t)); core->setVideoBuffer(core, buf, W);
    if (!mCoreLoadFile(core, argv[1])) { fprintf(stderr, "load failed\n"); return 1; }
    core->reset(core);
    char cmd[32], arg[64]; int n;
    FILE* in = fopen(argv[2], "r");
    while (fscanf(in, "%31s", cmd) == 1) {
        if (!strcmp(cmd, "wait")) { fscanf(in, "%d", &n); frames(n, 0); }
        else if (!strcmp(cmd, "press")) { fscanf(in, "%63s %d", arg, &n); frames(n > 0 ? n : 6, keymask(arg)); frames(12, 0); }
        else if (!strcmp(cmd, "shot")) { fscanf(in, "%63s", arg); shot(arg); }
        else if (!strcmp(cmd, "peek")) {
            unsigned addr, len, i;
            fscanf(in, "%x %u", &addr, &len);
            printf("PEEK %08x ", addr);
            for (i = 0; i < len; i++) printf("%02x", core->busRead8(core, addr + i));
            printf("\n");
            fflush(stdout);
        }
        else if (!strcmp(cmd, "peekp")) {
            unsigned ptr, off, len, i, base;
            fscanf(in, "%x %x %u", &ptr, &off, &len);
            base = core->busRead32(core, ptr);
            printf("PEEKP %08x+%x ", ptr, off);
            for (i = 0; i < len; i++) printf("%02x", core->busRead8(core, base + off + i));
            printf("\n");
            fflush(stdout);
        }
    }
    core->deinit(core);
    return 0;
}
