# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ説明書です。  
この README はソースコード（src/kabusys 以下）に基づき、プロジェクト概要・機能・セットアップ・基本的な使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・品質チェック・監査（トレーサビリティ）・発注管理に必要な基盤機能を提供する Python モジュール群です。  
主に以下を目的としています。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・XML攻撃対策・重複排除）
- DuckDB を用いたスキーマ定義・初期化・ETL（冪等保存・トランザクション）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order → execution のトレーサビリティ）
- カレンダー管理・営業日判定ロジック

設計上、冪等性、セキュリティ（SSRF/Zip bomb/XML攻撃対策）、および運用での堅牢性を重視しています。

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得と検証（KABUSYS_ENV / LOG_LEVEL 等）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ、401時の自動トークン更新
  - DuckDB への冪等保存用 save_* 関数
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得／XML パース（defusedxml 利用）
  - URL 正規化、トラッキングパラメータ除去、記事IDの SHA-256 ベース生成
  - SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検査）
  - DuckDB への一括挿入（トランザクション／チャンク分割／ON CONFLICT DO NOTHING）
  - テキストから銘柄コード抽出（4桁コード）
- スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義（DuckDB）
  - インデックス作成、init_schema() による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）とバックフィル
  - run_daily_etl() による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、期間内営業日リスト生成
  - calendar_update_job による夜間差分更新
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査向けテーブル
  - init_audit_schema / init_audit_db による初期化（UTC 固定）
- 品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合の検出と QualityIssue の報告

---

## 必要条件 / 推奨環境

- Python 3.10 以上（ソース内で | 型や Path 型などを使用）
- 必要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

実際の運用では他にログ/監視（Slack 通知等）や証券会社 API のクレデンシャルが必要になります。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトの requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みは無効化されます）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB などに使う SQLite（デフォルト: data/monitoring.db）

   例 .env（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化
   - Python REPL またはスクリプトから schema.init_schema() を呼び出して DuckDB スキーマを作成します（親ディレクトリは自動作成されます）。

---

## 基本的な使い方（例）

以下は最小限のサンプルコード例です（対話的実行 / スクリプト内で使用）。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログスキーマを追加（必要な場合）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

3) 日次 ETL の実行（J-Quants のトークンは環境変数から取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効銘柄コードのセット（省略可能）
known_codes = {"7203", "6758", "9984"}  # 例
summary = run_news_collection(conn, known_codes=known_codes)
print(summary)  # {source_name: 新規保存数, ...}
```

5) カレンダー差分更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

6) J-Quants API を直接呼ぶ（必要に応じて）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # 環境変数の refresh token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
```

注意点:
- run_daily_etl 等は各ステップで例外ハンドリングを行い、可能な限り処理を継続する設計です。戻り値の ETLResult からエラーや品質問題を確認してください。
- ニュース収集は defusedxml を用いて XML 攻撃を防ぎ、SSRF 対策も組み込まれています。外部 URL を扱う際はネットワークポリシーに注意してください。

---

## 環境変数の自動読み込み仕様

- プロジェクトルートは __file__ を起点に親ディレクトリをさかのぼり `.git` または `pyproject.toml` を探すことで判定します。これにより CWD に依存せずパッケージ配布後も機能します。
- 自動読み込み順:
  1. OS 環境変数（優先）
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば読み込み）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数と設定管理
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch/save）
  - news_collector.py            — RSS ニュース収集と保存
  - schema.py                    — DuckDB スキーマ定義・初期化
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py       — マーケットカレンダー管理（営業日判定等）
  - audit.py                     — 監査ログ（signal/order/execution）
  - quality.py                   — データ品質チェック
- strategy/
  - __init__.py                   — 戦略関連（拡張ポイント）
- execution/
  - __init__.py                   — 発注実行関連（拡張ポイント）
- monitoring/
  - __init__.py                   — 監視関連（拡張ポイント）

（上記以外の補助モジュールは data 以下に配置されています。）

---

## 運用上の注意点

- J-Quants API: レート制限（120 req/min）や 401 トークン期限切れへの対応を組み込んでいますが、運用時はより細かいレート制御やエラーハンドリングを追加する必要がある場合があります。
- DuckDB: 大規模データや同時アクセスの要件がある場合、ファイルロックや接続ポリシーに注意してください。
- セキュリティ: RSS の外部フェッチや外部 API 呼び出しは SSRF / XML / 圧縮爆弾対策を組み込んでいますが、社内ネットワークポリシー・プロキシ等の環境に合わせて設定してください。
- テスト: モジュール内ではネットワーク呼び出し箇所を差し替えやすい設計（id_token 注入、_urlopen の差し替え）にしています。単体テストではこれらをモックして実行してください。

---

## 今後の拡張案（参考）

- strategy / execution 層の実装（ポートフォリオ最適化、リスク管理、ブローカー連携）
- Slack 等への通知ラッパー実装（kabusys.monitoring）
- 定期実行用の CLI / systemd / Airflow 等の統合
- メトリクス収集（Prometheus 等）や監査レポート出力

---

この README はリポジトリ内のソース（src/kabusys）を参照して作成しています。実際に運用する場合は運用ポリシーや外部秘密情報の取り扱いに従って導入してください。質問や追加のドキュメント化（CLI、デプロイ、運用手順など）を希望される場合はお知らせください。