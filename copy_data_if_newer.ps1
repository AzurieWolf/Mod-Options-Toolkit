
$source = "data"
$destination = "dist\data"

Get-ChildItem -Recurse $source | ForEach-Object {
    $targetPath = $_.FullName.Replace($source, $destination)

    if (!(Test-Path $targetPath) -or ($_.LastWriteTime -gt (Get-Item $targetPath).LastWriteTime)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $targetPath) | Out-Null
        Copy-Item $_.FullName -Destination $targetPath -Force
        Write-Host "Copied: $($_.FullName)"
    }
}
