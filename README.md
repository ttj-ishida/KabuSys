# KabuSys — 日本株自動売買システム（README）

概要
---
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants からの株価・財務・カレンダー等の ETL パイプライン（DuckDB 保存）
- RSS ベースのニュース収集と LLM（OpenAI）を用いたニュースセンチメント／市場レジーム判定
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索ユーティリティ
- 監査ログ（signal → order → execution トレーサビリティ）用スキーマ初期化
- データ品質チェック・市場カレンダー管理 等

設計上のポイント
- Look-ahead bias（将来情報の漏洩）を意識した設計（内部で date.today() 等を直接参照しない、DB クエリに排他条件を入れる等）
- API 呼び出しはリトライ・バックオフ・フェイルセーフを備える（失敗時は安全側の既定値で継続）
- DuckDB を中心に冪等性（ON CONFLICT / DELETE→INSERT）を重視した保存
- 外部呼び出し（OpenAI / J-Quants / HTTP）箇所はモックしやすく設計

主な機能
---
- data:
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - market_calendar 管理（営業日判定 / next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF/サイズ制限/正規化対策あり）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLU（score_news: articles → ai_scores）
  - 市場レジーム判定（score_regime: MA + macro sentiment → market_regime）
  - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定、レスポンス検証・リトライ付き
- research:
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索・IC / forward returns / summary utilities

セットアップ
---
前提:
- Python 3.10+
- DuckDB, OpenAI の利用に必要なネットワークアクセス

1. リポジトリルートでパッケージをインストール（開発モード推奨）
   - pip を利用する例:
     pip install -e ".[dev]"  # pyproject.toml に extras があれば使用
   - または最低限必要なライブラリを直接:
     pip install duckdb openai defusedxml

2. 環境変数 / .env
   - プロジェクトは .env を自動読み込みします（ルート判定は .git または pyproject.toml）。  
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（Settings から参照される）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API（発注）パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — 通知先チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時にも利用可能）
   - 任意 / デフォルト設定:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / ...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動読み込みを無効化
     - DUCKDB_PATH / SQLITE_PATH: データベースパス（デフォルト data/kabusys.duckdb 等）

   例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

3. データベースの初期化（監査DB 例）
   - Python から:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（簡単な例）
---
以下は最小限の利用例（Python REPL / スクリプト）。

- DuckDB 接続準備:
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

- ニュースセンチメント計算（OpenAI API キーは OPENAI_API_KEY 環境変数で指定可能）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("scored", n_written)

- 市場レジーム算出:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI APIキーが必要

- 研究用ファクター計算:
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

- 監査スキーマ初期化（既存接続に対して）:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意点 / テストに関するヒント
---
- OpenAI 呼び出し部分はモジュール内で _call_openai_api をラップしているため、ユニットテスト時は該当関数を patch してモックできます（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- J-Quants クライアントの _request はネットワーク／リトライロジックを内包。テストでは fetch_* をモックしてください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストでロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと便利です。
- DuckDB の executemany はバージョン差（空リストの取り扱い等）に注意している実装になっています。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py  (パッケージ定義、__version__)
- config.py    (環境変数 / Settings の定義、.env 自動読込)
- ai/
  - __init__.py
  - news_nlp.py          (ニュースセンチメント: score_news)
  - regime_detector.py   (市場レジーム判定: score_regime)
- data/
  - __init__.py
  - jquants_client.py    (J-Quants API クライアント: fetch / save)
  - pipeline.py         (ETL パイプライン: run_daily_etl 等)
  - etl.py              (ETL 結果クラスのエクスポート)
  - news_collector.py   (RSS 収集)
  - calendar_management.py (market_calendar 管理)
  - quality.py          (データ品質チェック)
  - stats.py            (zscore_normalize 等)
  - audit.py            (監査スキーマ / init_audit_db)
- research/
  - __init__.py
  - factor_research.py   (calc_momentum / calc_value / calc_volatility)
  - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)
- ai 以外にも strategy / execution / monitoring などのサブパッケージを公開する設計だが、今回のコードベースでは data / research / ai が中心です。

ライセンス・貢献
---
（リポジトリに LICENSE があればその内容に従ってください。開発者向けの貢献方法はプロジェクトの CONTRIBUTING.md を参照してください。）

最後に
---
この README はコード内の設計意図や公開 API を簡潔にまとめたものです。実運用やテストを行う際は、各モジュールの docstring とログ出力を参照し、環境変数や DB スキーマの要件を満たしていることを確認してください。必要であれば、利用したい機能（例: 発注実行、Slack通知、strategy 実装など）に合わせた追加ドキュメントを作成します。