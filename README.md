# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
このリポジトリは、戦略の研究・ファクター計算・ポートフォリオ構築・発注エンジン・監視/アラート・AI を用いたニュース解析までを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を備えたモジュール化された自動売買フレームワークです。

- 戦略研究用のファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け）
- ポジションサイズ決定（リスク制御、単元丸め、aggregate cap）
- ExecutionEngine（ブローカークライアント経由の発注、paper_trading 対応）
- 監視コンポーネント（システム状態・注文ログ・リスク監視・Kill Switch）
- ニュースの NLP による銘柄センチメント評価（OpenAI API を利用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証）

設計方針の一部:
- DuckDB/SQLite によるデータ永続化と分析
- 本番 DB とペーパートレード DB の分離
- ルックアヘッドバイアスを避ける設計（日付参照に注意）
- フェイルセーフ（API 失敗時はフォールバックして継続）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading では MockBrokerClient を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で調整）
- 設定管理
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
  - config.Settings: 環境変数ラッパー（自動 .env ロード機能あり）
- 監視
  - monitoringモジュール: System/Trade/Risk モニタ、KillSwitch、MonitoringDB（SQLite）
  - monitoring_engine: 各監視をまとめてポーリング・アラート送出
- ポートフォリオ
  - portfolio モジュール: 候補選定、重み付け、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ
  - research モジュール: ファクター計算（momentum, volatility, value）、特徴量探索（IC, forward returns）
- AI
  - ai.news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - ai.regime_detector: ma200 とマクロニュースの LLM スコアを合成して市場レジームを決定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシなど）
- ユーティリティ
  - utils.logging_setup: 統一的ログ設定（stdout + 日次ローテーション）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定

---

## 要件

- Python 3.10 以上（| 型や match 等を使わないが union 型 `X | Y` を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config/*.yaml の検証を行う場合)
- 推奨: 仮想環境（venv / poetry / pipenv 等）

インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 仮想環境を作成し、依存パッケージをインストール。

3. .env の作成（推奨）
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは .env を手動作成。必要なキー（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG / INFO / ...）
     - OPENAI_API_KEY（AI 機能を使う場合）

   config.py はプロジェクトルート（.git か pyproject.toml がある場所）を基準に .env を自動ロードします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

5. DB ファイル（data ディレクトリ）は起動時に自動作成されますが、適宜権限を確認してください。

---

## 使い方（代表的コマンド）

- ExecutionEngine の起動（本番 / ペーパートレード共通）
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading にすると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient が使われます。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中、data/execution.pid に PID が記録されます。
  - Kill Switch は data/kill.flag を作成して ExecutionEngine に停止信号を送ります（monitoring の KillSwitch を通して書き込まれます）。

- Monitoring の起動（ポーリング）
  python -m kabusys.run_monitoring

  補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - Monitoring は Settings に依らず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを管理します。
  - 停止には data/stop_requested.flag を作成する／CTRL+C で中断。

- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  （--db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照）

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: development / paper_trading / live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルトあり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モード）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（INFO 等）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

---

## 停止・Kill スイッチ

- 監視プロセス / 実行プロセスの停止制御:
  - data/stop_requested.flag: run_monitoring / run_execution のループで検出して安全終了します（外部から停止を指示するためのフラグ）。
  - data/kill.flag: KillSwitch が条件達成時に作成。ExecutionEngine はこのファイルの存在を検出して発注エンジンを停止します。
  - 設定により、ExecutionEngine 起動時に kill.flag を自動クリアするオプションがあります（KILL_FLAG_CLEAR_ON_START）。

---

## ディレクトリ構成

（プロジェクトルートの src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - config.py                 — 環境変数 / 設定ラッパー（自動 .env ロード）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視テーブル）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留／約定異常チェック（存在）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — モニタの統合実行ループ
    - alert_manager.py        — アラート送出（LINE 等）（存在）
  - execution/
    - execution_engine.py     — 実行エンジンコア（EngineConfig 等）
    - broker_factory.py       — ブローカークライアントの生成（Mock を含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数決定・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/value/volatility 等の計算
    - feature_exploration.py  — forward returns / IC / summary 等
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — ma200 + マクロニュースでレジーム検出
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/monitoring_db.py   — 監視 DB スキーマ・API（上に記載）

data/ と logs/ はランタイムで生成されるディレクトリです（DB・フラグ・PID・ログ格納）。

---

## 開発・拡張のヒント

- DuckDB / SQLite テーブルスキーマは monitoring_db.py / research modules を参照してください。
- AI 部分は OpenAI SDK のラッパーを利用しています。テスト時は _call_openai_api をモックすると良いです。
- ログは utils.logging_setup.setup_logging で統一的に設定しています。外部プロセス監視 / systemd で起動する場合は stdout とログファイルの両方に出るので扱いやすいです。
- 設定ファイル（config/*.yaml）や .env の変更は validate_config.py で事前チェックできます。

---

## ライセンス・注意事項

- このドキュメントはコードベースから生成した説明です。実運用前に必ず設定（特に本番 API キー・Kill Switch 設定）を確認してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起があります）。

---

何か追記してほしい箇所（詳細なコマンド例、systemd サービス定義テンプレート、CI/テスト手順、requirements.txt の候補等）があれば教えてください。README に反映して整備します。