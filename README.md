# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動用スクリプト群です。  
このリポジトリは取引エンジン、監視機能、ポートフォリオ構築、研究用ツール、AIによるニュース解析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の主要コンポーネントを備えたモジュール群です。

- 実行エンジン (ExecutionEngine) — ブローカークライアントを通じて発注を実行・管理
- 監視 (Monitoring) — システム状態・注文・リスク監視、Kill Switch（停止フラグ）の生成
- ポートフォリオ構築 — 候補選定、重み計算、株数決定（リスク制約・単元丸め）
- 研究モジュール — DuckDB を用いたファクター計算・特徴量解析
- AI モジュール — OpenAI を使ったニュースセンチメント・レジーム判定
- 設定支援ツール — .env ウィザード・設定検証 CLI
- 運用ツール — ペーパートレード検証レポート生成など

設計方針として、データアクセス・発注は明確に分離され、ペーパートレード時は本番 DB と分離して動作するようになっています（安全対策）。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - python -m kabusys.config_setup : .env 対話ウィザード
  - python -m kabusys.validate_config : .env / config/*.yaml の事前検証
- 監視 (monitoring)
  - system_monitor / trade_monitor / risk_monitor を統合する MonitoringEngine
  - kill.flag を生成する KillSwitch（条件に応じて ExecutionEngine を停止）
  - 永続化層: SQLite ベースの monitoring DB（テーブル生成・マイグレーション機能含む）
- Execution
  - BrokerClientFactory による本番 / モックブローカー切替（KABUSYS_ENV=paper_trading）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等の実装
- ポートフォリオ
  - 候補選定・等重・スコア重み付け
  - position sizing（リスクベース、等配分、スコア配分）、単元株丸め、aggregate cap 調整
  - セクター上限適用・レジーム乗数
- 研究 (research)
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（Information Coefficient）など
- AI
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント評価（ai_scores への保存）
  - regime_detector: ETF の MA とマクロニュースの LLM 評価を合成して市場レジーム判定
- 運用ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

---

## セットアップ手順（推奨）

以下はローカル開発・運用の一般的な手順です。

1. Python 仮想環境を作成・有効化
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # POSIX
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージをインストール
   - 依存一覧はプロジェクトの requirements.txt / pyproject.toml を参照してください。
   - 本プロジェクトで利用が想定される主要パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に推奨）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

3. プロジェクトルートに移動し、.env を作成
   - 対話ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` を参考に手動で `.env` を作成してください。

4. 設定検証
   - .env や config/*.yaml の不備を検出:
     ```
     python -m kabusys.validate_config
     ```
   - 必須環境変数が不足している場合はエラーになります。`--strict` を付けると警告も失敗扱いになります。

5. ディレクトリ/ファイル作成
   - 実行時に `data/` や `logs/` が必要です。起動スクリプトが自動作成しますが、権限等に注意してください。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境 / ログ / DB
  - KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグファイルパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

- ペーパートレード挙動
  - PAPER_FILL_MODE — MockBroker の約定モード: instant / partial / never / reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY — AI モジュール使用時に必要（news_nlp / regime_detector）

- LINE 通知（オプション）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

注意: config モジュールは自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方（基本コマンド）

- .env ウィザード（対話的）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループの起動
  - デフォルト 60 秒間隔（MONITOR_POLL_INTERVAL で上書き可）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は常に production 用 sqlite_path（SQLITE_PATH）を使用します。

- 実行エンジン起動
  - KABUSYS_ENV により挙動が変わります。paper_trading の場合は MockBroker を使用し、専用 DB (PAPER_TRADING_SQLITE_PATH) に記録されます。
  ```
  python -m kabusys.run_execution
  ```

- 停止方法（Graceful）
  - run_execution / run_monitoring はプロジェクトルート下の data/stop_requested.flag を監視しています。停止したい場合は該当ファイルを作成してください（または既存の停止フラグを置く）。
  - Kill Switch により ExecutionEngine が停止されると data/kill.flag が作成されます。手動で削除する場合は削除してください（または設定 KILL_FLAG_CLEAR_ON_START=1 により自動クリア可能だが本番では推奨されません）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI 機能呼び出し（Python API）
  - ニューススコア（ai_scores へ書き込み）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定
    ```py
    from kabusys.ai.regime_detector import score_regime
    # conn: duckdb connection
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要パッケージは `src/kabusys` 以下にあります。代表的なファイル/モジュール:

- src/kabusys/
  - __init__.py (プロジェクトメタ)
  - config.py (環境変数読み込み・Settings)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor 起動スクリプト)

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 実行エンジン・ブローカー・リスク管理の実装

- src/kabusys/monitoring/
  - monitoring_db.py (SQLite テーブル作成・監視ログ永続化)
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
  - 監視ロジックおよび Kill Switch

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み計算・株数決定・セクター調整

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター・IC・統計解析

- src/kabusys/ai/
  - news_nlp.py (ニュースセンチメント)
  - regime_detector.py (市場レジーム判定)

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - logging_setup.py (統一ログ設定)
  - process_priority.py (プロセス優先度・CPU affinity 設定)

- データ / ログ
  - data/ (デフォルトの SQLite / PID / flag ファイル置き場)
  - logs/ (ログファイル: logs/execution.log, logs/monitoring.log など)

---

## 運用上の注意

- 本番環境では KABUSYS_ENV=live を使用します。validate_config は live 時に重要な警告を出すので必ず確認してください。
- kill.flag や stop_requested.flag による停止はファイルベースです。CI / スケジューラからの自動制御や手動運用時はファイルの存在・削除を注意して扱ってください。
- Monitoring は常に本番用の sqlite_path を使用する設計です（環境に依存せず監視データを一元化）。
- AI モジュールは OpenAI API を利用するため、APIキーの管理（環境変数・シークレット管理）が必要です。API呼び出し時のリトライやフォールバック設計が組み込まれていますが、レート制限やコストに注意してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリの作成権限に注意してください。

---

## 開発者向け補足

- config.py は .env / .env.local を自動読み込みします。テスト時に自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- monitoring_db.init_monitoring_db は冪等にテーブルを作成し、簡単なマイグレーションを行います（カラム追加など）。
- ポートフォリオ・ポジション決定ロジックは純粋関数として分離されており、単体テストが容易です（DB 参照を行いません）。
- duckdb を用いた研究モジュールは SQL を主体とした設計で、大量データ処理に適しています。

---

必要に応じて README に記載するサンプル .env や運用手順（systemd / supervisor 用の unit ファイル例）を追加できます。必要なら追記しますので、どの形式でのデプロイ／運用を想定しているか教えてください。