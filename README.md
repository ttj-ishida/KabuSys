KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」の実装の一部です。
本 README はコードベース（src/kabusys 以下）を元に、プロジェクト概要、
機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は日本株の自動売買を想定したモジュール群です。主要な機能群は以下のとおりです。

- 実行エンジン（ExecutionEngine） — ブローカーとのやりとり、注文管理、リスク管理、約定の調停（reconciler）など。
- 監視（Monitoring） — システム状態、取引ログ、リスク（ドローダウン・ポジション上限）監視、Kill Switch（停止フラグ）等をポーリングしてログ保存・アラート。
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ計算、セクター上限など。
- リサーチ（Research） — DuckDB を使ったファクター計算（モメンタム／バリュー／ボラティリティ）や特徴量解析。
- AI 利用（AI） — OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析・市場レジーム判定。
- ツール群 — Paper Trading の検証レポート生成などのユーティリティ。

特徴一覧
--------
- 環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え。
  - paper_trading は MockBroker を使用し、本番 DB と分離された paper_trading.db を使用。
- 設定管理:
  - .env（および .env.local）から環境変数自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 対話式ウィザード（config_setup.py）で .env を簡単作成。
  - 起動前に設定検証ツール（validate_config）で不足や警告を検出。
- 監視／フェイルセーフ:
  - SQLite 監視 DB（デフォルト data/monitoring.db）へ system_status / trade_logs / risk_logs / positions / dashboard を保存。
  - Kill Switch（data/kill.flag）で ExecutionEngine を停止可能。
  - stop_requested.flag（data/stop_requested.flag）で起動スクリプトを安全に停止できる仕組み。
- OpenAI 統合:
  - ニュースをまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores テーブルへ保存（トークンオーバーフロー対策、バッチ処理、リトライ等を実装）。
  - 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）。
- ロギング:
  - 統一的な logging 設定。コンソール（stdout）と日次ローテーションするファイル出力（logs/<app_name>.log）。

セットアップ手順
--------------
以下は最小限のセットアップ手順（開発者向け）です。環境によって適宜読み替えてください。

