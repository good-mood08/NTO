# получить твой локальный IP в сети 192.168.x.x
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -like '192.168.*' } |
  Select-Object -First 1 -ExpandProperty IPAddress)

# поднять docker-проект
docker-compose up -d

Write-Host ""
Write-Host "site: https://$ip" -ForegroundColor Green
Write-Host ""site: https://"$ip":8000"" -ForegroundColor Green
# запустить caddy из public web
$caddyPath = "$PSScriptRoot\apps\web\public\caddy_windows_amd64.exe"
$backend  = "localhost:3000"
$backendServer = "$($ip):443"
# if (-not $ip) {
#   Write-Error "Не удалось определить локальный IP (192.168.*)."
#нет   exit 1
# }
$args = @(
  "reverse-proxy"
  "--from", $backendServer
  "--to", $backend
  
)

& $caddyPath @args

