<#
  Atacante SGIS — PowerShell nativo (cero instalación).

  Pensado para las laptops Windows del equipo: usa .NET (System.Net.Sockets),
  no requiere Python ni pip. Lanza un escaneo de puertos y luego fuerza bruta
  contra el sensor; el motor de reglas del SGIS levantará los incidentes.

  Uso:
    powershell -ExecutionPolicy Bypass -File attacker.ps1 -Target 192.168.1.50
    .\attacker.ps1 -Target 127.0.0.1 -Attempts 10
#>
param(
    [string]$Target = "127.0.0.1",
    [int[]] $Ports = @(2121, 2222, 8080, 8443, 3306, 3389, 5432, 9000, 1433, 5900, 6379, 9200),
    [int]   $AuthPort = 2222,
    [int]   $Attempts = 8,
    [double]$Delay = 0.25
)

# Abre un socket TCP, opcionalmente envía datos, y cierra. Devuelve $true si conectó.
function Invoke-Knock([string]$TargetHost, [int]$Port, [string]$Payload) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($TargetHost, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(600)) { return $false }
        $client.EndConnect($async)
        if ($Payload) {
            $bytes = [Text.Encoding]::ASCII.GetBytes($Payload)
            $client.GetStream().Write($bytes, 0, $bytes.Length)
        }
        return $true
    } catch { return $false }
    finally { $client.Close() }
}

Write-Host "=== Atacante apuntando a $Target ===" -ForegroundColor Cyan

Write-Host "`n[1/2] Escaneo de puertos ($($Ports.Count) puertos)..."
foreach ($p in $Ports) {
    $ok = Invoke-Knock $Target $p $null
    $estado = if ($ok) { "abierto" } else { "cerrado" }
    Write-Host ("   {0}:{1,-5} {2}" -f $Target, $p, $estado)
    Start-Sleep -Seconds $Delay
}

Write-Host "`n[2/2] Fuerza bruta contra ${Target}:${AuthPort} ($Attempts intentos)..."
$users  = @("admin", "root", "administrator", "postgres", "oracle", "test", "ucv", "soporte")
$passwd = @("123456", "password", "admin", "qwerty", "root123")
for ($i = 1; $i -le $Attempts; $i++) {
    $u = $users  | Get-Random
    $c = $passwd | Get-Random
    [void](Invoke-Knock $Target $AuthPort "${u}:${c}`n")
    Write-Host ("   intento {0,2}/{1}  {2}:{3}" -f $i, $Attempts, $u, $c)
    Start-Sleep -Seconds $Delay
}

Write-Host "`nListo. Revisa el Centro de Operaciones del SGIS." -ForegroundColor Green
