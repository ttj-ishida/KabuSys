# KabuSys

KabuSys は日本株の自動売買システム向けのライブラリ群です。  
データ取得（J-Quants API）、ETL、DuckDB スキーマ、データ品質チェック、監査ログ、設定管理など、取引システムの土台となるコンポーネントを提供します。

バージョン: 0.1.0

---

## 主な特徴（概要）

- J-Quants API クライアント
  - 株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止
- DuckDB ベースの 3 層データモデル
  - Raw / Processed / Feature / Execution（監査含む）テーブル定義とインデックス
  - 冪等性を考慮した保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新、backfill、カレンダー先読み、品質チェックを一括実行
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付整合性チェック
  - 問題は全件収集（Fail-Fast ではなく呼び出し元で判断可能）
- 監査ログ（signal → order → executions のトレーサビリティ）
  - UUID による連鎖、冪等キー、UTC タイムスタンプ
- 環境変数管理
  - .env / .env.local の自動ロード（プロジェクトルートを検出）
  - 必須設定は settings オブジェクト経由で取得

---

## 機能一覧

- kabusys.config
  - 環境変数の自動ロード（.env/.env.local）、必須キー取得（Settings）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ保存）
- kabusys.data.schema
  - DuckDB テーブル定義（raw, processed, feature, execution）
  - init_schema / get_connection
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（ETL の統合）
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.audit
  - 監査用テーブル作成（init_audit_schema / init_audit_db）
- その他の名前空間: strategy, execution, monitoring（拡張用プレースホルダ）

---

## セットアップ手順

1. Python（3.9+ 推奨）を用意します。

2. 仮想環境を作成・有効化（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt があればそれを使ってください。最低限必要なのは duckdb です。
   ```
   pip install duckdb
   ```
   - 開発インストール（パッケージが pyproject/セットアップを持つ場合）
   ```
   pip install -e .
   ```

4. 環境変数を準備する
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用可）。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（基本的な例）

以下はライブラリを直接呼び出す簡単なサンプルです。

- DuckDB スキーマの初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査ログテーブルの追加
```python
from kabusys.data import audit
# 既存の conn（schema.init_schema の返り値）に監査テーブルを追加
audit.init_audit_schema(conn)
```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡さなければ今日が対象
print(result.to_dict())
```

- 品質チェックのみを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- J-Quants トークン取得（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照して取得
```

- settings の利用例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- jquants_client は内部でレート制限・リトライを行い、401 時にはトークン自動更新を試みます。
- ETL は差分更新を行います。最終取得日から backfill 日数分（デフォルト 3 日）を遡って再取得することで API の後出し修正に対応します。
- run_daily_etl の結果（ETLResult）には品質問題やエラーメッセージが含まれます。呼び出し元で適切にハンドリングしてください。

---

## ディレクトリ構成

リポジトリ内の主要なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得 & 保存）
      - schema.py                    -- DuckDB スキーマ定義 & init_schema
      - pipeline.py                  -- ETL パイプライン（差分更新 / run_daily_etl）
      - audit.py                     -- 監査ログ（signal / order_requests / executions）
      - quality.py                   -- データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py                   -- 戦略用プレースホルダ
    - execution/
      - __init__.py                   -- 発注/ブローカ連携用プレースホルダ
    - monitoring/
      - __init__.py                   -- 監視機能プレースホルダ

主なテーブル（schema.py）
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査用（audit.py）: signal_events, order_requests, executions

---

## 実運用に関する注意

- 環境（KABUSYS_ENV）:
  - development / paper_trading / live のいずれかを指定してください。live の場合は実発注等の処理を有効化するなど追加の安全対策が必要になります。
- ログ・監視:
  - LOG_LEVEL により出力レベルを制御できます。
- 安全性:
  - 秘密情報（API トークン等）は .env やシークレットマネージャで安全に管理してください。
- テスト:
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテストや CI で便利です）。

---

## 貢献・拡張

- strategy / execution / monitoring モジュールは拡張ポイントです。戦略実装やブローカー連携はこれらに追加していく想定です。
- 新しいデータソースや品質チェック、監査項目を追加する際は既存のスキーマ整合性と冪等性ルール（ON CONFLICT, UUID によるトレーサビリティ）を守ってください。

---

必要であれば README に実行スクリプト例（cron/airflow ジョブ）、CI 用のセットアップ、依存関係一覧（requirements.txt）なども追加できます。追加希望があれば教えてください。