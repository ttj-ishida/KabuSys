# KabuSys

日本株向け自動売買システム（ライブラリ/ツール群）の README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主な関心事は以下です。

- 発注エンジン（ExecutionEngine）：実口座／ペーパートレードの発注フローを実装
- 監視（Monitoring）：プロセス/データ鮮度/取引ログなどのポーリング監視とアラート
- ポートフォリオ構築（Portfolio）：銘柄選定、重み付け、株数決定、リスク調整
- リサーチ（Research）：ファクター計算、将来リターン、統計解析
- AI ユーティリティ（AI）：ニュースのセンチメントスコアリング（OpenAI）
- ツール群：ペーパートレード結果の検証レポート生成など
- 設定ユーティリティ：対話式 `.env` ウィザードや設定検証 CLI
- 共通ユーティリティ：ロギング設定、プロセス優先度など

設計方針としては、可能な限り副作用を少なくして、DuckDB / SQLite を使ったデータ処理や、外部 API 呼び出し（kabuステーション、J-Quants、OpenAI）への疎結合を保つことを重視しています。

---

## 機能一覧（抜粋）

- Execution：
  - 実口座（live） / ペーパートレード（paper_trading）に対応
  - ペーパートレード時は専用 DB（data/paper_trading.db）に記録し、本番 DB と分離
  - BrokerClientFactory によるブローカークライアント生成
  - RiskManager / OrderManager / Reconciler を組み合わせた ExecutionEngine

- Monitoring：
  - SystemMonitor：CPU / メモリ / ディスク、データ鮮度、Execution プロセス生存を監視
  - TradeMonitor：取引ログの異常検知（滞留注文、約定異常など）
  - RiskMonitor：ドローダウン、ポジション上限などをチェックして risk_logs に記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記監視を統合して定期実行・アラート通知

- Portfolio：
  - 銘柄選定（スコア降順選択）
  - 重み算出（等配分・スコア加重）
  - 株数（lot）決定（リスクベース、配分ベース）、aggregate cap のスケーリング
  - セクターキャップ適用、レジーム乗数計算

- Research：
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC（Spearman rank）計算、ファクター統計
  - DuckDB を用いた高速集計

- AI：
  - news_nlp：raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出、ai_scores テーブルへ格納
  - regime_detector：ETF とマクロニュースを組み合わせて日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書込

- ツール：
  - config_setup：対話式で `.env` を生成/更新
  - validate_config：環境変数・config/*.yaml の検証（--strict あり）
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

- ユーティリティ：
  - logging_setup：stdout + 日次ローテートログを統一設定
  - process_priority：Windows/Linux の差分を吸収してプロセス優先度や CPU affinity を設定

---

## 前提・依存

最低限必要なパッケージ（例）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config 検証を行う場合)

実際の依存はプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。ローカル開発手順の一例は次節を参照。

---

## セットアップ手順（ローカル開発向けの例）

1. Python 環境準備（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai pyyaml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。

3. `.env` を作成（対話式ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
     対話に従って必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

   - 生成された `.env` は絶対に Git にコミットしないでください。

4. 設定検証（任意）
   - 基本検証:
     ```
     python -m kabusys.validate_config
     ```
   - 厳密モード（警告も失敗扱い）:
     ```
     python -m kabusys.validate_config --strict
     ```

5. 必要なディレクトリ作成（通常は起動時に自動作成されますが明示的に作ることも可）
   - data/
   - logs/

6. OpenAI を利用する場合は環境変数 OPENAI_API_KEY を設定

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト：development）
  - paper_trading の場合、MockBrokerClient を使い DB は分離されます
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、data/paper_trading.db に記録されます。
  - 停止方法: プロセスを終了するか、監視側が data/kill.flag を書き込むことで停止できます。
  - 実行中は PID ファイル（data/execution.pid）が作成されます。

- Monitoring 起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は monitoring DB（settings.sqlite_path）を使ってログを永続化します。監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。
  - 監視停止: プロジェクトルート下の data/stop_requested.flag を作成するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では .env に機密情報が含まれるため絶対にリポジトリに含めないでください。
- Monitoring は常に本番 sqlite_path を参照する点に注意（run_monitoring のドキュメントより）。
- run_execution は start 時に data/stop_requested.flag を検出すると起動しません。
- KillSwitch により data/kill.flag が書かれると ExecutionEngine に停止シグナルが送られます（監視側が書き込みます）。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリが作れない場合はコンソール出力のみになります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み / Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ・モジュール
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム / データ鮮度監視
  - trade_monitor.py — （取引監視、ファイルに示された）取引チェックロジック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — モニタ群の統合実行
  - alert_manager.py — （アラート送信管理）
- execution/  (Engine, OrderManager, Reconciler, RiskManager, broker_factory 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity
  - __init__.py
- monitoring/（上記参照）

data/（デフォルトデータ格納場所）
- monitoring.db （デフォルト SQLITE_PATH）
- paper_trading.db （PAPER_TRADING_SQLITE_PATH）
- kill.flag
- stop_requested.flag
- execution.pid

logs/
- execution.log
- monitoring.log
- ...（アプリごとに daily ローテート）

---

## 開発／拡張のヒント

- DuckDB 接続を受け取る関数群（research, ai）は、ローカルでテスト用の DuckDB ファイルを準備して回帰テストが容易です。
- OpenAI 呼び出しは再試行・バックオフ処理を行い、失敗時は安全側にフォールバックする設計です（テスト時は _call_openai_api をモックしてください）。
- MonitoringDB はスキーマ変更に対して簡単なマイグレーション（カラム追加）ロジックを含んでいます。
- Logging は setup_logging で統一しておくと、各コマンドで同じ出力形式/ファイル配置になります。

---

## よく使うコマンド例

- 環境セットアップウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（問題がないか確認）
  ```
  python -m kabusys.validate_config
  ```

- 監視プロセスを手動で早めに回す（ポーリング間隔 10 秒）
  ```
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
  ```

- Execution をペーパートレードで起動
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート（2026-04-01 から 2026-04-11）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば、README に「環境変数一覧の完全表」「DB スキーマ」「API（関数）ドキュメント抜粋」などの節も追加します。どの部分を詳しく出力すればよいか教えてください。