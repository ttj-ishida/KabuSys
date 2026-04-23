# KabuSys

日本株向け自動売買・リサーチ基盤（略称: KabuSys）のリポジトリ用 README（日本語）。

本ドキュメントはコードベースから読み取れる設計・運用情報をまとめたものです。起動スクリプトや CLI、環境変数、主要コンポーネントの役割とディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買およびリサーチ用の内部ツール群です。主な機能は以下です。

- 日次/オンデマンドでファクター計算（モメンタム、ボラティリティ、バリュー等）を行う研究モジュール
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- ExecutionEngine による発注管理（paper_trading と live の切替対応）
- 監視サブシステム（システム状況、注文ログ、リスク監視、Kill Switch）
- ニュースの LLM によるセンチメントスコア化（OpenAI 経由）
- Paper Trading の検証レポート生成ツール

設計方針として、DuckDB を分析用 DB、SQLite を軽量な永続化（監視/ペーパートレード）に使用し、OpenAI など外部 API 呼び出しは明示的に環境変数で有効化します。

---

## 機能一覧（抜粋）

- CLI / スクリプト
  - python -m kabusys.config_setup : .env の対話式ウィザードで作成/更新
  - python -m kabusys.validate_config : .env や config/*.yaml の起動前検証
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
  - python -m kabusys.tools.paper_verification_report : Paper Trading 検証レポートの生成

- 主要コンポーネント
  - kabusys.research: ファクター計算（calc_momentum, calc_volatility, calc_value）と特徴量解析
  - kabusys.portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
  - kabusys.execution: ブローカークライアント生成、注文管理、リスク管理、発注エンジン（ExecutionEngine）
  - kabusys.monitoring: system/trade/risk の監視、KillSwitch、MonitoringEngine、監視用 DB（SQLite）
  - kabusys.ai: news_nlp（ニュースの LLM スコアリング）、regime_detector（市場レジーム判定）
  - kabusys.utils: ロギング設定、プロセス優先度・CPU affinity 設定などユーティリティ

- 永続化
  - DuckDB: 分析用（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視・トレードログ用（デフォルト: data/monitoring.db）
  - Paper Trading 用 SQLite は完全分離（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）

---

## セットアップ手順

1. Python 環境を準備
   - 推奨: 仮想環境を作成して使用
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 最低限の依存（例）:
     - pip install duckdb psutil openai
   - YAML 検証を行いたい場合:
     - pip install PyYAML
   - （プロジェクトに requirements.txt が無い場合は上記を個別インストール）

3. リポジトリルートでデータ・ログディレクトリを作成
   - mkdir -p data logs

4. .env の初期作成（対話式）
   - python -m kabusys.config_setup
   - このウィザードは .env を生成します（.env を絶対にリポジトリにコミットしないでください）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

6. OpenAI を利用する機能を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、関数引数で渡す。

注意:
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 本番運用時は KABUSYS_ENV を `live` に設定する（デフォルトは `development`）。
- paper_trading モード（KABUSYS_ENV=paper_trading）は MockBrokerClient を用い、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録されます。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の満足（instant | partial | never | reject）（デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0|1、デフォルト: 0）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（デフォルトは data/ 以下）

短い補足:
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング周期を上書き可能（デフォルト 60 秒）。
- 実行停止のためのフラグ:
  - data/stop_requested.flag: 実行スレッドが存在確認して停止するためのフラグ（run_monitoring/run_execution が参照）
  - data/kill.flag: KillSwitch が書き込む停止要求（ExecutionEngine に対する安全装置）

---

## 使い方（起動例）

1. .env を作成・編集
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. ExecutionEngine（実際の発注またはペーパートレード）
   - KABUSYS_ENV を適宜設定（paper_trading / live）
   - python -m kabusys.run_execution
   - 補足: paper_trading モードは専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され実際の発注は行われません。

4. 監視ループ（SystemMonitor）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定可能（例: export MONITOR_POLL_INTERVAL=30）

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - もしくは DB を指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

6. AI / ニューススコアリング（プログラム API）
   - kabusys.ai.score_news(conn, target_date, api_key=...)
   - OpenAI API キーが必要（または環境変数 OPENAI_API_KEY）

停止方法の例:
- 実行中の run_execution/run_monitoring プロセスを優雅に停止するには、プロジェクトルートの data/stop_requested.flag を作成するとループが検出して終了します。
- KillSwitch による停止は監視コンポーネントが条件を満たすと data/kill.flag を書き込みます。

ログ:
- logs/<app_name>.log に日次ローテートで出力されます（デフォルト 30 日保持）。
- コンソール出力は stdout に出ます（set up の logging 設定による）。

---

## ディレクトリ構成（概要）

リポジトリの主要な Python パッケージ構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（アプリ設定）
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度/CPU affinity 設定
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算、ラウンド処理、キャップ調整
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - execution/
    - （発注エンジン、リポジトリ、オーダー管理、リスク管理などの実装）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と DB 操作用 API
    - system_monitor.py — システム状態・データ鮮度の監視
    - trade_monitor.py — 注文ログの整合性チェック（省略部分あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねるループロジック
    - kill_switch.py — kill.flag の書き込み/評価
    - alert_manager.py — （アラート送信ロジック）
  - ai/
    - news_nlp.py — ニュース記事を LLM でスコアリングして ai_scores に書込む
    - regime_detector.py — ma200 と LLM センチメントの合成で市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の Pass/Fail レポート生成
  - data/ (実行時に生成される想定)
    - stop_requested.flag
    - kill.flag
    - execution.pid
    - monitoring.db, paper_trading.db など（デフォルトパス）

---

## 運用上の注意点 / トラブルシューティング

- .env を誤ってコミットしないでください（機密情報が含まれます）。
- KABUSYS_ENV=live の場合は特に注意（LINE 通知設定や Kill Switch の設定を確認）。
- run_execution 起動前に data/kill.flag が存在すると起動を抑止する動作があります（必要に応じて KILL_FLAG_CLEAR_ON_START=1 を検討。ただし本番では 0 を推奨）。
- Paper Trading は本番の発注 API とは分離された専用 DB を使用します（安全性のため）。
- OpenAI の呼び出しはレート制限/ネットワーク障害を考慮してリトライやフォールバック実装が入っていますが、API キー・課金ルール等は運用上考慮してください。
- DuckDB / SQLite のファイルパスは環境変数で上書きできます。ログディレクトリや data ディレクトリに書き込み権限があることを確認してください。

---

必要があれば、本 README の各セクションを具体的なコマンド例、.env のサンプル、システム図（アーキテクチャ）、運用手順（デプロイ、バックアップ、監視）などでもう少し詳しく作成できます。どの部分を詳しくしたいか教えてください。