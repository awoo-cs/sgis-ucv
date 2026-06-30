<#
  SGIS-UCV — Kit de demo (Launcher rol-aware).

  Mini-tablero para desplegar, en cada laptop del salón, el rol que le toca en la
  demostración (Atacante / Sensor / Operador) con un par de clics. GUI nativa de
  Windows PowerShell 5.1 (WinForms): NO instala nada en las laptops que solo atacan
  o solo observan. La laptop "Sensor" sí necesita Python (es la única).

  No se ejecuta a mano: doble clic en Iniciar.bat (que lo lanza con la política
  de ejecución correcta).

  Roles:
    Atacante  → corre attacker.ps1 contra la IP del sensor (cero instalación).
    Sensor    → corre sensor.py reportando al backend; opción de firewall REAL (UAC).
    Operador  → abre el Centro de Operaciones en el navegador y muestra credenciales.

  Nota de ámbito (PowerShell): los manejadores de los botones (Add_Click) se ejecutan
  DESPUÉS de que Render-Role retorna, así que solo pueden leer variables de ámbito de
  script ($script:/nivel raíz). Por eso los campos compartidos son $script:* .
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Carpeta de este script (donde viven sensor.py / attacker.ps1).
$dir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }

# ── Valores por defecto (editables en la ventana) ─────────────────────────────
# Apuntan al entorno DEV (Railway + Vercel). Para la demo final contra producción,
# cámbialos en la ventana o edita estas 3 líneas.
$DEFAULT_BACKEND  = 'https://backend-dev-6d4d.up.railway.app'
$DEFAULT_FRONTEND = 'https://sgis-ucv-git-dev-awoo-cs-projects.vercel.app'
# Clave de ingesta del entorno DEV (no es un secreto de producción).
$DEFAULT_APIKEY   = 'dev-cloud-test-2026'

# Puertos que el sensor escucha; el rol Sensor abre estos en el firewall al arrancar.
$SENSOR_PORTS = '2121,2222,8080,8443,3306,3389,5432,9000,1433,5900,6379,9200'

# Python a usar para el sensor (la única laptop que lo necesita).
$script:PythonExe = $null
foreach ($cand in @('python', 'py')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $script:PythonExe = $cand; break }
}
$script:SensorProc = $null
$script:txtIp = $null    # campo "IP del sensor" (solo existe en el rol Atacante)

# ── Ventana ───────────────────────────────────────────────────────────────────
$form = New-Object System.Windows.Forms.Form
$form.Text = 'SGIS-UCV — Kit de demo'
$form.Size = New-Object System.Drawing.Size(700, 600)
$form.StartPosition = 'CenterScreen'
$form.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$form.BackColor = [System.Drawing.Color]::White

