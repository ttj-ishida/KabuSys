KabuSys
=======

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）などを提供します。

概要
----
KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価/財務/カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS によるニュース収集と前処理（SSRF 対策・正規化・冪等保存）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント／市場レジーム判定
- ファクター（モメンタム／ボラティリティ／バリュー）計算と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブル（signal → order_request → executions）の初期化ユーティリティ

主な機能一覧
-------------
- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須キーの取得（例: JQUANTS_REFRESH_TOKEN）
- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得・バックフィル・品質チェックを統合
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save の実装（レートリミット・リトライ・401 refresh 対応）
- ニュース収集（kabusys.data.news_collector）
  - RSS フェッチ、URL 正規化、記事 ID 生成、前処理、SSRF 対策
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄ごとのセンチメント付与（ai_scores への書き込み）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロ記事の LLM センチメントを合成して日次レジーム判定
- リサーチ支援（kabusys.research）
  - ファクター計算（momentum, volatility, value）、特徴量解析（forward returns, IC, summary）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・将来日付・非営業日データの検出
- 監査ログ初期化（kabusys.data.audit）
  - 監査用スキーマ作成、専用 DuckDB 初期化ユーティリティ

前提条件・依存
---------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）
- DuckDB を使ったローカル DB（デフォルト path は data/kabusys.duckdb）

推奨のインストール例
-------------------
（プロジェクトルートで）

1) 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate

2) 必要パッケージをインストール
   pip install duckdb openai defusedxml

※ packaging / requirements.txt が用意されている場合はそちらを使用してください。

環境変数（主なもの）
------------------
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用、引数で上書き可能）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用トークン（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス監視用ファイルパス
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/...

注意: パッケージはプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読み込みします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------

1. リポジトリをクローン
   git clone <repo>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージインストール
   pip install duckdb openai defusedxml

4. 環境変数設定
   プロジェクトルートに .env ファイルを作成するか、環境変数を設定します。必要最低限は JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（AI を使う場合）。

   例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. ディレクトリ（data 等）を作成
   mkdir -p data

基本的な使い方（コード例）
-------------------------

- DuckDB 接続と ETL の実行（日次 ETL）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコアリング（OpenAI キーは環境変数か引数で渡す）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("scored:", n_written)

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化（独立した監査 DB を作る）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可

運用・実行上の注意
------------------
- Look-ahead バイアス回避: 本ライブラリの多くの関数は内部で datetime.today() を使わず、呼び出し側が target_date を指定する設計です。バックテストや日次バッチでは target_date を明示してください。
- OpenAI 呼び出し: レスポンスのパース失敗や API エラーはフェイルセーフとして 0.0（中立）などで継続する実装になっていますが、実運用では API の安定性とコスト管理に注意してください。
- J-Quants API: レート制限（120 req/min）を守る実装が含まれています。大量の同時リクエストは避けてください。
- NewsCollector: RSS の取得は SSRF 対策や最大サイズチェックを行います。外部 URL を追加する場合は信頼できるソースを利用してください。
- DuckDB executemany: 一部の DuckDB バージョンでは executemany に空リストを渡すとエラーになるため空チェックが実装されています。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）です。

- kabusys/
  - __init__.py                - パッケージ定義（version）
  - config.py                  - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースセンチメント（ai_scores への書き込み）
    - regime_detector.py       - 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（fetch/save）
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - news_collector.py        - RSS ニュース収集
    - calendar_management.py   - マーケットカレンダー管理 / 営業日判定
    - quality.py               - データ品質チェック
    - stats.py                 - 汎用統計（zscore_normalize）
    - audit.py                 - 監査ログ用スキーマ初期化
    - etl.py                   - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   - forward returns / IC / summary / rank

付録：よく使う関数
------------------
- run_daily_etl(conn, target_date, id_token=None, run_quality_checks=True, ...)
  → 日次 ETL を実行して ETLResult を返す

- score_news(conn, target_date, api_key=None)
  → ニュースセンチメントを計算して ai_scores テーブルに書き込む

- score_regime(conn, target_date, api_key=None)
  → 市場レジーム（bull/neutral/bear）を market_regime テーブルに書き込む

- init_audit_db(path) / init_audit_schema(conn)
  → 監査ログ用 DB/スキーマを初期化

トラブルシューティング
---------------------
- .env が読み込まれない:
  - パッケージは __file__ を起点に親ディレクトリに .git または pyproject.toml を探してプロジェクトルートを検出します。CI 等で検出できない場合は環境変数を直接設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自前でロードしてください。
- OpenAI / J-Quants エラー:
  - ネットワークやキーの問題が多いです。ログを確認し、API キー・レート制限をチェックしてください。
- DuckDB の互換性:
  - DuckDB のバージョン差分で executemany の空リスト挙動が異なるため、ライブラリ側で保護しています。問題がある場合は duckdb のバージョンを合わせてください。

ライセンス・貢献
----------------
（ここにライセンスや貢献方法を記載してください）

最後に
------
この README はコードベースの主要機能と使い方をまとめた概要です。各モジュールの詳細な使い方はソース内 docstring を参照してください。必要であれば、具体的なユースケース（例: バックテスト用データ準備、運用バッチの systemd / cron 設定、OpenAI のコスト最適化など）に合わせた追加ドキュメントを生成します。