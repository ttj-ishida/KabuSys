# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（README 日本語版）

概要
- KabuSys は日本株のデータ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、監査ログ（発注/約定トレース）などをまとめた内部ライブラリ群です。
- DuckDB をデータストアとして利用し、ETL パイプラインやリサーチ用ファクター計算、AI ベースのニュースセンチメント評価、監査テーブル初期化などを提供します。
- 設定は環境変数 / .env ファイルで管理します。自動で .env/.env.local をプロジェクトルートから読み込みます（無効化可）。

主な機能
- データ取得・ETL
  - J-Quants から株価（OHLCV）・財務指標・マーケットカレンダー取得（jquants_client）
  - 差分 ETL / バックフィル機能（data.pipeline）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 取得および前処理（news_collector）
  - OpenAI を用いた銘柄ごとのニュースセンチメントスコアリング（ai.news_nlp）
  - マクロニュース + ETF 200 日 MA を融合した市場レジーム判定（ai.regime_detector）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Spearman）・統計サマリー（research.feature_exploration）
  - 標準化ユーティリティ（data.stats）
- 監査・トレーサビリティ
  - signal/order_request/execution を記録する監査スキーマの初期化と DB ハンドリング（data.audit）
- ユーティリティ
  - プロジェクトルートベースの .env 自動読み込み（config）
  - システム設定（ログレベル・環境判定・閾値などを settings 経由で取得）

セットアップ手順（開発環境向け）
1. リポジトリを取得し、パッケージをインストール
   - ソースをローカルへ取得（例: git clone ...）
   - 開発インストール（仮想環境推奨）
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -e .
     ```
   - 必要パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml

2. 環境変数 / .env を準備
   - プロジェクトルート（.git や pyproject.toml のある場所）に `.env` または `.env.local` を作成すると自動読み込みされます。
   - 主要な環境変数（コード内参照）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
     - OPENAI_API_KEY        : OpenAI API キー（ai モジュール使用時に必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite 監視 DB（デフォルト: data/monitoring.db）
     - PID_FILE_PATH         : 実行監視 PID ファイル（デフォルト: data/execution.pid）
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - 自動 .env 読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. DuckDB 初期化（監査用など）
   - 監査テーブルを初期化する例:
     ```python
     import duckdb
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)
     # または
     # conn = duckdb.connect(str(settings.duckdb_path))
     # init_audit_schema(conn)
     ```

使い方（主要な例）
- ETL を日次で実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"スコアを書き込んだ銘柄数: {count}")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィード取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

設定（settings）について
- settings = kabusys.config.settings から各種設定値をプロパティ経由で取得できます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.is_live）。
- 重要: settings は必須の環境変数が足りないと ValueError を送出します。開発時は .env に必要なキーを設定してください。
- .env の読み込み優先順位: OS環境変数 > .env.local > .env。既存 OS 環境変数は保護されます。

トラブルシューティング（よくある問題）
- ValueError: 環境変数が見つからない
  - settings が必須キーを要求します。.env を正しく配置し値をセットしてください。
- OpenAI / J-Quants API エラー
  - APIキーやトークンが正しいか、ネットワーク/レート制限を確認してください。ライブラリは再試行・バックオフを行いますが、キーの未設定は即時例外です。
- DuckDB のテーブル・スキーマがない
  - ETL 実行や audit 初期化前にスキーマ作成手順が必要な場合があります（プロジェクトに schema 初期化関数があればそれを利用してください）。audit.init_audit_db は監査用スキーマを作成します。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       -- ニュース NLP と OpenAI 呼び出し
    - regime_detector.py                -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
    - etl.py                            -- ETL 型の再エクスポート（ETLResult）
    - news_collector.py                 -- RSS 収集・前処理
    - calendar_management.py            -- 市場カレンダー管理（営業日判定等）
    - quality.py                        -- データ品質チェック
    - stats.py                          -- zscore_normalize 等の統計ユーティリティ
    - audit.py                          -- 監査テーブル DDL/初期化
  - research/
    - __init__.py
    - factor_research.py                -- モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py            -- forward returns / IC / summary
  - research/* other modules as provided
- pyproject.toml / setup.cfg 等（プロジェクトルート）

開発のヒント
- テストやスクリプト実行時に .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しは各モジュールで独立して実装されており、テスト時は内部 _call_openai_api をモックすることで外部 API 呼び出しを避けられます。
- DuckDB の executemany に関する挙動（空リスト不可等）に注意して実装されています。

ライセンス / コントリビューション
- 本 README にはライセンス情報を含めていません。実際に公開する際は LICENSE を追加してください。
- コントリビュート時はコードスタイル・テスト・ドキュメントを整備の上 PR をお願いします。

以上が本コードベースの README.md（日本語）です。必要に応じて「セットアップ手順の詳細化（依存パッケージの具体的な pip install 行）」「実行スクリプト例（cron, systemd, Docker Compose）」などを追記できます。どの部分を詳しく書きたいか指示してください。