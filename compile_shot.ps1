$code = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

class Shot {
    [DllImport("user32.dll")] static extern IntPtr GetDesktopWindow();
    [DllImport("user32.dll")] static extern IntPtr GetWindowDC(IntPtr hWnd);
    [DllImport("gdi32.dll")] static extern bool BitBlt(IntPtr hdc, int x, int y, int w, int h, IntPtr srcDC, int sx, int sy, int rop);
    [DllImport("user32.dll")] static extern bool ReleaseDC(IntPtr hWnd, IntPtr hDC);
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int n);

    static void Main(string[] args) {
        int w = GetSystemMetrics(0), h = GetSystemMetrics(1);
        IntPtr desk = GetDesktopWindow();
        IntPtr dc = GetWindowDC(desk);
        Bitmap bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
        Graphics g = Graphics.FromImage(bmp);
        IntPtr gdcHandle = g.GetHdc();
        BitBlt(gdcHandle, 0, 0, w, h, dc, 0, 0, 0x00CC0020);
        g.ReleaseHdc(gdcHandle);
        g.Dispose();
        ReleaseDC(desk, dc);
        bmp.Save(args[0], ImageFormat.Png);
        bmp.Dispose();
    }
}
'@

Add-Type -TypeDefinition $code -ReferencedAssemblies 'System.Drawing' -OutputAssembly 'C:\Users\vosil\Desktop\jarvis\screenshot_tool.exe' -OutputType ConsoleApplication
Write-Host "EXE compiled OK"