$title = New-Object System.Windows.Forms.Label
$title.Text = 'SGIS-UCV · Centro de mando de la demo'
$title.Font = New-Object System.Drawing.Font('Segoe UI', 13, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(20, 14)
$title.AutoSize = $true
$form.Controls.Add($title)

# Rol
$lblRole = New-Object System.Windows.Forms.Label
$lblRole.Text = 'Rol de esta laptop:'
$lblRole.Location = New-Object System.Drawing.Point(20, 52)
$lblRole.AutoSize = $true
$form.Controls.Add($lblRole)

$cboRole = New-Object System.Windows.Forms.ComboBox
$cboRole.DropDownStyle = 'DropDownList'
$cboRole.Location = New-Object System.Drawing.Point(170, 49)
$cboRole.Size = New-Object System.Drawing.Size(220, 26)
[void]$cboRole.Items.AddRange(@('Atacante', 'Sensor', 'Operador'))
$form.Controls.Add($cboRole)

# Backend
$lblUrl = New-Object System.Windows.Forms.Label
$lblUrl.Text = 'Backend (Railway):'
$lblUrl.Location = New-Object System.Drawing.Point(20, 84)
$lblUrl.AutoSize = $true
$form.Controls.Add($lblUrl)

$txtUrl = New-Object System.Windows.Forms.TextBox
$txtUrl.Location = New-Object System.Drawing.Point(170, 81)
$txtUrl.Size = New-Object System.Drawing.Size(490, 26)
$txtUrl.Text = $DEFAULT_BACKEND
$form.Controls.Add($txtUrl)

# API key
$lblKey = New-Object System.Windows.Forms.Label
$lblKey.Text = 'API Key (ingesta):'
$lblKey.Location = New-Object System.Drawing.Point(20, 116)
$lblKey.AutoSize = $true
$form.Controls.Add($lblKey)

$txtKey = New-Object System.Windows.Forms.TextBox
$txtKey.Location = New-Object System.Drawing.Point(170, 113)
$txtKey.Size = New-Object System.Drawing.Size(490, 26)
$txtKey.Text = $DEFAULT_APIKEY
$form.Controls.Add($txtKey)

# Panel de acciones (cambia según el rol)
$gbActions = New-Object System.Windows.Forms.GroupBox
$gbActions.Text = 'Acciones'
$gbActions.Location = New-Object System.Drawing.Point(20, 148)
$gbActions.Size = New-Object System.Drawing.Size(640, 185)
$form.Controls.Add($gbActions)

# Log
$rtbLog = New-Object System.Windows.Forms.RichTextBox
$rtbLog.Location = New-Object System.Drawing.Point(20, 345)
$rtbLog.Size = New-Object System.Drawing.Size(640, 205)
$rtbLog.ReadOnly = $true
$rtbLog.BackColor = [System.Drawing.Color]::FromArgb(15, 15, 15)
$rtbLog.ForeColor = [System.Drawing.Color]::Gainsboro
$rtbLog.Font = New-Object System.Drawing.Font('Consolas', 9)
$form.Controls.Add($rtbLog)

function Write-Log([string]$msg, [string]$color = 'Gainsboro') {
    $stamp = (Get-Date).ToString('HH:mm:ss')
    $rtbLog.SelectionColor = [System.Drawing.Color]::FromName($color)
    $rtbLog.AppendText("[$stamp] $msg`n")
    $rtbLog.ScrollToCaret()
}

# ── Helpers ─────────────────────────────────────────────────────────────────
function Get-LanIPv4 {
    try {
        return @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
            Select-Object -ExpandProperty IPAddress)
    } catch {
        $ip = (Test-Connection -ComputerName $env:COMPUTERNAME -Count 1 -ErrorAction SilentlyContinue).IPV4Address.IPAddressToString
        if ($ip) { return @($ip) }
        return @()
    }
}

function New-ActionButton([string]$text, [int]$x, [int]$y, [int]$w, [int]$h) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.Location = New-Object System.Drawing.Point($x, $y)
    $b.Size = New-Object System.Drawing.Size($w, $h)
    $b.FlatStyle = 'Flat'
    $b.BackColor = [System.Drawing.Color]::FromArgb(10, 10, 10)
    $b.ForeColor = [System.Drawing.Color]::White
    return $b
}

function New-Note([string]$text, [int]$y) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text
    $l.Location = New-Object System.Drawing.Point(15, $y)
    $l.Size = New-Object System.Drawing.Size(610, 40)
    $l.ForeColor = [System.Drawing.Color]::Gray
    return $l
}

# Lanza attacker.ps1 en una ventana nueva. $scanOnly => solo escaneo (sin fuerza bruta).
function Start-Attack([bool]$scanOnly) {
    $ip = if ($script:txtIp) { $script:txtIp.Text.Trim() } else { '' }
    if (-not $ip) { Write-Log 'Escribe primero la IP del sensor.' 'Khaki'; return }
    # -WorkingDirectory => attacker.ps1 (relativo) resuelve aunque la ruta tenga espacios.
    $argList = @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', 'attacker.ps1', '-Target', $ip)
    if ($scanOnly) { $argList += @('-Attempts', '0') }
    Start-Process -FilePath 'powershell' -WorkingDirectory $dir -ArgumentList $argList
    $modo = if ($scanOnly) { '(solo escaneo)' } else { '(escaneo + fuerza bruta)' }
    Write-Log "Atacando $ip $modo…" 'Tomato'
}

