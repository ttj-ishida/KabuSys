# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム（研究・ペーパートレード・実行・監視）のコア実装群です。  
主要機能はファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、LLM を使ったニュース評価やレジーム判定などを含みます。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 重要な環境変数・ファイルパス
- よくある運用フロー・注意点

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- DuckDB / SQLite を用いたデータ分析・永続化
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- 実行エンジン（ExecutionEngine）と注文管理（発注・約定ログ等）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- OpenAI を利用したニュース NLP（センチメント）と市場レジーム判定
- ペーパートレード検証レポート生成ツール

設計方針の特徴:
- 本番とペーパートレードは DB を分離（PAPER_TRADING_SQLITE_PATH）
- ルックアヘッドバイアスを防ぐ設計（date/datetime の使い方に配慮）
- フェイルセーフ：外部 API 失敗時は安全側にフォールバックして継続
- ログは統一的に設定（コンソール + 日次ローテートファイル）

---

## 機能一覧

主な機能（抜粋）:

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 監視 DB（SQLite）初期化 / 永続化レイヤ（monitoring_db）
- RiskMonitor / SystemMonitor / TradeMonitor を束ねる MonitoringEngine
- ニュース NLP（OpenAI）による銘柄別センチメント計算（kabusys.ai.news_nlp）
- 市場レジーム判定（kabusys.ai.regime_detector）
- 研究用ファクター計算・IC 計算（kabusys.research）
- ポートフォリオ構築・リスク調整・ポジションサイズ決定（kabusys.portfolio）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（パッケージの型ヒントや一部機能は 3.9 以上を想定）
- SQLite は標準ライブラリ
- DuckDB, psutil, openai など外部パッケージが必要

推奨手順:

1. 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows
   ```

2. 依存パッケージをインストール
   必要なパッケージ（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定ファイル検証を行う場合に任意）
   - （その他必要に応じて）

   pip でインストール:
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

   プロジェクトに requirements.txt があればそちらを使用してください。

3. .env の準備
   - 最初は対話式ウィザードで作成するのが簡単です:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作成してください。
   - 自動ロードはデフォルトで有効。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 設定検証（必須環境変数やファイルパスをチェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成
   デフォルトで使用されるディレクトリ:
   - data/（SQLite, DuckDB, PID, フラグファイル など）
   - logs/（ログファイル）
   これらは自動的に作成されますが、必要に応じて事前作成して権限を確認してください。

---

## 使い方（主要コマンド）

- 実行エンジン（Engine を開始）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - PID ファイル: data/execution.pid（設定で変更可）

- 監視プロセス（SystemMonitor のポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用します（環境に依らず同一 DB）。

- 設定ウィザード（.env の対話式作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ペーパートレード DB からレポート）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 研究用関数や API はモジュールとして呼び出して使用できます（例: kabusys.research.calc_momentum など）。

---

## ディレクトリ構成（抜粋）

プロジェクトルート: src/kabusys 配下に実装があります。主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（console + 日次ローテート）
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py       — （存在する前提の監視ロジック）
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラートの送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine の本体（起動 / run_session）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — OpenAI を使った銘柄別ニューススコア
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
  - data/                    — データ・DB・フラグ用ディレクトリ（実行時に使用）
  - tools/
    - paper_verification_report.py

（注）一部ファイルはこの README のサンプルコードに含まれるのみで、さらに補助モジュールや実装ファイルが存在します。

---

## 重要な環境変数・ファイルパス

主な環境変数（デフォルトや意味）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: 実行はモックブローカー、DB は PAPER_TRADING_SQLITE_PATH
  - live: 実際の発注が行われるため設定に注意
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能用 API キー（ニュース NLP / レジーム判定）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- LOG_DIR: ログファイル出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）デフォルト 60
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=クリア、0=クリアしない。production は 0 推奨）

重要なファイル / フラグ:
- data/kill.flag: ExecutionEngine を停止させるための Kill Switch（存在すると停止）
- data/stop_requested.flag: run_monitoring / run_execution が見てプロセスを終了させるフラグ
- data/execution.pid: ExecutionEngine の PID（デフォルト）
- logs/<app>.log: 日次ローテートされるログファイル

---

## 運用上の注意・推奨

- 本番（KABUSYS_ENV=live）設定時は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config は本番時の追加ガードを行います。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。通常は 0 を推奨します。
- OpenAI を使用する機能は API キーとコストに注意してください。API 呼び出し失敗時は安全側にフォールバックする設計ですが、過度なリトライやバッチ設定に留意ください。
- ログディレクトリや DB ファイルのパーミッションを適切に設定してください（サービス実行ユーザーの権限）。
- psutil を利用したプロセス優先度設定は、OS の種類や権限に依存します。権限不足で設定に失敗する場合は警告が出ますが処理自体は継続されます。

---

この README はコードの主要な利用方法と設計上のポイントをまとめたものです。詳細な実装や追加の CLI、設定テンプレート（.env.example）などはリポジトリ内の該当ファイルを参照してください。必要であれば .env.example のサンプルや運用手順書（systemd/cron 用）も作成できますのでお知らせください。