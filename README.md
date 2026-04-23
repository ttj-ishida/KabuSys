KabuSys — 日本株自動売買システム（README）
========================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なシステム群です。本リポジトリは以下の主要機能を含みます:

- 発注実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理を行う
- 監視（Monitoring）: システム稼働状況、注文／約定の監視、リスク判定と Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制約等の純粋関数群
- リサーチ（Research）: ファクター計算・特徴量探索ツール（DuckDB を利用）
- AI モジュール: ニュースのセンチメント（OpenAI）によるスコアリング、レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、環境設定ウィザード／検証 CLI、ツール類

主な特徴
--------
- 環境分離: paper_trading モードでは実口座 DB と完全分離（data/paper_trading.db）
- .env ウィザード（config_setup.py）で対話的に環境変数を作成・更新可能
- validate_config.py で起動前に設定の妥当性を検証（--strict モードあり）
- DuckDB を用いたデータ分析・ファクター計算
- OpenAI（gpt-4o-mini）を使ったニュース NLP、レジーム判定（API キーによる）
- 監視モジュールは kill.flag を書き込むことで ExecutionEngine を停止させる Kill Switch を実装
- ログはコンソール + 日次ローテートファイル（logs/<app>.log）へ出力

セットアップ手順
----------------
前提:
- Python 3.9+（プロジェクトの pyproject.toml を参照）
- 必要パッケージ（duckdb, psutil, openai, PyYAML（任意）など）をインストール

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存関係をインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は duckdb, psutil, openai を個別にインストール）

3. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザード完了後、.env に設定が保存されます。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- モード
  - KABUSYS_ENV — 実行環境: development | paper_trading | live
- DB パス（デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db （paper_trading 用）
- ログ / 動作
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp/regime_detector を使う場合必須）
- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject

使い方（主要スクリプト）
-----------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録する（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 実行中に data/stop_requested.flag を作成するとエンジンを停止する

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を環境に関わらず使用
    - 停止フラグ: data/stop_requested.flag を作成するとループを抜ける

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI モジュール（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY または明示的な api_key 引数が必要

運用上の注意
------------
- paper_trading と live は DB を分離しており、paper_trading は data/paper_trading.db を使用します。誤って本番 DB に書き込まないよう設定を確認してください。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine に対する停止命令として使用されます。監視モジュールは特定のリスク条件で kill.flag を書き込みます。
- ログは logs/<app>.log に日次ローテートで出力されます。ログディレクトリ作成に失敗した場合はコンソールのみにフォールバックします。
- run_execution / run_monitoring は起動直後にプロセス優先度を high に設定しようとします（プラットフォーム依存で失敗する場合は警告に留まります）。

ディレクトリ構成（主なファイル）
-------------------------------
以下はリポジトリ内の主要モジュールとファイルの抜粋です（src/kabusys 以下）:

- __init__.py
- config.py — 環境変数・設定管理（自動 .env ロード、Settings クラス）
- config_setup.py — .env 対話ウィザード（CLI）
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- execution/   — 発注関連（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py — システム稼働・データ鮮度監視
  - trade_monitor.py — 注文約定監視（省略ファイルは同ディレクトリ内）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — アラート送信（LINE 等。実装ファイル参照）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・キャップ・丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

- ai/
  - news_nlp.py — ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
  - regime_detector.py — マクロ + ETF MA に基づくレジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

- utils/
  - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

例: 簡単な起動手順
------------------
1. .env を作成（ウィザード）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 監視プロセス起動（別ターミナル）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

4. 実行エンジン起動（本番または paper_trading 設定に応じて）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

サポート・拡張ポイント
---------------------
- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_breadth など）を用意することでリサーチ／AI モジュールが動作します。
- logging_setup を全スクリプトで利用してログ挙動を統一しています。LOG_DIR/LOG_LEVEL を環境変数で調整可能です。
- AI 呼び出しはリトライ・バックオフ・レスポンス検証を実装していますが、API レートやコスト管理に注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

最後に
------
この README はコードベースの主要機能と使い方をまとめた概要です。各モジュールの詳細な実装や追加設定（broker クライアントの設定、strategy / execution の YAML 設定ファイルなど）は該当ファイル／config ディレクトリのドキュメントやソースコメントを参照してください。必要であれば各モジュールの使い方サンプルや運用手順をさらに追記できます。