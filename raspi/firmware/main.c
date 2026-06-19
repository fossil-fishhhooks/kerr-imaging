#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <math.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <termios.h>

static inline void draw_pixel(int pixel, int x, int y, unsigned char *fbptr,
                               int bpp, int xoffset, int yoffset, int stride) {
    *((unsigned int *)(fbptr + ((x + xoffset) + (y + yoffset) * stride) * (bpp / 8))) = pixel;
}

void drawRing(int r1, int r2, int q1, int q2, int x0, int y0, int color,
              int fbfd, unsigned char *fbptr, int bpp, int xoffset, int yoffset, int stride) {
    (void)fbfd; // unused
    int r1sq = r1 * r1;
    int r2sq = r2 * r2;

    bool fullcircle = ((q2 - q1) == 360);
    bool reversed   = (q1 > q2);
    q1 = q1 % 360; q2 = q2 % 360;
    if (q1 > 180) q1 -= 360;
    if (q2 > 180) q2 -= 360;

    for (int dx = -r2; dx <= r2; dx++) {
        int dx2 = dx * dx;
        if (dx2 > r2sq) continue;

        int y_outer    = (int)sqrt((double)(r2sq - dx2));
        int y_inner_sq = r1sq - dx2;

        int y_start    = (y_inner_sq > 0) ? (int)sqrt((double)y_inner_sq) + 1 : 0;


        for (int s = 0; s < 2; s++) {
            for (int a = y_start; a <= y_outer; a++) {
                int dy = s ? -a : a;
                if (s == 1 && a == 0) continue; 

                if (fullcircle) {
                    draw_pixel(color, x0 + dx, y0 + dy, fbptr, bpp, xoffset, yoffset, stride);
                } else {
                    int pt_angle = (int)(atan2(dy, dx) * 180.0 / M_PI);
                    if ((!reversed && pt_angle > q1 && pt_angle < q2) ||
                        ( reversed && (pt_angle > q1 || pt_angle < q2)))
                        draw_pixel(color, x0 + dx, y0 + dy, fbptr, bpp, xoffset, yoffset, stride);
                }
            }
        }
    }
}

int main() {
    struct fb_var_screeninfo vinfo;
    int fbfd = open("/dev/fb0", O_RDWR);
    if (fbfd == -1) { perror("Error opening framebuffer device"); return 1; }

    if (ioctl(fbfd, FBIOGET_VSCREENINFO, &vinfo)) {
        perror("Error reading variable information");
        close(fbfd); return 1;
    }

    int screensize = vinfo.yres_virtual * vinfo.xres_virtual * vinfo.bits_per_pixel / 8;
    int stride     = vinfo.xres_virtual;   
    int bpp        = vinfo.bits_per_pixel;

    unsigned char *fbptr = (unsigned char *)mmap(0, screensize, PROT_READ | PROT_WRITE, MAP_SHARED, fbfd, 0);
    if ((intptr_t)fbptr == -1) {
        perror("Error mapping framebuffer to memory");
        close(fbfd); return 1;
    }

    int serial;
    char buffer[100];
    int bytesRead = 0;

    if ((serial = open("/dev/ttyGS0", O_RDWR | O_NOCTTY)) < 0) {
        perror("Unable to open serial device"); return 1;
    }

    int r1, r2, q1, q2, pixel_color;
    int x = 1;
    int origx, origy;
    bool y = false;

    int offset_x = 0, offset_y = 0;

    FILE *f = fopen("config.txt", "r");
    if (f) {
        char key[64]; int val;
        while (fscanf(f, "%63s %d", key, &val) == 2) {
            if (strcmp(key, "offset_x") == 0) offset_x = val;
            if (strcmp(key, "offset_y") == 0) offset_y = val;
        }
        fclose(f);
    }

    origx = vinfo.xres_virtual / 2 + offset_x;
    origy = vinfo.yres_virtual / 2 + offset_y;

    while (x == 1) {
        char c;
        int n = read(serial, &c, 1);
        if (n > 0) {
            if (c == '\n') {
                y = false;
                buffer[bytesRead] = '\0';

                if (strcmp(buffer, "quit") == 0) {
                    memset(fbptr, 0, screensize);
                    const char *stop = "Stop signal recieved\r";
                    write(serial, stop, strlen(stop));
                    x = 0; y = true;
                }
                if (strncmp(buffer, "arc", 3) == 0) {
                    memset(fbptr, 0, screensize);
                    sscanf(buffer, "arc %d %d %d %d %d", &r1, &r2, &q1, &q2, &pixel_color);
                    drawRing(r1, r2, q1, q2, origx, origy, pixel_color,
                             fbfd, fbptr, bpp, vinfo.xoffset, vinfo.yoffset, stride);
                    y = true;
                }
                if (strcmp(buffer, "*IDN?") == 0) {
                    const char *IDN = "IPG version 2.1\n";
                    write(serial, IDN, strlen(IDN));
                    y = true;
                }
                if (strcmp(buffer, "help") == 0) {
                    const char *help =
                        "++++++++++++++++++++++++++++++\n"
                        "IPG help:\nStandard commands:\n"
                        ">arc [inner] [outer] [start] [end] [color]\n"
                        ">*IDN?\n>help\n"
                        "++++++++++++++++++++++++++++++\n";
                       
                    write(serial, help, strlen(help));
                    y = true;
                }
                if (strcmp(buffer, "") == 0) {
                    const char *running = "RUNNING\n";
                    write(serial, running, strlen(running));
                    y = true;
                }
                if (!y) {
                    const char *error = "Unknown command\n";
                    write(serial, error, strlen(error));
                }

                bytesRead = 0;
            } else {
                if (bytesRead < (int)sizeof(buffer) - 1)
                    buffer[bytesRead++] = c;
            }
        }
    }

    close(serial);
    munmap(fbptr, screensize);
    close(fbfd);
    return 0;
}
