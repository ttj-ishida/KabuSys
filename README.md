KabuSys
=======

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー収集）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。

主な用途
- J-Quants API からの日次データ取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と LLM を用いた銘柄ごとのニュースセンチメント算出
- ETF 指標＋マクロニュースでの日次市場レジーム判定（bull/neutral/bear）
- ファクター（モメンタム・ボラティリティ・バリュー等）計算・探索用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 発注／約定まで追跡可能な監査ログ（DuckDB に監査スキーマを初期化）

機能一覧
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS 取得・前処理・raw_news への保存補助）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- ai
  - ニュース NLP（gpt-4o-mini を想定した JSON Mode でのスコア化）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns, IC, 統計サマリー, rank 等）
- config
  - .env / 環境変数パーサと Settings（自動ロード機能付き）

必要条件（推奨）
- Python 3.10+
- duckdb
- openai（openai パッケージの Chat Completions を使用する想定）
- defusedxml
- （標準ライブラリの urllib 等を使用、requests は必須ではありません）

セットアップ手順

1) リポジトリをチェックアウト（例）
   git clone <repo-url>
   cd <repo>

2) 仮想環境作成（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows PowerShell

3) 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトがパッケージ化されている場合は）
   pip install -e .

4) 環境変数設定
   プロジェクトルートに .env（または .env.local）を作成することで自動で読み込まれます。
   自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - OPENAI_API_KEY=sk-...

   任意（デフォルトが用意されています）
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  (デフォルト: INFO)
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   最小 .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=CXXXXXXX
   KABU_API_PASSWORD=your_password
   ```

使い方（代表的な例）

- DuckDB 接続を作成して日次 ETL を実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースの NLP スコアを実行（OpenAI API キーを渡すか環境変数を設定）
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {count} codes")

- 市場レジーム判定（例）
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログスキーマ初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # または既存接続へスキーマを追加
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)

- 研究用ユーティリティ（ファクター計算など）
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  res = calc_momentum(conn, target_date=date(2026,3,20))

設定 / 環境変数の注意点
- 自動で .env を読み込む仕組みがあります（プロジェクトルートを .git や pyproject.toml を基準に探索）。テスト中などで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- Settings クラスは必須環境変数が欠けていると ValueError を投げます。特に J-Quants や Slack、kabu API の設定は整えてください。
- OPENAI_API_KEY は ai モジュールの関数に渡すか環境変数で提供してください。関数は api_key 引数で上書き可能です。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュースの LLM スコアリング
    - regime_detector.py         -- 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py          -- J-Quants API クライアント + 保存ロジック
    - news_collector.py          -- RSS 取得・正規化・挿入補助
    - calendar_management.py     -- 市場カレンダー関連ユーティリティ
    - quality.py                 -- データ品質チェック
    - stats.py                   -- 統計ユーティリティ（Zスコア等）
    - audit.py                   -- 監査ログスキーマ初期化
    - etl.py                     -- ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py         -- factor 計算（momentum/value/volatility）
    - feature_exploration.py     -- forward returns / IC / summary / rank

設計上のポイント（抜粋）
- Look-ahead bias を避けるため日付処理は現在日時を暗黙に参照せず、関数呼び出しに target_date を明示する設計です。
- ETL・DB 書き込みは冪等（ON CONFLICT / DELETE → INSERT）を意識して実装されています。
- 外部 API 呼び出しにはリトライとバックオフ、レートリミット制御を入れています（J-Quants, OpenAI）。
- ニュース収集は SSRF 対策や XML の堅牢化（defusedxml）・サイズ制限を実装しています。
- DuckDB をデータレイヤに採用し、分析・リサーチ用途に最適化されています。

開発・貢献
- コードは src レイアウトで管理されています。ローカルで開発する際は virtualenv を使い、必要パッケージをインストールして lint / unit tests を追加してください（本リポジトリにはテストスクリプトの例は含まれていません）。
- バグ報告・Pull Request を歓迎します。設計思想や既存の API に影響を出す変更は事前に Issue で相談してください。

ライセンス
- 本 README では省略します。実際のプロジェクトでは LICENSE ファイルを用意してください。

補足
- 本ドキュメントはリポジトリ内のソースコードから仕様を抜粋して整理しています。実行には各種 API キーやネットワークアクセスが必要です。運用環境（特に本番での約定や資金管理）に適用する際は十分な検証・安全対策を行ってください。