param(
    [Parameter(Mandatory = $true)][string]$MockRun,
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$StartupTimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runsRoot = [IO.Path]::GetFullPath((Join-Path $root 'runs\m4'))
$outPath = [IO.Path]::GetFullPath($Out)
if (-not $outPath.StartsWith($runsRoot + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Raw parity artifacts must remain beneath ignored runs/m4.'
}
if ((Test-Path -LiteralPath $outPath) -and (Get-ChildItem -LiteralPath $outPath -Force | Measure-Object).Count -gt 0) {
    throw 'Refusing to overwrite a previous parity attempt.'
}
New-Item -ItemType Directory -Force -Path $outPath | Out-Null

$sidLine = (& whoami.exe /user /fo csv /nh | ConvertFrom-Csv -Header Account,SID | Select-Object -First 1)
$sid = $sidLine.SID
if (-not $sid.StartsWith('S-')) { throw 'Could not resolve the current-user SID.' }
$dirGrant = "*$($sid):(OI)(CI)F"
& icacls.exe $outPath /inheritance:r /grant:r $dirGrant | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the parity output directory ACL.' }

$privateDir = Join-Path $outPath 'private'
$requestDir = Join-Path $outPath 'requests'
$responseDir = Join-Path $outPath 'responses'
New-Item -ItemType Directory -Force -Path $privateDir,$requestDir,$responseDir | Out-Null

trap {
    $fatal = $_
    $diagnostic = [ordered]@{
        type = $fatal.Exception.GetType().Name
        message = $fatal.Exception.Message
        script_line = $fatal.InvocationInfo.ScriptLineNumber
        position = $fatal.InvocationInfo.PositionMessage
        stack = $fatal.ScriptStackTrace
    }
    $diagPath = Join-Path $outPath 'unhandled-error.json'
    [IO.File]::WriteAllText($diagPath, (ConvertTo-Json -InputObject $diagnostic -Depth 10) + "`n",
        (New-Object Text.UTF8Encoding($false)))
    if ($keyPath -and (Test-Path -LiteralPath $keyPath)) { Remove-Item -LiteralPath $keyPath -Force }
    Write-Output (ConvertTo-Json -InputObject $diagnostic -Compress -Depth 10)
    exit 2
}

$keyBytes = $null
$apiKey = $null
$apiKeyHash = $null
$keyPath = $null

$configPath = Join-Path $root 'configs\m4-runtime-v2.json'
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$modelPath = $config.model.path
$serverPath = $config.runtime.binary_path
$modelExpected = $config.model.sha256
$serverExpected = $config.runtime.binary_sha256
$modelActual = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant()
$serverActual = (Get-FileHash -LiteralPath $serverPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($modelActual -ne $modelExpected) { throw 'Frozen model SHA256 mismatch.' }
if ($serverActual -ne $serverExpected) { throw 'Frozen llama-server SHA256 mismatch.' }

$expectedPath = Join-Path $outPath 'expected-prompts.json'
$python = (Get-Command python.exe).Source
& $python (Join-Path $root 'scripts\export_m4_server_parity_inputs.py') `
    --mock-run ([IO.Path]::GetFullPath($MockRun)) --out $expectedPath
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare offline tokenizer input manifest.' }
$expected = Get-Content -LiteralPath $expectedPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($expected.prompt_count -ne 96 -or $expected.model_sha256 -ne $modelExpected) {
    throw 'Frozen parity input manifest is incomplete or uses a different model.'
}
if ($expected.server_binary_sha256 -ne $serverExpected -or
    $expected.runtime_bundle_sha256 -ne $config.runtime.bundle_sha256) {
    throw 'Frozen llama.cpp binary or runtime bundle identity differs from the v2 config.'
}

$port = 8081
$existingOwners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
if ($existingOwners.Count -gt 0) { throw '127.0.0.1:8081 is occupied; no unrelated process will be contacted.' }

$keyBytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($keyBytes)
$apiKey = [Convert]::ToBase64String($keyBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$apiKeyBytes = [Text.Encoding]::ASCII.GetBytes($apiKey)
$apiKeyHash = [BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($apiKeyBytes)).Replace('-','').ToLowerInvariant()
$keyPath = Join-Path $privateDir 'llama-api-key.txt'
[IO.File]::WriteAllText($keyPath, $apiKey + "`n", [Text.Encoding]::ASCII)
& icacls.exe $keyPath /inheritance:r /grant:r "*$($sid):(F)" | Out-Null
if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $keyPath -Force; throw 'Could not restrict API key ACL.' }

$stdoutPath = Join-Path $outPath 'llama-server.stdout.log'
$stderrPath = Join-Path $outPath 'llama-server.stderr.log'
$serverArgs = @(
    '--model', $modelPath, '--alias', $config.model.id, '--offline',
    '--host', '127.0.0.1', '--port', "$port", '--no-webui', '--no-warmup', '--jinja',
    '--cors-origins', 'localhost', '--no-cors-credentials', '--ctx-size', '4096',
    '--parallel', '1', '--device', 'Vulkan1', '--n-gpu-layers', 'all', '--fit', 'off',
    '--reasoning', 'off', '--reasoning-format', 'none', '--temp', '0', '--top-p', '1',
    '--top-k', '0', '--min-p', '0', '--samplers', 'top_k;top_p;min_p;temperature',
    '--api-key-file', $keyPath
)

$serverProcess = $null
$httpClient = $null
$httpAttempts = 0
$httpTerminals = 0
$results = New-Object System.Collections.Generic.List[object]
$ownerChecks = New-Object System.Collections.Generic.List[object]
$routes = New-Object System.Collections.Generic.List[string]
$runError = $null
$status = 'NO_GO_LLAMA_TOKEN_PARITY'
$cleanupPass = $false
$listenerAfterShutdown = @()
$utf8NoBom = New-Object Text.UTF8Encoding($false)

function Get-Sha256Hex([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Write-JsonExclusive([string]$Path, [object]$Value) {
    $json = ConvertTo-Json -InputObject $Value -Depth 100
    $bytes = $utf8NoBom.GetBytes($json + "`n")
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
}

function Add-Jsonl([string]$Path, [object]$Value) {
    $line = (ConvertTo-Json -InputObject $Value -Depth 100 -Compress) + "`n"
    [IO.File]::AppendAllText($Path, $line, $utf8NoBom)
}

function Get-Owners {
    $rows = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
    $owners = @()
    foreach ($row in $rows) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($row.OwningProcess)"
        $owners += [pscustomobject]@{
            LocalAddress = [string]$row.LocalAddress
            LocalPort = [int]$row.LocalPort
            OwningProcess = [int]$row.OwningProcess
            ExecutablePath = if ($proc) { [string]$proc.ExecutablePath } else { $null }
        }
    }
    return $owners
}

function Assert-ExactOwner([string]$Phase) {
    $owners = @(Get-Owners)
    $match = ($owners.Count -eq 1 -and
        $owners[0].LocalAddress -eq '127.0.0.1' -and
        $owners[0].LocalPort -eq $port -and
        $owners[0].OwningProcess -eq $serverProcess.Id -and
        [string]::Equals($owners[0].ExecutablePath, $serverPath, [StringComparison]::OrdinalIgnoreCase))
    $snapshot = [pscustomobject]@{
        phase = $Phase; expected_pid = $serverProcess.Id; expected_executable = $serverPath
        observed_owners = $owners; exact_owner_match = $match
    }
    $ownerChecks.Add($snapshot)
    Add-Jsonl (Join-Path $outPath 'listener-ownership.jsonl') $snapshot
    if (-not $match) { throw "Listener owner verification failed during $Phase." }
}

function Invoke-TokenRoute([string]$RequestId, [string]$Route, [object]$Body) {
    if (@('/apply-template','/tokenize') -notcontains $Route) { throw "Refused non-token route: $Route" }
    if ($script:httpAttempts -ge 192) { throw 'Hard token-only HTTP request ceiling (192) reached.' }
    Assert-ExactOwner "before:$RequestId"
    $bodyJson = ConvertTo-Json -InputObject $Body -Depth 100 -Compress
    $bodyBytes = $utf8NoBom.GetBytes($bodyJson)
    $requestRecord = [pscustomobject]@{
        request_id = $RequestId; method = 'POST'; route = $Route
        url = "http://127.0.0.1:$port$Route"; body = $Body
        body_sha256 = Get-Sha256Hex $bodyBytes; authorization_header_saved = $false
    }
    Write-JsonExclusive (Join-Path $requestDir "$RequestId.json") $requestRecord
    Add-Jsonl (Join-Path $outPath 'http-ledger.jsonl') ([pscustomobject]@{
        event = 'attempt_started'; request_id = $RequestId; method = 'POST'; route = $Route
        url = "http://127.0.0.1:$port$Route"; request_body_sha256 = Get-Sha256Hex $bodyBytes
        auth_header_saved = $false; proxy_disabled = $true
    })
    $script:httpAttempts++
    $content = [System.Net.Http.StringContent]::new($bodyJson, [Text.Encoding]::UTF8, 'application/json')
    $terminalWritten = $false
    try {
        $response = $httpClient.PostAsync("http://127.0.0.1:$port$Route", $content).GetAwaiter().GetResult()
        $rawBytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        $responseText = [Text.Encoding]::UTF8.GetString($rawBytes)
        [IO.File]::WriteAllBytes((Join-Path $responseDir "$RequestId.bin"), $rawBytes)
        Add-Jsonl (Join-Path $outPath 'http-ledger.jsonl') ([pscustomobject]@{
            event = 'attempt_terminal'; request_id = $RequestId; http_status = [int]$response.StatusCode
            response_body_sha256 = Get-Sha256Hex $rawBytes; authorization_header_persisted = $false
        })
        $script:httpTerminals++
        $terminalWritten = $true
        $routes.Add($Route)
        if ([int]$response.StatusCode -ne 200) { throw "$Route returned HTTP $([int]$response.StatusCode)." }
        return $responseText | ConvertFrom-Json
    }
    catch {
        if (-not $terminalWritten) {
            Add-Jsonl (Join-Path $outPath 'http-ledger.jsonl') ([pscustomobject]@{
                event = 'attempt_terminal'; request_id = $RequestId; error_type = $_.Exception.GetType().Name
                error = $_.Exception.Message; authorization_header_persisted = $false
            })
            $script:httpTerminals++
        }
        throw
    }
    finally { $content.Dispose() }
}

try {
    $serverActual = (Get-FileHash -LiteralPath $serverPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($serverActual -ne $serverExpected) { throw 'llama-server SHA256 changed after input freeze.' }
    $serverProcess = Start-Process -FilePath $serverPath -ArgumentList $serverArgs `
        -WorkingDirectory (Split-Path $serverPath -Parent) -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $listening = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($serverProcess.HasExited) { throw "llama-server exited during startup: $($serverProcess.ExitCode)" }
        $owners = @(Get-Owners)
        $match = ($owners.Count -eq 1 -and $owners[0].LocalAddress -eq '127.0.0.1' -and
            $owners[0].OwningProcess -eq $serverProcess.Id -and
            [string]::Equals($owners[0].ExecutablePath, $serverPath, [StringComparison]::OrdinalIgnoreCase))
        $snapshot = [pscustomobject]@{
            phase = 'startup'; expected_pid = $serverProcess.Id; expected_executable = $serverPath
            observed_owners = $owners; exact_owner_match = $match
        }
        $ownerChecks.Add($snapshot)
        Add-Jsonl (Join-Path $outPath 'listener-ownership.jsonl') $snapshot
        if ($match) { $listening = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $listening) { throw 'Frozen llama-server did not bind as the exact 127.0.0.1:8081 process.' }

    $handler = [System.Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $false
    $httpClient = [System.Net.Http.HttpClient]::new($handler)
    $httpClient.Timeout = [TimeSpan]::FromSeconds(30)
    $httpClient.DefaultRequestHeaders.Authorization =
        [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $apiKey)

    foreach ($item in $expected.prompts) {
        $requestPrefix = '{0:D3}-{1}' -f $results.Count, $item.request_id
        $templateBody = [ordered]@{
            messages = @($item.messages)
            chat_template_kwargs = @{ enable_thinking = $false }
        }
        $templateResponse = Invoke-TokenRoute "$requestPrefix-apply-template" '/apply-template' $templateBody
        $serverPrompt = [string]$templateResponse.prompt
        $templateMatch = ($serverPrompt -ceq [string]$item.local_rendered_prompt)
        $tokenBody = @{ content = $serverPrompt; add_special = $true; parse_special = $true; with_pieces = $false }
        $tokenResponse = Invoke-TokenRoute "$requestPrefix-tokenize" '/tokenize' $tokenBody
        $serverIds = @($tokenResponse.tokens | ForEach-Object { [long]$_ })
        $localIds = @($item.local_token_ids | ForEach-Object { [long]$_ })
        $serverIdString = $serverIds -join ','
        $localIdString = $localIds -join ','
        $result = [pscustomobject]@{
            request_id = [string]$item.request_id; action_kind = [string]$item.action_kind
            server_prompt_sha256 = Get-Sha256Hex ($utf8NoBom.GetBytes($serverPrompt))
            local_prompt_sha256 = [string]$item.local_prompt_sha256
            server_token_count = $serverIds.Count; local_token_count = $localIds.Count
            server_token_ids_sha256 = Get-Sha256Hex ($utf8NoBom.GetBytes($serverIdString))
            local_token_ids_sha256 = [string]$item.local_token_ids_sha256
            template_exact = $templateMatch; token_ids_exact = ($serverIdString -ceq $localIdString)
        }
        $results.Add($result)
    }
    if ($results.Count -eq 96 -and
        @($results | Where-Object { -not $_.template_exact }).Count -eq 0 -and
        @($results | Where-Object { -not $_.token_ids_exact }).Count -eq 0) {
        $status = 'PASS_LLAMA_SERVER_TOKENIZER_PARITY'
    }
}
catch {
    $runError = @{ type = $_.Exception.GetType().Name; message = $_.Exception.Message }
}
finally {
    if ($httpClient) { $httpClient.Dispose() }
    if ($serverProcess -and -not $serverProcess.HasExited) {
        try {
            $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($serverProcess.Id)"
            if ($procInfo -and [string]::Equals([string]$procInfo.ExecutablePath, $serverPath,
                    [StringComparison]::OrdinalIgnoreCase)) {
                Stop-Process -Id $serverProcess.Id -Force
                $serverProcess.WaitForExit(30000) | Out-Null
            }
        } catch { $runError = @{ type = $_.Exception.GetType().Name; message = "shutdown: $($_.Exception.Message)" } }
    }
    $listenerAfterShutdown = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object LocalAddress,LocalPort,OwningProcess)
    if ($keyPath -and (Test-Path -LiteralPath $keyPath)) { Remove-Item -LiteralPath $keyPath -Force }
    $keyRemoved = (-not $keyPath) -or (-not (Test-Path -LiteralPath $keyPath))
    $cleanupPass = ($listenerAfterShutdown.Count -eq 0 -and $keyRemoved)
    if ($status -eq 'PASS_LLAMA_SERVER_TOKENIZER_PARITY' -and -not $cleanupPass) {
        $status = 'NO_GO_TOKEN_PARITY_CLEANUP'
    }
    $ledgerRows = @()
    $ledgerPath = Join-Path $outPath 'http-ledger.jsonl'
    if (Test-Path -LiteralPath $ledgerPath) {
        $ledgerRows = @(Get-Content -LiteralPath $ledgerPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
    }
    $attemptCount = @($ledgerRows | Where-Object event -eq 'attempt_started').Count
    $terminalCount = @($ledgerRows | Where-Object event -eq 'attempt_terminal').Count
    # Precompute values outside the hashtable. Windows PowerShell 5.1 can throw
    # "Argument types do not match" when an inline if-expression is a hashtable
    # value after a long-running script, discarding the final receipt after all
    # HTTP responses were safely recorded.
    $serverPidForReport = $null
    if ($serverProcess) { $serverPidForReport = [int]$serverProcess.Id }
    $ownerChecksForReport = @($ownerChecks.ToArray())
    $resultsForReport = @($results.ToArray())
    $routesForReport = @($routes | Sort-Object -Unique)
    $listenersForReport = @($listenerAfterShutdown)
    $report = [ordered]@{
        schema_version = 'm4-tokenizer-server-parity-v1'; status = $status
        checked_at_local = (Get-Date).ToString('o'); host_platform = [Environment]::OSVersion.VersionString
        claim_scope = 'local chat-template and token-ID parity only; no model generation or behavioral result'
        mock_run = [IO.Path]::GetFullPath($MockRun); prompts_checked = $results.Count
        template_exact_matches = @($results | Where-Object template_exact).Count
        token_id_exact_matches = @($results | Where-Object token_ids_exact).Count
        focal_and_positive_pair_prompts = 96; http_attempts = $attemptCount
        http_terminal_records = $terminalCount; routes_used = $routesForReport
        generation_routes_used = @(); real_model_generations = 0; external_network_requests = 0
        server_process_pid = $serverPidForReport
        startup_owner_checks = $ownerChecksForReport; listener_rows_after_shutdown = $listenersForReport
        shutdown_cleanup_pass = $cleanupPass; model_sha256 = $modelActual; server_sha256 = $serverActual
        runtime_bundle_sha256 = [string]$expected.runtime_bundle_sha256
        runtime_config_sha256 = [string]$expected.runtime_config_sha256
        prompt_file_sha256 = $expected.prompt_file_sha256
        tokenizer_sha256 = [string]$expected.tokenizer_sha256
        chat_template_sha256 = [string]$expected.chat_template_sha256
        api_key_sha256 = $apiKeyHash; api_key_content_saved = $false
        api_key_removed = $keyRemoved; error = $runError
        prompt_results = $resultsForReport
    }
    Write-JsonExclusive (Join-Path $outPath 'parity-report.json') $report
}

Write-Output (ConvertTo-Json -InputObject ([ordered]@{
    status = $status; prompts_checked = $results.Count
    template_exact_matches = @($results | Where-Object template_exact).Count
    token_id_exact_matches = @($results | Where-Object token_ids_exact).Count
    http_attempts = $httpAttempts; http_terminal_records = $httpTerminals
    routes_used = @($routes | Sort-Object -Unique); generation_routes_used = @()
    real_model_generations = 0; external_network_requests = 0
    listener_rows_after_shutdown = $listenerAfterShutdown; shutdown_cleanup_pass = $cleanupPass; error = $runError
}) -Depth 10 -Compress)
if ($status -ne 'PASS_LLAMA_SERVER_TOKENIZER_PARITY') { exit 2 }
exit 0
