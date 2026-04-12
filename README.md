KabuSys
======

KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。  
このリポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- Monitoring（プロセス・データ鮮度・注文監視、アラート送信）
- Research（ファクター計算・特徴量探索）
- AI 補助機能（ニュース NLP によるセンチメント、レジーム検出）
- ユーティリティ（設定読み込み・プロセス優先度設定など）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な機能
--------

- 発注の状態遷移管理とブローカー同期（Reconciler）
- Paper Trading と Live の環境分離（Paper 用 SQLite を利用）
- 監視ループ（System / Trade / Risk）と kill.flag による安全シャットダウン
- LINE Push による一方向アラート（AlertManager）
- DuckDB を用いた時系列・財務データのファクター計算・リサーチ
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（スコアを ai_scores に書き込み）
- Streamlit による運用向けダッシュボード
- Paper Trading の検証レポート生成ツール

セットアップ
------------

前提
- Python 3.9+（型アノテーションや pathlib の機能を利用）
- システムに duckdb, psutil がインストール可能であること
- OpenAI API を使う機能を使う場合は有効な API キー

仮想環境と依存関係（例）
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）:
   - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合はそれを利用してください）

環境変数 / .env
- .env/.env.local をプロジェクトルート（.git / pyproject.toml を基準に検出）から自動読み込みします。OS の環境変数が優先され、.env.local は .env の上書きに使えます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主な環境変数（デフォルトや必須有無の注記）:

  - KABUSYS_ENV: 起動環境（必須、開発時は "development"、Paper Trading は "paper_trading"、本番は "live"）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は通知をスキップ）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db） — Monitoring は環境にかかわらず本番 sqlite_path を使用します
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を消す（"1" で有効）
  - PAPER_FILL_MODE: Paper Trading の約定挙動（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）
  - LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
  - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト: 60）

使い方（主要スクリプト）
-----------------------

1) ExecutionEngine を起動（発注実行プロセス）
- コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が "paper_trading" の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
  - プロセス優先度を "high" に設定しようとします（psutil を使用）。
  - PID ファイル（Settings.pid_file_path）を使ってプロセス存在チェック／再起動時のリカバリ等に対応可能。
  - 起動時に KILL_FLAG_CLEAR_ON_START が "1" なら kill.flag を削除します。

2) Monitoring を起動（監視ループ）
- コマンド:
  - python -m kabusys.run_monitoring
- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。1 未満・不正値はデフォルトにフォールバックします。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行し、必要に応じて kill.flag を生成したり LINE 通知を行います。

3) Streamlit 監視ダッシュボード
- コマンド例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視用 SQLite を read-only で開いて、Positions / Orders / System / Overview を表示します。

4) Paper Trading 検証レポート（コマンドラインツール）
- コマンド例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - あるいは DB を直接指定: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 説明:
  - 指定期間の稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定します。

5) AI 関連（ニュースセンチメント / レジーム判定）
- News NLP スコアリング:
  - 使用関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（引数または OPENAI_API_KEY 環境変数）が必須
  - raw_news と news_symbols を集約して銘柄ごとに LLM に投げ、ai_scores テーブルへ書き込み
- レジーム判定:
  - 使用関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込み
- 注意:
  - LLM 呼び出しはリトライ・バックオフやレスポンスバリデーションを組み込んでいますが、API 制限やエラーには注意してください。

設定と運用上のポイント
----------------------

- Monitoring は常に本番監視 DB（SQLITE_PATH）を使う設計です。テスト環境から本番 DB を誤って上書きしないように環境変数を確認してください。
- ExecutionEngine は paper_trading 環境のときに別 DB（PAPER_TRADING_SQLITE_PATH）を使い、本番と完全分離します。
- kill.flag（Settings.kill_flag_path）を作成すると ExecutionEngine 停止の合図になります。KillSwitch は冪等で既存の flag を上書きしません。
- PID ファイル（Settings.pid_file_path）の扱いに注意。SystemMonitor は stale PID を検出して削除します。
- Process priority / CPU affinity の設定はプラットフォーム依存で許可が必要な場合があります（psutil の例外を安全に扱う実装済み）。
- DuckDB を使ったリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルが前提です。

ディレクトリ構成（主要ファイルと説明）
---------------------------------

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数読み込み、Settings クラス（アプリ設定）
- run_execution.py — ExecutionEngine 起動スクリプト（CLI 実行用）
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート（CLI）
- monitoring/
  - monitoring_db.py — SQLite テーブル定義 / MonitoringDB ラッパー（永続化）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねてポーリング実行
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード
- execution/
  - order_manager.py — Order の作成 / 送信 / 同期ロジック
  - reconciler.py — 起動時のリコンシリエーション（注文・ポジション突合）
  - (その他ブローカ関連・OrderRepository 等は同フォルダ内に存在します)
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 発注株数計算・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC/統計サマリ計算
- ai/
  - news_nlp.py — raw_news を LLM で集約評価し ai_scores へ書き込み
  - regime_detector.py — マクロ + MA200 でレジーム判定
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/monitoring_db.py など — DB スキーマ、マイグレーション処理、読み書きラッパー

その他の注意事項
----------------

- DB スキーマ変更のための簡易マイグレーション（監視 DB へのカラム追加）を行う処理が含まれます。運用時はバックアップを取ってください。
- OpenAI や外部 API の呼び出しは失敗に対してフォールバック（スコア 0.0 など）する設計ですが、API 利用料やレート制限には注意してください。
- Logging は基本 INFO レベル。デバッグが必要な場合は LOG_LEVEL=DEBUG を指定してください。
- テストや CI の際には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動ロードを抑止できます。

サンプル .env（プロジェクトルート）
----------------------------------
以下は一例です（必須値は環境や運用に合わせて設定してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant

ライセンス / 貢献
-----------------
（ここでは明示していません。実運用に使う場合は適切なライセンスや利用規約を追加してください。）

お問い合わせ / 開発
------------------
- コードを読むことで設計意図や細かい挙動が理解できるよう、各モジュールに詳細な docstring とログ出力が含まれています。実装や拡張を行う際は各モジュールの docstring を参照してください。

以上。必要であれば README に実際のコマンド例、環境変数テンプレート（.env.example）、および requirements.txt の生成（pip freeze → requirements.txt）を追記します。どの情報を追加しますか？