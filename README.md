KabuSys
======

日本株自動売買システムのサンプル実装（ライブラリ＋起動スクリプト群）。  
このリポジトリは以下の主要機能を持ちます：戦略用ファクター計算、ポートフォリオ構築、発注エンジン実行・監視、Paper Trading 用検証ツール、AI（LLM）を使ったニュースセンチメント／レジーム判定など。

概要
----
- 設計方針の要点
  - 取引ロジック（ExecutionEngine）と監視（Monitoring）は分離。監視は停止フラグ等を用いてエンジンを安全に停止可能。
  - Paper Trading と Live は DB を分離（paper_trading 環境では data/paper_trading.db を使用）。
  - DuckDB を分析／リサーチ用途のローカル DB として使用。SQLite は監視・トレードログの永続化に使用。
  - OpenAI API（gpt-4o-mini）を用いたニュースセンチメント、レジーム判定を実装（API キー必須）。
  - .env ベースの設定管理・対話式ウィザード・事前検証ツールを用意。

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（実売買 / ペーパートレード切替）。
  - run_monitoring.py: SystemMonitor を定期ポーリングする監視プロセス起動。
- 設定管理
  - config_setup.py: .env を対話式に作成/更新するウィザード。
  - validate_config.py: .env と config/*.yaml の事前検証ツール（--strict オプションあり）。
  - config.Settings: 環境変数アクセスラッパー（デフォルト値と検証含む）。自動で .env をロード（プロジェクトルートが検出できる場合）。
- 監視/アラート
  - monitoring package:
    - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch など。
    - MonitoringDB: monitoring 用 SQLite スキーマの初期化と CRUD。
    - kill.flag / stop_requested.flag を用いた安全停止機構。
- 発注関連（Execution 内部コンポーネント）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（実装はコードベースに依存）。
- ポートフォリオ構築（純粋関数）
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数。
- 研究 / リサーチ
  - research: ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、統計サマリ等（DuckDB 接続を受ける）。
- AI 関連
  - ai.news_nlp: raw_news を集約して OpenAI に送信し、ai_scores テーブルへ格納。
  - ai.regime_detector: ETF の MA とマクロニュースの LLM 評価を合成して market_regime を計算・永続化。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシなど）。

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai
   - オプション:
     - PyYAML（validate_config で config/*.yaml の構文チェックを行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （パッケージ名はプロジェクトの requirements.txt がある場合はそちらを使用してください）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考にしてください。
   - 自動ロード:
     - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env/.env.local を自動ロードします。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります。

5. データディレクトリ
   - デフォルトで data/ 以下に SQLite/DuckDB/フラグファイル等を作成します。必要に応じて .env のパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）を変更してください。

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 用
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY — AI 関連機能で必須
- PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒（デフォルト 60 秒）
- KILL_FLAG_CLEAR_ON_START — 本番起動時の kill.flag 自動クリアフラグ（0/1）

使い方（実行例）
----------------
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring 起動（SystemMonitor の定期実行）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します（両方のスクリプトで参照）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定できます。

- AI 処理（プログラム呼び出し）
  - ai.news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡す必要があります。

ログ
----
- setup_logging により、ルートロガーは stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用します。

停止・Kill Switch
-----------------
- run_execution / ExecutionEngine 停止
  - 監視モジュール（KillSwitch）が条件を満たすと data/kill.flag に理由を保存し、ExecutionEngine 側で検出して停止する仕組みがあります。
  - run_execution.run も data/stop_requested.flag の存在を監視し、あれば Engine.stop() を呼び出します。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で制御（本番では 0 推奨）。

ディレクトリ構成（主なファイル）
-----------------------------
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数ラッパーと自動 .env ロード
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 起動前検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP / OpenAI 連携
    - regime_detector.py          — 市場レジーム判定
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ + MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py            — （コードベースに含まれる想定の監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — アラート送信管理（LINE 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - その他: execution/*（発注周りコンポーネント）、data/（実行時に使用されるファイル群）

注意事項 / 運用上のポイント
--------------------------
- 本リポジトリは学習用／参考実装の側面を持ちます。実際の証券会社 API での運用は法的・セキュリティ面の確認が必要です。
- .env は決して Git にコミットしないでください（config_setup でも注意喚起あり）。
- OpenAI API を利用する処理はコストがかかり、レート制限や一時エラーへのリトライ設計が入っています。API キーの管理に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL で間隔を変更できます。ただし極端に短くするとコストや負荷が増えます。
- Paper Trading（検証）では本番 DB と分離するため環境を適切に設定してください（KABUSYS_ENV=paper_trading）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問題報告・拡張
--------------
- 各モジュールは比較的モジュール化されています。AI 処理や DB スキーマ、監視閾値などは config/*.yaml や環境変数で調整可能な点が多く、要件に応じて拡張してください。

以上がこのコードベースの簡易 README です。必要であれば起動フロー図・主要 API のシーケンス図や詳しい環境変数一覧（説明付き）を追加で作成します。どの情報をより詳細にしたいか教えてください。