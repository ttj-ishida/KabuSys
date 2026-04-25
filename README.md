# KabuSys

日本株向けの自動売買 / 研究プラットフォームの一部を集めたリポジトリ。  
このリポジトリには、実行エンジン、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ用モジュール、AI を使ったニュース解析などのユーティリティが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数 / .env の例
- 停止・Kill スイッチについて
- ディレクトリ構成（概要）
- 主要モジュール説明
- 依存関係

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムとそれを支える周辺ツール群です。本リポジトリのコードは主に以下の目的を持ちます。

- ExecutionEngine：発注ロジックの実行（本番 / ペーパートレード切り替え対応）
- Monitoring：システム稼働状況・注文状況・リスク監視
- Portfolio：銘柄選定・配分・サイズ決定（純粋関数群）
- Research：ファクター計算・特徴量探索
- AI：ニュースの NLP によるセンチメント評価や市場レジーム判定
- Tools：ペーパートレード検証レポート生成など

本リポジトリは実運用を想定しており、ログ出力、PID ファイル、フラグファイルによる制御、Db（SQLite / DuckDB）による永続化を行います。

---

## 機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録
  - PID ファイルを書き込み、stop フラグで停止可能
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status 等を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話式に .env を生成 / 更新
- 設定検証 CLI（validate_config.py）
  - 必須環境変数、YAML 設定ファイル、DB パスの存在等をチェック
- AI モジュール
  - news_nlp.score_news：ニュース記事を OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロニュースを組み合わせて日次レジーム判定
- Portfolio モジュール（選定 / 重み付け / セクター制限 / ポジション決定）
- Monitoring（MonitoringDB、RiskMonitor、TradeMonitor、KillSwitch、AlertManager 等）
- Tools
  - paper_verification_report：ペーパートレードの検証レポートを出力

---

## セットアップ手順

前提：
- Python 3.10+（typing の | 記法を参照）
- 仮想環境を推奨（venv / poetry など）

1. リポジトリをクローンし、仮想環境を作成・有効化する

2. 依存パッケージをインストール（例: pip）
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で利用）
   - 例:
     pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそちらを使ってください）

3. .env を作成
   - 対話式ウィザードを利用する場合:
     python -m kabusys.config_setup
   - 手動作成の場合、後述の環境変数セクションを参照してください

4. 設定検証（任意）
   python -m kabusys.validate_config
   - さらに厳密に FAIL にしたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ等の作成（通常はコード内で自動作成されますが、必要に応じて）
   mkdir -p data logs

---

## 使い方

主要なスクリプトと実行例を示します。

- 環境設定ウィザード (.env 作成)
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパートレードは KABUSYS_ENV に依存）
  python -m kabusys.run_execution

  仕様メモ:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップ
  - 実行中に data/stop_requested.flag が作成されると安全に停止する
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring 起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定。デフォルト 60 秒
  - 監視は production sqlite_path（Settings.sqlite_path）を使用する（環境変数にかかわらず）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を優先）

- AI モジュール呼び出し（プログラム内）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OpenAI API キー（OPENAI_API_KEY）を設定する必要あり。api_key 引数で上書き可能。

---

## 環境変数（主なもの）

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知用（任意）

監視関連
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）

その他（細かい設定は Settings クラスを参照）

---

### .env の最小例

以下は .env の一例（機密情報は適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

config_setup.py を使えば対話的に安全に作成できます。

---

## 停止・Kill スイッチについて

- 停止フラグ（プロセス終了用）
  - data/stop_requested.flag を作成すると、run_execution や run_monitoring のループが検知して安全に終了します。
  - ストップを要求する際に手でファイルを作成するか、管理ツールから書き込んでください。

- Kill Switch（自動停止）
  - RiskMonitor 等の結果に基づいて kabusys.monitoring.kill_switch.KillSwitch が kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込みます。
  - ExecutionEngine は起動時や実行中にこの kill.flag の存在を参照し、あれば停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアします（本番では推奨しない）。

- PID ファイル
  - 実行エンジンは data/execution.pid に PID を書き込みます（設定で変更可能）。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src 配下がパッケージ）:

- src/kabusys/
  - __init__.py
  - config.py                ：Settings / .env 自動読み込み
  - config_setup.py          ：.env 対話式ウィザード
  - validate_config.py       ：設定検証 CLI
  - run_execution.py         ：ExecutionEngine 起動スクリプト
  - run_monitoring.py        ：SystemMonitor ポーリング起動
  - utils/
    - logging_setup.py       ：ログ設定ユーティリティ
    - process_priority.py    ：プロセス優先度 / CPU affinity ユーティリティ
  - execution/                ：発注エンジン周り（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       ：監視用 SQLite テーブル定義・永続化クラス
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

データ / ログ:
- data/                      ：SQLite / PID / フラグファイル等のデフォルト位置
- logs/                      ：ログファイル（appごとに logs/<app_name>.log）

---

## 主要モジュール説明（短い参照）

- Settings (kabusys.config)
  - 環境変数の取得と検証を行う。自動でプロジェクトルートの .env を読み込む（.git または pyproject.toml を起点に探索）。
  - settings = Settings() またはモジュール変数 settings を利用。

- MonitoringDB (kabusys.monitoring.monitoring_db)
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブルを作成・操作する永続化レイヤ。

- SystemMonitor / RiskMonitor / TradeMonitor
  - システム状態、ドローダウンやポジション超過の監視、注文の停滞や約定異常を検出する。

- KillSwitch
  - リスク条件に合致した際に kill.flag を書き込むロジック。

- Portfolio モジュール
  - select_candidates, calc_equal_weights, calc_score_weights（候補の選定と重み付け）
  - calc_position_sizes（各銘柄の発注株数を計算）

- Research モジュール
  - calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算）
  - calc_forward_returns, calc_ic（特徴量探索、IC 計算）

- AI モジュール
  - news_nlp.score_news：Discord/LINE とは別にニュースを LLM で解析し ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロニュースを組み合わせて市場レジームを判定

---

## 依存関係（代表的なもの）

主要ライブラリ（抜粋）:
- python >= 3.10
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証のために推奨）

インストール例:
pip install duckdb psutil openai PyYAML

---

## 運用上の注意点

- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- KABUSYS_ENV=live の場合は本番の資金・注文が動きます。設定を十分に確認してから起動してください（validate_config に本番ガードあり）。
- デフォルトではログは logs/ に日次ローテーションで保存されます。ログディレクトリに書き込み権限があることを確認してください。
- OpenAI を利用する機能は API コストがかかります。API キーと利用頻度に注意してください。

---

以上がリポジトリの概要と利用方法のまとめです。詳細な実装や追加のコマンドは各モジュールの docstring を参照してください（例: kabusys.ai.news_nlp、kabusys.research.factor_research 等）。問題や追加したい情報があれば教えてください。