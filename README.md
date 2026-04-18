# KabuSys

日本株自動売買システムのコアライブラリ（ドメインロジック・運用ユーティリティ群）。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ、実行方法、およびディレクトリ構成をまとめたものです。

注意: 実際の取引を行うには外部 API の認証情報や適切な運用体制が必要です。本 README は開発／運用支援のための説明であり、本番運用にあたっては十分な確認を行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤で、次のような機能を持ちます。

- 日次／リアルタイムのファクター計算（DuckDB を使った prices_daily / raw_financials 参照）
- ポートフォリオ構築（候補選定、重み算出、位置サイズ計算、セクター制限）
- 実行エンジン（Broker 抽象、ペーパートレード分離）
- 監視（システム稼働・データ鮮度・注文状態・リスク監視、Kill Switch）
- ニュース NLP を用いた銘柄センチメント（OpenAI）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポート生成）

主要な実行スクリプト:
- run_execution.py — ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて本番 / ペーパートレード切替）
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートから）
  - 対話式ウィザードで .env 生成: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
- 実行・注文関連
  - ExecutionEngine（Broker の抽象化、RiskManager、OrderManager、Reconciler 等）
  - Paper Trading 用に本番 DB とは分離された SQLite を使用可能
- 監視 / アラート
  - SystemMonitor: CPU/MEM/Disk、Execution プロセス、生データ鮮度
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - 監視ログの永続化（SQLite）
- 研究・ファクター
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン、IC、統計サマリ）
- AI 統合
  - ニュースセンチメント（OpenAI を使ったスコアリング）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度設定（Windows/Linux を吸収）
  - Paper Trading レポート生成スクリプト

---

## 要件（Prerequisites）

- Python 3.9+（実行環境に合わせて調整）
- 必要パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — config/*.yaml の検証に使用
- SQLite（Python 標準ライブラリで OK）
- ネットワーク接続（OpenAI / 外部 API を使う場合）

インストール例（venv 作成後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# config 検証で YAML を使う場合:
pip install pyyaml
```

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 既定値:
- KABUSYS_ENV: development / paper_trading / live（既定: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- OPENAI_API_KEY: OpenAI API を使う場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 1 にすると Execution 起動時に kill.flag を自動クリア（注意：本番では 0 推奨）

設定の作成や初期化は下記コマンドを参照してください。

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成
   ```bash
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # ある場合
   pip install duckdb psutil openai
   ```

2. .env を作成
   - 対話式ウィザードで生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - または .env.example をコピーして編集（リポジトリに例がある場合）。必須変数は設定してください。

3. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も厳格に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

4. ディレクトリ作成
   - ログディレクトリ（既定: logs/）とデータディレクトリ（既定: data/）が自動作成されますが、権限やパスを確認してください。

5. OpenAI 連携を使う場合:
   - 環境変数 OPENAI_API_KEY を設定してください。

6. （任意）Paper Trading 用 DB:
   - KABUSYS_ENV=paper_trading を使う場合、PAPER_TRADING_SQLITE_PATH を設定するかデフォルトの data/paper_trading.db が使われます。

---

## 使い方（実行例）

- ExecutionEngine 起動（実行環境に応じて .env を設定）
  ```bash
  # デフォルトは .env の KABUSYS_ENV を参照
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、paper_trading 用 DB（data/paper_trading.db）へ記録します。
  - run_execution は data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。

- SystemMonitor（監視）起動
  ```bash
  # ポーリングループ起動
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する場合（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  補足:
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV にかかわらず）。
  - 停止は data/stop_requested.flag を作成するか、プロセスを SIGINT（Ctrl+C）で終了します。

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ログ
  - ログは stdout にも出ますが、ファイル出力は logs/<app_name>.log に日次ローテートで保存されます（30日保持）。
  - setup_logging() により root ロガーが設定されます。LOG_DIR を指定することで保存先を変更可能。

---

## シャットダウン / Kill Switch

- run_execution / run_monitoring はプロセス内で data/stop_requested.flag の存在を監視しており、作成されると安全に停止します。
- KillSwitch はリスク条件（ドローダウンやポジション上限など）で data/kill.flag を書き込み、外部から ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリアします（本番では 0 推奨）。

---

## 開発時の注意点

- DuckDB や SQLite のパスは .env で指定できます。デフォルトは data/kabusys.duckdb と data/monitoring.db。
- AI（OpenAI）関連機能は API キーが必要です。API エラー時もフェイルセーフを備えており、致命的な例外を投げずに継続する設計です。
- psutil によるプロセス優先度設定や CPU affinity は権限に依存します。権限不足時は警告を出してスキップします。
- YAML 検証は PyYAML がないとスキップされます（validate_config）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（AI + ETF MA）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ
    - system_monitor.py       — システム状態・データ鮮度監視
    - monitoring_engine.py    — Monitor 統合ループ
    - risk_monitor.py         — ドローダウン・ポジション監視
    - trade_monitor.py        — （注文監視、実装あり）
    - kill_switch.py          — kill.flag 制御
    - alert_manager.py        — （アラート送信、実装あり）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py       — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py

（上記は現在の実装ファイルを元にした抜粋です。実際のリポジトリにはさらにファイルやサブモジュールが存在する可能性があります。）

---

## よくある操作・コマンドまとめ

- .env を作る:
  python -m kabusys.config_setup

- 設定チェック:
  python -m kabusys.validate_config

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視プロセス起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## その他

- ログ／DB の権限やパスは運用環境に合わせて適切に設定してください。
- 本リポジトリのコードはモジュール設計に配慮しており、個別コンポーネントを単体テストしやすく設計されています。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env の自動読み込みを抑制できます。
- 実運用（特に KABUSYS_ENV=live）の場合は、必須環境変数や通知（LINE）の設定、Kill Switch の動作確認を事前に行ってください。

---

README に不足している詳細（API の仕様、ExecutionEngine 内部の使用方法、Broker 実装詳細など）について追記が必要でしたら、対象モジュールを指定していただければその節の README/ドキュメントを作成します。