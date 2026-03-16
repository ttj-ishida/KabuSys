# KabuSys — 日本株自動売買システム

軽量なデータプラットフォームと ETL、監査ログ基盤を備えた日本株自動売買用ライブラリです。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存し、品質チェック・監査ログ・実行レイヤにデータを供給します。

主な設計方針:
- API レート制限とリトライを備えた安全なデータ取得
- DuckDB を用いた冪等的な保存（ON CONFLICT DO UPDATE）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注フローの監査ログをトレーサブルに保存（UUID 連鎖）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RateLimiter による 120 req/min 制限順守
  - リトライ（指数バックオフ、最大 3 回）および 401 時のトークン自動リフレッシュ
  - ページネーション対応
  - DuckDB への保存関数（save_*）は冪等性を担保

- data/schema.py
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution 層）定義と初期化
  - 推奨インデックスの作成

- data/pipeline.py
  - 日次差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分算出、バックフィル（デフォルト 3 日）対応
  - ETL の結果を ETLResult で集約

- data/quality.py
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合のチェック
  - QualityIssue を返し呼び出し側が対応を判断できる設計

- data/audit.py
  - シグナル → 発注 → 約定までを追跡する監査テーブル定義
  - order_request_id を冪等キーとして二重発注防止

- config.py
  - .env ファイル（プロジェクトルートの .env/.env.local）または環境変数から設定を読み込み
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う
  - 必須設定の取り出し、環境種別判定（development / paper_trading / live）

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型 | を使用）
- ネットワーク接続（J-Quants API 等）

1. リポジトリをクローンし、仮想環境を作成・有効化します（例: venv / poetry 等）。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストールします（例: duckdb）。
   - pip install duckdb

   （プロジェクトに requirements ファイルがある場合はそちらを利用してください。パッケージ化している場合は `pip install -e .`）

3. 環境変数を設定します。
   - プロジェクトルートに `.env`（および機密用に `.env.local` を .gitignore）を作成すると自動で読み込まれます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限これらを設定してください）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ID トークン取得に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション:
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（コード例）

基本的な DB 初期化と日次 ETL の実行サンプル。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) 監査ログテーブルの初期化（既存接続へ追加）
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
```

3) 日次 ETL 実行
```python
from kabusys.data import pipeline
from datetime import date

# conn は init_schema の戻り値
result = pipeline.run_daily_etl(conn, target_date=date.today())

# ETL 結果確認
print(result.to_dict())
```

4) 低レベル API の利用例
```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# 取得だけ
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# 保存
jq.save_daily_quotes(conn, records)
```

5) 品質チェックを個別に実行する例
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- J-Quants へのリクエストは内部でレート制限・リトライを行います。
- トークンの自動リフレッシュは 401 の場合に 1 回のみ行われます。
- save_* 系関数は冪等設計です（ON CONFLICT DO UPDATE）。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要なファイル・モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - quality.py             — 品質チェック
    - audit.py               — 監査ログテーブル
    - pipeline.py
  - strategy/
    - __init__.py            — 戦略関連モジュール（未実装／拡張領域）
  - execution/
    - __init__.py            — 発注実行関連（未実装／拡張領域）
  - monitoring/
    - __init__.py            — 監視・アラート用モジュール（拡張領域）

スキーマの概要
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_performance
- 監査: signal_events, order_requests, executions

---

## 運用・開発時の補足

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込みます。
  - .env.local は .env の上書き（override）を行います（既存 OS 環境変数は保護）。
  - テスト時などに自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- ロギング
  - 設定は LOG_LEVEL 環境変数で制御できます。デフォルトは INFO。

- DB 初期化
  - init_schema() は冪等です。既存テーブルがあればスキップされます。
  - init_audit_schema() は既存接続に監査テーブルを追加します（UTC タイムゾーンを強制）。

- テスト容易性
  - jquants_client の関数は id_token を注入できるため、テストでモックトークンを使えます。
  - DuckDB はインメモリ ":memory:" が使えるためユニットテスト環境への導入が容易です。

---

## 今後の拡張案（参考）

- strategy 層の具体的な実装（シグナル生成・リスク管理）
- execution 層の証券会社 API 統合（kabuステーションとの注文送信／受信）
- monitoring 層に Slack/Prometheus 連携
- CI ワークフローでの DB マイグレーション・品質レポート出力

---

ご不明点や README に追記したい項目があれば教えてください。README のセクション追加やインストール手順の環境別（Docker / systemd / cron）サンプルも作成できます。