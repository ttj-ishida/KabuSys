# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
DuckDB をデータレイクとして用い、J-Quants API や RSS を取得してデータ整備→特徴量生成→シグナル作成までをサポートします。

## 主な特徴（概要）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
- DuckDB ベースのスキーマ定義・初期化
- 日次 ETL（株価・財務・市場カレンダー）の差分取得と品質チェック
- 研究向けファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け、BUY/SELL ルール）
- RSS ニュース収集と銘柄抽出（SSRF対策 / トラッキングパラメータ除去）
- 監査ログ（発注→約定のトレーサビリティ用DDL）
- 環境変数による設定管理（.env 自動ロード機構）

## 機能一覧（主要モジュール）
- kabusys.config
  - 環境変数の自動ロード（.env, .env.local）と Settings オブジェクト
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
- kabusys.data.schema
  - DuckDB のテーブル定義と init_schema(), get_connection()
- kabusys.data.pipeline
  - 日次 ETL 実行（run_daily_etl）や個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- kabusys.data.news_collector
  - RSS 取得（fetch_rss）・raw_news保存（save_raw_news）・銘柄紐付け（save_news_symbols）
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job など
- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 解析ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- kabusys.strategy
  - build_features（特徴量作成・features テーブルへの upsert）
  - generate_signals（features + ai_scores を統合して signals を生成）
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- kabusys.data.audit
  - 監査用テーブル定義（signal_events / order_requests / executions 等）

## 前提条件
- Python 3.10+
- 必要な外部ライブラリ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants / RSS 取得時）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージとして開発インストールする場合（プロジェクトに pyproject.toml 等がある想定）
pip install -e .
```

## 環境変数（主なキー）
このプロジェクトは .env を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須 / 主要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視系で使用する sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL : ログレベル (DEBUG/INFO/...)（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. .env を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
# これで必要なテーブルがすべて作成されます
conn.close()
```

## 使い方（主要なワークフロー例）

- 日次 ETL を実行してデータを取得・保存・品質チェックする:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量を作成（features テーブルの生成）:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"build_features: {n} 銘柄")
conn.close()
```

- シグナルを生成（signals テーブルへ書き込み）:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generate_signals: {count} シグナル")
conn.close()
```

- RSS ニュース収集ジョブの実行:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- J-Quants から手動でデータ取得して保存:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

conn = init_schema(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
conn.close()
```

## 注意事項 / 運用上のヒント
- KABUSYS_ENV を `live` にすると本番向けの判定がオンになります（安全対策や発注フローを組む際は注意してください）。
- .env 自動ロードはプロジェクトルートを .git または pyproject.toml で探索して行います。テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API はレートリミットがあります（120 req/min）。jquants_client は内部でレート制御とリトライを実装していますが、運用バッチの同時実行に注意してください。
- news_collector は SSRF 対策や応答サイズ制限を実装していますが、追加のフィードソース導入時は検証してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に配置されます。バックアップ運用や共有/ロック設計は環境に応じて検討してください。

## ディレクトリ構成
（主要ファイルのみ抜粋）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ execution/
   │  └─ __init__.py
   ├─ monitoring/            # 監視・アラート系（将来的な実装領域）
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ pipeline.py
   │  ├─ schema.py
   │  ├─ stats.py
   │  ├─ features.py
   │  ├─ calendar_management.py
   │  └─ audit.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   └─ strategy/
      ├─ __init__.py
      ├─ feature_engineering.py
      └─ signal_generator.py
```

## 開発・拡張ポイント
- execution 層（実際の発注ブローカー連携）はまだ薄く、ここに各証券会社 API のアダプタを差し込む想定です。
- AI スコアの生成システム（ai_scores テーブルに格納）を外部サービスと連携するとニュースや NLP に基づくスコアを組み込めます。
- 品質チェック（quality モジュール）を強化して ETL の監査とアラートルールを充実させるのが推奨です。
- パフォーマンス要件に応じて DuckDB のクエリ最適化やインデックス設計を調整してください。

---

問題や実装に関するご質問、README の追加項目（例: API リファレンスや CLI の使い方）を作成したい場合は教えてください。必要に応じてサンプルスクリプトや運用手順書も用意します。