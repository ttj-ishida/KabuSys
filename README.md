KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買フレームワークです。  
主に以下を目的としています。

- J-Quants からのマーケットデータ ETL（株価 / 財務 / カレンダー）
- ニュース収集と LLM によるニュースセンチメント評価（銘柄単位）
- 市場レジーム判定（ETF + マクロニュース）
- 研究用のファクター計算・特徴量評価ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック、ニュース収集の SSRF/DoS 対策など実運用向けの配慮

本リポジトリは src/kabusys 以下にモジュール実装を含み、DuckDB を主要なローカルDBとして利用します。

主な機能
--------
- データ ETL
  - J-Quants API から株価（daily quotes）、財務データ、JPXカレンダーを差分取得して DuckDB に保存
  - ページネーション・レートリミッティング・トークン自動更新・リトライ（指数バックオフ）対応
- ニュース収集
  - RSS から記事取得、前処理、記事ID生成（正規化URL → SHA256）、raw_news / news_symbols への冪等保存
  - SSRF 対策、レスポンスサイズ制限、XML の安全パース（defusedxml）
- ニュース NLP（OpenAI）
  - 銘柄ごとに記事をまとめて gpt-4o-mini に投げ、JSON モードで厳密にスコアを取得（ai_scores へ保存）
  - バッチ化、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次でレジーム判定
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC、Zスコア正規化、統計サマリー
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、将来日付 / 非営業日検出
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ。監査・冪等性を担保

セットアップ手順
----------------

前提
- Python 3.9+（typing に型注釈が多く使われています。プロジェクトの実際の要件に合わせて調整してください）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

1. リポジトリをチェックアウト（src レイアウトを想定）
   - 例: git clone ... && cd repo

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発用: pytest や linters 等を追加）

   もしパッケージ化済みなら:
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（src/kabusys/config.py により .git または pyproject.toml を基準に探索）。
   - 自動ロードを抑止する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨される .env の例
- .env.example（内容例）

  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=your_openai_api_key
  KABU_API_PASSWORD=your_kabu_api_password
  SLACK_BOT_TOKEN=your_slack_bot_token
  SLACK_CHANNEL_ID=your_slack_channel_id
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

必須（実行する機能により変わります）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（ETL）
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabu API（発注機能を使う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知を使う場合

使い方（簡易例）
----------------

共通: DuckDB 接続の取得
- import duckdb
- conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

1) ETL（日次パイプライン）実行例
- from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

2) ニュースのセンチメントを算出して ai_scores に保存
- from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"written: {n_written}")

  ※ OpenAI API キーを引数で上書きすることも可能: score_news(conn, date(2026,3,20), api_key="...")

3) 市場レジーム判定
- from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026,3,20))

4) 監査ログ DB の初期化（監査用の standalone DB）
- from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_db は transactional=True 相当で DDL を作成します

5) データ品質チェック（ETL の一部としても実行）
- from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

設定・環境変数の補足
--------------------
- KABUSYS_ENV: development | paper_trading | live
  - settings.is_live / is_paper / is_dev で参照可能
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化

ディレクトリ構成（主要ファイルと役割）
------------------------------------

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ など）
- config.py
  - .env / 環境変数の自動読み込み、Settings クラス（各種設定値をプロパティで提供）
- ai/
  - __init__.py
  - news_nlp.py    — ニュースを銘柄別に集約し OpenAI でスコア化（ai_scores）
  - regime_detector.py — ETF とマクロニュースを組み合わせた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / token 管理 / rate limit）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL の公開型（ETLResult の再エクスポート）
  - news_collector.py — RSS 取得・前処理・保存ロジック（SSRF/サイズ制限等）
  - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py — zscore_normalize（共通統計ユーティリティ）
  - audit.py — 監査ログ DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank ユーティリティ

注意点 / 運用上のポイント
-------------------------
- Look-ahead バイアス防止: 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に受け取ります。バッチ・バックテスト時には必ず target_date を指定してください。
- OpenAI 呼び出し: JSON モード（厳密な JSON 出力）を期待していますが、実運用ではレスポンス不正時にフォールバックやスキップを行う設計です。API 呼び出し回数に注意（料金・レート）。
- J-Quants API: rate limit（120 req/min）を遵守するための RateLimiter を実装しています。長時間のフル取得はページネーションを利用します。
- ニュース取得: RSS のサイズやリダイレクト先を検査するなどセキュリティ対策を実装しています。外部フィードの扱いには十分注意してください。
- DuckDB バージョン依存: 一部実装（executemany の空リストなど）は DuckDB のバージョン依存の挙動に配慮しています。運用環境の DuckDB バージョンで動作確認を行ってください。

貢献 / テスト
--------------
- 単体テスト、モック（OpenAI 呼び出し、HTTP）を活用してユニットテストを実装することを推奨します。
- 大規模なデータ操作はサンドボックス DB（:memory: やテスト用ファイル）で実行してから本番 DB に投入してください。

ライセンス
----------
（ここに実際のライセンス情報を記載してください）

問い合わせ
-----------
実装に関する質問や不具合はリポジトリの issue にて報告してください。

--- 

必要であれば README 内に具体的な .env.example ファイルや docker / systemd のデプロイ例、CI のワークフロー、より詳しい API 使用例（パラメータ一覧）などを追加で作成します。どの情報が必要か教えてください。