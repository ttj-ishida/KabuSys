KabuSys
=======

日本株向けのデータプラットフォーム / 自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、研究用ファクター計算、監査ログ用スキーマなどを含むモジュール群を提供します。

要点
- DuckDB をデータレイク / 一時 DB として利用
- J-Quants API から株価・財務・市場カレンダーを差分取得して保存
- RSS ベースのニュース収集と OpenAI（gpt-4o-mini）による銘柄センチメント / マクロセンチメント評価
- 研究用ファクター（モメンタム、ボラティリティ、バリュー）や統計ユーティリティを提供
- 発注・約定のトレーサビリティを担保する監査スキーマを DuckDB に初期化する機能

主な機能一覧
- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（差分取得・冪等保存・認証・レート制御・リトライ）
  - market calendar 管理と営業日ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - ニュース収集（RSS）: フィード取得 → 前処理 → raw_news へ保存（SSRF / Gzip / サイズ制限 等の対策あり）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（signal_events / order_requests / executions）のスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime を算出
  - 両関数とも OpenAI クライアント（gpt-4o-mini）を利用し、リトライやフェイルセーフを組み込んでいる
- research
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み & Settings（.env 自動ロード、必須チェック、はずせる自動ロードフラグ）

セットアップ手順（開発環境向け）
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（代表例）
   - DuckDB、OpenAI SDK、defusedxml などが必要です。プロジェクトに requirements ファイルがある場合はそちらを使用してください。
     例:
     - pip install duckdb openai defusedxml

   - 開発インストール（パッケージとして利用する場合）
     - pip install -e .

3. 環境変数（.env）設定
   - リポジトリのプロジェクトルートに .env または .env.local を置くと自動読み込みされます（自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須のキー（主要）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知実装がある場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - オプション（デフォルトあり）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite path（監視等で使用）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - 例 (.env)
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=yourpassword
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

4. データベース初期化（監査ログ用）
   - 監査ログ専用 DB を作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 既存接続にスキーマを追加する:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

使い方（簡易サンプル）
- ETL（日次パイプライン）を実行して J-Quants からデータを取り込む:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（OpenAI を用いる）を実行:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定しておく
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)

- 市場レジームスコアを計算:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算:
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  print(len(momentum))

設定関連の注意点
- 自動 .env ロードは package 内の config モジュールで行われます。テストなどで自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラスは必須キーが未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を想定しており、レスポンスパース失敗や API エラー時は フェイルセーフ（スコア 0 やスキップ）で継続する設計です。

開発・テストのヒント
- ai モジュールの OpenAI 呼び出し部分は内部関数を独立実装しており、ユニットテスト時には該当関数（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）をモックすることを想定しています。
- news_collector ではネットワーク・XML パース・SSRF 対策が組み込まれているため、外部アクセスを伴うテストはモックやローカルファイルを用いるとよいです。
- DuckDB を使うため、SQL クエリの結果型に注意（date 型など）。テスト時は ":memory:" 接続も可能です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定読み込み
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py             # ニュースセンチメント処理（OpenAI）
    - regime_detector.py      # 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得 / 保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - calendar_management.py # 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      # RSS 取得・正規化・保存
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログスキーマ（init_audit_schema / init_audit_db）
    - etl.py                 # ETLResult の再輸出
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank

ライセンス / 貢献
- （この README にライセンス・貢献ルールは含まれていません。実際のリポジトリに LICENSE / CONTRIBUTING を追加してください。）

付録: よくある問題と対処
- OpenAI の API エラーやタイムアウト
  - ライブラリはリトライとフェイルセーフを備えています。繰り返す場合は API キーやレート制限を確認してください。
- J-Quants の 401 エラー
  - refresh token の設定（JQUANTS_REFRESH_TOKEN）を確認。jquants_client は 401 を検知するとトークンを自動リフレッシュして再試行します。
- DuckDB の executemany が空リストを受け付けない
  - モジュール内で空リストをチェックして回避していますが、外部から呼ぶ場合も params が空でないことを確認してください。

以上が本リポジトリの概要と導入・実行手順です。特定の機能について詳しい使い方や API の例が必要であれば教えてください。