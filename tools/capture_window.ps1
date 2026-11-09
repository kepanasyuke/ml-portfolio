# Снимок нативного окна приложения по заголовку (PrintWindow).
param(
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$Out
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class WinShot {
  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@

$handle = [IntPtr]::Zero
$callback = [WinShot+EnumProc]{ param($window, $_) if ([WinShot]::IsWindowVisible($window)) { $text = New-Object System.Text.StringBuilder 512; [void][WinShot]::GetWindowText($window, $text, 512); if ($text.ToString() -match [regex]::Escape($Title)) { $script:handle = $window } }; return $true }
[void][WinShot]::EnumWindows($callback, [IntPtr]::Zero)
if ($handle -eq [IntPtr]::Zero) { Write-Error "окно '$Title' не найдено"; exit 1 }

[void][WinShot]::SetForegroundWindow($handle)
Start-Sleep -Milliseconds 800
$rect = New-Object WinShot+RECT
[void][WinShot]::GetWindowRect($handle, [ref]$rect)
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
$printed = [WinShot]::PrintWindow($handle, $hdc, 2)
$graphics.ReleaseHdc($hdc)
$graphics.Dispose()

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$bitmap.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
"$Out : ${width}x${height}, PrintWindow=$printed"
