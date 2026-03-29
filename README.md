KabuSys — 日本株自動売買プラットフォーム（README）
================================

概要
----
KabuSys は日本株の自動売買・データ基盤・リサーチ機能を統合したライブラリ群です。  
主に以下を目的とします：

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL と品質チェック
- RSS ベースのニュース収集と LLM によるニュースセンチメント解析（OpenAI）
- マーケットレジーム判定（ETF とマクロニュースの融合）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定）のトレーサビリティ（DuckDB）

機能一覧
--------
- data/*:
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 各種データ、トークン管理、レートリミット、リトライ）
  - market_calendar 管理と営業日判定ユーティリティ（is_trading_day / next_trading_day / get_trading_days 等）
  - news_collector：RSS 取得・前処理・ID 正規化（SSRF / Gzip / size 制限対策）
  - quality：ETL 後のデータ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit：監査ログ（signal_events / order_requests / executions）のスキーマ初期化・DB 初期化ユーティリティ
  - stats：汎用統計ユーティリティ（zscore_normalize 等）
- ai/*:
  - news_nlp.score_news：銘柄単位のニュースセンチメントを OpenAI に問い合わせて ai_scores に書き込む
  - regime_detector.score_regime：ETF（1321）200日MA乖離とマクロニュースの LLM スコアを合成して market_regime を作成
  - OpenAI 呼び出しはリトライとフェイルセーフを持つ（失敗時は安全に 0 を使う等）
- research/*:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、ランク変換等
- その他:
  - config: 環境変数/.env ロード、必須設定ラッパー（settings）
  - パッケージの __version__/エクスポート設定

前提・要件
----------
- Python 3.10+
- 必須ライブラリ（代表例）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime 等）
- J-Quants API アクセス（リフレッシュトークン）
- OpenAI API（ニュース NLP / レジーム判定に任意。無ければ該当処理は動作しない）
- kabuステーション等のブローカー連携は別途設定（本コードでは API パス等の設定読み取りあり）

環境変数（主要）
----------------
このプロジェクトで参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API 基本 URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- OPENAI_API_KEY (推奨) — OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境 ("development", "paper_trading", "live")
- LOG_LEVEL (任意) — ログレベル ("DEBUG", "INFO", ...)

.env 自動読み込み
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある .env / .env.local を自動で読み込みます。
- 自動読み込みを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（ローカル開発向け）
-------------------------------
1. リポジトリをクローンし作業ディレクトリへ移動
   - プロジェクトルートには pyproject.toml がある想定

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install -r requirements.txt
   - または pyproject.toml / poetry を利用している場合は poetry install

   必要そうな主要パッケージ例:
   - pip install duckdb openai defusedxml

4. .env を作成
   - .env.example を参考に、最低限以下を設定してください:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...（AI 機能を使う場合）

5. DuckDB / 監査 DB 初期化（例）
   - Python REPL で:
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))
     # （必要であればスキーマ作成関数を呼ぶ）
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

   - または専用監査 DB を作る:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)  # または別ファイル名

使い方（主要ユースケース）
-----------------------

1) 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）
- サンプル:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- run_daily_etl は内部で calendar → prices → financials → quality の順に処理します。ETLResult に処理結果・品質問題が入ります。

2) ニュースセンチメントのスコアリング（OpenAI 必須）
- サンプル:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使う

- 注意: 外部 API 呼び出しはリトライ・フェイルセーフが入っており、失敗時は該当銘柄のスキップとなります。テスト時には内部の _call_openai_api をモックできます。

3) マーケットレジーム判定
- サンプル:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) ファクター計算 / リサーチ
- 例: モメンタム
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026,3,20))

5) RSS ニュース取得（個別呼び出し）
- fetch_rss を使って RSS を取得し raw_news テーブルへ保存するパイプラインを実装できます。
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- news_collector は SSFR 対策、gzip 上限チェック、ID 正規化等を実装済みです。

6) 監査ログの初期化（order/audit）
- init_audit_db または init_audit_schema を用いて監査用スキーマを作成します。

設定・運用に関する注意点
-----------------------
- config.Settings は一部の環境変数を必須（例: JQUANTS_REFRESH_TOKEN 等）としているため、不足すると ValueError が発生します。
- .env の自動読み込みはプロジェクトルートを基準に行われます（.git または pyproject.toml を探索）。
- OpenAI 呼び出しは API 料金・レート制限の影響を受けるため、テストではモックを推奨します（kabusys.ai.* モジュールは _call_openai_api を patch 可能）。
- J-Quants API のレート制限遵守・トークン自動リフレッシュ・リトライは jquants_client に実装されています。
- DuckDB の executemany の制約（空リスト不可）に注意した実装が各所にあります。

ディレクトリ構成
----------------
（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数管理・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP スコアリング
    - regime_detector.py            -- レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン / run_daily_etl 等
    - etl.py                        -- ETL 結果型の再エクスポート
    - calendar_management.py        -- マーケットカレンダー判定・更新ジョブ
    - news_collector.py             -- RSS 取得 / 前処理
    - quality.py                    -- 品質チェック
    - stats.py                      -- 統計ユーティリティ
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム/バリュー/ボラティリティ
    - feature_exploration.py        -- 将来リターン / IC / 統計サマリー
  - (その他: strategy/, execution/, monitoring/ という名前で公開予定のモジュール群)

ライセンス・貢献
----------------
- 本 README はコードベースの説明です。実運用で使用する際はライセンス条項・外部 API 利用規約（J-Quants / OpenAI / ブローカー）を必ず確認してください。
- 貢献や機能追加は Issue / PR を通じて歓迎します。テスト・ドキュメントを添えてください。

問い合わせ
----------
実装に関する質問や使い方の補足が必要であれば、具体的な実行例（エラーメッセージや実行コード）を添えてご連絡ください。README の補足やサンプルスクリプトの追加も対応可能です。