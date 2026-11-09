Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new("en-US"))
}

$imgDir = "D:\ATC\radar-trainer\scratch\smac_images"
$ocrDir = "D:\ATC\radar-trainer\scratch\smac_ocr"
if (-not (Test-Path $ocrDir)) { New-Item -ItemType Directory -Path $ocrDir | Out-Null }

$airports = @('VEAT', 'VIAR', 'VOBG', 'VOVI', 'VEBS', 'VOCL', 'VOCI', 'VEGT', 'VIJP', 'VILK', 'VANP', 'VEPT', 'VOTR', 'VEBN')

foreach ($icao in $airports) {
    $imgPath = Join-Path $imgDir "$icao.png"
    if (Test-Path $imgPath) {
        Write-Host "Running OCR on $icao..."
        $fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($imgPath)
        $file = Await $fileTask ([Windows.Storage.StorageFile])

        $streamTask = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
        $stream = Await $streamTask ([Windows.Storage.Streams.IRandomAccessStream])

        $decoderTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
        $decoder = Await $decoderTask ([Windows.Graphics.Imaging.BitmapDecoder])

        $bitmapTask = $decoder.GetSoftwareBitmapAsync()
        $bitmap = Await $bitmapTask ([Windows.Graphics.Imaging.SoftwareBitmap])

        $ocrTask = $engine.RecognizeAsync($bitmap)
        $result = Await $ocrTask ([Windows.Media.Ocr.OcrResult])

        $outPath = Join-Path $ocrDir "$icao.txt"
        $lines = @()
        foreach ($line in $result.Lines) {
            $lines += $line.Text
        }
        [System.IO.File]::WriteAllLines($outPath, $lines, [System.Text.Encoding]::UTF8)
        Write-Host "Saved $($lines.Count) lines for $icao"
    }
}
