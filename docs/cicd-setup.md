# CI/CD セットアップ

`.github/workflows/deploy.yml` は `main` または `master` への push と手動実行で起動する。`check` ジョブで依存関係の解決と Python の構文を検証し、成功した場合だけ Workload Identity Federation (WIF) で認証して Cloud Run にデプロイする。

以下のコマンドは、リポジトリ管理者が一度だけローカルで実行する。値を確認してから実行し、サービスアカウントキーは作成しない。

## 1. API と変数

```bash
gcloud config set project yui-agent-2026

export PROJECT_ID=yui-agent-2026
export PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
export REGION=asia-northeast1
export REPOSITORY=itiwoja/yui-agent
export POOL_ID=github-pool
export PROVIDER_ID=github-provider
export DEPLOY_SA_NAME=github-cloud-run-deployer
export DEPLOY_SA="${DEPLOY_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  calendar-json.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudscheduler.googleapis.com
```

PowerShellでは `export NAME=value` の代わりに `$env:NAME = "value"` を使う。

## 2. デプロイ用サービスアカウント

```bash
gcloud iam service-accounts create "${DEPLOY_SA_NAME}" \
  --display-name="GitHub Cloud Run deployer"

for ROLE in \
  roles/run.admin \
  roles/cloudbuild.builds.editor \
  roles/storage.admin
do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEPLOY_SA}" \
    --role="${ROLE}"
done

gcloud iam service-accounts add-iam-policy-binding \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/iam.serviceAccountUser"
```

Cloud Run の実行サービスアカウントを明示している場合は、最後のコマンドの対象をそのサービスアカウントに置き換える。組織ポリシーや Cloud Build のサービスアカウント構成によって追加権限を求められた場合は、Actions のエラーに示された主体へ必要最小限で付与する。

## 3. GitHub用WIF

```bash
gcloud iam workload-identity-pools create "${POOL_ID}" \
  --location=global \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --location=global \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${REPOSITORY}'"

gcloud iam service-accounts add-iam-policy-binding "${DEPLOY_SA}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPOSITORY}"

export WIF_PROVIDER="$(gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --location=global \
  --workload-identity-pool="${POOL_ID}" \
  --format='value(name)')"

gh variable set WIF_PROVIDER --repo "${REPOSITORY}" --body "${WIF_PROVIDER}"
gh variable set WIF_SERVICE_ACCOUNT --repo "${REPOSITORY}" --body "${DEPLOY_SA}"
```

`WIF_PROVIDER` は `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/.../providers/...` 形式の値にする。GitHub CLIを使わない場合は、GitHubの **Settings → Secrets and variables → Actions → Variables** で同名のRepository variableを登録する。

## 4. 初回デプロイ確認

GitHubの **Actions → CI/CD to Cloud Run → Run workflow** から手動実行し、`check` と `deploy` が成功することを確認する。その後、次のコマンドで新しいリビジョンとURLを確認する。

```bash
gcloud run revisions list \
  --service=yui-agent \
  --region="${REGION}" \
  --project="${PROJECT_ID}"

gcloud run services describe yui-agent \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)'
```

`main` または `master` に小さな変更をpushし、pushイベントでも同じworkflowが起動することを確認する。

## 5. Cloud Schedulerの再現

Scheduler専用サービスアカウントから認証付きで `/autonomous-review` を30分ごとに呼ぶ。既に同名ジョブがある場合は `create` ではなく `gcloud scheduler jobs update http` を使う。

```bash
export SCHEDULER_SA_NAME=yui-scheduler
export SCHEDULER_SA="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export SERVICE_URL="$(gcloud run services describe yui-agent \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)')"

gcloud iam service-accounts create "${SCHEDULER_SA_NAME}" \
  --display-name="Yui Cloud Scheduler"

gcloud run services add-iam-policy-binding yui-agent \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${SCHEDULER_SA}" \
  --role="roles/run.invoker"

gcloud scheduler jobs create http yui-autonomous-review \
  --location="${REGION}" \
  --schedule="*/30 * * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="${SERVICE_URL}/autonomous-review" \
  --http-method=POST \
  --oidc-service-account-email="${SCHEDULER_SA}" \
  --oidc-token-audience="${SERVICE_URL}"

gcloud scheduler jobs run yui-autonomous-review --location="${REGION}"
```

現在のworkflowは既存運用との互換性のため `--allow-unauthenticated` を指定している。SchedulerはOIDCを使うため、他の公開エンドポイントへの影響を確認できた段階でCloud Run全体の未認証アクセスを外すことを推奨する。

## 6. CalendarスコープのOAuth再同意

Calendar連携の初回だけ、Google Tasksが動作していることを確認してからローカルで再同意する。この操作とSecret Manager更新は自動化せず、ユーザー本人が実行する。

```bash
# 更新前のバージョンを確認する（トークン値そのものは表示しない）
gcloud secrets versions list google-tasks-refresh-token \
  --project=yui-agent-2026

# ローカルでブラウザ認証し、Tasks + Calendar readonlyのrefresh tokenを
# google-tasks-refresh-tokenの新バージョンとして保存する
python scripts/setup_google_tasks_auth.py

# 新バージョンが追加されたことを確認する
gcloud secrets versions list google-tasks-refresh-token \
  --project=yui-agent-2026
```

`tasks_client.py` は認証情報をプロセス内でキャッシュするため、トークン更新後はGitHub Actionsの `workflow_dispatch` を実行して新しいCloud Runリビジョンへ切り替える。切り替え後、会話で今日の予定を確認し、通常の発言からGoogle Tasksへの登録も再確認する。

新しいトークンで問題が起きた場合は、更新前のバージョン番号を指定して旧トークンを新バージョンとして再登録し、もう一度デプロイする。

```bash
export PREVIOUS_VERSION=1  # 更新前に確認した有効なバージョン番号
gcloud secrets versions access "${PREVIOUS_VERSION}" \
  --secret=google-tasks-refresh-token \
  --project=yui-agent-2026 \
  --out-file=google-tasks-refresh-token.rollback

gcloud secrets versions add google-tasks-refresh-token \
  --project=yui-agent-2026 \
  --data-file=google-tasks-refresh-token.rollback

rm google-tasks-refresh-token.rollback
```

## 7. `master` から `main` への移行

workflowは移行前後の両ブランチに対応している。履歴を保ったまま次の順で移行する。

```bash
git switch master
git pull --ff-only origin master
git branch main
git push -u origin main
```

1. GitHubの **Settings → Branches** で必要なbranch protectionを `main` に設定する。
2. **Settings → General → Default branch** で既定ブランチを `main` に変更する。
3. ActionsとCloud Runのデプロイ成功を確認する。
4. ローカルを `main` に切り替え、不要になった後だけ `master` を削除する。

```bash
git switch main
# 十分に確認した後だけ実行する
git push origin --delete master
```

移行完了後にworkflowの `master` トリガーを削除するかは任意。ハッカソン提出中は復旧経路として残してよい。
