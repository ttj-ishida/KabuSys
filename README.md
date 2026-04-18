# KabuSys

日本株向け自動売買システム（ライブラリおよび起動用スクリプト群）

このリポジトリは、データ処理・リサーチ・ポートフォリオ構築・発注エンジン・監視・AI ニュース解析までを含む自動売買基盤の一部実装を提供します。

## 概要

- データ分析用に DuckDB、運用ログ・監視には SQLite を利用する設計。
- 発注部分は実環境（kabuステーション）・ペーパートレード（MockBroker）を切り替え可能。
- モニタリング（System / Trade / Risk）と Kill Switch による自動停止機構を備える。
- ニュースを LLM（OpenAI）で解析して銘柄別スコアを生成する機能を持つ。
- 設定は .env ファイルおよび config/*.yaml（生成サポートあり）で管理。

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により本番／ペーパー切替）
  - run_monitoring: SystemMonitor ポーリングループ起動（ポーリング間隔は MONITOR_POLL_INTERVAL）
- 設定管理
  - config_setup: .env を対話式に作成・更新するウィザード
  - validate_config: .env と config/*.yaml の事前検証（--strict あり）
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - monitoring_db: 監視用 SQLite スキーマ（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索（forward returns / IC / summary）
- AI（OpenAI）
  - ニュース文章の銘柄別センチメントスコア化（ai.news_nlp.score_news）
  - マクロニュースと ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
- ユーティリティ
  - ロギング設定（utils.logging_setup）
  - プロセス優先度設定（utils.process_priority）
  - Paper Trading の検証レポート生成ツール（tools.paper_verification_report）

## 必要要件（想定）

最低限必要なパッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）
その他、パッケージは実際の requirements.txt またはセットアップで補完してください。

インストール例（開発環境）:
```
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai pyyaml
# またはプロジェクトの requirements.txt があればそれを使用
# pip install -r requirements.txt
```

## 環境設定 (.env)

プロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

代表的な環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）※ run_monitoring 用
- PID_FILE_PATH / KILL_FLAG_PATH — PID / Kill flag のファイルパス（デフォルト data/ 以下）

.env を対話式で作成するには:
```
python -m kabusys.config_setup
```

作成後に内容を検証:
```
python -m kabusys.validate_config
# 警告をエラー扱いにする場合
python -m kabusys.validate_config --strict
```

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成、依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定の事前検証
4. 必要なら DuckDB/SQLite の初期テーブルは各起動スクリプトが自動で作成します（init_monitoring_db 等）

## 実行方法（主要コマンド）

- ExecutionEngine（発注エンジン）起動:
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存
  - ペーパートレード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録
  ```
  python -m kabusys.run_execution
  ```
  実行中に data/stop_requested.flag を置くと起動直後に停止、起動中に置くとスレッドに検知させて停止します。PID ファイル（data/execution.pid など）にプロセス情報を書きます。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を環境変数で変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  Monitoring は常に Settings.sqlite_path（監視用 DB）を使用します（KABUSYS_ENV に依らない点に注意）。

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す場合）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定
  - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 停止 / Kill Switch / フラグ

- stop_requested.flag: run_execution / run_monitoring のループを優雅に終了させるためのファイル（data/stop_requested.flag）。存在を検知するとループを抜けます。
- kill.flag: KillSwitch が評価により書き込むファイル。ExecutionEngine に対する停止シグナルとして機能します。場所は Settings.kill_flag_path（デフォルト data/kill.flag）。
- execution.pid: 実行中の ExecutionEngine の PID を書き込むファイル（設定で指定可能）。

## 監視用 SQLite（monitoring_db）スキーマ（要約）

init_monitoring_db により以下テーブルを作成（冪等）:

- system_status: recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs: logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions: code (PK), qty, avg_price, current_price, updated_at
- risk_logs: logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard: 単一行（id=1）で集計情報を保持（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

これらは Monitoring と Execution の間で監視・分析・アラート発火に使われます。

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込みロジック（.env 自動ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成 + CRUD ユーティリティ）
    - system_monitor.py — システム状態監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py —（発注ログ等を監視するモジュール、本ツリーに存在）
    - monitoring_engine.py — 各 Monitor の統合ループ
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py —（アラート送信ロジック、LINE 等）
  - execution/ — 発注エンジン関連（BrokerClientFactory、ExecutionEngine、OrderManager 等）
  - portfolio/ — 候補選定・重み付け・ポジションサイズ計算・リスク調整
  - research/ — ファクター計算・特徴量探索
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）連携
    - regime_detector.py — レジーム判定（MA + マクロ NLU 合成）
  - tools/
    - paper_verification_report.py — Paper Trading 用検証レポート生成
  - data/ — デフォルトの DB / フラグファイル / PID 等（実行時に自動作成される場合あり）
  - config/ — 各種 YAML 設定（system_config.yaml 等。generate_config.py で生成可能）

（実際のリポジトリでは上記に加えて execution や data などの補助ファイルが存在します。）

## 注意事項 / 運用上のポイント

- KABUSYS_ENV=live は本番動作を意味するため、設定（特に API トークン・KILL_FLAG_CLEAR_ON_START）は慎重に行ってください。
- Monitoring は基本的に production sqlite_path（デフォルト: data/monitoring.db）を使用します。run_execution は KABUSYS_ENV=paper_trading 時、専用の paper_sqlite_path を使用して本番 DB と分離します。
- .env は機密情報を含むため、絶対にバージョン管理（Git）へコミットしないでください。
- OpenAI など外部 API を利用する処理は API のレスポンス不良に対してリトライやフォールバックを実装していますが、API キーの設定やレート制限に注意してください。
- ポートフォリオ構築・リサーチ系関数は副作用のない純粋関数を重視しています。ユニットテストが書きやすい設計です。

---

README はプロジェクトの“入り口”です。実際の運用・デプロイ時は `config/*.yaml` の中身や ExecutionEngine の詳細、BrokerClient の設定、Alert（LINE 等）設定を必ず確認してください。必要であれば、実行時ログ（logs/ 以下）を確認し問題発生時のトラブルシュートを行ってください。