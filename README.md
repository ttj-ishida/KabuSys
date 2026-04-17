# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買システムの一部実装です。ポートフォリオ構築、発注エンジン（本番／ペーパートレード分離）、監視・アラート、研究用ファクター計算、LLM を使ったニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要要件（概略）
- セットアップ手順
- 使い方（主要コマンド / 実行例）
- 環境変数（主なもの）
- ディレクトリ構成
- 補足 / 注意点

---

## プロジェクト概要

KabuSys は以下の目的を想定したモジュール群です。

- 株価 / 財務データを使ったファクター計算・研究（DuckDB）
- シグナルに基づくポートフォリオ構築（候補選定、重み、ポジションサイズ算出）
- 発注エンジン（ExecutionEngine） — 本番とペーパートレードを分離
- 監視(監査)機能 — プロセス生存、システムリソース、データ鮮度、注文滞留、リスク（ドローダウンなど）
- アラート送信（LINE Messaging API）
- OpenAI を使ったニュース NLP による銘柄センチメント評価、及び市場レジーム判定
- ペーパートレードの検証レポート出力ツール

設計方針の一部:
- 本番 DB（monitoring）とペーパートレード DB は分離（PAPER_TRADING_SQLITE_PATH）
- ルックアヘッドバイアス防止（date.today() などを直接参照しない実装方針）
- フェイルセーフ（API 失敗時のフォールバック、部分書き込みで既存データ保護等）

---

## 機能一覧

主な機能（抜粋）:

- config_setup: 対話式ウィザードで .env を生成 / 更新
- validate_config: .env および config/*.yaml の事前検証ツール
- ExecutionEngine 実行: 本番／ペーパートレード対応（BrokerFactory によりクライアント生成）
- MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を組合せて定期監視・アラート判定
- Kill Switch: 指定フラグファイルを書き込むことで ExecutionEngine を停止させる仕組み
- Monitoring DB 層: SQLite を使った永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- portfolio モジュール: 候補選定、等重/スコア重み配分、ポジションサイズ算出、セクター上限適用、レジーム乗数など
- research モジュール: ファクター計算（Momentum / Volatility / Value）、将来リターン、IC 計算、統計要約
- ai モジュール: OpenAI を用いたニューススコア（news_nlp）、市場レジーム判定（regime_detector）
- tools: Paper Trading 検証レポート生成スクリプト

---

## 必要要件（概略）

- Python 3.9+
- 必要なパッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - pyyaml （config 検証で YAML 検査を有効にする場合）
- SQLite（標準ライブラリで利用）
- ネットワーク（kabuステーション API / OpenAI / LINE API を使う場合）

（プロジェクトに requirements.txt が無い場合は上記を参考に requirements を作成してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil requests openai pyyaml
   ```

4. 初期設定 (.env) を作る
   - 対話形式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードでは J-Quants トークンや KABU API パスワード、DB パス、KABUSYS_ENV などを設定します。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. data ディレクトリ等の作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要コマンド / 実行例）

以下はパッケージをそのままモジュールとして実行する例です。

- 監視ループ起動（SystemMonitor を定期実行）
  ```
  # デフォルト: ポーリング間隔 60 秒
  python -m kabusys.run_monitoring
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  実装のポイント:
  - stop control: プロジェクトルート/data/stop_requested.flag を作るとループが終了します。
  - run_monitoring は Monitoring 用に常に本番 sqlite_path を使用します（KABUSYS_ENV に依らず）。

- 発注エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  実装のポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 実行中にデータ/stop_requested.flag を作成するとエンジンを停止します。
  - 起動時に data/execution.pid を書き込む仕組みがあります（PID ファイル）。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- OpenAI を使う処理（ニュース NLP / レジーム判定）
  - 必須: 環境変数 OPENAI_API_KEY を設定するか、api_key を関数引数で渡す
  - 例 (スクリプトから呼ぶ):
    - kabusys.ai.news_nlp.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

---

## 環境変数（主なもの）

重要な環境変数（Settings / validate_config に基づく）:

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / ログ:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- データベースパス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB: デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用: デフォルト data/paper_trading.db）

- Paper Trading 設定:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI:
  - OPENAI_API_KEY

- LINE（アラート送信用、任意）:
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- 監視 / Kill Switch:
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag をクリアするか（本番では 0 推奨）

- 監視の閾値（例）:
  - CPU_THRESHOLD_PCT（デフォルト 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト 85.0）
  - DISK_THRESHOLD_PCT（デフォルト 90.0）

run_monitoring について:
- MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60）。0 や負の値は無効でデフォルトにフォールバックします。

---

## ディレクトリ構成（該当ファイル含む）

以下はソース内の主要ファイル / ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - utils/
    - process_priority.py    — psutil を用いたプロセス優先度 / CPU affinity
  - execution/               — 発注エンジン周り（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — OpenAI を用いたニュースセンチメント
    - regime_detector.py     — マクロ + ETF MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py

プロジェクトルート:
- .env, .env.local（任意）
- config/ (system_config.yaml など、generate 可能)
- data/ （デフォルト DB ファイルやフラグファイルを配置）
  - stop_requested.flag (スクリプト停止用)
  - kill.flag (ExecutionEngine 停止指示用)
  - execution.pid (ExecutionEngine PID)

---

## 補足 / 注意点

- ペーパートレードと本番は DB を分離する設計です。KABUSYS_ENV=paper_trading を使うと paper_trading 用 SQLite に記録されます。
- OpenAI/API を使う機能は API キーが必須です。API 呼び出しはリトライロジックやフェイルセーフを備えていますが、API 利用コスト・レート制限に注意してください。
- Monitoring 系は本番監視用に設計されています。run_monitoring は KABUSYS_ENV の値にかかわらず本番用の sqlite_path を参照します（監視 DB は本番と共有する意図）。
- process priority / cpu affinity の設定には psutil が必要で、OS 権限によっては失敗（警告を出してスキップ）します。
- config/*.yaml の中身を検証するには PyYAML が必要です。
- データ鮮度チェックは DuckDB の prices_daily を参照します。DuckDB 内のテーブルが準備されていることを確認してください。
- kill.flag を自動でクリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番で危険です。デフォルトでは 0（クリアしない）を推奨します。
- ログ設定は各スクリプト内で基本的な logging.basicConfig(level=INFO) を設定しています。より詳細に運用する場合はプロジェクト側でハンドラを設定してください。

---

何か特定のファイルの説明を README に追加したい、あるいはインストール / CI 用の requirements / entrypoint を整備したいなどあれば指示してください。