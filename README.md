# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（開発初期版）

バージョン: 0.1.0

概要
- KabuSys は日本株のデータ取得・ETL・品質チェック・特徴量計算・監査ログ基盤を提供する Python パッケージです。
- J-Quants API など外部データソースから株価・財務・市場カレンダー・ニュースを取得して DuckDB に蓄積し、研究・戦略用の特徴量を作成できるように設計されています。
- 設計方針として「本番発注 API へは直接触れない」「冪等性」「Look‑ahead バイアス回避」「SSRF 等のセキュリティ対策」を重視しています。

主な機能
- 環境変数／.env 管理（自動ロード機能、必要変数チェック）
- J-Quants API クライアント（レートリミット・再試行・トークン自動更新を含む）
  - 日足（OHLCV）取得 / 財務データ取得 / 市場カレンダー取得
  - DuckDB への冪等保存（ON CONFLICT を利用）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェックを統合）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS → 前処理 → DuckDB 保存、SSRF / Gzip / XML 脆弱性対策あり）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリューなど）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログスキーマ（signal / order_request / executions 等のトレーサビリティ）

前提条件
- Python 3.10 以上（型ヒントの union 演算子 `|` を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージをパッケージ配布として扱う場合）pip install -e .

環境変数（必須・任意）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注等の連携がある場合）
  - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID: 通知先の Slack チャンネル ID
- 任意（デフォルト値あり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- .env 自動ロード
  - プロジェクトルートに .env / .env.local があれば読み込まれます。
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順（最小例）
1. DuckDB スキーマ初期化
   - Python スクリプト例:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る場合:
     ```
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```
2. 必要な環境変数を設定（.env に記述するのが簡単）

使い方（代表的な API・実行例）
- settings を参照（環境変数のラッパー）
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- データ取得と保存（J-Quants から株価を取得して保存）
  ```
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  jq.save_daily_quotes(conn, records)
  ```

- 日次 ETL 実行（pipeline）
  ```
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 対象銘柄一覧
  run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  ```

- 研究用ファクター計算例
  ```
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 2, 1)
  momentum = calc_momentum(conn, d)
  fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

注意点・運用メモ
- J-Quants API のレート制限（120 req/min）や再試行ロジックは jquants_client に組み込まれていますが、大規模パイプラインでは適切にトークン・スロットリングを監視してください。
- DuckDB のバージョン差分により一部 DDL の制限（ON DELETE CASCADE など）があるため、スキーマ初期化や削除時はアプリ側で整合性管理を行う設計です。
- ニュース収集は外部 RSS を取得するため、SSRF・gzip 大量展開・XML Bomb 等の対策を実装しています。テスト用に URL オープン関数をモック可能です。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py (バージョン情報)
  - config.py (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント & DuckDB 保存)
    - news_collector.py (RSS 収集・前処理・DB 保存)
    - schema.py (DuckDB スキーマ定義・初期化)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - pipeline.py (ETL パイプライン)
    - features.py (特徴量インターフェース)
    - calendar_management.py (市場カレンダー管理)
    - audit.py (監査ログスキーマ初期化)
    - etl.py (ETL 公開インターフェース)
    - quality.py (データ品質チェック)
  - research/
    - __init__.py
    - feature_exploration.py (将来リターン・IC・summary)
    - factor_research.py (モメンタム/ボラ/バリュー計算)
  - strategy/ (パッケージプレースホルダ)
  - execution/ (パッケージプレースホルダ)
  - monitoring/ (パッケージプレースホルダ)

今後の拡張例
- 発注実行部分（kabu ステーション連携）と戦略管理レイヤーの具現化
- 特徴量の増強（テキスト（ニュース）由来のセンチメント、AI スコア等）
- モニタリング・アラートパイプライン（Slack 連携の具体化）
- 分散実行・スケジューラ統合（Airflow / Dagster 等）

問い合わせ・貢献
- この README はコードベース（src/kabusys）に基づく概略ドキュメントです。実装の詳細や追加のユースケースに関する質問があればお知らせください。

--- 
README は以上です。必要ならサンプル .env.example や具体的なスクリプトテンプレートも作成します。どの部分を優先して追加しますか？