<#
.SYNOPSIS
Cloud Run の ERROR ログをメール通知する Monitoring 設定を作成する。

.DESCRIPTION
リポジトリ管理者が手動で実行する。既存の同名チャンネルとポリシーは再利用し、
同じ設定を重複作成しない。gcloud の beta/alpha Monitoring コマンドが必要。
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Email,
    [string]$ProjectId = "yui-agent-2026"
)

$ErrorActionPreference = "Stop"
$channelDisplayName = "Yui Agent ERROR email"
$policyDisplayName = "Yui Agent ERROR logs"
$channelFilter = "type=`"email`" AND labels.email_address=`"$Email`""
$policyFilter = "displayName=`"$policyDisplayName`""

# 同名のリソースがあれば再利用するため、繰り返し実行しても重複作成しない。
$channel = @(
    & gcloud beta monitoring channels list --project=$ProjectId --filter=$channelFilter `
        --format="value(name)"
)[0]
if (-not $channel) {
    & gcloud beta monitoring channels create --project=$ProjectId `
        --display-name=$channelDisplayName --type=email `
        --channel-labels="email_address=$Email"
    $channel = @(
        & gcloud beta monitoring channels list --project=$ProjectId --filter=$channelFilter `
            --format="value(name)"
    )[0]
}

if (-not $channel) {
    throw "メール通知チャンネルを確認できませんでした。"
}

$policy = @(
    & gcloud alpha monitoring policies list --project=$ProjectId --filter=$policyFilter `
        --format="value(name)"
)[0]
if ($policy) {
    Write-Host "既存のアラートポリシーを再利用します: $policy"
    exit 0
}

$policyFile = Join-Path $env:TEMP "yui-error-alert-$PID.yaml"
@"
displayName: $policyDisplayName
combiner: OR
conditions:
  - displayName: Cloud Run ERROR log detected
    conditionMatchedLog:
      filter: 'resource.type="cloud_run_revision" AND severity>=ERROR AND resource.labels.service_name="yui-agent"'
notificationChannels:
  - $channel
alertStrategy:
  notificationRateLimit:
    period: 300s
  autoClose: 604800s
"@ | Set-Content -Encoding utf8 $policyFile

try {
    & gcloud alpha monitoring policies create --project=$ProjectId --policy-from-file=$policyFile
}
finally {
    Remove-Item -LiteralPath $policyFile -ErrorAction SilentlyContinue
}