1. リポジトリをクローン
   - git clone ... で取得。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 推奨/状況依存:
     - PyYAML（config/*.yaml の中身検証に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がない場合は上記を個別にインストールしてください。

4. 初期設定（.env 作成）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit code=1）になります。

5. データディレクトリ準備
   - デフォルトの SQLite / DuckDB パスは data/ 以下にある想定。
   - 必要であればディレクトリ作成:
     - mkdir -p data logs

環境変数（主要）
----------------
重要な環境変数（.env に設定する想定）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD        (必須)
- KABU_API_BASE_URL        (オプション, デフォルト http://localhost:18080/kabusapi)
- OPENAI_API_KEY           (AI 機能を使う場合に必要)
- DUCKDB_PATH              (デフォルト data/kabusys.duckdb)
- SQLITE_PATH              (監視 DB、デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- KABUSYS_ENV              (development | paper_trading | live)
- LOG_LEVEL                (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KILL_FLAG_CLEAR_ON_START (0|1)
- MONITOR_POLL_INTERVAL    (run_monitoring のポーリング間隔（秒）: デフォルト 60)

設定自動読み込みの順序:
- OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方（主なスクリプト・API）
----------------------------

1. 実行エンジン（ExecutionEngine）を起動
   - 実際の注文処理を行うエンジンを別プロセスで起動します。
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します（本番 DB と完全分離）。
     - 起動時に data/stop_requested.flag が存在する場合は起動せずに終了します。
     - エンジンは data/execution.pid（デフォルト）に PID を書きます。
     - 停止は stop_requested.flag を作成するか、Kill Switch（kill.flag）によりトリガーされます。

2. 監視プロセスを起動
   - システム監視のポーリングループを実行します。
   - 実行:
     - python -m kabusys.run_monitoring
   - オプション/環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
   - 監視内容:
     - システムリソース（CPU/MEM/DISK）、データ鮮度、Execution プロセス存在チェック、trade_logs や risk の監視、Kill Switch 評価など。
   - stop_requested.flag を検知するとループを終了します。

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code=1）。

4. .env ウィザード
   - python -m kabusys.config_setup

5. Paper Trading 検証レポート
   - レポート生成:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db path/to/paper_trading.db
     - または環境変数 PAPER_TRADING_SQLITE_PATH を設定

6. プログラム API（Python から呼び出す例）
   - ニュースセンチメントスコア算出（AI）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")  # 書き込みは ai_scores テーブル
   - 市場レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")
   - リサーチ（ファクター計算）:
     - from kabusys.research import calc_momentum, calc_volatility, calc_value
     - calc_momentum(duckdb_conn, target_date)
   - ポートフォリオ構築:
     - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

運用上の注意
------------
- paper_trading モードは本番 DB を汚さないように設計されています。必ず KABUSYS_ENV を確認してから運用してください（live は本番）。validate_config は live 設定時に警告を出すので必ず確認を。
- Kill Switch（Settings.kill_flag_path）を利用すると、重大なリスク条件で ExecutionEngine に停止シグナルを送れます。通常は本番環境での誤操作に注意してください（KILL_FLAG_CLEAR_ON_START=1 は本番では危険）。
- ログは logs/ 以下にアプリ名ごとの日次ローテートファイルが作成されます。logs ディレクトリの作成・書き込み権限に注意してください。
- process priority を起動時に "high" に設定しますが、権限不足で失敗する場合は警告を出しスキップします（プラットフォーム依存）。

ディレクトリ構成
----------------
src/kabusys の主なファイル・ディレクトリ（抜粋）:

- __init__.py
- config.py                 — 環境変数 / Settings 管理（自動 .env ロード）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

パッケージ群:
- /execution
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py
  - 実際の注文処理周りのロジック（ブローカー、リスク制御、オーダー永続化等）
- /monitoring
  - monitoring_db.py         — SQLite 永続化層
  - system_monitor.py        — CPU/MEM/DISK、データ鮮度、PID チェック
  - trade_monitor.py         — trade_logs の異常検出（※ファイル中に実装あり）
  - risk_monitor.py          — ドローダウン / ポジション上限監視
  - monitoring_engine.py     — 各 Monitor を束ねる
  - kill_switch.py           — kill.flag の生成・管理
  - alert_manager.py         — アラート送信（LINE 等） ※実装参照
- /portfolio
  - portfolio_builder.py     — 候補選定・重み付け
  - position_sizing.py       — 発注株数計算、aggregate cap 等
  - risk_adjustment.py       — セクターキャップ、レジーム乗数
- /research
  - factor_research.py       — モメンタム / ボラ / バリュー等のファクター計算
  - feature_exploration.py   — 将来リターン・IC・統計サマリー
- /ai
  - news_nlp.py              — ニュース NLP（OpenAI）で銘柄別スコアを生成
  - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント）
- /utils
  - logging_setup.py         — アプリ共通のログ設定ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ
- /tools
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

（補足）
- DuckDB は分析用の主データベース（prices_daily / raw_financials / raw_news 等のテーブル想定）。
- SQLite は監視・取引ログ / order 履歴用に使用。
- OpenAI への呼び出しはネットワーク/リトライ/バリデーションを組み込んでおり、失敗時にフェイルセーフ（例: スコア 0.0 やスキップ）する設計です。

よくあるコマンドまとめ
--------------------
- .env を作る: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

最後に
------
この README はコードベースの主要機能・運用フローを簡潔にまとめたものです。各モジュールに詳細なドキュメント（ソース内ドックストリング）や追加の config/*.yaml、スクリプトがあるため、実運用前に必ず validate_config の実行、.env の確認、テスト環境（paper_trading）での動作検証を行ってください。質問や補足があれば教えてください。