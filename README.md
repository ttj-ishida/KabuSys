KabuSys
=======

日本株向けのデータプラットフォームとリサーチ / 自動売買補助ライブラリです。  
DuckDB をデータ層に用い、J-Quants / JQ API からの株価・財務・カレンダー取得、RSS ニュース収集、LLM を用いたニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログスキーマ等の機能を提供します。

主な用途
- 日次 ETL（株価・財務・市場カレンダー）の自動差分取得と保存
- ニュース収集と LLM による銘柄センチメント算出（ai_scores 生成）
- 市場レジーム判定（MA と LLM の合成）
- ファクター計算・特徴量探索・IC 計算（リサーチ用途）
- 監査ログテーブル（signal / order / execution）初期化ユーティリティ

機能一覧
- 環境設定管理（.env 自動読み込み、Settings オブジェクト）
- J-Quants クライアント
  - 差分取得（株価 daily_quotes / 財務 statements / 上場情報 / market calendar）
  - Rate-limit 保護 / リトライ / トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 個別 ETL 関数: run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult による結果集約
- データ品質チェック（欠損 / 重複 / スパイク / 日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（gpt-4o-mini を利用）
  - score_news: 銘柄ごとのセンチメント ai_scores 生成（バッチ、JSON Mode、リトライ）
  - calc_news_window: 対象ウィンドウ（JST 前日15:00〜当日08:30 相当）計算
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を合成）
  - score_regime: market_regime テーブルへ冪等書込
- 研究モジュール
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算 / IC（スピアマン） / 統計サマリー / Z-score 正規化
- 監査ログ（audit）スキーマ初期化ユーティリティ（init_audit_schema / init_audit_db）

セットアップ手順（開発環境想定）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに packaging がある場合は pip install -e . を推奨）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（既定）。  
     自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（想定）環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に利用）
- KABU_API_PASSWORD     : kabu API パスワード（kabu 関連モジュールで利用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）

その他（オプション・デフォルトあり）
- KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH           : data/kabusys.duckdb（デフォルト）
- SQLITE_PATH           : data/monitoring.db（デフォルト）
- PID_FILE_PATH         : data/execution.pid（デフォルト）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

簡単な使い方（コード例）
- DuckDB 接続を作成して日次 ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアを計算して ai_scores テーブルへ保存する例:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written {n_written} scores")

- 市場レジーム判定を実行する例:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB を初期化する例:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

注意点 / 運用メモ
- Look-ahead bias の回避を設計の基本に置いています。内部処理は target_date を明示して実行することを推奨します（datetime.today() を直接参照しない）。
- OpenAI 呼び出しは JSON Mode を使用し、リトライやレスポンス検証を実装していますが、APIキーのレートやコスト管理に注意してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client 内でレート制限とリトライを実装しています。
- テーブル操作は多くが冪等（ON CONFLICT DO UPDATE/DO NOTHING）になるよう実装されていますが、バックアップやバージョン管理は運用で行ってください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準とするため、配布後も安定して動作します。

ディレクトリ構成（主要ファイル／モジュール）
- src/kabusys/
  - __init__.py            （パッケージ定義、version）
  - config.py              （Settings、.env ロード、環境変数管理）
  - ai/
    - __init__.py
    - news_nlp.py          （news の LLM スコアリング、score_news）
    - regime_detector.py   （市場レジーム判定、score_regime）
  - data/
    - __init__.py
    - jquants_client.py    （J-Quants API クライアント／保存関数）
    - pipeline.py          （ETL パイプライン、run_daily_etl 他）
    - calendar_management.py（市場カレンダー管理）
    - news_collector.py    （RSS 収集・前処理）
    - quality.py           （データ品質チェック）
    - stats.py             （zscore_normalize 等）
    - audit.py             （監査ログスキーマ初期化）
    - etl.py               （ETLResult 再公開）
  - research/
    - __init__.py
    - factor_research.py   （momentum/value/volatility)
    - feature_exploration.py（forward returns, IC, rank, summary）
  - ai/*.py, research/*.py 等: 各種ユーティリティ・主要処理実装

貢献・開発
- コードは PEP8 等のスタイルに従っており、テストの容易性を考慮して依存注入（APIキーや HTTP 呼び出しの差し替え）が可能な設計になっています。
- モック化しやすい箇所（_call_openai_api、_urlopen 等）があり、ユニットテストを作成しやすい構造です。

ライセンス / 注意
- （この README はコードベースの説明用です。実際のライセンス表記や利用規約はリポジトリに従ってください。）
- 本ソフトウェアを実際の資金運用に用いる場合は十分な検証と運用監査を行ってください。金融取引や API 利用に伴う責任は利用者側にあります。

補足（よく使う Settings）
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.slack_bot_token / settings.slack_channel_id
- settings.duckdb_path / settings.sqlite_path
- settings.env （development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化可能

README は以上です。必要ならセットアップスクリプト例、.env.example、よくある運用手順（cron/airflow で ETL 実行など）を追加で作成します。どの情報を優先して追加しましょうか？