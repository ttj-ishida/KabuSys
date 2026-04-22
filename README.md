# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）です。  
この README はリポジトリ内の主要モジュールに基づき、日本語で使い方・セットアップ手順・ディレクトリ構成などをまとめたものです。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（コマンド例）
- 環境変数（主要）
- ディレクトリ構成
- その他の注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python パッケージです。
- 実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築、リサーチ（ファクター計算、特徴量探索）、AI（ニュース NLP / レジーム判定）などの機能を含みます。
- sqlite / DuckDB をデータ永続化に利用し、OpenAI を用いた NLP（任意）機能を備えます。
- KABUSYS_ENV によって動作モードを切り替えられ、paper_trading モードでは発注 API をモックして本番 DB と分離して動作可能です。

---

主な機能一覧
- Execution
  - ExecutionEngine（発注実行の起動スクリプト: run_execution.py）
  - Broker クライアントの切り替え（paper_trading では MockBrokerClient）
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler 等の実装
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - 監視データの永続化（monitoring_db.py）
  - Kill Switch：閾値超過で data/kill.flag により ExecutionEngine を停止させる仕組み
  - stop_requested.flag による停止制御等
- Portfolio construction
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリ
- AI
  - ニュースのセンチメントスコアリング（OpenAI 使用）: kabusys.ai.news_nlp.score_news
  - レジーム判定（ma200 + マクロニュース）: kabusys.ai.regime_detector.score_regime
- Tools
  - config_setup.py: 対話式の .env 設定ウィザード
  - validate_config.py: 起動前に設定・ファイルを検証する CLI
  - tools/paper_verification_report.py: ペーパートレードログから検証レポートを生成
- Utils
  - ロギング設定（ローテートファイル + stdout）: utils.logging_setup.setup_logging
  - プロセス優先度 / CPU affinity 設定ユーティリティ: utils.process_priority
  - 環境読み込みロジック（.env の自動読み込み）: config.py

---

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントの union 演算子 `|` を使用）。
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 追加で YAML 検証を行う場合: pip install PyYAML
   - （リポジトリに requirements.txt があれば pip install -r requirements.txt を使用）
4. プロジェクトルートを決定
   - config.py は __file__ を起点に .git / pyproject.toml を探索してプロジェクトルートを特定します。通常リポジトリルートで実行してください。
5. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後: python -m kabusys.validate_config で検証（--strict を付けると警告もエラー扱い）
6. データディレクトリ
   - デフォルトの DB / PID / フラグなどは data/ 下に置かれます。必要に応じて .env で上書きしてください。
   - 例: data/monitoring.db（SQLite）, data/kabusys.duckdb（DuckDB）, data/execution.pid, data/kill.flag
7. OpenAI を使う機能を利用する場合
   - OPENAI_API_KEY 環境変数を設定するか、関数に api_key を渡してください。

---

主要な環境変数（抜粋）
- 必須（実行に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API 用
- 動作モード
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- ログ / DB パス
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading モード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_DIR — ログ出力先（デフォルト: logs/）
- AI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使うときに必要）
- その他
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効。production では "0" 推奨）
  - MONITOR_POLL_INTERVAL — run_monitoring 起動時のポーリング間隔（秒。デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動ロードを無効化

補足:
- config.py はプロジェクトルートの .env / .env.local を自動的に読み込みます（OS 環境変数が優先されます）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

使い方（コマンド例）
- 設定ウィザード（.env を作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL とする）: python -m kabusys.validate_config --strict
- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
    - run_monitoring は monitoring 用 DB（settings.sqlite_path）に接続し、定期的に SystemMonitor.check_once を呼びます
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH デフォルト）へ記録します
    - 実行中は data/execution.pid を扱い、data/stop_requested.flag による停止に対応します
    - kill.flag（data/kill.flag）は KillSwitch により ExecutionEngine の停止を要求するために使います
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（未指定時は env または data/paper_trading.db）
- AI 関連（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースのセンチメントを ai_scores テーブルへ書き込みます
    - api_key を指定しない場合は OPENAI_API_KEY 環境変数を参照します
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ判定結果を書き込みます
- ライブラリ関数の呼び出し例（リサーチ）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb"); results = calc_momentum(conn, date(2026,4,1))

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理、自動 .env ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
  - monitoring/
    - monitoring_db.py — 監視 DB 操作（SQLite）
    - monitoring_engine.py — 各 Monitor の束ね
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — （注文ログ関連の監視: ソース参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — （アラート送信管理: ソース参照）
  - execution/ — ExecutionEngine 関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・制限・単元丸め
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — 共通ロギング設定（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/monitoring_db.py など（SQLite スキーマ／API）

（上記はリポジトリに含まれる主要ファイルの抜粋です。すべてのファイルは src/kabusys 以下に配置されています。）

---

その他の注意点 / 運用メモ
- ロギング
  - setup_logging により stdout（StreamHandler）と logs/<app_name>.log（TimedRotatingFileHandler: 日次・30日保持）が設定されます。ログディレクトリは LOG_DIR またはデフォルト logs/ に作成されます。
- プロセス優先度
  - run_execution / run_monitoring の起動時に set_process_priority("high") が呼ばれます。権限不足で失敗しても警告が出て続行します。
- DB マイグレーション
  - init_monitoring_db は冪等にテーブルを作成し、既存 DB にカラムがない場合は ALTER TABLE でカラム追加を試みます。
- Kill Switch / Stop フラグ
  - kill.flag（Settings.kill_flag_path。デフォルト data/kill.flag）を書くことで ExecutionEngine に停止シグナルを送る仕組みがあります。KillSwitch は一度書くと上書きせず冪等に動作します。
  - stop_requested.flag（data/stop_requested.flag）を用いた手動停止もスクリプト側で検知します。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient によって行われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されて本番 DB と分離されます。
- 自動 .env ロード
  - config.py はプロジェクトルートの .env, .env.local を自動読み込みします（OS 環境変数が保護されます）。テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API の利用
  - AI 機能は外部 API（OpenAI）に依存します。API キー管理やレート制限、費用については運用時に注意してください。API 呼び出しはリトライとフォールバックを備えていますが、失敗時はフェイルセーフ（0.0 等）で続行します。

---

開発 / 貢献
- ローカルでの動作確認やユニットテストを追加する際は、環境変数や DB ファイルの配置に注意してください（特に本番 DB を誤って書き換えないよう paper_trading 用 DB を利用するか、環境変数でパスを変更してください）。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも明記）。

---

問い合わせ
- この README はコードベースの静的解析に基づいて作成しています。実装の詳細や未記載のモジュール（order_repository, alert_manager 等）の振る舞いはソースを参照してください。

以上。必要であれば README に追加したいサンプルコマンドや、より詳細な環境変数一覧、運用手順（デプロイ/サービス化）を追記します。どの情報を優先的に追記しましょうか？