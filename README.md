KabuSys
=======

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、AI を使った市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレース）など、取引システム／リサーチ環境に必要な機能群を提供します。

主な特徴
--------
- ETL パイプライン（prices / financials / market calendar）の差分取得と DuckDB への冪等保存
- J-Quants API クライアント（自動トークン管理、レート制御、リトライ）
- ニュース収集（RSS）と前処理、raw_news / news_symbols への保存
- ニュースの LLM ベースセンチメント（gpt-4o-mini）による銘柄単位スコアリング（ai_scores）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- 研究用ファクター計算（Momentum / Volatility / Value など）と統計ユーティリティ（Z スコア正規化、IC 計算等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログスキーマ（signal_events, order_requests, executions）と初期化ユーティリティ
- .env / 環境変数により設定管理（自動ロード機能あり）

必要条件（目安）
----------------
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / RSS / OpenAI）

インストール
------------
開発環境向けにソースを使う場合の一例:

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. パッケージを編集可能モードでインストール（プロジェクトに setup/pyproject がある場合）
   - pip install -e .

環境変数 / .env
----------------
config.Settings を通じて以下の環境変数を参照します。必須変数は明記しています。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD : kabu ステーション等の API パスワード（実行モジュールが利用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV : 環境 ('development' / 'paper_trading' / 'live')。デフォルト 'development'
- LOG_LEVEL : ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）。デフォルト 'INFO'
- KABUSYS_DISABLE_AUTO_ENV_LOAD : '1' を設定するとプロジェクトルートの .env 自動ロードを無効化
- OPENAI_API_KEY : OpenAI 呼び出しに使う API キー（score_news / regime_detector の引数でも指定可能）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUS_API_BASE_URL : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env → .env.local の順で読み込みます。
- OS 環境変数を優先し、.env.local が .env を上書きします。
- 自動読み込みを避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。

セットアップ例（.env）
-------------------
プロジェクトルートに .env（または .env.local）を作成してください。最低限以下を設定します（例）:

JQUANTS_REFRESH_TOKEN=xxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

使い方（コード例）
-----------------

- DuckDB 接続を作成して ETL を実行する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースの NLP スコアリング（ai_scores へ書き込み）
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {written}")

  - OpenAI API キーは OPENAI_API_KEY 環境変数か、score_news の api_key 引数で渡します。

- 市場レジーム判定
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn は DuckDB 接続。監査テーブルが作成される。

主要モジュール / 機能一覧
-----------------------
- kabusys.config
  - 環境変数の読み込み・検証（.env 自動ロード、Settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（認証・レート制御・リトライ）
  - fetch / save のユーティリティ（daily_quotes、financials、market_calendar 等）
- kabusys.data.pipeline
  - run_daily_etl などの ETL パイプライン
  - 差分取得と品質チェックの統合
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news への保存（SSRF / Gzip / XML 安全対策付き）
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェック
- kabusys.data.calendar_management
  - JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマの初期化
- kabusys.ai.news_nlp
  - ニュースを LLM に投げて銘柄別センチメントを ai_scores に書き込む
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して市場レジーム判定
- kabusys.research
  - ファクター計算（momentum / value / volatility 等）、特徴量探索・IC 計算、zscore_normalize

ディレクトリ構成（主なファイル）
------------------------------
（ソース配置: src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - calendar_management.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（execution, strategy, monitoring パッケージを想定）

※ 実際のパッケージはさらに細分化されているため、上記は主要ファイルの抜粋です。

設計上のポイント / 注意事項
--------------------------
- ルックアヘッドバイアス防止:
  - 多くの処理（news window 計算、MA 計算、ETL のターゲット日など）は datetime.today() を直接参照せず、明示的な target_date を受け取る設計です。バックテストでの再現性を確保します。
- 冪等性:
  - J-Quants の保存処理や監査ログ初期化などは冪等（ON CONFLICT / INSERT … DO UPDATE）を意識して実装されています。
- フェイルセーフ:
  - LLM 呼び出し失敗時はゼロ寄せ（中立）で続行したり、エラーを集約して処理を継続する方針です（運用での可用性重視）。
- セキュリティ:
  - RSS 取得での SSRF 対策、defusedxml による XML 安全化、URL 正規化によるトラッキング除去などが実装されています。

開発・テスト
--------------
- 環境変数の自動ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- OpenAI 呼び出しや HTTP など外部依存呼び出しはモック可能（モジュール内の _call_openai_api や _urlopen を patch）。

ライセンス・貢献
----------------
- 本 README はコードベースに基づく説明書きです。実運用に用いる場合はライセンス、法令、API 利用規約（J-Quants / OpenAI / 各ニュースサイト等）を確認してください。

補足
----
- 実行時エラーや細かな使い方は各モジュールの docstring に詳細が記載されています。関数単位で引数・戻り値や例外の情報があるため、必要に応じて参照してください。