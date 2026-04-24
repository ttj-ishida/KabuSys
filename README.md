KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買・研究・監視ツール群（KabuSys）です。  
本 README はコードベース（src/kabusys 以下）に基づき、導入・実行方法、主要機能、構成を日本語でまとめたものです。

概要
----
KabuSys は以下の機能群を持つモジュール式のシステムです。

- 発注エンジン（ExecutionEngine）: ブローカーとのやり取り、注文管理、リスク管理を行う。
- 監視（Monitoring）: システム健全性、注文・約定ログ、リスク（ドローダウン等）を定期的に監視しログ保存・アラートを行う。
- 研究（Research）: DuckDB を用いたファクター計算・特徴量解析モジュール。
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ算出、セクター制限などの純粋関数群。
- AI 支援（AI）: ニュースのセンチメント評価や市場レジーム判定（OpenAI を利用するモジュール）。
- ツール: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- 設定ユーティリティ: .env のウィザード生成、設定検証 CLI。

主な機能一覧
-------------
- 環境管理
  - Settings クラスで環境変数を一元管理（自動で .env / .env.local を読み込み）。
  - config_setup による対話式 .env 生成。
  - validate_config による起動前チェック（必須環境変数・ファイル存在・YAML 検証など）。
- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 用 DB に分離保存。
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔、環境変数で上書き可）。
- 監視
  - MonitoringDB: SQLite に system_status / trade_logs / positions / risk_logs / dashboard テーブルを作成・更新。
  - RiskMonitor / TradeMonitor / SystemMonitor による定期チェック、KillSwitch による停止シグナル書き込み。
  - logging_setup: stdout（Stream）と日次ローテーションのファイルロギングを統一的に設定。
- 研究・分析
  - research モジュールで momentum / volatility / value ファクター、将来リターン・IC・統計サマリを計算。
  - DuckDB ベースの処理（prices_daily / raw_financials 等を参照）。
- AI
  - news_nlp: ニュース記事をまとめて OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存。
  - regime_detector: ETF（1321）とマクロニュースを組み合わせて日次レジーム判定を行い DB に保存。
- ツール
  - paper_verification_report: ペーパートレード DB（data/paper_trading.db）から検証レポートを生成。

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（型ヒントに | union 表記などを使用）。
- システム依存のライブラリ: duckdb, psutil, openai。研究や設定検証で PyYAML があると YAML 検証が有効になります。

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください）

3. プロジェクトルートに .env を配置
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（下の「推奨 .env の例」を参照）。

4. データディレクトリ作成（自動作成されることも多いですが事前準備）
   - mkdir -p data logs

5. 初期 DB は実行時に自動作成（monitoring は init_monitoring_db でテーブル作成）。DuckDB 用のスキーマや prices_daily などは運用に応じて事前にロードしてください。

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 環境で使用）
- ロギング / 制御
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI 呼び出しに使用
- 監視パラメータ（Settings 経由）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KILL_FLAG_CLEAR_ON_START （0/1）

推奨 .env の例
----------------
（config_setup を使えば自動生成できます）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
（.env は決して Git にコミットしないでください）

使い方
-------
基本的なコマンド（プロジェクトルートで仮想環境を有効にした状態で実行）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意:
    - run_monitoring は常に本番用 sqlite_path を使用（環境に関わらず monitoring DB は同一ファイルを参照）。
    - 停止にはプロジェクトルート/data/stop_requested.flag ファイルを作成する。（run_monitoring はこのフラグを検知してループを抜けます）

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB とは分離）。
  - 実行中の停止は data/stop_requested.flag を作成することでエンジンに通知されます。
  - 実行エンジンは起動時に PID ファイルを data/execution.pid に書きます。

- AI / レジーム / ニュース （プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ロギング
  - 各起動スクリプトは kabusys.utils.logging_setup.setup_logging を使用し、logs/<app_name>.log に日次ローテーションで出力します。ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/。

動作上の注意点 / 運用メモ
------------------------
- monitor のポーリング間隔 MONITOR_POLL_INTERVAL は秒 (int)。1 未満や負数を設定した場合はデフォルトの 60 秒にフォールバックします。
- Settings は起動直後に .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- run_execution は paper_trading 環境時に paper_trading 用 DB を使い、本番データと完全分離します。
- Kill Switch（data/kill.flag）は RiskMonitor の評価・KillSwitch.evaluate により書き込まれる仕組みです。ExecutionEngine は起動時に kill.flag のクリア設定（KILL_FLAG_CLEAR_ON_START）を選べますが、本番では 0 を推奨。
- AI モジュールは OpenAI API を利用します。API の呼び出し・リトライロジックが組み込まれていますが、API キー・費用・利用制限に注意してください。
- SQLite / DuckDB のスキーマはコード内で自動作成・マイグレーションを行います（init_monitoring_db 等）。

ディレクトリ構成
----------------
主要ファイル / ディレクトリ（src/kabusys 以下。抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (存在を前提 — 実装ファイルは個別に)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (存在を前提)
  - execution/
    - execution_engine.py      (存在を前提)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/monitoring_db.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

（注）上記はこの README を生成する時点でのソース抜粋に基づく構成です。細かいファイルや追加のモジュールはリポジトリ全体を参照してください。

開発・テストについて
--------------------
- 自動テストや CI を導入する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存の自動 .env 読み込みを無効化するとテストの再現性が高まります。
  - OpenAI 呼び出しはユニットテスト中は外部呼び出しをモック（unittest.mock.patch）してください。news_nlp._call_openai_api や regime_detector._call_openai_api を差し替えられるよう実装されています。
- DuckDB / SQLite に対するテスト用軽量 DB パスを使用することを推奨します（tmp ディレクトリ等）。

ライセンス / 貢献
-----------------
- README 中ではライセンス情報を含めていません。リポジトリに LICENSE ファイルがある場合はそちらを参照してください。
- 機能追加や問題報告は Issue / Pull Request を通じてお願いします。

最後に
------
本ドキュメントはコードのコメント・構造から自動的にまとめた要約です。導入や運用の詳細は実運用環境に合わせて設定ファイル（config/*.yaml や .env）やブローカ接続情報を適切に管理してください。必要であれば README を補足する運用手順書やデプロイ手順を別途作成することをおすすめします。