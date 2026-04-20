KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／ランタイム群です。本リポジトリは注文実行エンジン、監視基盤、ポートフォリオ構築・資金配分ロジック、リサーチ／ファクター計算、LLM を使ったニュース解析などを含むモジュール群を提供します。  
設計方針の一部：データベースは分析用に DuckDB、運用ログ／監視には SQLite を使用し、本番とペーパートレードはファイルで分離。LLM 呼び出しは冗長性・リトライを備えフェイルセーフで実行します。

主な機能
--------
- 実行エンジン起動スクリプト (run_execution)
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory を利用してブローカー接続（ペーパートレード時は MockBrokerClient を利用し専用 DB に記録）
  - リスク管理（RiskManager）、注文管理（OrderManager）、再突合（Reconciler）を組み合わせてセッション実行
  - 停止フラグ（data/stop_requested.flag）や kill.flag を使った安全停止機構
- 監視ポーリング (run_monitoring / MonitoringEngine)
  - システム監視（CPU/メモリ/ディスク、Execution プロセス監視）
  - 取引ログ監視、リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（重大リスク時に data/kill.flag を書き込み実行エンジンを停止）
  - アラート発行ポイント（AlertManager 経由）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み付け、セクターキャップ、レジーム乗数、株数算出（LOT 丸め・aggregate cap）
- リサーチ / ファクター計算（kabusys.research）
  - モメンタム、バリュー、ボラティリティ等の計算（DuckDB を用いた SQL 実行）
  - 将来リターン・IC 計算、ファクター統計サマリ
- AI（kabusys.ai）
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを生成・保存
  - 市場レジーム判定（MA200 とマクロニュースの組合せ）
  - リトライ・JSON バリデーション・スコアクリッピング等フェイルセーフ設計
- 管理ツール
  - .env 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     主要依存:
     - duckdb
     - psutil
     - openai  (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証機能用、なくても動作するが警告になる)
   - 必要に応じて追加のライブラリをインストールしてください。

4. .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - ウィザード実行後、python -m kabusys.validate_config で検証してください。

重要な環境変数（主なもの）
------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DB / パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, default: data/paper_trading.db)
- ログ
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
  - LOG_DIR (default: logs/)
- その他
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒, default: 60) — run_monitoring で上書き可能
  - PAPER_FILL_MODE (ペーパートレードの約定挙動: instant | partial | never | reject, default: instant)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: "1" or "0", default: "0")

使い方（主要コマンド）
---------------------
- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱い

- 実行エンジン起動（ローカル実行 / サービス化）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と完全分離）
    - data/stop_requested.flag が存在する場合起動せず終了
    - 起動時に data/execution.pid に PID を書き込む（Engine の pid_file パラメータ）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒）
  - 注意: 監視プロセスは KABUSYS_ENV に関わらず Settings.sqlite_path（本番監視 DB）を使用します

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 周り（ニューススコア / レジーム判定）は呼び出し関数として利用可能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数か、関数引数で渡す

停止・Kill Switch / 管理ファイル
------------------------------
- data/stop_requested.flag
  - run_execution/run_monitoring がポーリング中に検知すると安全に停止します（外部から停止指示するためのファイル）。
- data/kill.flag
  - KillSwitch がリスク閾値超過時（ドローダウン、ポジション上限超過など）に書き込む。ExecutionEngine はこのファイルを検知して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると実行時に自動クリアされますが、本番では 0 を推奨します。
- data/execution.pid
  - 実行エンジンの PID を記録するファイル（Engine をデーモン化・監視する際に利用）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動読み込み・Settings クラス
  - config_setup.py          — .env 生成ウィザード（対話式）
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB のスキーマ初期化・アクセス層
    - system_monitor.py      — システム監視（CPU/メモリ/データ鮮度・PID チェック）
    - trade_monitor.py       — 取引ログ監視（滞留注文・約定異常 等）  ← 実装参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 複数モニタを束ねて定周期で実行
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — アラート送信ロジック（実装参照）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - position_sizing.py     — 株数算出・aggregate cap 処理
  - research/
    - factor_research.py     — モメンタム／ボラティリティ／バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・バリデーション）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - execution/                — ExecutionEngine、OrderManager 等（実行ロジック）
  - data/                     — 実行時に生成されるファイル群（DB, flags, pid, logs など）

運用上の注意点 / トラブルシューティング
--------------------------------------
- .env は絶対に Git にコミットしないでください（config_setup はその旨を明示しています）。
- run_monitoring は監視目的の DB（Settings.sqlite_path）を使用します。ペーパートレード用 DB とは分離されます。
- OpenAI を利用する機能は API キーが必須です。API コールにはリトライ・バックオフが入っていますが、コストとレート制限に注意してください。
- psutil によるプロセス優先度設定は権限によって失敗することがあります（警告ログのみ）。root 権限での実行やスケジューラ設定を検討してください。
- validate_config により設定の初歩チェックが可能です。--strict モードは CI のプリチェックに有用です。

拡張・開発
------------
- DuckDB を用いたリサーチ関数群は外部データの整備（prices_daily / raw_financials / raw_news テーブル）に依存します。データパイプラインと連携して日次で DuckDB を更新してください。
- BrokerClient の実装を追加すれば任意のブローカーへ接続可能です（BrokerClientFactory を拡張）。
- AlertManager を実装すれば LINE などへの通知を有効化できます（Settings で LINE 関連トークンを指定）。

ライセンス・バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

補足
----
README に記載の挙動はソース内の docstring / コメントに基づいています。実際の運用前に python -m kabusys.validate_config を必ず実行し、.env の内容と DB パス／権限を確認してください。質問や補足があれば、どの部分を詳しく説明するかを指定してください。