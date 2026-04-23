KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買・リサーチ・監視ユーティリティ群をまとめた Python パッケージ「KabuSys」です。  
本 README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

概要
----
KabuSys は以下の目的を持つモジュール群で構成されています。

- 自動発注（ExecutionEngine）とペーパートレードの分離実行
- システム／注文／リスクの監視（Monitoring）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- ファクター計算・特徴量探索（Research、DuckDB を用いる）
- ニュース NLP による銘柄／マクロセンチメントのスコアリング（OpenAI）
- 運用補助ツール（設定ウィザード、設定検証、レポート生成）

主な特徴
--------
- 実行環境（development / paper_trading / live）を環境変数で切替可能
- Paper Trading 実行時は本番 DB と分離して専用 SQLite を使用
- DuckDB によるオフライン分析（prices_daily / raw_financials 等を想定）
- OpenAI を用いたニュース NLP（batch 処理、Retry／バリデーション実装済み）
- 監視エンジン（System / Trade / Risk）と Kill Switch による安全停止
- ログは stdout と日次ローテートファイルの両方に出力（logs/ ディレクトリ）

セットアップ手順
----------------
前提:
- Python 3.8+（環境に合わせて読み替えてください）
- SQLite は標準の sqlite3 を利用
- OS によっては psutil の一部機能で権限が必要

1. リポジトリをクローンし、作業ディレクトリへ移動します。

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化（推奨）。

   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストールします（例）。

   pip install duckdb openai psutil PyYAML

   - PyYAML は config/*.yaml の検証に必要（任意）。
   - requirements.txt があればそちらを利用してください。

4. .env の作成
   - 対話式ウィザードで .env を作成・更新できます:

     python -m kabusys.config_setup

   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（ニュース NLP / レジーム判定を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR など

5. 設定検証（起動前チェック）:

   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い

使い方（起動コマンド例）
-----------------------

- 監視プロセスを起動する（SystemMonitor のポーリングループ）:

  python -m kabusys.run_monitoring

  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は常に本番 sqlite_path を使用して監視テーブルを記録します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。

- ExecutionEngine（発注エンジン）を起動する:

  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止検出時は stop_requested.flag を用いてエンジンを停止します。

- 設定ウィザード:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config

- ペーパートレード検証レポート（ツール）:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db PATH を使って別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）。

- AI / リサーチ機能（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research の関数は DuckDB 接続を受け取り純粋関数で計算します（例: calc_momentum, calc_volatility, calc_value, calc_forward_returns 等）。

重要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development / paper_trading / live（実行モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用監視 DB（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR: ログ設定
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするフラグ（"1" で有効）

監視／停止フラグ
----------------
- stop_requested.flag: run_monitoring / run_execution はプロジェクト内 data/stop_requested.flag を検知して優雅に終了します（外部プロセスからの停止指示）。
- kill.flag: KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します（Execution 側は kill.flag を検出して処理を止める仕組みを使用）。

ログ
---
- ログは stdout と logs/<app_name>.log（日次ローテート、30 日保管）に出力されます。ログレベルは LOG_LEVEL で設定可能。

ディレクトリ構成
----------------
（主要なファイル・モジュールの概要）

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み等）
  - config_setup.py            — .env 対話ウィザード CLI
  - validate_config.py         — 起動前設定検証 CLI
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — 共通ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite ベースの監視 DB レイヤ
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （注文監視ロジック）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - monitoring_engine.py     — 各 Monitor のまとめ（ポーリング）
    - kill_switch.py           — kill.flag を書く Kill Switch
    - alert_manager.py         — （アラート送信管理）
  - execution/                 — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py     — 銘柄選定・スコアソート
    - position_sizing.py       — 株数決定・スケーリング・lot 単位丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー等
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）による銘柄センチメント集計
    - regime_detector.py       — マクロ + ETF MA200 を合成した市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

補足・運用上の注意
-----------------
- 本番運用（KABUSYS_ENV=live）では設定ミスが致命的になり得るため validate_config でのチェックや LINE 通知設定の確認を強く推奨します。
- Paper Trading（KABUSYS_ENV=paper_trading）時は、発注はモックで処理され本番 DB とは分離されます（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI による NLP は API 呼び出しのレート制限やコストが発生します。API キー管理と呼出頻度に注意してください。
- process_priority.set_process_priority() はプラットフォーム依存の振る舞いをラップしています。権限不足で設定できない場合は警告のみ出力します。

ライセンス・貢献
----------------
- 本プロジェクトのライセンスや貢献ルールはリポジトリのトップレベルファイル（LICENSE, CONTRIBUTING.md 等）を参照してください。

問題や質問
----------
- 実行時エラーや設定方法に関する問い合わせは Issue を作成してください。ログや .env（機密情報は除く）の該当部分を添えていただくと対応が早くなります。

以上がこのコードベースの概要と利用方法です。README に追加したい具体的なコマンド例や環境サンプル（.env.example）を希望される場合は教えてください。必要に応じてサンプル .env のテンプレートも作成します。