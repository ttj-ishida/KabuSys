# KabuSys — 日本株自動売買基盤 (README)

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ・自動売買基盤です。  
主に以下を提供します。

- J-Quants API からの市場データ（OHLCV / 財務 / カレンダー）取得と DuckDB への保存（冪等）
- RSS ニュース収集と記事 → 銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL パイプライン（差分更新 / バックフィル / カレンダー同期）
- ファクター（モメンタム / バリュー / ボラティリティ）計算・特徴量ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ用スキーマ）
- 設定管理（.env 自動読み込み、環境変数）

このリポジトリはライブラリ形式で設計されており、研究（research）、データ（data）、戦略（strategy）、発注（execution）、監視（monitoring）モジュールなどに分かれています。

主な機能
--------
- data.jquants_client
  - J-Quants API への安全な HTTP クライアント（レートリミット制御、リトライ、トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB に冪等保存する save_* 関数
- data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
  - init_schema(), get_connection()
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- data.news_collector
  - RSS 取得（gzip 対応）・前処理・記事ID生成（正規化 URL の SHA-256）・DB 保存
  - SSRF 対策、レスポンスサイズ制限、XML の安全パース（defusedxml）
  - run_news_collection により複数ソースの一括収集・銘柄紐付け
- data.quality
  - 欠損・スパイク・重複・日付不整合を検出するチェック群と QualityIssue 型
  - run_all_checks でまとめて実行
- data.stats / data.features
  - zscore_normalize: クロスセクションでの Z スコア正規化
- research.*
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - DuckDB テーブル（prices_daily / raw_financials）を用いたローカル処理（外部 API を呼ばない設計）
- config
  - .env 自動読み込み（プロジェクトルートに基づく .env/.env.local）
  - 必須環境変数のラップ（settings オブジェクト）：JQUANTS_REFRESH_TOKEN 等

セットアップ手順
----------------

前提
- Python 3.10 以上（アノテーションに | 演算子を使用）
- 仮想環境を推奨（venv / poetry 等）

1. リポジトリを取得して開発環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで配布される requirements があればそれに従ってください）
   - 開発モードでインストールする場合:
     - pip install -e .

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と（任意で） `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

必須の主な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注モジュール利用時）
- SLACK_BOT_TOKEN: Slack 通知用トークン（任意だが監視連携に必要）
- SLACK_CHANNEL_ID: Slack チャンネル ID

データベースパスなど（任意デフォルト）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視データ用 SQLite（デフォルト: data/monitoring.db）

また以下の設定をサポート
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

使い方（コード例）
-----------------

以下は最小限の利用例です。適宜ログ設定や例外処理を追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は記事から抽出する有効な銘柄コード集合（例: prices_daily の code 一覧）
known_codes = {"7203", "6758", "9984"}  # 実運用では全銘柄を読み込んで渡す
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

4) ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2024, 1, 15))
# factors は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} を含む dict のリスト
```

5) Z スコア正規化（クロスセクション）
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factors, ["mom_1m","mom_3m","ma200_dev"])
```

6) J-Quants から生データを直接取得して保存する（テスト／ツール用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection, init_schema
from datetime import date

conn = init_schema(":memory:")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = save_daily_quotes(conn, records)
print(saved)
```

注意点・設計方針
----------------
- DuckDB を中心にデータレイヤーを構築しており、ほとんどの処理は SQL（および一部 Python）で完結します。
- J-Quants クライアントはレート制限（120 req/min）を守る設計です。大量取得時は注意してください。
- ETL は差分更新を基本とし、バックフィル（デフォルト3日）で API の後出し修正を吸収します。
- research モジュールは DuckDB の prices_daily / raw_financials のみ参照し、実際の発注や外部 API へはアクセスしません（研究用途で安全）。
- news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限など安全性を考慮して実装しています。
- config モジュールはプロジェクトルートの .env/.env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD が用意されています。

ディレクトリ構成
----------------
（主要なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / .env 自動読み込み / settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（fetch/save）
    - news_collector.py       # RSS 収集・前処理・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - pipeline.py             # ETL パイプライン
    - features.py             # 特徴量インターフェース（再エクスポート）
    - quality.py              # データ品質チェック
    - calendar_management.py  # 市場カレンダー管理 / 営業日判定 / バッチ更新
    - audit.py                # 監査ログスキーマ（signal/events/order/execution）
    - etl.py                  # ETL 結果型のエクスポート
  - research/
    - __init__.py
    - factor_research.py      # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  # 将来リターン計算 / IC / summary / rank
  - strategy/                  # 戦略関連（実装ファイルは別途）
  - execution/                 # 発注実装（証券会社連携）
  - monitoring/                # 監視・アラート（未実装のプレースホルダ）

補足: 環境変数サンプル (.env)
----------------------------
以下は例です（実際のトークン等は秘匿してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

ライセンス / 貢献
-----------------
（この README ではライセンス情報・貢献ルールは明示していません。必要に応じてリポジトリの LICENSE や CONTRIBUTING を参照してください。）

問い合わせ
----------
実運用・導入や拡張に関する質問があれば、コード内のドキュメントやロギングメッセージを参照してください。具体的なユースケースに応じた使い方サンプルが必要であれば、要件を教えてください。