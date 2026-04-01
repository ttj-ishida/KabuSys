# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP、ファクター計算、監査ログ・発注トレーサビリティ、マーケットカレンダーなど、戦略開発・実行に必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数一覧（.env からの自動読み込み）
- 注意事項

---

プロジェクト概要
- DuckDB をデータストアとして用い、J-Quants API からの株価・財務・市場カレンダーを差分取得して保存する ETL パイプラインを提供します。
- RSS ニュース収集、OpenAI を使ったニュースセンチメント評価、マーケットレジーム判定、ファクター計算（モメンタム・ボラティリティ・バリュー等）、データ品質チェック、監査（signal → order → execution のトレーサビリティ）など、量的運用に必要な機能を備えます。
- 設定は .env または環境変数から取得します。パッケージは自動でプロジェクトルートの .env / .env.local を読み込みます（無効化可）。

主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - market_calendar 管理と営業日判定ユーティリティ
  - news_collector: RSS 取得、前処理、raw_news 保存（SSRF 対策、サイズ制限、トラッキング除去）
  - data quality チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル初期化、専用 DB 初期化ユーティリティ
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア生成（ai_scores テーブルへ書込）
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュース（LLM）を合成して市場レジーム（bull/neutral/bear）を判定
  - リトライ・フェイルセーフやレスポンスバリデーションを実装
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env 自動読み込み、主要設定の取得（settings オブジェクト）

セットアップ手順（開発向け・ローカル実行）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境作成（推奨 Python 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （実運用では追加のパッケージやテストツールが必要になる可能性があります。requirements.txt がある場合は pip install -r requirements.txt を利用してください）
4. 環境変数の準備
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定します。
   - 自動読み込みはデフォルトで有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. DuckDB ローカル DB などデータディレクトリ作成（必要に応じて）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path）

使い方（簡単なコード例）
- 共通: DuckDB 接続生成
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行 (prices / financials / calendar を差分取得して品質チェック)
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（AI）スコア付け
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  - 戻り値は書き込んだ銘柄数（ai_scores テーブルに sentiment_score / ai_score を書き込む）

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))
  - volatility = calc_volatility(conn, target_date=date(2026,3,20))
  - value = calc_value(conn, target_date=date(2026,3,20))

- 監査ログスキーマ初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/monitoring.duckdb")
  - これで signal_events / order_requests / executions テーブルとインデックスが作成されます

注: これらの関数はデータベースの特定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime 等）を期待します。初回はスキーマ作成や初期ロードが必要です（スキーマ作成ユーティリティは別途用意されている想定）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py                 (score_news を公開)
    - news_nlp.py                 (ニュース NLP / OpenAI 呼び出し、score_news)
    - regime_detector.py          (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - pipeline.py                 (ETL パイプライン、run_daily_etl 等)
    - etl.py                      (ETLResult の再エクスポート)
    - jquants_client.py           (J-Quants API クライアント: fetch/save 系)
    - news_collector.py           (RSS 取得、前処理、raw_news 保存)
    - calendar_management.py      (market_calendar 管理、営業日ユーティリティ)
    - quality.py                  (データ品質チェック)
    - stats.py                    (zscore正規化 等)
    - audit.py                    (監査ログ DDL / 初期化)
  - research/
    - __init__.py
    - factor_research.py          (calc_momentum / calc_volatility / calc_value)
    - feature_exploration.py      (calc_forward_returns / calc_ic / factor_summary / rank)
  - monitoring/ (パッケージ公開に含まれるがここでは省略)
  - strategy/ (戦略・実行関連は別モジュールで実装想定)
  - execution/ (発注/ブローカー統合は別モジュールで実装想定)

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行プロセス PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると config の自動 .env ロードを無効化

注意事項 / 実運用上のポイント
- OpenAI/API キーや J-Quants トークンはセキュアに管理してください。リポジトリに含めないでください。
- ai モジュールは外部 API に依存するため、テストや CI ではレスポンスをモックすることを推奨します（ソース内でモックポイントが用意されています）。
- DuckDB のスキーマ・テーブルは ETL 実行前に作成しておく必要があります（スキーマ初期化用ユーティリティを別途用意することを推奨）。
- データ品質チェックは fail-fast ではなく問題の集約を行います。ETL 呼び出し側で結果に応じた運用判断を行ってください。
- news_collector は SSRF 対策（リダイレクト検査・プライベート IP の拒否など）やレスポンスサイズ制限を実装していますが、外部ソースは常に信頼できないため運用では注意が必要です。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。CI やテストで挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

---

追加情報 / 今後の拡張
- strategy / execution / monitoring モジュールの実装（発注ロジック、ポジション管理、監視エージェント）
- バックテスト用ユーティリティ、パラメータ最適化ツール
- 監査ログからの可視化ダッシュボード

---

問い合わせ / 貢献
- バグ報告や機能要望は Issue を作成してください。Pull Request は歓迎します。README に載せる情報や使用例の追加も歓迎します。

以上。README の内容はコードベースの現在の実装に合わせてまとめています。必要であれば、実行例の追加、requirements.txt の作成、スキーマ初期化スクリプトのサンプルなどを追記します。