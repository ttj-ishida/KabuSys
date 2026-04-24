KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を目的とした Python パッケージです。本リポジトリには以下の主要機能を持つモジュール群が含まれます。

- 実行エンジン (ExecutionEngine) — 発注・注文管理・リスク管理
- 監視 (Monitoring) — システム状態、注文状況、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースのセンチメント評価、レジーム判定：OpenAI を利用）
- 開発用ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）

主要な設計方針：
- DuckDB / SQLite を用いてデータを保存・分析（設定でパスを変更可）
- 本番/ペーパートレードを環境変数で切替可能（DB 分離）
- ログはコンソール＋日次ローテートファイルに出力
- 外部 API（OpenAI など）呼び出しは失敗してもフェイルセーフで継続

機能一覧
--------
- 設定管理
  - .env の自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine の起動スクリプト（run_execution）
  - paper_trading モードで MockBrokerClient を使い、専用 DB に記録
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部停止指示（Kill Switch）
  - 監視用 DB スキーマの初期化（monitoring_db）
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（リスクベース等）
  - セクター上限、レジーム乗数の適用
- リサーチ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB ベース）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - ニュースセンチメントのスコアリング（news_nlp.score_news）
  - マクロ＋ETF 指標を用いた市場レジーム判定（regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順（開発用）
------------------------
1. リポジトリをクローン（既にパッケージ構成済みと仮定）。
2. Python 仮想環境を作成・有効化（例: Python 3.10+ 推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（プロジェクトに requirements.txt がある想定、なければ手動）
   - pip install duckdb psutil openai
   - optional: PyYAML（config 検証で YAML のパースを行う場合）
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（下記「主要環境変数」参照）
5. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict
6. データディレクトリ（デフォルト）を作成:
   - mkdir -p data logs

主要な環境変数（代表例）
-----------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（paper_trading モードで使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（デフォルト 0）

使い方（起動例）
----------------

- 実行エンジンを起動（通常はサービスとして起動）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、デフォルトで data/paper_trading.db に記録されます。
    - プロセス PID は data/execution.pid（Settings の pid_file_path により変更可）に書き込まれます。
    - 停止は data/stop_requested.flag を作成することでスレッドを安全に停止します（run_execution がこのファイルを監視します）。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 備考:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する点に注意（設計上の意図）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ライブラリ呼び出し例）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

停止 / Kill Switch
------------------
- 外部から実行エンジンを停止したい場合:
  - data/kill.flag に理由を書き込む（KillSwitch が評価している場合、ExecutionEngine による停止を誘発）
- run_execution / run_monitoring の強制停止:
  - data/stop_requested.flag を作成するとループが安全に終了します（両スクリプトで使用）

ログ
----
- デフォルトで logs/ ディレクトリにアプリケーションごとの日次ログ (例: logs/execution.log, logs/monitoring.log) が作成されます。
- ローテーションは日次、30日分保持。
- コンソールログは stdout に出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの主要な階層は以下の通り（抜粋）。実際のファイルは src/kabusys 以下に配置されています。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度設定ユーティリティ
    - execution/               — 発注・リスク・レポジトリ等（Engine 実装）
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - ...
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/ (runtime 用、リポジトリに含めるかは運用次第)
      - monitoring.db (デフォルト SQLITE_PATH)
      - paper_trading.db (paper_trading 用)
      - kill.flag, stop_requested.flag, execution.pid

注意事項 / 運用上のポイント
-------------------------
- monitoring は設計上「本番監視」目的のため、run_monitoring は常に本番 sqlite_path を使います。ローカルテストのときは注意してください。
- Paper Trading は DB を分離するため、KABUSYS_ENV=paper_trading を使えば実際の発注を行わずに動作検証できます。
- OpenAI を用いる AI 機能は API キーが必要です。API の失敗時はフェイルセーフでスコアにデフォルトを使う設計ですが、API 使用量には注意してください。
- logs/ と data/ ディレクトリは適切な権限でサービスユーザが書き込み可能であることを確認してください。
- .env はセキュアな情報（API トークン等）を含むため Git にコミットしないでください（config_setup.py のヘッダにも警告があります）。

貢献 / テスト
--------------
- 開発やテスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化できます（テストケース等で便利）。
- 各モジュールは可能な限り副作用を抑えた純粋関数または小さな責務で設計されています。ユニットテストを追加する場合は OpenAI 等の外部呼び出しをモックしてください。

---

この README はリポジトリ内の主要なスクリプト・モジュールの概要と使い方をまとめたものです。実際の運用に当たっては config/*.yaml（存在する場合）や .env の設定を必ず確認し、python -m kabusys.validate_config で起動前チェックを行ってください。必要であれば各モジュールの docstring を参照してください。