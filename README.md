# KabuSys

日本株自動売買システムのミニマル実装リポジトリ（ライブラリ & 起動スクリプト群）。

この README はソースツリー（src/kabusys 以下）に基づいて、セットアップ方法・主要機能・使い方・ディレクトリ構成をまとめたものです。

目的
- 取引エンジン（ExecutionEngine）・監視モジュール（Monitoring）・ペーパートレード用ツール・研究用ファクター計算を含む自動売買基盤の構成例を提供します。

注意
- 本リポジトリは実運用に使う前に十分な確認が必要です。特に KABUSYS_ENV=live にした場合は実際に発注が行われます。

---

## 主な機能一覧

- Execution エンジン起動スクリプト
  - run_execution.py
  - KABUSYS_ENV に応じて本番ブローカー／モックブローカーを切替（paper_trading では MockBrokerClient を使用し、paper DB に記録）
  - PID 管理・停止フラグ検知（data/stop_requested.flag）対応

- Monitoring（監視）起動スクリプト
  - run_monitoring.py
  - システムリソース・データ鮮度・プロセス生存確認、リスク監視、Kill Switch（停止フラグ）評価、アラート発動連携
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）

- 監視 DB 層
  - monitoring_db.py: SQLite ベースのテーブル定義・読み書き用 API（system_status / trade_logs / positions / risk_logs / dashboard など）
  - RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / MonitoringEngine 等の監視ロジック

- 環境設定ユーティリティ
  - config_setup.py: 対話式ウィザードで .env ファイルを生成・更新
  - validate_config.py: 起動前の設定検証 CLI（必須環境変数や config/*.yaml の存在チェック等）

- 研究（Research）モジュール
  - factor_research.py / feature_exploration.py: ファクター計算（Momentum / Volatility / Value）・将来リターン / IC / 統計サマリ等
  - DuckDB を用いた SQL ベースの処理を想定

- ポートフォリオ構成モジュール
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py: 候補選定、重み計算、株数決定、セクター制約、レジーム乗数など

- AI 関連
  - ai/news_nlp.py: OpenAI を使ったニュースのセンチメントスコアリング（ai_scores テーブル書込）
  - ai/regime_detector.py: ETF とマクロニュースを組み合わせた市場レジーム判定（market_regime テーブル書込）
  - OpenAI API キー（OPENAI_API_KEY）が必要

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB（data/paper_trading.db）から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

- ログ / プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度/CPU affinity 設定

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+ を想定。必要な外部パッケージ（例: duckdb, psutil, openai, PyYAML 等）をインストールしてください。

1. リポジトリをクローン / ソースを配置
   - ソースは `src/` 配下に配置されています。パッケージを開発モードで使う場合は作業ルートで次を実行:
     - pip install -e . など（必要に応じて pyproject.toml/setup を用意）

2. Python パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 任意: pip install pyyaml（validate_config が YAML 検証を行う場合に必要）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成。重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=（AI機能を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

   - 自動読み込み:
     - config.Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）で `.env` / `.env.local` を自動的に読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。

4. データディレクトリ作成（必要に応じて）
   - data/logs ディレクトリ等がなければ作成されますが、手動で作ると権限問題を回避できます。
   - data/ 以下に DB ファイルやフラグファイルが作られます。

5. 必要に応じて DuckDB / SQLite の初期データをロード

---

## 使い方

基本的にはモジュールを直接実行します（プロジェクトルートから実行することを想定）。

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いにできます

- .env の対話式作成
  - python -m kabusys.config_setup

- Execution エンジン（実行）
  - python -m kabusys.run_execution
    - KABUSYS_ENV により動作:
      - development: 発注を行わない（開発用）
      - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
      - live: 実ブローカー（kabuステーション）を使用（KABU_API_PASSWORD 等が必須）
    - 実行中は data/execution.pid を PID ファイルに保存します
    - data/stop_requested.flag が存在すると安全に停止します
    - プロセス優先度は起動時に "high" に設定されます（utils/process_priority）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
    - 監視ループのポーリング間隔は環境変数で上書き可能:
      - MONITOR_POLL_INTERVAL=30 （秒）
      - デフォルトは 60 秒
    - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）
    - 停止は data/stop_requested.flag を作成することで行います

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
  - 出力: 稼働率・注文成功率・レイテンシ・判定（PASS/FAIL）

- AI 関連（ニューススコア・レジーム判定）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼び出す API が用意されています
  - 実行時には OPENAI_API_KEY（または引数で API キー）必須
  - LLM 呼び出しはリトライ・バックオフ・レスポンスバリデーションを行います

- DB 初期化
  - 監視用 SQLite は init_monitoring_db(conn) でテーブル作成・マイグレーション（冪等）を行います
  - run_execution/run_monitoring は起動時に自動で初期化します

- Kill Switch / 停止フラグ
  - KillSwitch はリスク閾値を超えた場合に data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - 手動停止には data/stop_requested.flag を作成してください（監視・実行プロセスはこれを検知して終了します）

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用、デフォルト）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定モード）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログ保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 1 にすると Execution 起動時に kill.flag を自動クリア（注意: 本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

---

## DB/ファイルの役割（簡単な説明）

- data/kabusys.duckdb: 分析・研究用（prices_daily / raw_financials / raw_news 等のテーブルを想定）
- data/monitoring.db: 監視ログ・trade_logs・positions・risk_logs・dashboard（run_monitoring / run_execution が使用）
- data/paper_trading.db: paper_trading 実行時に MockBrokerClient が記録する専用 DB（本番 DB と分離）
- data/execution.pid: ExecutionEngine の PID
- data/stop_requested.flag: このファイルが存在すると run_monitoring/run_execution は安全に終了する
- data/kill.flag: KillSwitch による強制停止フラグ（ExecutionEngine 側での処理対象）

---

## 典型的なワークフロー（例）

1. .env を作成（config_setup）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. DuckDB / SQLite を準備（データ投入）

4. 監視プロセス起動（別ターミナル）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

5. Execution 起動（別ターミナル）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

6. ペーパートレード検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

7. 停止
   - touch data/stop_requested.flag
   - または KillSwitch が自動で data/kill.flag を作成し Execution を停止させることがあります

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードロジック、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照あり)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
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
  - execution/                — Execution 関連（OrderManager, BrokerClientFactory, ExecutionEngine 等。起動スクリプトから参照）
  - data/                     — 実行時に利用する data ディレクトリ（DB やフラグファイル）

（注）上記にある一部ファイル（例: trade_monitor.py, alert_manager.py, execution/*.py など）はこの README に掲載されたソースの断片から参照されています。プロジェクト全体ではそれらの実装ファイルが必要です。

---

## 開発・運用上の注意

- KABUSYS_ENV=live に設定すると実際の発注を行う可能性があるため、環境変数・API キー・DB パスを慎重に設定してください。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも明記）。
- OpenAI 等の外部 API を利用する部分は、APIコスト・レートリミットに注意して運用してください。AI 部分はリトライ・フォールバック処理を行いますが、無制限に呼び出すと問題になります。
- run_execution/run_monitoring は stop_requested.flag による停止を採用しており、プロセスを安全に終了させるには該当ファイルを作成してください。手短に強制 kill する場合は OS 側のプロセス管理を利用してください。
- ログは stdout と logs/<app>.log（日次ローテーション）に出力されます。ログディレクトリに書き込み権限があることを確認してください。

---

もし README に追加したい運用レシピ（systemd ユニットの例、docker-compose、CI のセットアップ等）があれば、その用途に合わせたセクションを追加します。必要な場合は目的をお知らせください。