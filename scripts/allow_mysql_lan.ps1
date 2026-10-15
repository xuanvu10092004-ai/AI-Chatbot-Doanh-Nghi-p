param(
    [string]$Network = '192.168.10.0/24',
    [int]$Port = 3306
)

$ruleName = 'Honda chatbot MySQL LAN'
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Action Allow -Profile Private,Public -Direction Inbound
    Set-NetFirewallAddressFilter -AssociatedNetFirewallRule $existingRule -RemoteAddress $Network
    Set-NetFirewallPortFilter -AssociatedNetFirewallRule $existingRule -Protocol TCP -LocalPort $Port
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Enabled True -Profile Private,Public -Protocol TCP -LocalPort $Port -RemoteAddress $Network -EdgeTraversalPolicy Block
}

Write-Host "Da cho phep TCP $Port tu $Network qua rule '$ruleName'."