KabuSys — 日本株自動売買プラットフォーム（README）
======================================

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、ニュースNLP、マーケットレジーム判定、ETL、監査ログ等を含む自動売買支援ライブラリです。  
主に以下用途を想定しています。

- J-Quants / JPX などから価格・財務・カレンダーを取得して DuckDB に蓄積する ETL
- ニュース（RSS）収集と OpenAI を用いた銘柄別センチメントスコアリング
- マーケットレジーム（bull / neutral / bear）判定（ETF + LLM 合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- データ品質チェック・カレンダー管理

主な設計方針
- ルックアヘッドバイアスを避ける（date.today() 等に依存しない実装）
- DuckDB を中心としたローカルデータ管理（冪等保存）
- 外部呼び出し（API）はリトライやレート制御、フェイルセーフを備える
- テスト容易性を考慮し API 呼び出しを差し替え可能に設計

機能一覧
----
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / token refresh / rate limiter）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存・SSRF 対策・URL 正規化）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄別センチメント算出・AI バッチ処理・JSON モード対応）
  - レジーム判定（score_regime：ETF MA とマクロニュース LLM を合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込みと設定（自動 .env ロード機能、各種必須値のチェック）

セットアップ手順
----
前提
- Python 3.10+（typing の一部表記が使われているため）
- DuckDB がネイティブで動作する環境
- OpenAI API 利用時は API キー
- J-Quants API を利用する場合はリフレッシュトークン

1. リポジトリをクローンして開発環境を作成
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存関係をインストール
   - 必要なパッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （パッケージ一覧はプロジェクトの pyproject.toml / requirements.txt を参照してください）

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を作成すると自動で読み込まれます（config モジュールが .git または pyproject.toml をルートとして探索）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

  主な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL で使用）
  - KABU_API_PASSWORD     : kabu ステーション API のパスワード（約定系で使用）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知機能）
  - SLACK_CHANNEL_ID      : 通知先チャネル ID
  - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用）

  任意（デフォルトあり）
  - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : SQLite（monitoring 用）パス（デフォルト data/monitoring.db）

使い方（簡易リファレンス）
----
- DuckDB 接続の作成例
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=my_date)  # target_date を省略すると today を使用
  - print(result.to_dict())

- 単体ジョブ
  - run_prices_etl / run_financials_etl / run_calendar_etl をそれぞれ使用可能

- ニュースセンチメントを算出（OpenAI キーを環境変数に設定）
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=my_date)  # 取得・書込み件数を返す

  - API キーを引数で渡すことも可能:
    - score_news(conn, target_date=my_date, api_key="sk-...")

- マーケットレジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=my_date)  # market_regime テーブルへ書込み

- 監査ログ初期化
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - conn_audit = init_audit_db("data/audit.duckdb")
  - または既存 conn に対して init_audit_schema(conn)

- ファクター・リサーチ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - moments = calc_momentum(conn, target_date=my_date)
  - values = calc_value(conn, target_date=my_date)

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=my_date)
  - for i in issues: print(i)

注意点 / テスト時のヒント
- OpenAI 呼び出しは外部 API なので unittest.mock.patch で _call_openai_api を差し替えてテスト可能です（modules: kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基準に行います。CI / テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL はルックアヘッドバイアスを避けるため target_date を引数で明示することを推奨します。
- DuckDB executemany の仕様に依存する箇所があるため、空パラメータでの executemany を避けています（モジュール内部でガード済み）。

ディレクトリ構成（主要ファイル）
----
src/kabusys/
- __init__.py
- config.py                — 環境設定 / .env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py            — ニュースのセンチメントスコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（ETF MA + LLM）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch/save）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day など）
  - news_collector.py      — RSS 収集・前処理・保存（SSRF 対策）
  - quality.py             — データ品質チェック
  - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- research/ （他モジュール）
- その他モジュール（execution, monitoring, strategy 等は __all__ に含まれるが本リストは抜粋です）

ライセンス / 貢献
----
- この README はコードベースの説明を目的とした簡易ドキュメントです。実運用・本番発注を行う前に必ずコードレビュー・追加の安全対策（リスク管理、二重発注防止、テスト）を実施してください。
- 貢献する場合は pull request を送る前にテストとスタイルチェックをお願いします。

お問い合わせ
----
不明点や追加のドキュメントが必要であれば、プロジェクトの issue に記載してください。