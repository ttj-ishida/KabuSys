# KabuSys

日本株自動売買システムのパッケージ（ライブラリ兼起動スクリプト群）。

この README はリポジトリ内の主要なモジュールと実行手順を簡潔にまとめたものです。
（詳細はソースコードの docstring / コメントも参照してください）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な機能は以下を含みます。

- マーケットデータ（DuckDB）を使ったファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード対応）
- 監視（Monitoring）コンポーネントによるシステム状態・注文状態・リスク監視と Kill Switch
- AI ツール（OpenAI）を用いたニュースセンチメント評価、レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポート）

---

## 機能一覧

- 設定管理
  - .env の自動読み込み（.env / .env.local、必要に応じて無効化可能）
  - Settings クラスによる環境変数ラップ

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker を使用、専用 DB）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）

- 監視 / リスク管理
  - MonitoringDB: SQLite に監視ログを永続化
  - SystemMonitor: CPU/MEM/Disk、データ鮮度、プロセス生存チェック
  - TradeMonitor: 注文の滞留/約定異常などをチェック（ソース参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、リスクイベント記録
  - KillSwitch: 条件で data/kill.flag を書き ExecutionEngine 停止を指示
  - MonitoringEngine: 各 Monitor を統合してポーリング・通知

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等重 / スコア重み（calc_equal_weights / calc_score_weights）
  - 単元・資金制約を考慮した株数算出（calc_position_sizes）
  - セクター制限、レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC（Information Coefficient）計算
  - 単体関数群は DuckDB 接続を受け取って動作

- AI
  - news_nlp.score_news: raw_news を LLM（OpenAI）で評価して ai_scores に書き込み
  - regime_detector.score_regime: ETF(ma200) とマクロニュース（LLM）を合成してレジーム判定

- ツール
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

1. Python 環境
   - Python 3.10 以上を推奨（ソースは typing 構文等を使用）
   - 仮想環境を作成してアクティベートしてください

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリのインストール（代表例）
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（validate_config の YAML 検証を行う場合）
   - その他: sqlite3 は標準ライブラリ

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. リポジトリルートで .env を作成
   - 対話式:
     ```
     python -m kabusys.config_setup
     ```
   - または .env.example を参考に手動で作成
   - 自動読み込みはデフォルトで有効。自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
   ```

5. ディレクトリ作成
   - デフォルトで data/ や logs/ を使用します。権限・所有権を確認してください。
   - 例:
     ```
     mkdir -p data logs
     ```

6. OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、ai 関数へ api_key を渡してください。

---

## 使い方（代表的なコマンド）

- 実行エンジン起動（本番 / ペーパートレード）
  - 本番（KABUSYS_ENV=live）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 注意:
    - run_execution は起動時にプロセス優先度を "high" に設定します（set_process_priority）。
    - paper_trading の場合は paper 専用 SQLite を使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    export MONITOR_POLL_INTERVAL=30  # 30秒間隔
    ```
  - monitoring は環境にかかわらず本番 sqlite_path を使用します（監視ログは共有される想定）。

- 停止制御
  - run_* スクリプトはプロジェクト内 data/stop_requested.flag の検出で安全終了します。
  - Kill Switch（重大リスク時）は data/kill.flag を書き込み、ExecutionEngine に停止指示を出します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（本番では 0 推奨）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- ライブラリ API（例）
  - ポートフォリオ関数:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```
  - リサーチ:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```
  - AI:
    ```
    from kabusys.ai import score_news
    # score_news(duckdb_conn, target_date, api_key=...) を実行
    ```

---

## 環境変数（主要なもの）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能で必須)

- システム / DB
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (logs ディレクトリの指定)

- 監視 / 動作
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数; default: 60)
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START

- Paper Trading の挙動
  - PAPER_FILL_MODE: instant | partial | never | reject

- 自動 env ロードの無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ログ・ファイル

- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（30 日分保持）。
- setup_logging() がアプリケーション共通のログ設定を行います（stdout とファイル両対応）。
- run_* スクリプトは起動時にプロセス優先度を高く設定し、PID ファイルや stop flag を扱います。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル / ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト

  - execution/                    — 実行エンジン関連（broker, engine, order_manager など）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用する SQLite / DuckDB ファイルやフラグファイルを格納する想定)
  - logs/ (ログ出力先。デフォルトで作成されます)

---

## 運用上の注意

- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知や監視設定を必ず確認してください。
- .env は絶対にバージョン管理にコミットしないでください。
- run_monitoring は監視用 DB に常に本番用 sqlite_path を使います（環境に依存せず監視を一元化する意図）。
- ExecutionEngine の停止は kill.flag により安全に指示できます。KILL_FLAG_CLEAR_ON_START の扱いに注意してください（本番では 0 推奨）。
- OpenAI を利用する機能は API へのアクセスコスト・レートリミットを考慮して運用してください（リトライ・バックオフ実装あり）。

---

必要であれば README を拡張して、各モジュールの詳細ドキュメント（API 仕様、設定項目の完全一覧、実運用のチェックリスト、systemd / supervisor の例など）を追加します。どの部分を詳しくしたいか教えてください。