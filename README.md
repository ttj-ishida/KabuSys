# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株のデータ収集（J-Quants）、特徴量計算、シグナル生成、ETL および監査用スキーマを備えた自動売買用ライブラリ群です。DuckDB をデータレイクとして利用し、研究（research）→データ（data）→戦略（strategy）→発注（execution）といった層を分離した設計を採用しています。

主な特徴
---
- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、リトライ／レートリミット対応）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（市場カレンダー、株価、財務データの差分更新・品質チェック）
- ニュース収集（RSS、SSRF 対策、テキスト前処理、銘柄抽出）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量構築（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数ファクターの加重合成、Bear レジーム対応、エグジット判定）
- 監査ログ用スキーマ（シグナル→発注→約定のトレースを保証）

前提・必要環境
---
- Python 3.10+
  - コード内で PEP 604（X | Y）などの構文を使用しています。
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- J-Quants のリフレッシュトークン、kabu API 等の外部サービスの認証情報

簡易インストール例
---
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存インストール
   - pip install duckdb defusedxml

3. ソースを editable インストール（任意）
   - pip install -e .

環境変数 / .env
---
KabuSys は .env/.env.local または OS 環境変数から設定を読み込みます（自動読み込み順: OS 環境 > .env.local > .env）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須項目は README 内に記載）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ手順（データベース初期化）
---
1. DuckDB データベースの初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB を使用します。

2. （必要に応じて）SQLite などの外部 DB の設定ファイル準備

基本的な使い方（コード例）
---

1) 日次 ETL を実行して市場カレンダー・株価・財務データを取得する
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の構築（build_features）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {count}")
```

3) シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {total}")
```

4) ニュース収集ジョブ（RSS 収集と保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

モジュールと主要 API（概要）
---
- kabusys.config
  - settings: 環境変数ラッパー（settings.jquants_refresh_token など）
- kabusys.data
  - jquants_client: J-Quants への HTTP クライアント／保存関数（fetch_*, save_*）
  - news_collector: RSS 取得・解析・DB 保存（fetch_rss / save_raw_news / run_news_collection）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - calendar_management: 営業日判定・カレンダー更新ジョブ（is_trading_day / next_trading_day / calendar_update_job）
  - stats: zscore_normalize などの統計ユーティリティ
  - features: zscore_normalize の再エクスポート
  - audit: 監査ログ用スキーマ初期化ロジック
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - feature_engineering.build_features: ファクター統合と features テーブル UPSERT
  - signal_generator.generate_signals: final_score 計算・BUY/SELL 生成・signals テーブル UPSERT
- kabusys.execution, kabusys.monitoring
  - （コードベースに準備されたパッケージ、発注層や監視機能の実装を想定）

ディレクトリ構成（主要ファイル）
---
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      audit.py
      stats.py
      features.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      (監視関連モジュールを配置)

補足・運用上の注意
---
- 環境変数の管理は慎重に（API トークンやパスワードは秘匿してください）。
- J-Quants の API レート制限（デフォルト 120 req/min）に合わせた実装済みですが、大量バッチを組む場合は追加のレート管理を検討してください。
- DuckDB のスキーマは冪等に作成されますが、スキーマ変更は注意して実施してください。
- run_daily_etl は品質チェックを行い、問題があっても処理を継続する設計です。結果の ETLResult を確認し、必要に応じてアラート／手動対応してください。
- production（live）環境では KABUSYS_ENV=live を設定し、実運用に適したログ/通知/安全弁（発注前のリスクチェック等）を必ず組み込んでください。

開発・テスト
---
- 単体テストや CI を追加する場合は、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みを無効化し、テスト用の環境を明示的に注入してください。
- jquants_client のネットワーク関係関数はモックまたはローカルの録画済みレスポンスでテストすることを推奨します。

ライセンス・貢献
---
- 本リポジトリに LICENSE がない場合はプロジェクトルールに従って追加してください。コントリビューションは PR と issue を通じて行ってください。

お問い合わせ
---
実装の意図やモジュール間の設計方針（StrategyModel.md / DataPlatform.md 等の設計文書）に関する質問があれば README またはコード内の docstring を参照し、必要に応じて issue を作成してください。

以上。README の内容をプロジェクト要件に合わせて調整したい場合は、追加で欲しい項目（例: 実行スクリプト、cron 設定例、Docker イメージ化手順）を教えてください。