# Abre/cierra en el Firewall de Windows los puertos de ENTRADA del sensor.
# Sin esto, Windows rebota las conexiones entrantes y el sensor no ve nada
# (cero líneas en consola). Requiere admin → se eleva con un aviso UAC.
function Set-SensorFirewall([bool]$open) {
    $rule = 'SGIS-sensor-in'
    if ($open) {
        $a = @('advfirewall', 'firewall', 'add', 'rule', "name=$rule", 'dir=in',
               'action=allow', 'protocol=TCP', "localport=$SENSOR_PORTS")
        $msg = "Puertos del sensor abiertos en el firewall ($SENSOR_PORTS)."
    } else {
        $a = @('advfirewall', 'firewall', 'delete', 'rule', "name=$rule")
        $msg = 'Puertos del sensor cerrados en el firewall.'
    }
    try {
        Start-Process -FilePath 'netsh.exe' -Verb RunAs -WindowStyle Hidden -ArgumentList $a -Wait
        Write-Log $msg 'Gray'
    } catch {
        Write-Log "No pude tocar el firewall (¿cancelaste el aviso de administrador?)." 'Khaki'
    }
}

# Lanza sensor.py. $firewall => con reglas netsh reales (pide UAC).
function Start-Sensor([bool]$firewall) {
    if (-not $script:PythonExe) {
        Write-Log 'No encontré Python en esta laptop. El rol Sensor lo necesita.' 'Tomato'; return
    }
    # Abrimos los puertos de entrada SIEMPRE (en ambos modos), si no, no llega tráfico.
    Set-SensorFirewall $true
    $u = $txtUrl.Text.Trim(); $k = $txtKey.Text.Trim()
    $sargs = @('sensor.py', '--target', $u, '--api-key', $k)
    if ($firewall) { $sargs += '--firewall' }
    try {
        if ($firewall) {
            $script:SensorProc = Start-Process -FilePath $script:PythonExe -Verb RunAs `
                -WorkingDirectory $dir -ArgumentList $sargs -PassThru
            Write-Log 'Sensor iniciado con FIREWALL REAL (acepta el aviso de administrador).' 'Tomato'
        } else {
            $script:SensorProc = Start-Process -FilePath $script:PythonExe `
                -WorkingDirectory $dir -ArgumentList $sargs -PassThru
            Write-Log 'Sensor iniciado (corte a nivel de aplicación).' 'LightGreen'
        }
        Write-Log "Reportando a $u" 'Gray'
    } catch {
        Write-Log "No pude iniciar el sensor: $($_.Exception.Message)" 'Tomato'
    }
}

function Stop-Sensor {
    if ($script:SensorProc -and -not $script:SensorProc.HasExited) {
        try { Stop-Process -Id $script:SensorProc.Id -ErrorAction Stop; Write-Log 'Sensor detenido.' 'Khaki' }
        catch { Write-Log 'No pude detenerlo (¿está elevado?). Cierra su ventana con Ctrl-C.' 'Khaki' }
    } else { Write-Log 'No hay un sensor en marcha lanzado desde aquí.' 'Gray' }
    # Dejamos el firewall como estaba: cerramos los puertos que abrió el kit.
    Set-SensorFirewall $false
}

