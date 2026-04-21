KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコードベースです。戦略（リサーチ）・ポートフォリオ構築・発注（Execution）・監視（Monitoring）・AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。本 README は開発者/運用者向けに、プロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は次の機能を持つモジュール群で構成されています。

- 市場データ（DuckDB）を用いたファクター計算・特徴量探索（research）
- 銘柄選定・重み付け・株数決定（portfolio）
- 発注エンジン（Execution）とブローカークライアント抽象化（本番 / ペーパー両対応）
- システム状態・注文・リスクの監視（monitoring）
- ニュースを LLM（OpenAI）でセンチメント解析する AI モジュール（ai）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定 等）

主要な実行スクリプト（モジュール）
- monitoring: kabusys.run_monitoring (監視ループのデーモン)
- execution: kabusys.run_execution (ExecutionEngine の起動)
- 設定ウィザード: kabusys.config_setup
- 設定検証: kabusys.validate_config
- ペーパートレード検証レポート: kabusys.tools.paper_verification_report

機能一覧
--------
主な機能のサマリ:

- Research / ファクター計算
  - momentum, volatility, value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC 計算、統計サマリー

- Portfolio Construction
  - 候補選定（スコア順）
  - 等金額・スコア加重の重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（risk_based / equal / score）・単元株丸め・aggregate cap

- Execution
  - 本番・ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory によるクライアント生成（Mock 対応）
  - RiskManager / OrderManager / Reconciler / ExecutionEngine の統合

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働/データ鮮度監視
  - TradeMonitor: 発注ログ・滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill switch 評価
  - MonitoringEngine: 各モニタをまとめて定期実行、アラート発行・kill.flag 書き込み

- AI
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores テーブルへ書込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュース LLM を合成して market_regime を判定・書込み

- 運用支援
  - config_setup: .env を対話形式で作成/更新
  - validate_config: 起動前チェック（必須環境変数・ファイル・YAML パース等）
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------

1. リポジトリをクローン／配置
   - この README の想定はソースが `src/kabusys` 以下にある構成です。

2. Python 仮想環境を作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 以下はこのコードベースで使用されている主要依存です。環境に合わせてインストールしてください。
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML を検証したい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を作成してください。主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB; デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の DB; デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL (INFO 等)
     - PAPER_FILL_MODE (paper_trading の埋め方: instant|partial|never|reject)

5. データディレクトリ等の作成（自動で作られることがあるが手動で準備しても可）
   - data/
   - logs/

6. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit code 1）

使い方（基本）
--------------

起動スクリプトはモジュールとして実行できます。各コマンドは仮想環境を有効にした上で実行してください。

- 監視デーモンを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
    - 監視は常に本番 sqlite_path を使用（環境に関わらず）。停止はプロジェクトルートの data/stop_requested.flag を作成するか Ctrl-C。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper SQLIte（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB とは分離されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動を行わず終了します。
    - エンジンは data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成または kill でプロセスを停止。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡す。api_key は引数または環境変数 OPENAI_API_KEY を使用。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に DuckDB 接続を渡して実行。

運用・停止
-----------
- 停止フラグ:
  - 実行中コンポーネントの停止要求はプロジェクトの data/stop_requested.flag を作成して行えます（run_monitoring / run_execution がチェックします）。
- Kill Switch:
  - 監視モジュールがリスク条件に応じて data/kill.flag を書き込むことがあります（ExecutionEngine 側は設定に応じてこれを検知して停止する設計）。
- ログ:
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR 環境変数で変更可能。

重要な環境変数（抜粋）
--------------------
- KABUSYS_ENV
  - 値: development | paper_trading | live
  - 動作モードを切り替え。paper_trading は発注のモック化と DB 分離を行う。
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 必須。外部 API 認証用。
- OPENAI_API_KEY
  - AI 機能（news_nlp / regime_detector）を使う場合に必要。
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - DB のファイルパス。デフォルトは data 以下。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。整数 >0。デフォルト 60。
- PAPER_FILL_MODE
  - ペーパートレード時の埋め方 (instant|partial|never|reject)。デフォルト "instant"。

注意事項 / 動作保証
-------------------
- .env ファイルは絶対にバージョン管理にコミットしないでください（config_setup が注意文を出力します）。
- OpenAI 周りは外部 API 呼び出しを行うため、API キーとネットワークの可用性に依存します。API エラーやレート制限はリトライ戦略が組まれていますが、運用上の注意が必要です。
- run_monitoring は Monitoring のため常に本番 sqlite_path を使用します（環境変数にかかわらず）。これは監視が本番データを参照する設計によるものです。
- 実行環境（KABUSYS_ENV）が live の場合は特に慎重に設定と権限を確認してください（validate_config が警告を出します）。

ディレクトリ構成
----------------
（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_monitoring.py              — Monitoring デーモン起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py            — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py              — SQLite テーブル定義・ラッパー
    - monitoring_engine.py          — 各 Monitor を束ねる実行エンジン
    - system_monitor.py             — システム・データ鮮度監視
    - trade_monitor.py              — (存在する想定の) 注文監視ロジック
    - risk_monitor.py               — ドローダウン・ポジション監視
    - kill_switch.py                — kill.flag 制御
    - alert_manager.py              — (存在する想定の) 通知送信ユーティリティ
  - execution/
    - execution_engine.py           — 実際の発注エンジン（EngineConfig 等）
    - broker_factory.py             — BrokerClientFactory（Mock / 実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py               — 共通ロギング設定
    - process_priority.py            — プロセス優先度 / CPU affinity
    - __init__.py

補足（開発者向け）
-----------------
- DuckDB 接続を引数で受ける設計なので、REPL やテストから関数を直接呼んで検証が可能です。
- テストを書く際は外部 API（OpenAI 等）呼び出しをモックすることを推奨します。コード中に _call_openai_api を差し替えられる箇所が用意されています。
- monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。

最後に
------
この README はコードベースのエントリポイントと運用に必要な情報をまとめたものです。実装の詳細（例えば TradeMonitor の具体的なチェック、ExecutionEngine の内部フロー等）は各モジュールの docstring / コメントを参照してください。運用前に必ず python -m kabusys.validate_config で設定検証を行ってください。