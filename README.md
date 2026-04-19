KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコードベースです。  
本 README はコードベースの主要コンポーネント、セットアップ方法、使い方、ディレクトリ構成の概要を日本語でまとめたものです。

要点
-----
- Python 製（型ヒント・最新構文を利用）  
- DuckDB（分析用）＋ SQLite（運用ログ/監視用）を使用  
- 実行エンジン（ExecutionEngine）と監視（Monitoring）を分離  
- Paper trading（ペーパートレード）モードをサポート（本番 DB と分離）  
- OpenAI を使ったニュース NLP / レジーム判定モジュールを含む（任意）

プロジェクト概要
----------------
KabuSys は以下の主要機能をもつ自動売買プラットフォーム設計を含みます。

- ExecutionEngine（発注処理・リスク管理・オーダー管理）
- Monitoring（システム状態監視、取引監視、リスク監視、Kill Switch）
- Portfolio construction（候補選定・配分・ポジションサイズ決定）
- Research（ファクター計算、特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、Paper Trading レポート生成）

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup）で対話的に .env を生成
- 設定検証ツール（kabusys.validate_config）で起動前チェック
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に分離
  - 起動時にプロセス優先度を高く設定
  - stop フラグ（data/stop_requested.flag）や kill.flag に対応
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - 定期ポーリングで System / Trade / Risk をチェック
  - MONITOR_POLL_INTERVAL で間隔上書き（デフォルト 60 秒）
  - 監視ログを SQLite に永続化
- MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard 等の永続化
- Portfolio モジュール: 候補選定・等比率/スコア重み・ポジションサイズ計算・セクターキャップ
- Research モジュール: momentum, volatility, value 等のファクター計算（DuckDB 使用）
- AI モジュール:
  - news_nlp: raw_news を OpenAI（gpt-4o-mini 想定）でスコアリングして ai_scores へ保存
  - regime_detector: ETF の MA200 とマクロニュースで市場レジーム判定（market_regime へ保存）
- ユーティリティ: ロギング設定、プロセス優先度 / CPU affinity 設定、各種ヘルパー
- ツール: Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（Union 型表記や型ヒントの構文を利用）
- システムに sqlite3 が使えること（標準ライブラリ）
- 必要な外部パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定検証で YAML 検証を行う場合に推奨）

例（仮想環境の作成とインストール）
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール:
  - pip install duckdb psutil openai pyyaml

環境変数（.env）
- 推奨ワークフロー:
  1. python -m kabusys.config_setup を実行して対話式に .env を作成
  2. python -m kabusys.validate_config で設定チェック（--strict オプションあり）

- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
- 重要な任意/設定:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、Execution は paper_trading 用 SQLitePath を利用（本番 DB と分離）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能を利用する場合必須）
  - PAPER_FILL_MODE（paper_trading 時のモック約定挙動: instant|partial|never|reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0|1、本番は 0 推奨）
- 監視関連:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）を上書き（デフォルト 60）

使い方（主要コマンド）
--------------------

1) 環境ファイル作成（対話式）
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

3) 実行エンジン起動（Production / Paper）
- 本番（設定に応じて実際のブローカークライアントが使用されます）
  - python -m kabusys.run_execution
- ペーパートレード（KABUSYS_ENV=paper_trading を設定）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレードは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB とは分離されます
- 補足:
  - 実行開始時にプロセス優先度を "high" にセットします
  - data/stop_requested.flag を作成すると実行スレッドは安全に停止します
  - data/execution.pid に PID を書き出します

4) 監視プロセス起動
- python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は monitoring 用 sqlite（Settings.sqlite_path）を利用して state を永続化します
- 監視は kill.flag の作成や alert_manager を通じた通知を行い得ます

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- データベース指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

ログ
----
- ログディレクトリ（デフォルト）: logs/
- ログレベルは LOG_LEVEL 環境変数、もしくは setup_logging() 引数で指定
- setup_logging は stdout の StreamHandler（stdout）と日次ローテート（TimedRotatingFileHandler）を設定します

注意 / 運用上のポイント
-----------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険。デフォルト 0 を推奨
- OpenAI を使う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要
- paper_trading は本番 DB と分離される設計になっているため、検証時のデータ汚染リスクが低い
- MONITOR は常に本番の sqlite_path を参照（KABUSYS_ENV に依存しない）
- stop_requested.flag / kill.flag による外部制御が可能（ファイルベースのシンプルな Kill Switch）

ディレクトリ構成（主なファイル/モジュール）
---------------------------------------
以下は src/kabusys 以下の主要ファイル・サブパッケージ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                   — Settings クラス（.env 自動ロード / env 取得）
  - config_setup.py             — 対話式 .env ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py          — ログ初期化ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — （取引監視）※コードベースに実装あり
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag の読書きロジック
    - monitoring_engine.py      — 監視コンポーネントを束ねるエンジン
    - alert_manager.py          — （通知管理）※コードベースに実装あり
  - execution/
    - execution_engine.py       — ExecutionEngine 本体（run_session 等）
    - order_manager.py          — 注文管理
    - order_repository.py       — 注文履歴の永続化
    - risk_manager.py           — 発注時のリスク制御
    - broker_factory.py         — BrokerClient の生成（Mock / 実ブローカー切替）
    - reconciler.py             — ブローカ状態と DB の突合せ
  - portfolio/
    - portfolio_builder.py      — 候補選定 / 重み計算
    - position_sizing.py        — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py        — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py        — momentum / volatility / value 等の factor 計算
    - feature_exploration.py    — forward returns / IC / summary
  - ai/
    - news_nlp.py               — ニュース記事の LLM によるセンチメントスコア化
    - regime_detector.py        — 市場レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト

（メモ）実際のリポジトリでは他にも data/, config/, scripts/ 等が存在することが想定されます。

開発時のヒント
---------------
- テスト: 各モジュールは純粋関数（portfolio, research など）として設計されているため単体テストが書きやすい
- ローカル動作確認:
  - .env を作成して validate_config を実行
  - paper_trading モードで run_execution を起動して DB の動作を確認
  - run_monitoring を別プロセスで動かして監視ログが監視 DB（monitoring.db）へ蓄積されることを確認
- DuckDB を使った分析は研究モジュールのクエリ実行で使われるため、prices_daily / raw_financials 等のテーブルが必要

ライセンス・その他
------------------
- 本 README は実装から推測した使い方・要点をまとめたものです。実際の運用では config/*.yaml や scripts/、README の補足を参照してください。コードのライセンスや著作権情報はリポジトリのルートにある LICENSE 等を確認してください。

補足（よく使うコマンドまとめ）
-----------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

必要があれば README にサンプル .env のテンプレートや具体的な systemd / supervisor のユニットファイル例、デプロイ手順や DB スキーマ説明（テーブル定義）などの追記を行います。どの情報を詳細化したいか教えてください。