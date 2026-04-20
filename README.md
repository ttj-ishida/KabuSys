# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行スクリプト群。

このリポジトリは取引エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助機能などを含むモジュール群を提供します。  
ライブラリとしての利用（関数呼び出し）と、実行用スクリプト（エンジン起動・監視ループ・各種ツール）の両方を想定しています。

Version: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境設定（.env）
- 使い方（起動コマンド / ライブラリ API）
- 重要な環境変数
- ディレクトリ構成
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するためのコンポーネント群です。  
主な目的は以下：

- 発注エンジン（ExecutionEngine）による注文管理とブローカークライアントのラップ
- システム監視（SystemMonitor / MonitoringEngine）によるプロセス／データ鮮度監視・アラート・Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター濃度制御など）
- リサーチ（DuckDB を用いたファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- Paper Trading を使った検証用ワークフローと検証レポート生成

設計上、DB（DuckDB/SQLite）や外部 API（kabuステーション、J-Quants、OpenAI）との連携を前提としていますが、Paper Trading 環境では実際の発注を行わないモック実装を使い DB を分離して検証できます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト: run_execution.py
  - Paper Trading モード（MockBrokerClient）と専用 SQLite（data/paper_trading.db）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - データ永続化用 MonitoringDB（SQLite）
  - kill.flag / stop_requested.flag による安全停止制御
  - run_monitoring.py によるポーリングループ起動
- Portfolio
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP（OpenAI）による銘柄単位センチメントの算出（ai.news_nlp）
  - レジーム判定（ma200 + マクロセンチメントの合成）
- ユーティリティ
  - 簡易ロギングセットアップ（logs/ 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 設定ウィザード（.env 作成）と事前検証コマンド

---

## 必要条件

最低限の外部ライブラリ（主要な例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証を使う場合）
その他、実際にブローカー連携するには各 API のクライアントが必要です。

インストール要件ファイルがない場合は環境に合わせて個別に導入してください。開発環境では仮想環境の利用を推奨します。

例:
pip install duckdb psutil openai pyyaml

※ 実際の requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - 例: pip install duckdb psutil openai pyyaml
4. 初期設定ファイルの作成（.env）
   - 対話ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合は .env.example を参照してください（.env.example があれば）。
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

---

## 環境設定（.env）

- 自動読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

代表的な環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI 利用時の API キー
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モデル（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring 用, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効、開発用）

詳しいキーは kabusys.config.Settings と config_setup.py の _ITEMS を参照してください。

---

## 使い方

### 設定ウィザード
対話式で .env を作成:
- python -m kabusys.config_setup

### 設定検証
- python -m kabusys.validate_config
- 厳格モード: python -m kabusys.validate_config --strict

### ExecutionEngine（発注エンジン）起動
- 本番または paper_trading の挙動は KABUSYS_ENV に依存します。
- 起動:
  - python -m kabusys.run_execution
- 動作:
  - Paper trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 実行中は data/execution.pid に PID が書かれる想定
  - data/stop_requested.flag が存在すると安全に停止します

### Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
- 監視は常に本番 sqlite_path を使用（環境に依らず監視 DB は同一）
- 停止フラグ data/stop_requested.flag を検知するとループを終了

### Paper Trading 検証レポート出力
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能
- 指標: 稼働率、注文成功率、送信率、レイテンシ等を評価して PASS/FAIL を出力

### ライブラリとしての利用（例）
- ポートフォリオ関連:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- リサーチ:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- AI:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  — DuckDB 接続と日付を渡してニューススコアを生成
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

各関数の引数・戻り値は該当モジュールの docstring を参照してください（duckdb 接続や日付の取り扱いに注意）。

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_execution/run_monitoring が存在を検知して安全に停止するためのフラグ
- data/kill.flag
  - Kill Switch が書き込むフラグ。ExecutionEngine 側で検出して停止をトリガ可能
- data/execution.pid
  - ExecutionEngine 起動時に PID を書き込む想定（run_execution により使用）
- logs/
  - デフォルトのログ出力先。各アプリ（execution, monitoring など）ごとに日次ローテートされます

---

## ログとプロセス優先度

- ログは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
  - stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定
  - ログディレクトリは LOG_DIR 環境変数で変更可能（デフォルト logs/）
- 起動スクリプトは最初にプロセス優先度を high に設定します（psutil を使用）
  - kabusys.utils.process_priority.set_process_priority を利用（Windows / POSIX を吸収）

---

## ディレクトリ構成（主要ファイルを抜粋）

src/
- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定取得ロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — Monitoring 用 SQLite 操作レイヤ
    - system_monitor.py
    - trade_monitor.py       — （省略：注文監視ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （省略：通知管理）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（発注ループ等）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

ルートに data/、logs/、config/ 等の補助ディレクトリを想定しています。

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定ミスが致命的になり得ます。validate_config の実行を必須化してください。特に LINE 通知・Kill Switch 設定を確認してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py も注意喚起あり）。
- Paper Trading は本番 DB と分離されるよう設計されていますが、本番運用時は環境変数を再確認してください。
- AI（OpenAI）を使う機能は API リクエストに料金が発生します。api_key の管理と呼び出し頻度に注意してください。
- データのタイムゾーンや日付の扱い（UTC / JST）に注意。ニュース集計ウィンドウ等はコード内 docstring を参照してください。
- DuckDB への書き込みや executemany の挙動はバージョン差分で異なる可能性があります（コード中に互換性対策あり）。

---

以上がこのコードベースの概要と利用方法のまとめです。  
詳細な API 仕様や内部アルゴリズム（ポートフォリオ構築・リスク計算・ファクター定義等）は各モジュールの docstring と設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）が参照先となります。必要であればそれらの概要ドキュメントも作成できます。