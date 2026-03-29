KabuSys — 日本株自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買・リサーチ基盤の骨組みを提供する Python パッケージです。  
主に以下を目的としています。

- J-Quants API からのデータ ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM を用いたニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- ETL 品質チェック・監査ログ（トレーサビリティ）
- DuckDB ベースのローカルデータ管理

本 README はリポジトリ内の主要モジュールをもとにした利用ガイドラインです。

主な機能
--------
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（API 呼び出し、リトライ、レート制御）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - 監査ログ/トレーサビリティ（signal_events / order_requests / executions）
  - 統計ユーティリティ（Z スコア正規化）
- ai
  - ニュース NLP（news_nlp.score_news：銘柄ごとに LLM でセンチメント算出）
  - 市場レジーム判定（regime_detector.score_regime：ETF MA と LLM マクロセンチメント合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - .env / 環境変数の安全な読み込みと Settings 抽象化

必要な環境変数（代表）
---------------------
（config.Settings で参照される主要なキー）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（発注系がある場合）
- SLACK_BOT_TOKEN        : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で利用）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

セットアップ手順
--------------
1. Python 環境
   - Python 3.10 以上（typing の | 演算子等を使用しているため）
   - 推奨: 仮想環境を作成
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt / pyproject.toml がある場合はそれを利用してください。
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install -r requirements.txt
     - または手動:
       - pip install duckdb openai defusedxml

3. 環境変数（.env）の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可）。
   - 最低限、JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（AI を使う場合）を設定してください。
   - サンプル (.env.example 相当):
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=CXXXXXXXX
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

4. データベースディレクトリ作成
   - デフォルトの DuckDB 保存先は data/kabusys.duckdb。必要に応じてディレクトリを作成してください。
     - mkdir -p data

基本的な使い方
-------------

DuckDB 接続（サンプル）
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")

日次 ETL を実行する（例）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニュースセンチメントを算出する（AI 必須: OPENAI_API_KEY）
- from datetime import date
- from kabusys.ai.news_nlp import score_news
- n_written = score_news(conn, target_date=date(2026,3,20))  # ai_scores に書き込む

市場レジームスコアを算出する
- from datetime import date
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20))

研究用ファクター計算（例）
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- mom = calc_momentum(conn, target_date=date(2026,3,20))
- vol = calc_volatility(conn, target_date=date(2026,3,20))
- val = calc_value(conn, target_date=date(2026,3,20))

監査ログ（audit DB）初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")
- init_audit_schema は init_audit_db 内で実行されます（トランザクションあり）。

設定の自動読み込みの挙動
- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env / .env.local を自動読み込みします。
- .env.local は .env を上書きします（OS 環境変数は保護）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

注意点 / 設計上の方針
-------------------
- Look-ahead bias 回避: 多くの処理は target_date より未来のデータを使用しないよう設計されています（date 比較は排他的に扱われます）。
- API 呼び出しはリトライ・バックオフ・レート制御を実装（J-Quants のレート制限を尊重）。
- LLM 呼び出しはレスポンスのバリデーションとフォールバック（失敗時は中立スコア）を行います。
- DuckDB を用いてローカルで高速な分析が可能。ETL は冪等保存（ON CONFLICT）を行います。
- ニュース収集は SSRF・XML 攻撃・gzip bomb 等に対策を施しています。

ディレクトリ構成（抜粋）
---------------------
以下は主要ファイル／モジュールの一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースセンチメント（score_news）
    - regime_detector.py           -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント & 保存関数
    - pipeline.py                  -- ETL パイプライン run_daily_etl 等
    - etl.py                       -- ETL 便宜公開（ETLResult）
    - calendar_management.py       -- 市場カレンダー管理
    - news_collector.py            -- RSS 収集・前処理
    - quality.py                   -- データ品質チェック
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - audit.py                     -- 監査ログ DB 初期化
  - research/
    - __init__.py
    - factor_research.py           -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py       -- forward returns / IC / summary / rank
  - (strategy/, execution/, monitoring/ ... はトップパッケージで公開予定)

（実際のリポジトリにはその他の補助モジュールやテスト、設定ファイルが存在することがあります）

開発者向け / テスト
-------------------
- 自動 .env ロードはプロジェクトルート検出に依存します。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して環境の注入を制御できます。
- AI 呼び出し部分（news_nlp._call_openai_api など）はユニットテストでモック可能になるよう設計されています（monkeypatch / unittest.mock.patch）。

ライセンス／貢献
---------------
- この README はコードベースのドキュメント生成を目的とした要約です。ライセンス、コントリビュート手順、具体的な実運用上の注意（発注処理・実口座の接続など）はリポジトリの LICENSE / CONTRIBUTING / Ops ドキュメントを参照してください。

お問い合わせ
-------------
本プロジェクトに関する質問やバグ報告はリポジトリの issue を利用してください。README に記載されていない詳細な設計資料（DataPlatform.md / StrategyModel.md 等）がリポジトリに含まれている場合はそちらも参照してください。

以上。必要であれば、README に含める追加の実行例（具体的な .env.example、requirements.txt の候補、より詳細なディレクトリ木）を生成します。どの情報を優先しますか？