# ── Render por rol ────────────────────────────────────────────────────────────
function Render-Role([string]$role) {
    $gbActions.Controls.Clear()
    $script:txtIp = $null

    switch ($role) {
        'Atacante' {
            $lblIp = New-Object System.Windows.Forms.Label
            $lblIp.Text = 'IP del sensor:'
            $lblIp.Location = New-Object System.Drawing.Point(15, 33)
            $lblIp.AutoSize = $true
            $gbActions.Controls.Add($lblIp)

            $script:txtIp = New-Object System.Windows.Forms.TextBox
            $script:txtIp.Location = New-Object System.Drawing.Point(130, 30)
            $script:txtIp.Size = New-Object System.Drawing.Size(220, 26)
            $gbActions.Controls.Add($script:txtIp)

            $btnScan = New-ActionButton 'Escaneo de puertos' 15 75 300 40
            $btnFull = New-ActionButton 'Ataque completo (escaneo + fuerza bruta)' 325 75 300 40
            $btnScan.Add_Click({ Start-Attack $true })
            $btnFull.Add_Click({ Start-Attack $false })
            $gbActions.Controls.Add($btnScan)
            $gbActions.Controls.Add($btnFull)
            $gbActions.Controls.Add((New-Note 'Apunta a la IP LAN que muestra la laptop Sensor. No instala nada (PowerShell nativo).' 125))
        }

        'Sensor' {
            $ips = Get-LanIPv4
            $lblLan = New-Object System.Windows.Forms.Label
            if ($ips.Count) {
                $lblLan.Text = "IP(s) LAN de esta laptop:  $($ips -join '   ')"
            } else {
                $lblLan.Text = 'No detecté la IP LAN (revisa la conexión a la red del salón).'
            }
            $lblLan.Font = New-Object System.Drawing.Font('Consolas', 10, [System.Drawing.FontStyle]::Bold)
            $lblLan.Location = New-Object System.Drawing.Point(15, 28)
            $lblLan.Size = New-Object System.Drawing.Size(610, 24)
            $gbActions.Controls.Add($lblLan)

            $btnFw  = New-ActionButton 'Iniciar sensor (firewall REAL)' 15 65 300 40
            $btnApp = New-ActionButton 'Iniciar sensor (solo app)' 325 65 300 40
            $btnStop = New-ActionButton 'Detener sensor' 15 112 300 32
            $btnFw.Add_Click({ Start-Sensor $true })
            $btnApp.Add_Click({ Start-Sensor $false })
            $btnStop.Add_Click({ Stop-Sensor })
            $gbActions.Controls.Add($btnFw)
            $gbActions.Controls.Add($btnApp)
            $gbActions.Controls.Add($btnStop)
            $gbActions.Controls.Add((New-Note 'Dicta al Atacante la IP de arriba. Al iniciar pide UAC una vez para abrir los puertos en el firewall; «firewall real» además bloquea con netsh.' 150))
        }

        'Operador' {
            $btnOpen  = New-ActionButton 'Abrir Centro de Operaciones' 15 35 320 44
            $btnCreds = New-ActionButton 'Mostrar credenciales demo' 345 35 280 44
            $btnOpen.Add_Click({
                Start-Process $DEFAULT_FRONTEND
                Write-Log "Abriendo $DEFAULT_FRONTEND" 'LightGreen'
            })
            $btnCreds.Add_Click({
                Write-Log 'Credenciales demo (contraseña: Sgis2026*):' 'White'
                Write-Log '  admin.ti   -> Administrador TI (puede Reiniciar demo)' 'Gainsboro'
                Write-Log '  analista   -> Analista (puede Liberar contención)' 'Gainsboro'
                Write-Log '  jefe.area  -> Jefe de Área (valida el cierre)' 'Gainsboro'
            })
            $gbActions.Controls.Add($btnOpen)
            $gbActions.Controls.Add($btnCreds)
            $gbActions.Controls.Add((New-Note 'Esta laptop solo observa: proyecta el navegador con el tablero en vivo. No instala nada.' 95))
        }
    }
}

$cboRole.Add_SelectedIndexChanged({ Render-Role $cboRole.SelectedItem })

# Arranque
Write-Log 'Listo. Elige el rol de esta laptop arriba.' 'LightGreen'
if (-not $script:PythonExe) {
    Write-Log 'Aviso: no hay Python en esta laptop -> solo sirve como Atacante u Operador.' 'Khaki'
}
$cboRole.SelectedIndex = 0   # dispara Render-Role('Atacante')

[void]$form.ShowDialog()
