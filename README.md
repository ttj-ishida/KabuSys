# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォーム向けライブラリです。J-Quants API からデータを取得して DuckDB に保存し、ファクター計算（research）、特徴量生成（feature layer）、シグナル生成（strategy）、ニュース収集などの一連処理を提供します。発注・実行（execution）や監査（audit）を想定したスキーマも含まれます。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要な環境変数
- セットアップ手順
- 使い方（簡易サンプル）
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

本パッケージは次のレイヤーを想定しています。

- Raw Layer: J-Quants 等から取得した生データ（raw_prices, raw_financials, raw_news 等）
- Processed Layer: 整形済み市場データ（prices_daily, fundamentals, market_calendar 等）
- Feature Layer: 戦略/AI 用の特徴量（features, ai_scores 等）
- Execution Layer: シグナル→発注→約定→ポジション管理用テーブル（signals, orders, trades, positions 等）
- Research: ファクター計算 / 特徴量探索ユーティリティ（ルックアヘッドバイアス対策を含む）
- Data Pipeline: 差分ETL、カレンダー更新、品質チェック
- News: RSS 収集と銘柄紐付け（SSRF 対策、サイズ制限、XML 攻撃対策）

設計における主な方針:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- DuckDB を永続ストレージとして想定（:memory: も使用可能）
- 冪等性（ON CONFLICT / INSERT ... DO UPDATE / トランザクション）
- 外部 API 操作は jquants_client に集約（レート制御・リトライ・トークン自動更新）
- ニュース収集で SSRF や XML 脆弱性に配慮

---

## 主な機能一覧

- 環境設定自動読み込み（.env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- DuckDB スキーマ定義と初期化: kabusys.data.schema.init_schema()
- J-Quants クライアント: データ取得（株価、財務、マーケットカレンダー）、保存ユーティリティ（save_*）
  - レート制限、リトライ、トークン自動更新を実装
- ETL パイプライン: 差分取得 & 保存 & 品質チェック（run_daily_etl() など）
- ファクター計算（research/factor_research.py）
  - Momentum / Volatility / Value 等
- 特徴量構築（strategy/feature_engineering.build_features）
  - ユニバースフィルタ（最低株価・売買代金）、Zスコア正規化、日付単位の UPSERT
- シグナル生成（strategy/signal_generator.generate_signals）
  - ファクター＋AI スコア統合、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの書き込み
- ニュース収集（data/news_collector.run_news_collection）
  - RSS 取得、前処理、raw_news 保存、銘柄コード抽出・紐付け
- カレンダー管理（data/calendar_management）: 営業日判定/次・前営業日取得、カレンダー更新ジョブ
- 統計ユーティリティ（data/stats.zscore_normalize）
- 監査ログスキーマ（data/audit） — signal → order → execution のトレース用テーブル群

---

## 必要な環境変数

少なくとも次の環境変数を設定してください（プロジェクトルートの .env または OS 環境）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注を行う場合）
- SLACK_BOT_TOKEN — Slack 通知用（必要なら）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB など）（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

.env の自動読み込みは、.git または pyproject.toml をプロジェクトルートとして検出した上で行われます。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env.example):
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. Python バージョン
   - Python 3.10+ を推奨（型ヒントに | None 等を使用しているため）

2. 仮想環境の作成とアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 主要依存: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml

   （パッケージ管理用ファイル requirements.txt / pyproject.toml がある場合はそちらを利用してください。）

4. リポジトリのインストール（開発モード）
   - プロジェクトルートで:
     - pip install -e .

   （editable install が不要なら通常の pip install .）

5. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境に設定してください。
   - 自動読み込みが動作している場合はプロジェクトルートの .env/.env.local が読み込まれます。

6. DuckDB スキーマ初期化
   - 以下のサンプルに従って DB を初期化します（初回のみ）:

例:
from kabusys.data.schema import init_schema
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)

---

## 使い方（簡易サンプル）

以下は代表的な操作例です。実運用ではエラーハンドリング・ロギング・スケジューリングが必要です。

1) DuckDB 初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（株価/財務/カレンダーの差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", n)
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
results = run_news_collection(conn)
print("news collection:", results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("market calendar saved:", saved)
```

注意:
- 上記は最小限の例です。実際の運用では logging 設定やスケジューラ（cron / Airflow など）を導入してください。
- J-Quants API 呼び出しにはレート制限（120 req/min）やトークン処理があるため大量同時実行は避けてください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py (バージョン: 0.1.0)
- config.py — 環境変数 / .env 読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py — ETL パイプライン & run_daily_etl()
  - schema.py — DuckDB スキーマ定義と init_schema()
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — features エクスポート（zscore_normalize の再エクスポート）
  - news_collector.py — RSS 取得、前処理、raw_news 保存、銘柄抽出
  - calendar_management.py — market_calendar の管理 / 営業日ユーティリティ
  - audit.py — 監査ログ用スキーマ定義（signal_events, order_requests, executions 等）
  - (その他: quality モジュール想定)
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value 等のファクター計算
  - feature_exploration.py — forward return / IC / factor summary
- strategy/
  - __init__.py
  - feature_engineering.py — features の構築（Zスコア正規化・フィルタ）
  - signal_generator.py — final_score 計算・BUY/SELL 判定・signals 書き込み
- execution/
  - __init__.py (発注層は別途実装想定)
- monitoring/ (監視用モジュール想定)

---

## 注意事項 / 運用メモ

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から検索されます。テスト時や CI で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパス（settings.duckdb_path）はデフォルトで data/kabusys.duckdb です。必要に応じて絶対パスや :memory: を使用してください。
- J-Quants API 利用時は利用規約とレート制約を遵守してください。jquants_client はレート制限とリトライの基本を実装していますが、大量のリクエストや並列実行は注意が必要です。
- ニュース収集は XML や外部 URL の扱いに注意（defusedxml 、SSRF 対策を実装済み）。ただし運用環境での追加検査や監視を推奨します。
- 現在のコードベースはスキーマ/処理ロジックを提供しますが、ブローカー API との実際の発注連携・安全な本番運用のためのリスク管理（ポジションサイズ制約、再試行ポリシー、監査プロセス等）は利用者側での追加実装が必要です。

---

問題や追加ドキュメント（詳細な DataSchema.md / StrategyModel.md / DataPlatform.md 等）が必要であれば、その箇所を指定してください。README を特定の用途（開発者向け、運用者向け、デプロイ手順）に合わせて拡張できます。