# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム（KabuSys）の実装です。戦略・ポートフォリオ構築・監視・ペーパートレード検証・AI ベースのニュースセンチメント評価などのコンポーネントを含みます。

注意: この README はコードベース（src/kabusys 以下）から抽出した情報を基に作成しています。実際に運用する際は config/*.yaml や .env を正しく設定し、テスト環境で十分に検証してください。

---

## 概要

- コア機能:
  - 注文実行エンジン（ExecutionEngine）と発注フロー（OrderManager / Reconciler / RiskManager 等）
  - 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
  - ポートフォリオ構築ユーティリティ（銘柄選定・重み計算・ポジションサイズ計算）
  - リサーチ用モジュール（ファクター計算、特徴量解析）
  - AI 連携モジュール（ニュース NLP による銘柄センチメント、レジーム検出）
  - ペーパートレード用 DB と検証レポート生成スクリプト
  - .env 対話式ウィザードと設定検証 CLI

- 実行モード:
  - development: 開発用（発注なし想定）
  - paper_trading: ペーパートレード（MockBrokerClient を使用、別 DB に記録）
  - live: 本番（実際に発注を行う）

---

## 機能一覧（抜粋）

- 環境設定
  - .env 自動読み込み（プロジェクトルートが検出されれば .env / .env.local を読み込む）
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）

- 実行 / 監視
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading の動作を切替）
  - run_monitoring: SystemMonitor をポーリング（MONITOR_POLL_INTERVAL で間隔変更可能）
  - Kill Switch / stop フラグ機構（data/kill.flag / data/stop_requested.flag）
  - 監視 DB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard のテーブル群

- ポートフォリオ構築
  - 候補選定、等配分 / スコア加重配分、セクター制限、レジーム乗数、株数決定（単元丸め・資金制約考慮）

- リサーチ
  - Momentum / Volatility / Value の定量ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（情報係数）等の統計ツール

- AI（OpenAI）
  - news_nlp: ニュース記事を LLM（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ保存
  - regime_detector: ETF（1321）MA200乖離とマクロニュースセンチメントを合成して市場レジームを判定

- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発用）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - Unix/macOS:
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要なパッケージをインストール
   - 最低限必要なパッケージ（コード内で使用）:
     ```
     pip install duckdb psutil openai
     ```
   - 設定 YAML を検証したい場合:
     ```
     pip install pyyaml
     ```
   - テストや開発で追加の依存があれば requirements.txt を用意している想定で:
     ```
     pip install -r requirements.txt
     ```

3. .env の作成（対話式）
   ```
   python -m kabusys.config_setup
   ```
   - .env が生成されます。重要な必須キー:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 必要に応じて OPENAI_API_KEY（AI 機能使用時）、LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）などを設定します。

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```

5. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
   - デフォルトの DB/ファイルパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - Kill flag: data/kill.flag
     - Stop flag: data/stop_requested.flag

---

## 使い方

基本的な起動・操作方法:

- 実行エンジン（ExecutionEngine）起動
  - 本番/ペーパーは KABUSYS_ENV に依存:
    ```
    # ペーパートレード（.env で KABUSYS_ENV=paper_trading にするか環境変数で指定）
    python -m kabusys.run_execution
    ```
  - 実行開始時にプロセス優先度が "high" に設定されます（権限により失敗する場合あり）。

- 監視プロセス起動
  ```
  # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は Settings.sqlite_path（監視用 DB）を使用し、環境にかかわらず本番 sqlite_path を参照します。

- 停止方法
  - run_execution / run_monitoring のループはプロジェクトルートの data/stop_requested.flag を参照しています。ファイルを作成するとループは検知して終了します。
    ```
    # 停止フラグ作成（手動停止）
    mkdir -p data
    echo stop > data/stop_requested.flag
    ```
  - ExecutionEngine 側に停止シグナル（Kill Switch）を送るには data/kill.flag に理由を書き込みます（KillSwitch が存在を検知して処理を停止）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定していると自動クリアされる設定があります（本番では 0 推奨）。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または環境変数で DB を指定
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

- 設定の自動読み込み
  - プロジェクトルートが検出される場合、起動時に .env（優先度低）と .env.local（優先）を自動で読み込みます。
  - 自動読み込みを無効にするには:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## 重要な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live

- データベース / パス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1, default 0)

- 監視:
  - MONITOR_POLL_INTERVAL (秒, default 60)

- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector の呼び出しに必要）

- ログ:
  - LOG_LEVEL (DEBUG/INFO/...; default INFO)

---

## ディレクトリ構成（主要ファイル）

リポジトリ内 src/kabusys の主要なモジュール構成:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 経由で銘柄別スコアを計算）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py

  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル定義 / ラッパー
    - system_monitor.py       — CPU/MEM/DISK・データ鮮度・プロセス生存監視
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込み / 監視支援
    - monitoring_engine.py    — 監視コンポーネント束ねる実行ループ
    - alert_manager.py        — アラート通知（実装箇所あり）

  - execution/
    - broker_factory.py       — ブローカークライアント生成（Mock/実運用切替）
    - execution_engine.py     — ExecutionEngine 本体（run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - その他関連ファイル

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・資金割当
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py      — Momentum / Volatility / Value 等
    - feature_exploration.py  — forward returns, IC, summary 等
    - __init__.py

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成 CLI
    - __init__.py

  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

- data/                      — 実行時に使用するファイル群（DB、PID、フラグ等）
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (ペーパー時)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 運用上の注意

- 監視（Monitoring）は Settings.sqlite_path を使い、KABUSYS_ENV に関係なく本番の sqlite_path を参照します。監視用 DB とペーパートレード DB は分離されていますが、設定ミスに注意してください。
- run_execution はペーパートレード時に MockBrokerClient を利用し、data/paper_trading.db に記録します（本番 DB と分離）。
- OpenAI 連携機能を利用する場合は OPENAI_API_KEY を設定してください。API エラー時はフェイルセーフで継続する設計ですが、料金やレート制限に注意してください。
- Kill Switch（強制停止）はデリケートな操作です。KILL_FLAG_CLEAR_ON_START の設定や kill.flag の取り扱いは運用ポリシーに従ってください。
- process priority / cpu affinity の設定は権限依存で失敗することがあります（ログに警告が出ます）。

---

必要であれば、README にサンプル .env.example、起動/停止のより詳細な手順、ユニットテストの実行方法、Docker/CI のセットアップ手順などを追記できます。どの内容を優先して追加しますか？