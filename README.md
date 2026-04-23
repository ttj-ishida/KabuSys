KabuSys — 日本株自動売買ライブラリ
================================

このリポジトリは日本株の自動売買システム群（データ処理・ファクター生成・ポートフォリオ構築・発注実行・監視・AI 補助機能）を集めた Python パッケージです。モジュールは単体で再利用可能な純粋関数群・永続化層・起動スクリプトに分かれており、本番（live）／ペーパートレード（paper_trading）／開発（development）を切り替えて運用できます。

主な特徴
--------
- 分離された DB：DuckDB（分析用）と SQLite（監視・注文ログ）を併用
- 発注エンジン（ExecutionEngine）と監視ループ（MonitoringEngine）の起動スクリプト
- Paper Trading 用のモックブローカーと専用 DB（data/paper_trading.db）で本番 DB と完全分離
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 等の統計解析）
- AI 補助：ニュースセンチメント（OpenAI）による銘柄スコアリング、レジーム判定
- 監視機能：システム／注文／リスク監視、Kill Switch（停止フラグ）と通知のトリガ
- ユーティリティ：.env ウィザード、設定検証、ログ設定ユーティリティ、プロセス優先度セット

機能一覧
--------
- 起動スクリプト
  - run_execution.py — 発注エンジンを起動（paper_trading では MockBrokerClient を使用）
  - run_monitoring.py — 監視ポーリングループを起動（システム状態・注文ログ・リスク監視）
- 設定管理・支援
  - config.py — 環境変数 / デフォルト値をまとめた Settings
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前の設定検証 CLI（--strict オプションあり）
- ポートフォリオ
  - portfolio.portfolio_builder — 候補選定・重み計算（等分・スコア加重）
  - portfolio.position_sizing — 株数計算（risk-based / equal / score）
  - portfolio.risk_adjustment — セクター上限適用・レジーム乗数
- リサーチ
  - research.factor_research — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research.feature_exploration — 将来リターン計算、IC・統計サマリー
- AI
  - ai.news_nlp — OpenAI を使ったニュースセンチメント＋ai_scores 書き込み
  - ai.regime_detector — MA + マクロセンチメントで市場レジーム判定
- 監視（monitoring）
  - monitoring.monitoring_db — SQLite による永続化層（テーブル作成・CRUD）
  - monitoring.system_monitor / trade_monitor / risk_monitor — 個別監視ロジック
  - monitoring.monitoring_engine — 監視コンポーネント統合
  - monitoring.kill_switch — 条件に応じた停止フラグ書き込み
  - monitoring.alert_manager — （通知統括：実装例あり）
- ツール
  - tools.paper_verification_report — ペーパートレード検証レポート生成（期間指定可）
- ユーティリティ
  - utils.logging_setup — 統一ログ設定（stdout + 日次ローテートファイル）
  - utils.process_priority — プロセス優先度・CPU affinity 設定ユーティリティ

セットアップ手順（開発環境）
--------------------------
※ 以下は一般的な手順例です。プロジェクトに requirements.txt 等があればそちらを参照してください。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は、少なくとも duckdb, psutil, openai, pyyaml（設定検証）等をインストールしてください）

4. .env を作成・編集
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     ウィザードは .env を作成します（.env を Git にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は .env や config/*.yaml を修正してください
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. ディレクトリの確認
   - data/ — DB ファイル・フラグファイル等を置く（自動作成されることが多い）
   - logs/ — ログが出力されます（utils.logging_setup が自動で作成）

主要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時に必要)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB: default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の fill 動作: instant|partial|never|reject; default: instant)
- LOG_LEVEL (default: INFO)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 秒; default: 60)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

自動 .env ロード
- パッケージロード時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。
- 無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

基本的な使い方
----------------

1. ExecutionEngine を起動（発注エンジン）
- 通常（本番/ペーパーの切替は KABUSYS_ENV で制御）:
  - python -m kabusys.run_execution
- 動作:
  - 起動時にプロセス優先度を "high" に設定（utils.process_priority）
  - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に stop flag が存在するとエンジンに停止命令を送る

2. Monitoring を起動（監視ループ）
- python -m kabusys.run_monitoring
- 動作:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は Settings に基づき本番 sqlite_path を使用（環境に依らず同じ監視 DB）
  - data/stop_requested.flag を検知するとループを終了

3. .env の作成
- python -m kabusys.config_setup

4. 設定検証
- python -m kabusys.validate_config
- --strict を指定すると警告があっても exit(1) になります

5. Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- デフォルト DB: data/paper_trading.db。--db で別パスを指定可能。

6. AI 機能の呼び出し（ライブラリ利用）
- ニュースセンチメント（プログラムから呼ぶ例）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

停止 / Kill Switch
- Kill Switch は monitoring.kill_switch.KillSwitch が data/kill.flag を書き込むことで ExecutionEngine に停止を要求します。
- 手動で停止させたい場合は data/kill.flag を作成すればよい（または KabuSys 側の管理ツール経由）。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動でクリアされます（本番では 0 推奨）。

ディレクトリ構成（主なファイル）
-----------------------------
(リポジトリ内 src/kabusys 以下を抜粋)

- kabusys/
  - __init__.py
  - run_execution.py                — 発注エンジン起動スクリプト
  - run_monitoring.py               — 監視ポーリング起動スクリプト
  - config.py                       — Settings（環境変数とデフォルト）
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）処理
    - regime_detector.py            — レジーム判定
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - (その他 execution/、data/ 等のモジュール群)

データ・ログファイル（デフォルトパス）
- DuckDB: data/kabusys.duckdb (DUCKDB_PATH)
- Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
- Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- Logs: logs/<app_name>.log
- フラグ / PID:
  - data/kill.flag (Kill Switch)
  - data/stop_requested.flag (手動停止リクエスト)
  - data/execution.pid (ExecutionEngine の PID)

実運用上の注意
--------------
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します（誤って自動クリアされるのを防止）。
- OpenAI キー等の外部 API キーは安全に管理してください。AI 呼び出しは失敗時にフォールバック（0.0 など）する実装になっていますが、商用運用では注意が必要です。
- DuckDB / SQLite のパスはバックアップ・ディスク容量に注意してください。monitoring は常に sqlite_path を使います（run_monitoring 参照）。

テスト・開発
------------
- 各モジュールは純粋関数（副作用を持たない関数）として実装されている箇所が多く、ユニットテストを書きやすい設計です。OpenAI 等の外部呼び出しは差し替え（モック）可能です（コード内にモック用の patch 指針あり）。
- validate_config.py による事前チェックで必須環境変数や YAML のパース等を確認できます。

ライセンス・貢献
----------------
- 本 README に記載の内容はコードベースの説明に基づく概要です。実際のライセンス・貢献ルールがリポジトリに含まれている場合はそちらを参照してください。

お問い合わせ / 追加情報
---------------------
- 実行方法や設定項目で不明点があれば、該当するモジュール（config.py / config_setup.py / validate_config.py / tools/*.py）を参照してください。各ファイルの冒頭 docstring に使い方が記載されています。