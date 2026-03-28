KabuSys
======

バージョン: 0.1.0

概要
----
KabuSys は日本株を対象としたデータプラットフォーム／自動売買補助ライブラリです。  
主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーの差分 ETL（DuckDB への保存・品質チェック）
- RSS ニュース収集と OpenAI を使ったニュースセンチメント（ai_score）算出
- マーケットレジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- 研究用ユーティリティ（ファクター計算、forward returns、IC、統計ユーティリティ 等）

設計上の特徴
- Look-ahead bias を避けるため、内部処理で date.today() / datetime.today() に依存しない実装が多い
- DuckDB を利用したローカルデータレイヤ（冪等保存／トランザクション管理）
- J-Quants / OpenAI への堅牢な API 呼び出し（レート制御・リトライ・トークンリフレッシュ）
- ニュース収集における SSRF 対策・XML パース安全化（defusedxml）や受信サイズ制限
- ETL・品質チェックは失敗しても可能な限り継続するフェイルセーフ設計

主な機能一覧
- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl (kabusys.data.pipeline)
  - J-Quants クライアント：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存関数：save_daily_quotes, save_financial_statements, save_market_calendar
- データ品質チェック
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks (kabusys.data.quality)
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job (kabusys.data.calendar_management)
- ニュース収集・NLP
  - fetch_rss, preprocess_text (kabusys.data.news_collector)
  - score_news (銘柄別ニュースセンチメントを ai_scores テーブルへ書込) (kabusys.ai.news_nlp)
- 市場レジーム判定
  - score_regime (1321 の MA200 乖離とマクロセンチメントを合成) (kabusys.ai.regime_detector)
- 研究用ツール
  - calc_momentum / calc_volatility / calc_value (kabusys.research.factor_research)
  - calc_forward_returns / calc_ic / factor_summary / rank (kabusys.research.feature_exploration)
  - zscore_normalize (kabusys.data.stats)
- 監査ログ初期化
  - init_audit_schema / init_audit_db (kabusys.data.audit)
- 設定管理
  - kabusys.config.Settings: 環境変数経由の設定読み込み（.env 自動ロード機能付き）

必要条件（想定）
- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他プロジェクト固有で必要なパッケージがある場合は pyproject.toml を参照）

セットアップ手順
--------------
1. リポジトリをクローン / コピー
   - 通常の Python パッケージ構成（src/）になっています。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - または pyproject.toml / requirements.txt がある場合はそれに従ってください。
   - 開発向け：pip install -e .   （プロジェクトを編集しながら使う場合）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（設定は kabusys.config が行います）。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 (.env)
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi

   注意: 必須項目は Settings で _require() によって確認されます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。

使い方（簡単な例）
-----------------

共通準備（DuckDB 接続）
- Python スクリプト内で DuckDB 接続を作成して関数に渡します:

  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ファイル DB（ディレクトリは存在させておく）
  # または conn = duckdb.connect(":memory:")

ETL を実行する（日次）
- 日次 ETL（カレンダー取得 → 株価取得 → 財務取得 → 品質チェック）:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

個別 ETL 実行
- 価格データのみ差分 ETL:

  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))

ニュース取得とスコアリング
- RSS フィードを収集して raw_news に保存する処理は news_collector を使用（アプリ側で収集スケジューリングする想定）。
- OpenAI を使ったニューススコアリング（銘柄別 ai_scores への書き込み）:

  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数または api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {n_written} ai_scores")

マーケットレジーム判定
- ETF(1321) の MA200 とマクロニュースの LLM スコアを合成して market_regime テーブルに保存:

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

監査ログ DB 初期化
- 監査ログ用の DuckDB を初期化してスキーマを作成:

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions 等が作成されます

設定参照
- アプリケーション設定は kabusys.config.settings から参照できます:

  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  if settings.is_live:
      ...

自動環境変数読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env と .env.local を自動読み込みします。
- 読み込み順: OS環境変数 > .env.local > .env
- テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

監視・ログ
- 設定 LOG_LEVEL によりログレベルを制御します（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- KABUSYS_ENV は development / paper_trading / live のいずれか。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外にも strategy / execution / monitoring などのパッケージ公開が __all__ に見えますが、今回のコードベース内で注目すべきは data / ai / research 周りです。）

設計上の注意点・運用のヒント
- Look-ahead バイアス防止：多くの関数が target_date を明示的に受け、内部で現在時刻を不用意に参照しないようになっています。バックテスト時は適切な過去時点の DB スナップショットを利用してください。
- 冪等性：ETL の保存処理は ON CONFLICT DO UPDATE 等の冪等実装になっています。複数回実行しても上書きで安全に運用できます。
- エラーハンドリング：外部 API 呼び出しはリトライやフェイルセーフ（失敗時はスキップして続行）を採用しています。重大エラーはログに記録されるため運用時にはログの監視を行ってください。
- セキュリティ：news_collector は SSRF 対策・XML の安全なパーサーを利用し、受信サイズ制限を行います。外部から渡す URL には注意を払い、不用意な URL を処理しないでください。
- テスト時のフック：OpenAI や HTTP 呼び出し部分は内部関数をパッチしてモックしやすく設計されています。

ライセンス / 責任
- 本プロジェクトは金融データ・外部 API を扱います。実際の売買に使用する場合は十分な検証とリスク管理を行ってください。API キーや認証情報は安全に管理してください。

フィードバック / 貢献
- バグ修正や機能提案があれば Pull Request / Issue を送ってください。ドキュメント改善も歓迎します。

以上。README に記載してほしい追加項目（使用例、CI、テスト方法、pyproject 設定など）があれば教えてください。