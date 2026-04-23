# KabuSys

日本株自動売買システムのミニマル実装（ライブラリ & 起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム設計をコード化したリポジトリです。  
主な目的は次のとおりです:

- シグナル生成（Research / ファクター計算）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 発注実行エンジン（本番 / ペーパートレード分離）
- システム監視・リスクモニタリング・Kill Switch
- ニュース NLP を使った銘柄センチメント評価（OpenAI 経由）
- 運用・検証を支援するツール類（設定ウィザード、設定検証、レポート生成）

設計方針として、DB（DuckDB / SQLite）を用いたデータ集約・永続化と、外部 API 呼び出し（kabuステーション、J-Quants、OpenAI）は設定に応じて利用する構成になっています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的作成 / 更新）
- 設定・ファイルパス・環境変数の検証 CLI
- ExecutionEngine（発注エンジン）:
  - KABUSYS_ENV に応じて本番 / ペーパートレードを切替
  - Paper Trading は専用 SQLite に記録（data/paper_trading.db）
  - PID ファイル管理、停止フラグ読み取り
- Monitoring（監視）:
  - システム状態（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 取引ログ・リスク監視（drawdown, position limit）
  - Kill Switch（条件発生時に data/kill.flag を書き込み）
- AI 関連:
  - news_nlp: raw_news を OpenAI でスコアリングして ai_scores に保存
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定
- Portfolio モジュール:
  - 候補選定、等比率 / スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- Research モジュール:
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- ユーティリティ:
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity の設定
- ツール:
  - paper_verification_report: ペーパートレード DB から期間レポートを出力

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化してください。

   example:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 依存パッケージをインストールします（必要に応じて requirements.txt を用意してください）。本リポジトリの主な依存は次の通りです:

   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証を行う場合に推奨）
   - （その他、運用環境に応じて追加）

   例:
   - pip install duckdb psutil openai pyyaml

3. 初期環境変数ファイルを作成します（対話ウィザード推奨）:

   - python -m kabusys.config_setup

   ウィザードで .env を作成した後、設定が妥当か確認します:

   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

4. ディレクトリの準備（logs/, data/ はスクリプトが自動作成することもありますが、手動で作成しておくと権限エラーを防げます）:

   - mkdir -p data logs

5. OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください（.env に保存可）。

---

## 環境変数（主要なもの）

（.env で管理することを推奨）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: execution 環境
  - 値: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト60）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（0/1。production は 0 推奨）

その他は config_setup のウィザードで案内されます。

---

## 使い方（主要スクリプト）

- 環境の作成 / 更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/execution.pid に PID を書き込みます（設定により変更可）。
    - 停止方法:
      - data/stop_requested.flag を作成すると起動中のループが検知して終了します。
      - Kill Switch（monitoring 側が data/kill.flag を作成）で停止される場合もあります。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60）
  - 監視は Settings にある sqlite_path（監視用 SQLite）を使用します（環境に関わらず同一 DB を参照）。
  - 停止方法:
    - data/stop_requested.flag を作成すると停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

---

## 運用に関するポイント

- Kill Switch
  - monitoring がリスク条件（例: ドローダウン閾値超過、ポジション上限超過）を検知すると data/kill.flag を生成します。ExecutionEngine 起動時にこのフラグがあると起動を拒否し、稼働中はフラグ検出で停止します。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します（誤って自動クリアされることを防ぐ）。

- ペーパートレード分離
  - paper_trading 環境は発注ロジックをモックし、データベースも paper_trading 用に分離します（PAPER_TRADING_SQLITE_PATH）。

- ログ
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテート・30日保持）
  - setup_logging() が標準出力にも出力します（stdout）。

- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI を使用します。API キーがない場合は明確に失敗するかフォールバック（無視）します。API キーは OPENAI_API_KEY に設定してください。
  - 呼び出しはリトライ/バックオフロジックあり。部分失敗時に DB の整合性を保つ処理が組まれています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・.env 自動ロード・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト

src/kabusys/utils/
- logging_setup.py
  - 共通ログ設定ユーティリティ
- process_priority.py
  - プロセス優先度 / CPU affinity 設定

src/kabusys/monitoring/
- monitoring_db.py
  - SQLite テーブル作成・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py
  - システム状態・データ鮮度監視
- trade_monitor.py
  - （コードベースに詳細あり）取引監視
- risk_monitor.py
  - ドローダウン・ポジション上限監視
- kill_switch.py
  - Kill Switch 実装
- monitoring_engine.py
  - 各モニタを束ねるエンジン
- alert_manager.py
  - （通知管理: LINE 等、実装に依存）

src/kabusys/execution/
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注ロジック、ブローカ抽象、リスク管理、リコンシリエーション

src/kabusys/portfolio/
- portfolio_builder.py
  - 候補選定・重み計算
- position_sizing.py
  - 株数算出・上限・丸め
- risk_adjustment.py
  - セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
- feature_exploration.py
  - 将来リターン、IC、統計サマリ

src/kabusys/ai/
- news_nlp.py
  - raw_news を OpenAI で評価し ai_scores に格納
- regime_detector.py
  - ETF MA + マクロニュースで市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py
  - ペーパートレード検証レポート生成スクリプト

data/
- 実行時に生成されるファイル群例:
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - stop_requested.flag（ループ停止用）
  - kill.flag（Kill Switch）
  - execution.pid（Execution エンジン PID）

logs/
- ログファイルが出力されるディレクトリ（logs/<app_name>.log）

---

## よくある操作例

- .env を作成:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config

- ペーパートレード環境で Execution 起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視プロセス起動（デフォルト 60s 間隔）:
  - python -m kabusys.run_monitoring
  - 間隔を変更: export MONITOR_POLL_INTERVAL=30

- 強制停止（監視・実行プロセスに対して）:
  - touch data/stop_requested.flag  （run_* のループが検知して終了します）
  - monitoring が Kill 条件を満たすと data/kill.flag が書き込まれ、Execution 起動や継続を阻止します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 開発・拡張のヒント

- DuckDB は分析用途の主要 DB。prices_daily / raw_financials / raw_news 等のテーブルに依存する機能が多数あるため、テスト用データ整備が重要です。
- OpenAI 呼び出しはモジュール別にラップされており、テスト時は _call_openai_api をパッチしてモックできます。
- settings（kabusys.config.Settings）を経由して設定を取得する設計のため、テストでは環境変数を直接設定・クリアして動作をコントロール可能です。
- SQLite / DuckDB のファイルパスは Settings によりカスタマイズ可能。ペーパーと本番の DB 分離を厳格に維持してください。

---

この README はコードベースに含まれる実装（起動スクリプト、設定周り、主要モジュール）に基づいて作成しています。追加の操作手順や依存関係（requirements.txt の整備など）はプロジェクト運用に応じて補完してください。