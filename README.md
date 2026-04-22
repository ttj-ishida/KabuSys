# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究用ユーティリティを含む総合自動売買フレームワークの一部です。  
README は本コードベースに含まれる主要機能・セットアップ・使い方・ディレクトリ構成の概要を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します：
- データ加工・DuckDB を使ったファクター計算（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注（ExecutionEngine）およびブローカークライアント（本番 / ペーパートレード切替）
- 監視 (Monitoring)：システム健全性・取引ログ・リスクのモニタリング、Kill Switch
- AI 補助（OpenAI を用いたニュースセンチメント、レジーム判定）
- 設定ウィザード / 設定検証 / 検証レポートなどのツール

設計方針として、実行スクリプトと内部ライブラリの分離、DuckDB/SQLite による永続化、LLM 呼び出しのリトライ/フォールバック等の堅牢な実装が盛り込まれています。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み、対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV による paper_trading / live の切替
    - paper_trading 時は MockBroker を使用し DB を分離
    - 停止フラグ / PID 管理
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - kill_switch による停止フラグ発行（data/kill.flag）
  - SQLite ベースの監視 DB 初期化（monitoring_db.py）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスク調整（sector cap / regime multiplier）、株数計算（lot 単位で丸め）
- 研究用モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI モジュール
  - ニュースから銘柄別センチメントを作成して ai_scores に書き込む（news_nlp.score_news）
  - ETF + マクロニュースを統合して市場レジームを判定（regime_detector.score_regime）
  - OpenAI API 呼び出しはリトライとバリデーションを厳格に行う
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - ロギングセットアップ、プロセス優先度設定ユーティリティ

---

## セットアップ手順（ローカル開発想定）

1. リポジトリを取得
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 任意:
     - PyYAML（config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai
     - pip install PyYAML  # optional

   （プロジェクトに requirements.txt があればそれを使ってください）

4. 初期設定（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動: .env.example を参考に .env を作成（.env は絶対に Git にコミットしない）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL 扱いしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリ準備（通常はスクリプトが自動で作成）
   - デフォルト DB / ファイル:
     - data/kabusys.duckdb (DUCKDB_PATH)
     - data/monitoring.db (SQLITE_PATH)
     - data/paper_trading.db (paper_trading 用)
     - logs/ (LOG_DIR)

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- ログ
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- Kill Switch / PID
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番で 1 は危険）
- 監視間隔
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒（run_monitoring で上書き、デフォルト 60）

注意: .env 自動読み込みはプロジェクトルートが特定される場合に行われます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env を作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動時に data/stop_requested.flag があると起動を行わず終了
    - 実行中に stop フラグが作成されるとエンジン停止を試みる

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は Settings.sqlite_path（monitoring.db）を使用してログを永続化。DuckDB も併用します。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定

- AI モジュールの利用（コードから呼び出す例）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - どちらも DuckDB 接続と target_date、OpenAI API キーが必要です（api_key 引数または OPENAI_API_KEY 環境変数）

---

## 運用時の注意（本番向け）

- KABUSYS_ENV=live のときは設定ミスが重大な損失につながります。validate_config で警告・エラーを事前にチェックしてください。
- KILL_FLAG_CLEAR_ON_START は本番で 1 にしないことを推奨します（キルフラグを自動でクリアしてしまうため）。
- .env（機密情報を含む）は絶対に Git にコミットしないでください。
- OpenAI キーは安全に管理してください（環境変数経由）。
- run_execution / run_monitoring はプロセス優先度を高に設定します（set_process_priority）。必要に応じて変更してください。
- run_monitoring が使用する停止フラグはプロジェクトルート/data/stop_requested.flag（スクリプト内パス）です。運用上このファイルを作成することでループを安全に終了できます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB と永続化 API
    - system_monitor.py
    - trade_monitor.py       — （参照: 監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知管理: LINE 等、実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（発注ループ）
    - broker_factory.py      — Broker クライアント生成
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
    - news_nlp.py            — OpenAI を使ったニュースセンチメント
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - data/                    — 実行時に使用する SQLite/DuckDB/フラグ/ログ等（runtime）

※上記は代表的なファイル群です。その他補助的なモジュールや未掲示ファイルもあります。

---

## ログとトラブルシューティング

- ログ出力:
  - デフォルトは logs/<app_name>.log に日次ローテーションで出力（30日保持）。
  - コンソール（stdout）にも出力されます。
  - ログレベルは LOG_LEVEL / setup_logging の引数で制御可能。

- よくある問題:
  - .env 未作成 → config_setup を実行するか環境変数を設定
  - DuckDB/SQLite ファイルの親ディレクトリがない → スクリプトが自動作成を試みるが、権限等で失敗する場合は手動で作成
  - OpenAI 呼び出しの失敗 → ネットワークやレート制限。ライブラリはリトライを行うが、APIキー・課金設定を確認

---

## 開発者向けメモ

- DB マイグレーションは monitoring_db.init_monitoring_db 内で簡易的に行われる（カラム追加等）。
- AI系の OpenAI 呼び出し関数はテストで差し替え（mock）しやすいように分離されている（_call_openai_api を patch 可能）。
- research モジュールは DuckDB 接続を受け取り純粋関数で計算する設計（外部副作用なし）。
- ポートフォリオ/ポジション設計は単体関数群になっておりユニットテストが容易。

---

必要であれば、README に含める具体的な環境変数のサンプル .env（テンプレート）、systemd / supervisor 用のサービスユニット例、実際の API 呼び出しサンプル（score_news / score_regime の Python サンプル）などを追記できます。どの情報を優先して追加しましょうか？