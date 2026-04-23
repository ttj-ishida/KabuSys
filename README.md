# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）のリポジトリです。  
この README はコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

注意: 本リポジトリは実運用向けのコンポーネント（発注ロジック・外部 API 呼び出し）を含みます。実際に稼働させる場合は十分に理解した上で、テスト環境（paper_trading）で検証してください。

## プロジェクト概要

KabuSys は以下の機能群を持つ日本株自動売買システムの基盤です。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理・約定整合処理
- 監視 (Monitoring): システム稼働監視、注文監視、リスク監視、Kill Switch
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム係数
- 研究用モジュール: ファクター計算、特徴量探索、IC 計算等（DuckDB ベース）
- AI モジュール: ニュース NLP（OpenAI）を使ったセンチメント評価、レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、環境ファイルウィザード、設定検証
- ツール: Paper Trading 検証レポート生成など

設計方針の一部:
- Paper trading（ペーパートレード）と live（本番）DB を分離
- DuckDB を分析用 DB として採用
- .env による設定管理・対話式ウィザード・検証 CLI を提供
- AI 呼び出しはフェイルセーフ（失敗時にスキップ/フォールバック）

## 主な機能一覧

- run_execution: ExecutionEngine を起動（KABUSYS_ENV によって paper_trading 用の Mock ブローカーを使用可能）
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整可能）
- config_setup: .env を対話式に生成・更新するウィザード
- validate_config: .env と config/*.yaml を起動前に検証（--strict オプションあり）
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- research: DuckDB を用いたファクター計算・ファクター解析（モメンタム、バリュー、ボラティリティ等）
- ai.news_nlp: OpenAI（gpt-4o-mini）でニュースをスコア化して ai_scores テーブルへ格納
- ai.regime_detector: ETF とマクロニュースを組み合わせて市場レジームを判定
- monitoring: system_status, trade_logs, risk_logs, positions, dashboard の永続化（SQLite）と監視ロジック
- tools.paper_verification_report: ペーパートレード結果の検証レポート生成

## 前提・必要パッケージ

推奨 Python バージョン: 3.10+

主な依存ライブラリ（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合に推奨）
- その他標準ライブラリ（sqlite3, logging, threading など）

pip でのインストール例（仮の requirements の場合）:
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそちらを使用してください。）

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env の作成（推奨: 対話式ウィザードを使用）
   - python -m kabusys.config_setup
     ウィザードに従い J-Quants トークンや kabuAPI パスワード、KABUSYS_ENV 等を設定します。
   - 自動で .env を生成・更新します。

4. 設定検証
   - python -m kabusys.validate_config
   - 重大な設定ミスがあれば修正してください。
   - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルトの DB/ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite (paper_trading 環境時): data/paper_trading.db
     - ログ: logs/
   - 必要に応じて環境変数で上書き可能（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）

6. （オプション）OpenAI API を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、AI モジュール呼び出し時に引数で渡します。

## 使い方（実行方法）

基本的にパッケージモジュールとして提供されている実行スクリプトを Python -m で起動します。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で制御:
    - development: 発注は行わない（開発用）
    - paper_trading: MockBroker を用いて data/paper_trading.db に記録（本番 DB から分離）
    - live: 実際に発注を行います（注意して使用）
  - 実行中の停止:
    - データディレクトリに kill.flag を作成することで停止シグナルを送る（KillSwitch）
    - run_execution は data/stop_requested.flag の存在もチェックします

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に参照します（環境に依らず）
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究モジュール（ライブラリ関数の呼び出し）
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - kabusys.research.calc_momentum(...) など（DuckDB 接続を渡す）

## 主要な環境変数（抜粋）

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用・設定:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モードで使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除（1 = 削除。production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

注意: .env 自動ロード順は OS 環境変数 > .env.local > .env です。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## ロギング

共通のログ設定ユーティリティが提供されています:
- kabusys.utils.logging_setup.setup_logging(app_name="execution")
  - stdout（StreamHandler）と日次ローテートするファイルハンドラをルートロガーに設定します
  - ログファイルは <LOG_DIR>/<app_name>.log（デフォルト logs/）

## プロセス優先度

- kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
  - run_execution / run_monitoring 起動時に最初に high に設定する仕組みが組み込まれています
  - 権限不足等で設定できない場合は警告を出してスキップします

## データベースと永続化

- DuckDB: 分析・研究用データ（prices_daily, raw_financials など）
- SQLite (monitoring.db): 監視ログ・trade_logs・positions・risk_logs・dashboard を永続化
- Paper trading モードでは別 SQLite（data/paper_trading.db）を使用して本番 DB と分離

## ディレクトリ構成

リポジトリ内の主要なファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — 優先度 / CPU affinity 設定
  - execution/                — ExecutionEngine 周りの実装（発注・リスク等）
    - (BrokerClientFactory, ExecutionEngine, OrderManager, etc.)
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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

プロジェクトルートにはデフォルトで以下のパスが参照されます:
- data/ — DB / PID / フラグファイル等（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
- logs/ — ログファイル（デフォルト）

## 運用時の注意点（重要）

- KABUSYS_ENV=live の場合は十分に設定を確認（LINE 通知や Kill Switch 設定など）。validate_config の live 用検証を活用してください。
- 本番での起動は必ず事前に paper_trading モードで検証すること。発注ロジックは実際の金銭リスクを伴います。
- OpenAI や取引 API 呼び出しの失敗時はフェイルセーフが組み込まれていますが、運用前にロギング・通知が適切に機能するか確認してください。
- .env は絶対に機密情報（APIキー等）が含まれるため Git にコミットしないでください。

---

README に記載の内容はコードベースの現状に基づきまとめています。追加の機能説明や利用手順（デプロイ、コンテナ化、CI 設定など）が必要であれば、その目的に合わせてセクションを追加します。