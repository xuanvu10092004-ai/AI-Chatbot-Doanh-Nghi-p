param(
    [Parameter(Mandatory = $true)]
    [string]$Network,
    [Parameter(Mandatory = $true)]
    [System.Net.IPAddress]$ServerAddress,
    [ValidateRange(1, 65535)]
    [int]$Port = 3306
)

$ErrorActionPreference = 'Stop'
# Dùng cùng quy tắc xác thực RFC1918 như script cấp account MySQL.
$projectRoot = Split-Path -Parent $PSScriptRoot
$validatedNetwork = & python -c 'import sys; sys.path.insert(0,sys.argv[1]); from mysql_accounts import lan_account_host; print(lan_account_host(sys.argv[2])[0])' $projectRoot $Network
if ($LASTEXITCODE -ne 0) { throw 'Mang LAN khong hop le; chua thay doi firewall.' }
$Network = $validatedNetwork.Trim()
$addressBytes = $ServerAddress.GetAddressBytes()
$parts = $Network.Split('/')
$networkBytes = ([System.Net.IPAddress]::Parse($parts[0])).GetAddressBytes()
if ($addressBytes.Length -ne 4) { throw 'ServerAddress phai la IPv4.' }
$prefix = [int]$parts[1]
for ($index = 0; $index -lt 4; $index++) {
    $bits = [Math]::Min(8, [Math]::Max(0, $prefix - 8 * $index))
    $mask = if ($bits -eq 0) { 0 } else { 256 - [Math]::Pow(2, 8 - $bits) }
    if (($addressBytes[$index] -band [int]$mask) -ne $networkBytes[$index]) {
        throw 'ServerAddress khong nam trong mang LAN da chi dinh.'
    }
}
if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $ServerAddress.IPAddressToString -ErrorAction SilentlyContinue)) {
    throw 'ServerAddress khong phai dia chi cua may nay.'
}

$ruleName = 'Honda chatbot MySQL LAN'
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Action Allow -Profile Private,Public -Direction Inbound
    Set-NetFirewallAddressFilter -AssociatedNetFirewallRule $existingRule -LocalAddress $ServerAddress.IPAddressToString -RemoteAddress $Network
    Set-NetFirewallPortFilter -AssociatedNetFirewallRule $existingRule -Protocol TCP -LocalPort $Port
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Enabled True -Profile Private,Public -Protocol TCP -LocalPort $Port -LocalAddress $ServerAddress.IPAddressToString -RemoteAddress $Network -EdgeTraversalPolicy Block
}

Write-Host "Da cho phep TCP $Port tu $Network qua rule '$ruleName'."
