# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）。

この README はリポジトリ内の主要スクリプト・モジュールの目的、セットアップ、実行方法、ディレクトリ構成をまとめたものです。開発・テスト・本番（paper_trading / live）での動作差分や重要な環境変数についても記載しています。

---

## プロジェクト概要

KabuSys は日本株自動売買プラットフォームのコンポーネント群です。主な責務は以下：

- 市場データ / ファクター計算（research）
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算（portfolio）
- 発注エンジン（ExecutionEngine）および発注管理・リスク管理（execution）
- 監視・アラート・Kill Switch（monitoring）
- ニュース NLP を用いた AI スコアリング・レジーム判定（ai）
- 運用補助ツール（config ウィザード / 設定検証 / 検証レポート 等）
- ロギング・プロセス優先度等ユーティリティ（utils）

設計上の方針：
- 本番 DB とペーパートレードは分離（KABUSYS_ENV=paper_trading の場合は専用 SQLite を使用）
- DuckDB を分析用に使用（prices_daily / raw_financials 等）
- LLM（OpenAI）呼び出しは失敗時に安全側のフォールバックを行う（フェイルセーフ）
- .env 自動読み込み/設定ウィザード/検証 CLI を備える

---

## 主な機能一覧

- ExecutionEngine（発注処理）
  - 実口座 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リスク制御（RiskManager）、オーダー管理（OrderManager）
  - 実行スレッド管理・PID 管理（data/execution.pid）

- Monitoring（監視）
  - SystemMonitor: CPU・メモリ・ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 発注/約定ログの監視（滞留注文・異常約定の検出）
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件を満たした場合に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB：SQLite に監視ログ・トレードログ・リスクログ・ダッシュボードを永続化

- Research（因子計算・解析）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）等の解析ツール

- AI（OpenAI を利用）
  - news_nlp: ニュース記事の銘柄単位センチメントを LLM でスコアリングし ai_scores に書き込み
  - regime_detector: ETF の MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定

- Tools
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env および config/*.yaml の起動前チェック
  - paper_verification_report: ペーパートレード検証レポート生成

- Utils
  - logging_setup: 一貫したログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 管理

---

## セットアップ手順

前提：
- Python 3.9+（実装によっては 3.10+ を推奨）
- 必要なネイティブライブラリ等は OS に依存（psutil 等）

1. リポジトリをクローンして作業ディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使用してください（このサンプルコードでは明示的ファイルはないため、主要ライブラリを列挙します）。
   ```
   pip install duckdb psutil openai
   # 開発/検証用
   pip install PyYAML
   ```

4. .env の準備
   - 推奨：対話式ウィザードで作成
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合は .env.example を参照してください（必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
   - 自動読み込み:
     - デフォルトでプロジェクトルートの `.env` と `.env.local` が自動的に読み込まれます。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

6. ログディレクトリ・DB ファイル
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - カスタマイズは環境変数 `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `LOG_DIR` 等で上書き可能。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール用）
- PAPER_FILL_MODE（paper_trading のフィルモード: instant | partial | never | reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1、本番は 0 推奨）

監視ループのポーリング間隔（Monitoring の起動時に環境変数で上書き可能）:
- MONITOR_POLL_INTERVAL（秒、デフォルト 60）

プロセス優先度・PID/flag パス:
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）

---

## 使い方（起動・実行例）

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Execution（発注エンジン）を起動
  - 通常（環境は .env の KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレードで起動する場合は KABUSYS_ENV を paper_trading に設定してください（ペーパートレード時は専用 DB に記録され、本番 DB と分離されます）。

  実行時の注意:
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
  - 起動前に data/stop_requested.flag が存在すると起動を行いません（安全措置）。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成または KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこれらのフラグを監視して停止処理を行います。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数を設定（秒）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - Monitoring は監視用 SQLite（Settings.sqlite_path）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使用します（設計上）。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラム API）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

---

## 停止・Kill Switch の仕組み

- 手動停止：プロジェクトルートの data/stop_requested.flag を作成すると、run_monitoring / run_execution のループが検知して終了または停止処理を行います。
- 自動停止（KillSwitch）：Monitoring 側の KillSwitch がリスク条件（ドローダウン超過・ポジション上限超過等）を検出すると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。 kill.flag の有無は Settings.kill_flag_path で指定可能（デフォルト: data/kill.flag）。
- 実行時の起動スクリプトは、起動時に kill_flag_clear_on_start が 1 に設定されていると自動で kill.flag をクリアしますが、本番では 0 を推奨します（誤起動による自動クリアを防ぐため）。

---

## ログ

- logging_setup によりルートロガーを設定します。出力先は
  - コンソール（stdout）
  - 日次ローテーションされたファイル（デフォルト logs/<app_name>.log、30日分保持）
- ログレベルは引数（setup_logging に渡す）→ 環境変数 LOG_LEVEL → デフォルト INFO の順で決定されます。
- LOG_DIR 環境変数でログディレクトリを指定できます。

---

## データベース（マイグレーション挙動）

- monitoring_db.init_monitoring_db は冪等的にテーブルを作成します（存在チェックつき）。
- 既存 DB に対して後方互換のための簡易マイグレーションを行います（例: dashboard に peak_value を追加、trade_logs に latency_ms を追加）。
- Paper trading は settings.is_paper に応じて paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し、本番の SQLite と分離します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割（このリポジトリに含まれるファイル群に基づく）：

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/設定管理（.env 自動読み込みロジックを含む）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py — 監視用 SQLite のスキーマ + DB 操作ラッパー
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 発注ログ監視（ファイル内に実装あり）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書込ロジック
    - monitoring_engine.py — 各 Monitor を束ねるループロジック
    - alert_manager.py — LINE 等への通知（ファイル内に実装あり）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（起動/セッション管理）
    - broker_factory.py — ブローカークライアント生成（Mock と実ブローカーの切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理・永続化・リスク制御
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 特徴量と将来リターンの分析ツール（IC 等）
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA と マクロセンチメントの合成）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
    - ほかユーティリティ集合

（実際のリポジトリではさらに細分化されたファイルや追加モジュールがある場合があります。）

---

## 開発時の注意点 / よくある質問

- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- OpenAI API 呼び出しはコストがかかるため、開発時はモック関数で置き換えることを推奨します（news_nlp._call_openai_api 等はテスト時に patch 可能）。
- Monitoring は監視用 DB のパス（SQLITE_PATH）を使用します。Monitoring は KABUSYS_ENV に依存せず監視用 DB を利用するため、本番監視とペーパートレードの監視データの混在に注意してください（設計上、本番 sqlite_path を使用する実装になっています）。
- ペーパートレード時の挙動は PAPER_FILL_MODE 等で調整可能です（instant, partial, never, reject）。

---

## 参考コマンドまとめ

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動（デフォルト 60 秒間隔）
  ```
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はリポジトリ内のコードを参照して要点をまとめたものです。各モジュールの詳細な使用法や API は該当ソースコード（特に execution/*、monitoring/*、ai/*、research/*）のドキュメント文字列（docstring）をご参照ください。追加の説明やサンプルが必要であればお知らせください。