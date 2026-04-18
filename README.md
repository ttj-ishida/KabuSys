# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ + 起動スクリプト群）

本リポジトリは、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI を使ったニュース解析など、運用に必要な主要コンポーネントをモジュール化して実装しています。各コンポーネントは可能な限り副作用を抑え、設定は環境変数（.env）で管理します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド / スクリプト）
- 環境変数（主なもの）
- ファイル / ディレクトリ構成

---

## プロジェクト概要

このプロジェクトは日本株自動売買の概念実装を目的とした Python パッケージです。主に以下を提供します。

- ExecutionEngine: 発注・リスク管理・注文管理の実行エンジン（本番／ペーパートレード切替対応）
- Monitoring: システム稼働監視、注文遅延やドローダウンの検知、Kill Switch（停止フラグ）の発行
- Portfolio Construction: 候補選定、重み計算、ポジションサイズ決定、セクター制限等の純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI モジュール: OpenAI を用いたニュースセンチメント評価、レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、.env ウィザード・バリデータ等

設計方針の一部:
- 設定は環境変数（.env）で管理。config_setup.py による対話式ウィザードあり。
- validate_config による起動前チェック。
- ペーパートレード環境は本番 DB と分離（data/paper_trading.db）。
- DuckDB を分析用に使用（data/kabusys.duckdb）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により実ボroker / MockBroker 切替）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを保存
- 設定管理
  - config_setup.py: .env の対話式作成・更新ウィザード
  - validate_config.py: 環境変数・設定ファイルの検証ツール
- モニタリング
  - system_monitor, trade_monitor, risk_monitor を束ねた MonitoringEngine
  - MonitoringDB: SQLite を用いた監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: 条件達成時に data/kill.flag を書き込み、ExecutionEngine 停止を促す
- ポートフォリオ
  - 候補選定、等金額／スコア加重、リスクベースの株数算出、セクターキャップ適用 等
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースを集約して LLM でセンチメント評価し ai_scores テーブルに書込
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM センチメントを合成し市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析し検証レポートを出力

---

## セットアップ手順

前提: Python 3.10+（typing の | 演算子を使用）

1. リポジトリをクローン／展開
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt を用意して pip install -r requirements.txt する運用を推奨
4. .env を作成
   - python -m kabusys.config_setup
   - もしくは .env.example がある場合はそれを参考に手動で作成
5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

※ DuckDB / SQLite の DB ファイルはデフォルトで data/ 配下に作成されます。必要に応じて .env でパスを変更してください。

---

## 使い方

主要なスクリプトと実行例を示します。

- ExecutionEngine を起動（デーモン・サービス等で運用）
  - python -m kabusys.run_execution
  - 動作モードは環境変数 KABUSYS_ENV に依存:
    - development: ローカル開発（発注なし、想定）
    - paper_trading: MockBrokerClient を使い、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 実ブローカークライアントを使用（実際に注文が発行される）
  - 起動時、実行中のプロセス優先度を "high" に設定する試みを行います（psutil を利用）。
  - 起動時に data/stop_requested.flag が存在すると起動をやめます。
  - 終了は stop flag（data/stop_requested.flag）を書くことで実行中のスレッドに停止を促します。

- Monitoring を起動（システム監視）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30  python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用してログを永続化します。
  - 停止方法: data/stop_requested.flag を作成するか、Ctrl-C（KeyboardInterrupt）

- .env（対話式作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラム内から呼び出し）
  - OpenAI API キー（OPENAI_API_KEY） を .env または環境変数で設定してください。
  - 例（Python REPL / スクリプト内）:
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      import duckdb, os
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026,4,1), api_key=os.environ.get("OPENAI_API_KEY"))

- 停止・Kill Switch
  - KillSwitch は RiskMonitor 等の結果に基づいて data/kill.flag を書き込みます。ExecutionEngine は Settings.kill_flag_path を参照して起動時に kill.flag の自動クリア挙動（KILL_FLAG_CLEAR_ON_START）を制御できます。

---

## 環境変数（主なもの）

以下は Settings クラスで参照される主要な環境変数（.env で管理）。.env の例は config_setup で生成されます。

必須（validate_config でチェックされる）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

任意 / デフォルトあり
- KABUSYS_ENV: execution モード（development, paper_trading, live） デフォルト: development
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（本番でのアラート用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

監視関連
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

プロセス / フラグファイル
- PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）

---

## ディレクトリ構成

以下は主要なファイル / パッケージと簡単な説明です（src/kabusys 配下）。

- kabusys/
  - __init__.py: パッケージ定義（__version__ など）
  - config.py: 環境変数読み込み・Settings クラス（.env 自動ロード機能付き）
  - config_setup.py: .env の対話式ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト
  - utils/
    - logging_setup.py: 統一的なロギング設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite を用いた監視ログ永続化層（テーブル作成・CRUD）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス稼働監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - trade_monitor.py: （発注ログ監視：ソース参照）
    - monitoring_engine.py: 各 Monitor を束ねるループ
    - kill_switch.py: 条件達成で kill.flag を生成
    - alert_manager.py: （通知管理：LINE 等を想定）
  - execution/
    - execution_engine.py, order_manager.py, broker_factory.py, ...（発注ロジック・リスク管理）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数算出・集約キャップ処理
    - risk_adjustment.py: セクター制限・レジーム乗数
  - research/
    - factor_research.py: momentum, volatility, value 等のファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py: OpenAI を利用したニュースセンチメント評価ロジック
    - regime_detector.py: ETF MA + マクロニュースでレジーム判定
  - data/ (実行時に DB / フラグ / pid 等を置く想定：README や .gitignore で無視)
    - monitoring.db (SQLite)、paper_trading.db、kabusys.duckdb 等
  - config/ (YAML 設定テンプレート等)
    - *.yaml （system_config, strategy_config, risk_config 等）

---

## 運用上の注意・補足

- .env（秘密情報）は絶対に Git にコミットしないこと。
- 本番モード（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は本番向けのガード（LINE 設定未設定や kill_flag_clear_on_start のチェック）を行います。
- OpenAI API を利用する機能は API コストとレイテンシの制御（バッチサイズ・リトライ）を実装済みですが、実運用ではレート制限や料金に注意してください。
- run_execution/run_monitoring はファイルフラグ（data/stop_requested.flag）を使って外部から停止指示を受け取る単純な仕組みです。システム起動・監視は Supervisor / systemd 等でプロセス管理することを推奨します。
- logging_setup は stdout と日次ローテートファイル出力（logs/<app_name>.log）を両方設定します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

この README はコードベースの主要な利用方法と構成をまとめたものです。個別モジュール（ExecutionEngine、OrderManager、BrokerClient 等）の詳細な使い方や拡張点については該当ソースの docstring / コメントを参照してください。必要であれば各モジュールの詳細マニュアルも作成いたします。