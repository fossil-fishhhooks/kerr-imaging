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

void draw_pixel(int pixel, int x,int y, int fbfd,unsigned char *fbptr, int bits_per_pixel,int xoffset,int yoffset,int xres_virtual){
int pixel_offset = (x + xoffset) * (bits_per_pixel / 8) + (y + yoffset) * xres_virtual * (bits_per_pixel / 8);

    *((unsigned int*)(fbptr + pixel_offset)) = pixel;
}

void drawLine(int x0, int y0, int x1, int y1, int color, int fbfd, unsigned char* fbptr, int bits_per_pixel,int xoffset,int yoffset,int xres_virtual) {
    int dx = abs(x1 - x0);
    int dy = abs(y1 - y0);
    int sx = x0 < x1 ? 1 : -1;
    int sy = y0 < y1 ? 1 : -1;
    int err = dx - dy;

    while (true) {
        //drawPixel(x0, y0, r, g, b);
        draw_pixel(color,x0,y0,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) {
            err -= dy;
            x0 += sx;
        }
        if (e2 < dx) {
            err += dx;
            y0 += sy;
        }
    }
}

void drawSliceOfCircle(int centerX, int centerY, int radius, int startAngle, int endAngle, int color, int fbfd, unsigned char* fbptr, int bits_per_pixel,int xoffset,int yoffset,int xres_virtual) {
    int x, y;
    double angle;

    for (angle = startAngle; angle <= endAngle; angle += 0.5) {
        x = centerX + (int)(radius * cos(angle * M_PI / 180.0));
        y = centerY + (int)(radius * sin(angle * M_PI / 180.0));
        drawLine(centerX, centerY, x, y, color, fbfd, fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
    }
}

void drawWedge(int centerX, int centerY, int startAngle, int endAngle, int radius, int color, int fbfd, unsigned char *fbptr, int bits_per_pixel, int xoffset, int yoffset,int xres_virtual) {
    int x = 0;
    int y = radius;
    int decision = 3 - 2 * radius;

    while (x <= y) {
        double angle = atan2(y, x) * 180 / M_PI;
        int intAngle = (int)angle;

        if (intAngle >= startAngle && intAngle <= endAngle) {
        //drawPixel(centerX + x, centerY + y);
        draw_pixel(color,centerX+x,centerY+y,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX + x, centerY - y);
        draw_pixel(color,centerX+x,centerY-y,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX - x, centerY + y);
        draw_pixel(color,centerX-x,centerY+y,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX - x, centerY - y);
        draw_pixel(color,centerX-x,centerY-y,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX + y, centerY + x);
        draw_pixel(color,centerX+y,centerY+x,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX + y, centerY - x);
        draw_pixel(color,centerX+y,centerY-x,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX - y, centerY + x);
        draw_pixel(color,centerX-y,centerY+x,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
        //drawPixel(centerX - y, centerY - x);
        draw_pixel(color,centerX-y,centerY-x,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);

 }

        if (decision <= 0) {
            decision += 4 * x + 6;
        } else {
            decision += 4 * (x - y) + 10;
            y--;
        }
        x++;
    }
}

void drawRing(int r1, int r2, int q1, int q2, int x0,int y0, int color, int fbfd,unsigned char *fbptr, int bits_per_pixel,int xoffset,int yoffset,int xres_virtual){
int r1sq = r1*r1;
int r2sq = r2*r2;
int rsq;
int pt_angle;

bool fullcircle = ((q2-q1)==360);
bool reversed = (q1>q2);
q1 = q1 % 360;
q2 = q2 % 360;
if (q1 > 180) q1 -= 360;
if (q2 > 180) q2 -= 360;


for (int x = x0-r2;x<x0+r2;x++){
        for (int y = y0-r2;y<y0+r2;y++){

                rsq = ((x-x0)*(x-x0))+((y-y0)*(y-y0));

                if(r1sq<=rsq && rsq<=r2sq){
                        if (fullcircle){
                                draw_pixel(color,x,y,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
                        }
                        else {
                                pt_angle = (int)(atan2(y-y0,x-x0)*180/M_PI);
                                if ( (!reversed && pt_angle > q1 && pt_angle < q2) || (reversed && (pt_angle > q1 && pt_angle < q2)) ){
                                        draw_pixel(color,x,y,fbfd,fbptr,bits_per_pixel,xoffset,yoffset,xres_virtual);
                                }
                        }
                }
        }
}
}

int main() {
char CR =  (char)13;
struct fb_var_screeninfo vinfo;
int fbfd = open("/dev/fb0", O_RDWR);
    if (fbfd == -1) {
        perror("Error opening framebuffer device");
        return 1;
    }


    if (ioctl(fbfd, FBIOGET_VSCREENINFO, &vinfo)) {
        perror("Error reading variable information");
        close(fbfd);
        return 1;
    }

    int screensize = vinfo.yres_virtual * vinfo.xres_virtual *vinfo.bits_per_pixel / 8;

    unsigned char *fbptr = (unsigned char*)mmap(0, screensize, PROT_READ | PROT_WRITE, MAP_SHARED, fbfd, 0);
    if ((intptr_t)fbptr == -1) {
        perror("Error mapping framebuffer to memory");
        close(fbfd);
        return 1;
    }


//int alpha = 255;
//int pixel;
//int pixel_color = (alpha << 24) | (red << 16) | (green << 8) | blue;
//draw_pixel(pixel,1,1,fbfd,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
//drawWedge(500,500,100,45,70,pixel_color,fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
//drawSliceOfCircle(100, 100, 50, 50, 135,pixel_color,fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
//drawRing(50,100,0, 360, 1600, 300,pixel_color-255,fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
//drawRing(50,100,-45,45, 1600, 400,pixel_color-(255<<8),fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
//drawRing(50,100,-135, 135, 1600, 500,pixel_color-(255<<16),fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
//drawRing(50,100,135, -135, 1600, 600,pixel_color,fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
int serial;
    char buffer[100];
    int bytesRead = 0;

    // Open the serial device (replace "/dev/ttyUSB0" with the correct path)
    if ((serial = open("/dev/ttyGS0", O_RDWR | O_NOCTTY)) < 0) {
        perror("Unable to open serial device");
        return 1;
    }

    // Configure the serial port (optional, adjust the settings based on your device)
    // ...

    //printf("Reading data from the serial device...\n");

int r1,r2,q1,q2,pixel_color;
int red = 0;
int blue =0;
int green = 0;
int x=1;
int origx,origy;
bool y=false;
origx = vinfo.xres_virtual/2;
origy = vinfo.yres_virtual/2;
    while (x==1) {
        char c;
        //serialFlush(serial);
        int n = read(serial, &c, 1);
        if (n > 0) {
            if (c == '\n') {
                y=false;
                buffer[bytesRead] = '\0'; // Null-terminate the received data

                // Print the received data
                //printf("Received data: %s\n", buffer);
                const char* stop = "Stop signal recieved\r";
                int stop_len = strlen(stop);


                //write(serial, "echo: ",6);
                //write(serial, buffer, strlen(buffer));
                //write(serial, CR,1);
                if (strcmp(buffer, "quit") == 0) {
                        for (int i=0; i<screensize; *(fbptr+i++) = 0);
                        write(serial, stop, stop_len);
                        //printf("Stop signal recieved\n");
                        x=0;
                        y=true;
                }
                if (strncmp(buffer,"arc",3)==0){
                        for (int i=0; i<screensize; *(fbptr+i++) = 0);
                        sscanf(buffer, "arc %d %d %d %d %d",&r1,&r2,&q1,&q2,&pixel_color);
                        drawRing(r1,r2,q1, q2, origx, origy,pixel_color,fbfd,fbptr,vinfo.bits_per_pixel, vinfo.xoffset, vinfo.yoffset,vinfo.xres_virtual);
                        y=true;
                }
                if (strcmp(buffer, "*IDN?") == 0) {
                        const char* IDN = "IPG version 2.0\n";
                        write(serial, IDN, strlen(IDN));
                        y=true;
                }

                if (strcmp(buffer, "help") == 0) {
                        const char* help = "++++++++++++++++++++++++++++++\nIPG help:\nStandard commands:\n>arc [innerradius] [outerradius] [startangle] [endangle] [color]\n>*IDN?\n>help\n++++++++++++++++++++++++++++++\nCommand meanings:\n>quit>exit program\n>arc>draw an arc of the given 5 parameters\n>*IDN?>display version\n>help>display this help\n++++++++++++++++++++++++++++++\ncolors are 32 bit integers, however only 24 bit color is provided in arcs\nex:int pixel_color = (red << 16) | (green << 8) | blue\n\n";
                        write(serial, help, strlen(help));
                        y=true;

                }

                if (strcmp(buffer, "") == 0) {
                        const char* running = "RUNNING\n";
                        write(serial, running, strlen(running));
                        y=true;
                }

                if (y==false){
                        const char* error = "Unknown command\n";
                        write(serial, error, strlen(error));
                }
                // Reset bytesRead for the next line of data
                bytesRead = 0;
            } else {
                // Append the character to the buffer
                if (bytesRead < sizeof(buffer) - 1) {
                    buffer[bytesRead++] = c;
                }
            }
        }
    }

    // Close the serial device
    close(serial);
munmap(fbptr, screensize);
close(fbfd);
    return 0;
}
