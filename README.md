# KabuSys

日本株向けの自動売買基盤コンポーネント群（ライブラリ）。  
データ取得 / ETL / スキーマ定義 / 品質チェック / 監査ログなど、取引システムの基盤部分を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けの基盤ライブラリです。  
主に以下を提供します。

- J-Quants API からのデータ取得クライアント（株価日足、四半期財務、JPX カレンダー）
  - レート制限（120 req/min）の遵守
  - 再試行（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻 (fetched_at) を UTC で記録して Look-ahead Bias を回避
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、保存、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 環境変数 / .env の読み込みユーティリティ（自動読み込み機能あり）

戦略（strategy）や実行（execution）、監視（monitoring）用のモジュールの枠組みも用意されています（実装は分割可能）。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - レートリミッタ / リトライ / 自動トークン更新

- data.schema
  - DuckDB 上のテーブル定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) によるスキーマ初期化（冪等）

- data.pipeline
  - run_daily_etl(...)：カレンダー → 株価 → 財務 → 品質チェック の一括 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL ジョブ）
  - 差分更新とバックフィルの自動計算

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks による一括チェック（QualityIssue の一覧を返す）

- data.audit
  - 監査用テーブル定義（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db による初期化

- config
  - .env または OS 環境変数からの設定読み込み
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
  - 必須設定の検証（足りないと例外を投げる）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化

---

## セットアップ手順

前提:
- Python 3.10 以降（コードは型注釈や union 型を使用）
- 必要パッケージ（例）:
  - duckdb
  - （標準ライブラリのみで動く部分が多いですが、実運用ではログ送信や Slack 連携用のライブラリ等が別途必要です）

例: 仮想環境を作成し必要なパッケージをインストールする手順

1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）

3. パッケージとしてインストール（開発モード）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例 .env（テンプレート）
    JQUANTS_REFRESH_TOKEN=your_refresh_token
    KABU_API_PASSWORD=your_kabu_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

必須の環境変数（config.Settings でチェックされる）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

---

## 使い方（基本例）

以下は Python REPL またはスクリプトでの簡単な例です。

1) DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行
```python
from kabusys.data import pipeline
from kabusys.data import schema

# 既に init_schema で作成済みなら get_connection を使ってもよい
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

3) 監査テーブルの初期化（監査専用あるいは既存 DB に追加）
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
# または専用 DB を作る場合:
# conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

4) J-Quants の個別データ取得
```python
from kabusys.data import jquants_client as jq
# トークンは Settings から自動取得される（環境変数必須）
quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

注意事項:
- run_daily_etl は内部で市場カレンダーを先に取得し、営業日に調整してから株価/財務の差分取得を行います。
- J-Quants API のレート制限（120 req/min）に合わせて内部でスロットリングしています。
- 取得したデータは DuckDB に対して ON CONFLICT DO UPDATE な形式で保存され、冪等性を保ちます。

---

## API と動作上のポイント

- 環境変数自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動読み込み（OS 環境変数優先）。
  - 上書き挙動: OS 環境 > .env.local > .env（.env.local は上書き可）
  - テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化可能。

- J-Quants クライアント
  - _RateLimiter により最小インターバルを確保（_MIN_INTERVAL_SEC = 60 / 120）
  - リトライ: 最大 3 回、429 は Retry-After ヘッダ優先、その他 408/5xx は指数バックオフ
  - 401 はトークンを自動リフレッシュして 1 回だけリトライ

- ETL
  - 差分更新を行い、既存データに対してはバックフィル日数分（デフォルト 3 日）を再取得して API の後出し修正を吸収
  - 市場カレンダーは lookahead（デフォルト 90 日）で先読みして営業日の判定に使用

- 品質チェック
  - 各種チェックは失敗時も例外を投げず QualityIssue を返す（Fail-Fast ではなく全件収集）
  - ETL の最終レポートに品質問題を含められる

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                - 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      - J-Quants API クライアント & 保存ロジック
      - schema.py              - DuckDB スキーマ定義と初期化
      - pipeline.py            - ETL パイプライン
      - audit.py               - 監査ログ（トレーサビリティ）
      - quality.py             - データ品質チェック
    - strategy/
      - __init__.py            - 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py            - 発注/ブローカ接続周りの拡張ポイント
    - monitoring/
      - __init__.py            - 監視・メトリクス用の拡張ポイント

---

## 開発・運用のヒント

- DuckDB はローカル実行・解析に便利ですが、運用環境ではバックアップや永続化設計を検討してください。
- J-Quants の API レート制限や利用規約に従ってください。
- KABUSYS_ENV を `live` に設定すると実運用モードを表現できます。実際の発注実装を組み合わせる際は細心の注意を。
- ETL の品質チェックで "error" レベルが検出された場合は、手動確認や自動アラートのトリガーを検討してください（例: Slack 通知）。

---

必要であれば、README に以下を追記できます:
- requirements.txt / pyproject.toml のテンプレート
- CI / CD 用のスクリプト例（ETL の定期実行、監査 DB のバックアップ）
- 実際の発注フロー（kabu ステーション API 連携例）
- 詳細な DataSchema.md / DataPlatform.md へのリンク（設計ドキュメント）