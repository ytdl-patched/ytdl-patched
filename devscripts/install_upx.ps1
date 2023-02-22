# UPX installer for GitHub Actions' Windows
choco install upx

if ($LASTEXITCODE -ne 0) {
    # fallback to ZIP download
    $UpxVersion = "4.0.2"
    Invoke-WebRequest "https://github.com/upx/upx/releases/download/v${UpxVersion}/upx-${UpxVersion}-win64.zip" -O upx.zip
    Expand-Archive -Path 'upx.zip' -DestinationPath 'upx\'
    # add to PATH as we do for Actions
    echo "$((Get-Item .).FullName)/upx-${UpxVersion}-win64" | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
}
