KabuSys
======

日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレース）などを含むユーティリティ群を提供します。

主な目的
- J-Quants API を用いた株価 / 財務 / 市場カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集 → OpenAI による銘柄センチメントのスコア化
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（Research 用）
- データ品質チェックと監査ログ（発注→約定のトレーサビリティ）
- kabu ステーションや Slack などとの連携ポイント（設定管理あり）

機能一覧
- data.jquants_client: J-Quants API の取得/保存（レート制限・リトライ・トークン自動リフレッシュ・ページネーション対応）
- data.pipeline: 日次 ETL（calendar / prices / financials）の実行エントリポイント run_daily_etl と ETLResult
- data.news_collector: RSS 取得・正規化・raw_news への保存ユーティリティ（SSRF 対策、トラッキング除去、XML セーフパース）
- ai.news_nlp.score_news: 指定日のニュースを銘柄ごとに集約して OpenAI でスコアリングし ai_scores に保存
- ai.regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- research.*: ファクター計算（momentum / volatility / value）や将来リターン、IC 計算、統計サマリ等
- data.quality: 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- data.audit: 監査ログ（signal_events, order_requests, executions）スキーマ初期化ユーティリティ
- config: .env 自動ロード（.env, .env.local）、Settings オブジェクトで環境設定を提供

前提 / 必要環境
- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI / RSS）
- DuckDB を利用（Python 用 duckdb パッケージ）
- 必要な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （その他、標準ライブラリのみを使うモジュールも多い）

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （もしパッケージ化済みなら）pip install -e .

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込みます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必要な主な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=...   # J-Quants の refresh token（get_id_token に使用）
- OPENAI_API_KEY=...         # OpenAI を使う処理で使用（score_news, score_regime 等）。関数引数でも渡せます。
- KABU_API_PASSWORD=...      # kabu ステーション連携（将来的なモジュールで使用）
- SLACK_BOT_TOKEN=...        # Slack 通知
- SLACK_CHANNEL_ID=...       # Slack チャンネル
- DUCKDB_PATH=data/kabusys.duckdb   # デフォルト DuckDB ファイルパス
- SQLITE_PATH=data/monitoring.db    # 監視用 sqlite パス
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...   # ログレベル

使い方（主要なコード例）
- DuckDB 接続を作って ETL を実行する（run_daily_etl）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコアリングを実行する
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定を実行する
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する（監査専用 DB）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って発注ログ関連の INSERT/SELECT を行えます

主要な API / エントリポイント
- data.pipeline.run_daily_etl(conn, target_date, ...)
- data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
- data.jquants_client.get_id_token / fetch_daily_quotes / save_daily_quotes / fetch_market_calendar / save_market_calendar
- data.news_collector.fetch_rss
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- data.quality.run_all_checks(conn, target_date=..., reference_date=...)
- data.audit.init_audit_schema / init_audit_db

設定管理の挙動（自動 .env 読み込み）
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env, .env.local を自動読み込みします。
- 読み込み優先度は OS 環境 > .env.local > .env。
- テスト等で自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定は kabusys.config.settings から参照できます（Settings クラスのプロパティ経由）。

注意点 / 設計方針の要約
- バックテストや統計処理で Look-ahead bias を避ける設計（target_date を明示し、date.today() を直接参照しない箇所が多い）
- API 呼び出しはリトライとエクスポネンシャルバックオフを備える（429/接続/タイムアウト/5xx などを想定）
- ETL・保存処理は冪等（ON CONFLICT / DO UPDATE）に配慮
- ニュース取得は SSRF 対策・XML セーフパース・応答サイズ制限を行う
- OpenAI とのやり取りは JSON mode を期待し、レスポンスのバリデーションを実施している（失敗時はスコア 0 にフォールバックする等のフェイルセーフ）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / Settings 管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュース NLP（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py             # RSS 収集・前処理
    - calendar_management.py        # マーケットカレンダー管理（営業日判定等）
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            # Momentum / Volatility / Value 等
    - feature_exploration.py        # 将来リターン / IC / 統計サマリ
  - ai/、research/、data/ 内にさらに補助関数やユーティリティが含まれます

補足
- OpenAI の API 呼び出し箇所では api_key を関数引数で注入でき、テスト時は内部の _call_openai_api をモックして差し替えられる設計になっています。
- J-Quants API の id_token は内部でキャッシュされ、自動リフレッシュの仕組みがあります。
- DuckDB のバージョンや SQL の互換性へ注意してください（コード中に DuckDB バージョンに依存する回避が含まれます）。

問い合わせ / 貢献
- バグ報告や機能改善の提案は GitHub の Issues / PR を通じてお願いします。README に記載のない運用ルールやデプロイ手順はプロジェクト内の別ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。

以上。必要であれば .env.example のテンプレートや具体的な実行スクリプト（cron / systemd / Dockerfile など）のサンプルを追記します。どの部分を優先的に補足しますか？