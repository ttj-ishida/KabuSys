# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ群・起動スクリプト・解析ツールを含む）。  
この README は、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買に関連する以下の機能を提供します：

- 発注/実行エンジン（ExecutionEngine）およびブローカー抽象化
- システム監視・リスク監視・アラート/Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI を用いたニュースセンチメント解析・レジーム検出（OpenAI）
- ペーパートレード検証レポート作成ツール
- 環境設定ウィザード・設定検証ツール
- ログ設定・プロセス優先度設定などのユーティリティ

設計方針は「本番データベースと分析・ペーパー・監視を分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時は安全側へフォールバック）」です。

---

## 主な機能一覧

- run_execution.py: 実行エンジンの起動スクリプト。KABUSYS_ENV に応じてペーパートレードと本番を切り替え（ペーパートレードは専用SQLiteに記録）。
- run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔変更可。
- config_setup.py: .env を対話的に生成/更新するウィザード。
- validate_config.py: 環境変数・config/*.yaml を起動前に検証する CLI。
- monitoring/*: 監視用 DB 層・System/Trade/Risk Monitor・KillSwitch・MonitoringEngine 等。
- portfolio/*: 候補選定、重み計算、ポジションサイズ算出、セクター制約など。
- research/*: ファクター計算（モメンタム/ボラティリティ/バリュー）・将来リターン・IC・統計要約。
- ai/news_nlp.py: raw_news を OpenAI で評価し ai_scores に書き込む処理（バッチ・リトライ・バリデーション実装）。
- ai/regime_detector.py: MA とマクロニュースを統合して market_regime を判定・書き込み。
- tools/paper_verification_report.py: ペーパー口座の検証レポートを標準出力に生成。
- utils/*: ログ設定、プロセス優先度・CPU affinity 設定など共通ユーティリティ。

---

## セットアップ手順（開発者向け）

前提：Python 3.9+ を想定（コードは型ヒントで新しい構文を使用）。利用環境に応じて適宜調整してください。

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要なライブラリをインストールします（代表的な依存ライブラリ）:

   ```bash
   pip install duckdb psutil openai
   # オプション: YAML ファイル検証に PyYAML が使われます
   pip install pyyaml
   ```

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

3. .env を作成します（対話ウィザード推奨）:

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードを使わない場合はリポジトリルートに `.env` を作り、最低限以下を設定してください（例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   ```

   重要な環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV: development / paper_trading / live
   - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（必要に応じて上書き）
   - LOG_LEVEL, LOG_DIR（ログ設定）

4. 設定検証を行います:

   ```bash
   python -m kabusys.validate_config
   # 厳密モード（警告もFAIL扱い）
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じてログディレクトリや data ディレクトリを作成します（多くは起動スクリプトが自動作成しますが、権限等で失敗する場合があるため事前作成推奨）:

   ```bash
   mkdir -p logs data
   ```

---

## 使い方（起動・主要コマンド）

- 実行エンジン起動（ExecutionEngine）:

  - 本番 or 開発（KABUSYS_ENV に依存）:

    ```bash
    # 環境変数を設定済みとする
    python -m kabusys.run_execution
    ```

  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合はエンジンを起動せず終了します。
    - 実行中は PID ファイル（data/execution.pid）を書きます。

- 監視ループ起動（SystemMonitor）:

  ```bash
  # ポーリング間隔を環境変数で上書き可能（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - デフォルト間隔は 60 秒。
  - 監視は本番 sqlite_path を常に使用（環境に依らず監視 DB は同じパスを参照）。
  - data/stop_requested.flag を作成するとループが終了します（手動停止や自動停止処理に利用）。

- .env 設定ウィザード:

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:

  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（プログラム内 API 呼び出し）:

  - ニュースセンチメントを生成して DB に書き込むには OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）:
    - 関数: `kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)`
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)`

- ログ設定: すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を呼び出します。デフォルトは `logs/<app_name>.log` に日次ローテーションで出力。

---

## 重要な挙動メモ

- KABUSYS_ENV:
  - development: 開発用（発注なしなどの挙動）
  - paper_trading: ペーパートレード（MockBroker・専用 SQLite）
  - live: 本番（実際の発注）
- ペーパートレードのデータベースは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録され、本番監視 DB（`SQLITE_PATH` / `data/monitoring.db`）とは分離されます。
- Kill Switch:
  - `kabusys.monitoring.kill_switch.KillSwitch` はリスク基準（ドローダウンやポジション上限）で `data/kill.flag` を書き、ExecutionEngine に停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアする設定がありますが、本番では推奨されません。
- stop フラグ:
  - `data/stop_requested.flag` が存在すると監視・実行スクリプトはループ終了や起動中止を行います（手動停止用）。

---

## ディレクトリ構成

リポジトリの主要なディレクトリ / ファイル（src/kabusys 以下）:

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・設定取得ロジック（自動 .env ロード機能含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視 DB（SQLite）ラッパー / migration
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — (注文関連の監視, ファイル内に実装あり)
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch の実装（flag ファイル操作）
    - monitoring_engine.py — 各 Monitor の束ね
    - alert_manager.py — アラート送信（LINE 等の実装が入る想定）
  - execution/ (発注ロジック・ブローカ抽象化)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定と重み計算
    - position_sizing.py — 株数・配分の決定
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメント判定
    - regime_detector.py — マクロ＋MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

補助ディレクトリ（プロジェクトルート想定）:
- data/ — SQLite DB、PID、flag ファイル等を配置（実行時に作成）
  - data/monitoring.db（監視 DB のデフォルト）
  - data/paper_trading.db（ペーパートレード用 DB）
  - data/execution.pid（ExecutionEngine の PID）
  - data/kill.flag, data/stop_requested.flag（フラグ）
- logs/ — ログファイル（app_name.log が日次ローテートされ保存）

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- OPENAI_API_KEY (AI 機能を使う場合)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (0/1 — 起動時に kill.flag を自動クリア)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## 開発時の注意点 / ベストプラクティス

- 本番（live）モードでの起動前には `python -m kabusys.validate_config` で必須設定やログ設定を確認してください。
- AI 機能を利用する際は OPENAI_API_KEY を安全に管理してください（.env を Git にコミットしないこと）。
- DB パスやログ出力先は環境変数で上書きできるため、環境ごとに .env を分けてください（.env.local を利用）。
- 監視・実行コンポーネントはフラグファイルで制御されるため、運用上の停止/再開手順を運用ドキュメントに明記してください。
- DuckDB を使ったリサーチ処理はローカルの重い読み込みを行うことがあるため、データサイズに注意してください。

---

もし README をリポジトリのルートに合わせて微調整したい（例: Python バージョンや requirements.txt を反映する、起動コマンドに systemd/cron 例を追加する等）場合は、環境や運用要件を教えてください。必要に応じてサンプル .env や systemd ユニット例も作成します。