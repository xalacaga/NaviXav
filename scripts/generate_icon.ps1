[CmdletBinding()]
param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
if (-not $OutputPath) {
    $OutputPath = Join-Path $PSScriptRoot "..\assets\navixav.ico"
}

function New-IconPng([int]$Size) {
    $bitmap = [System.Drawing.Bitmap]::new($Size, $Size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.Clear([System.Drawing.Color]::Transparent)

    $scale = $Size / 256.0
    $background = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $radius = 54 * $scale
    $left = 8 * $scale
    $top = 8 * $scale
    $width = 240 * $scale
    $diameter = 2 * $radius
    $background.AddArc($left, $top, $diameter, $diameter, 180, 90)
    $background.AddArc($left + $width - $diameter, $top, $diameter, $diameter, 270, 90)
    $background.AddArc($left + $width - $diameter, $top + $width - $diameter, $diameter, $diameter, 0, 90)
    $background.AddArc($left, $top + $width - $diameter, $diameter, $diameter, 90, 90)
    $background.CloseFigure()

    $backgroundBrush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
        [System.Drawing.PointF]::new(28 * $scale, 18 * $scale),
        [System.Drawing.PointF]::new(224 * $scale, 238 * $scale),
        [System.Drawing.ColorTranslator]::FromHtml("#102441"),
        [System.Drawing.ColorTranslator]::FromHtml("#07111f")
    )
    $graphics.FillPath($backgroundBrush, $background)

    $points = @(
        [System.Drawing.PointF]::new(128 * $scale, 30 * $scale),
        [System.Drawing.PointF]::new(111 * $scale, 49 * $scale),
        [System.Drawing.PointF]::new(111 * $scale, 112 * $scale),
        [System.Drawing.PointF]::new(35 * $scale, 158 * $scale),
        [System.Drawing.PointF]::new(35 * $scale, 185 * $scale),
        [System.Drawing.PointF]::new(111 * $scale, 160 * $scale),
        [System.Drawing.PointF]::new(111 * $scale, 196 * $scale),
        [System.Drawing.PointF]::new(86 * $scale, 213 * $scale),
        [System.Drawing.PointF]::new(86 * $scale, 232 * $scale),
        [System.Drawing.PointF]::new(128 * $scale, 220 * $scale),
        [System.Drawing.PointF]::new(170 * $scale, 232 * $scale),
        [System.Drawing.PointF]::new(170 * $scale, 213 * $scale),
        [System.Drawing.PointF]::new(145 * $scale, 196 * $scale),
        [System.Drawing.PointF]::new(145 * $scale, 160 * $scale),
        [System.Drawing.PointF]::new(221 * $scale, 185 * $scale),
        [System.Drawing.PointF]::new(221 * $scale, 158 * $scale),
        [System.Drawing.PointF]::new(145 * $scale, 112 * $scale),
        [System.Drawing.PointF]::new(145 * $scale, 49 * $scale)
    )
    $aircraftBrush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
        [System.Drawing.PointF]::new(76 * $scale, 38 * $scale),
        [System.Drawing.PointF]::new(174 * $scale, 220 * $scale),
        [System.Drawing.ColorTranslator]::FromHtml("#67d8ff"),
        [System.Drawing.ColorTranslator]::FromHtml("#149ee8")
    )
    $graphics.FillPolygon($aircraftBrush, $points)

    $highlight = [System.Drawing.SolidBrush]::new(
        [System.Drawing.Color]::FromArgb(120, 223, 247, 255)
    )
    $graphics.FillRectangle($highlight, 123 * $scale, 48 * $scale, 10 * $scale, 157 * $scale)

    $stream = [System.IO.MemoryStream]::new()
    $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
    $bytes = $stream.ToArray()

    $stream.Dispose()
    $highlight.Dispose()
    $aircraftBrush.Dispose()
    $backgroundBrush.Dispose()
    $background.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
    return $bytes
}

$sizes = @(16, 24, 32, 48, 64, 128, 256)
$images = [System.Collections.Generic.List[byte[]]]::new()
foreach ($size in $sizes) {
    [byte[]]$image = New-IconPng $size
    $images.Add($image)
}
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($resolvedOutput)) | Out-Null

$file = [System.IO.File]::Create($resolvedOutput)
$writer = [System.IO.BinaryWriter]::new($file)
try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]$sizes.Count)
    $offset = 6 + (16 * $sizes.Count)
    for ($index = 0; $index -lt $sizes.Count; $index++) {
        $size = $sizes[$index]
        $bytes = $images[$index]
        $writer.Write([byte]$(if ($size -eq 256) { 0 } else { $size }))
        $writer.Write([byte]$(if ($size -eq 256) { 0 } else { $size }))
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]32)
        $writer.Write([uint32]$bytes.Length)
        $writer.Write([uint32]$offset)
        $offset += $bytes.Length
    }
    foreach ($bytes in $images) {
        $writer.Write($bytes)
    }
}
finally {
    $writer.Dispose()
    $file.Dispose()
}

Write-Host "Icône créée : $resolvedOutput"
