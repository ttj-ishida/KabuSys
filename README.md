# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究パイプラインを想定したモジュール群です。  
主な機能は戦略リサーチ、ポートフォリオ構築、ポジションサイズ算出、発注実行（本番／ペーパートレード分離）、監視・アラート、ニュースのLLM解析などを含みます。

バージョン: 0.1.0

---

## 概要

- DuckDB を使った時系列データ解析（prices_daily / raw_financials 等）
- SQLite（監視ログ / 発注ログ / ペーパートレード用 DB）による永続化
- ExecutionEngine による発注実行（本番 / ペーパートレードを切替可能）
- MonitoringEngine によるプロセス・システム監視、Kill Switch、アラート通知
- ニュースの LLM（OpenAI）によるセンチメントスコアリングと市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証 等）
- ペーパートレード検証レポート生成ツール

---

## 主な機能一覧

- 環境設定管理
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - 自動 .env 読み込み（プロジェクトルートに .env/.env.local があれば優先度付きで読み込む。無効化可能）
- Execution
  - 本番 / ペーパートレードの分離（KABUSYS_ENV により挙動を切替）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - RiskManager / OrderManager / Reconciler / ExecutionEngine の組立てと起動（run_execution.py）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - MonitoringDB: system_status, trade_logs, positions, risk_logs, dashboard の永続化
  - Kill Switch：条件に応じて kill.flag を書き込み Execution を停止させる
- Portfolio（純粋関数群）
  - 候補選定、等重・スコア重み付け、セクター制限、レジーム乗数、ポジション数算出（単元丸め・キャップ処理）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - ニュース NLP（OpenAI）で銘柄別センチメントスコア作成（ai_scores テーブルへ書込）
  - 市場レジーム判定（ETF 指標 + マクロニュース LLM）
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 要件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai (ニュース/レジーム機能を使う場合)
- PyYAML（config YAML 検証を行う場合に推奨）
- sqlite3（標準ライブラリ）

（実行環境に応じて pip install duckdb psutil openai pyyaml などを行ってください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt がない場合は必要に応じて個別にインストール）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数設定（ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 対話形式で .env を生成・更新します。
   - 生成後、`python -m kabusys.validate_config` で検証してください。

注意:
- 自動で .env を読み込む仕組みがあり（プロジェクトルートの .env/.env.local）、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
- .env は絶対にバージョン管理（git）にコミットしないでください。

---

## 主な環境変数

必須（実行前に設定してください）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に関わる主な変数
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し、ペーパートレード用 DB に記録します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"0" または "1"）

---

## 使い方

### 1) 設定の準備と検証
- .env の作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  # 警告も FAIL 扱いにする場合:
  python -m kabusys.validate_config --strict
  ```

### 2) Monitoring を起動
- 監視ループを起動します（ポーリングは MONITOR_POLL_INTERVAL で制御）
  ```
  python -m kabusys.run_monitoring
  ```
- 停止方法:
  - 監視スクリプト自体はプロジェクトルートの data/stop_requested.flag を作成するとループを抜けます。
    ```
    touch data/stop_requested.flag
    ```
  - また Monitoring 内の KillSwitch は必要に応じて data/kill.flag を書き込み、Execution 停止を要求します（デフォルトパスは Settings.kill_flag_path）。

### 3) Execution を起動
- 実行エンジンを起動（本番かペーパーかは KABUSYS_ENV で制御）
  ```
  python -m kabusys.run_execution
  ```
- ExecutionEngine は data/execution.pid に PID を書きます。
- 停止:
  - data/stop_requested.flag を作ると run_execution の監視ループがエンジン停止を行います。
  - KillSwitch により data/kill.flag が書かれた場合、ExecutionEngine 側でこれを検知して安全に停止します（実装内で kill_flag_path を参照します）。

### 4) Paper Trading 検証レポート（ツール）
- デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション:
  - --db PATH で DB を直接指定可能

### 5) AI 機能
- OpenAI API を使うために OPENAI_API_KEY を環境変数に設定してください。
- ニュース NLP / レジーム判定はそれぞれ kabusys.ai.news_nlp.score_news、kabusys.ai.regime_detector.score_regime を DuckDB 接続と target_date を渡して呼び出します。
- API 呼び出しはリトライやフォールバックを備え、失敗時は安全に続行する設計です。

---

## 停止・Kill の仕組み

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py の起動ループはこのファイルの存在を定期チェックして終了します。手動で停止したい場合はこのファイルを作成してください。
- kill.flag（Settings.kill_flag_path、デフォルト: data/kill.flag）
  - Monitoring の KillSwitch が条件を満たした際に書き込むファイルで、ExecutionEngine に対して安全停止を要求するために使用されます。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアしますが、本番環境では 0 を推奨します。

---

## ロギング

- ログは標準出力（stdout）とファイルログ（logs/<app_name>.log）に出力されます。
- ログファイルは日次ローテーションで _BACKUP_COUNT（30日）保持されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- ログディレクトリは LOG_DIR 環境変数または引数で指定できます。

---

## ディレクトリ構成（主なファイル / モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースの LLM センチメント解析と ai_scores 書込
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化層
    - monitoring_engine.py — モニター群のポーリング統括
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 注文ログ監視（滞留・約定異常等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（flag 書込）
    - alert_manager.py — （アラート実装を含む想定）
  - execution/
    - execution_engine.py — 発注エンジン（EngineConfig, run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター / 研究用ユーティリティ
  - data/ (想定されるデータディレクトリ)
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（ペーパートレード用）
  - utils/
    - logging_setup.py — ログ統一設定
    - process_priority.py — プロセス優先度・CPU affinity 設定

※上記はソース内の主要ファイルを抜粋したものです。

---

## 補足・運用上の注意

- 本番環境（KABUSYS_ENV=live）の場合は特に .env の内容、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）、KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください。validate_config は live 時に追加の警告を出します。
- ペーパートレード（paper_trading）は本番 DB と分離され、デフォルトで data/paper_trading.db に記録されます。PAPER_TRADING_SQLITE_PATH で変更できます。
- OpenAI を利用する機能は API キーとコストに注意して使用してください。失敗時はフェイルセーフで動作するよう設計されていますが、API 利用は料金が発生します。
- ローカル運用では logs/ と data/ ディレクトリが自動作成されますが、権限やディスク容量に注意してください。
- run_monitoring と run_execution は両方起動して連携して動作する想定です。Monitoring が Execution を監視して必要時に kill.flag を書き込みます。

---

必要があれば README に実運用例（systemd ユニット例、cron 設定、Dockerfile、requirements.txt）や各モジュールの API 使用例（関数シグネチャ）を追加します。どの情報を優先して追加しましょうか？