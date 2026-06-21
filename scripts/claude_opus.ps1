param(
    [Parameter(Mandatory = $true)]
    [string]$PromptFile,

    [string]$Model = "",

    [string]$OutputFile = ""
)

$baseUrl = if ($env:KRACKED_CLAUDE_BASE_URL) {
    $env:KRACKED_CLAUDE_BASE_URL
} else {
    [Environment]::GetEnvironmentVariable("KRACKED_CLAUDE_BASE_URL", "User")
}

$apiKey = if ($env:KRACKED_CLAUDE_API_KEY) {
    $env:KRACKED_CLAUDE_API_KEY
} else {
    [Environment]::GetEnvironmentVariable("KRACKED_CLAUDE_API_KEY", "User")
}

if (-not $baseUrl) {
    throw "KRACKED_CLAUDE_BASE_URL is not set."
}

if (-not $apiKey) {
    throw "KRACKED_CLAUDE_API_KEY is not set."
}

if (-not (Test-Path $PromptFile)) {
    throw "Prompt file not found: $PromptFile"
}

$prompt = Get-Content $PromptFile -Raw
$effectiveModel = if ([string]::IsNullOrWhiteSpace($Model)) { "claude-opus-4.6" } else { $Model }
$payload = @{
    model = $effectiveModel
    messages = @(
        @{
            role = "user"
            content = $prompt
        }
    )
} | ConvertTo-Json -Depth 8

$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/chat/completions" `
    -Headers @{ Authorization = "Bearer $apiKey" } `
    -ContentType "application/json" `
    -Body $payload

$text = $response.choices[0].message.content

if ($OutputFile) {
    Set-Content -Path $OutputFile -Value $text
}

$text
