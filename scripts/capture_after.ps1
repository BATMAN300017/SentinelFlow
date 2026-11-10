$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$baseDir = "$PWD\docs\screenshots\after"
$pages = @("dashboard", "transactions", "alerts", "investigations")

foreach ($p in $pages) {
    $url = "http://localhost:4174/$p"
    $dOut = "$baseDir\${p}_desktop.png"
    $mOut = "$baseDir\${p}_mobile.png"
    Write-Host "Capturing redesigned desktop for $p..."
    & $chrome --headless=new --disable-gpu --window-size=1440,900 --screenshot="$dOut" "$url"
    Start-Sleep -Milliseconds 500
    Write-Host "Capturing redesigned mobile for $p..."
    & $chrome --headless=new --disable-gpu --window-size=390,844 --screenshot="$mOut" "$url"
    Start-Sleep -Milliseconds 500
}
Get-ChildItem $baseDir
