KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買・研究・監視を目的とした軽量フレームワークです。  
設計方針として「本番と研究/ペーパートレードを明確に分離」「ルックアヘッドバイアスを防ぐ」「フェイルセーフを重視」を掲げています。

主な特徴
--------
- 実行環境の分離: development / paper_trading / live をサポート。paper_trading 時は MockBroker を使用し本番 DB と分離。
- 実行コンポーネント:
  - ExecutionEngine: 発注・リスク管理・約定管理
  - MonitoringEngine: システム稼働・注文状況・リスク監視、Kill Switch（フラグファイル）による強制停止
- 研究用モジュール: ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン、IC 計算など（DuckDB ベース）
- AI 支援モジュール: ニュースセンチメント（OpenAI）を用いた ai_score / regime 判定（OpenAI API 必須）
- ユーティリティ: ログ設定、プロセス優先度設定、.env ウィザード、設定検証 CLI、ペーパートレード検証レポートなど
- 永続化: DuckDB（分析用）と SQLite（監視・注文トラッキング）を併用

必須・主要な環境変数
--------------------
（.env を用意することを推奨。config_setup ウィザードあり）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知設定）

注記:
- run_monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用します（監視は本番 DB を見る想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して完全に分離します。

セットアップ手順（開発用）
------------------------
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil openai
   - 任意: PyYAML（config の検証で使う）: pip install PyYAML
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict
6. ディレクトリ（data, logs 等）が自動生成されます。必要に応じて手動で作成してください。

主要スクリプト・使い方
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いして exit(1)

- ExecutionEngine の起動（自動売買本体）
  - python -m kabusys.run_execution
  - 挙動:
    - プロセス優先度を high に設定（set_process_priority）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH を用いる
    - 停止: data/stop_requested.flag により優雅に停止
    - PID ファイル: data/execution.pid を利用

- MonitoringEngine の起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用
    - 停止: data/stop_requested.flag を検知して終了

- ペーパートレード検証レポート（標準出力にレポート）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ・ファイル
--------------
- logging_setup により:
  - コンソール出力（stdout）
  - 日次ローテートされるファイル出力: <LOG_DIR>/<app_name>.log（デフォルト logs/<app>.log）
  - バックアップ保持: 30 日
- PID ファイルやフラグ:
  - data/execution.pid（ExecutionEngine 用）
  - data/stop_requested.flag（run_* スクリプトの停止トリガ）
  - data/kill.flag（監視からの Kill Switch 発動時に生成）

監視・Kill Switch
----------------
- monitoring モジュールは system_status / trade_logs / risk_logs / positions / dashboard テーブルを SQLite に作成・保守します（monitoring.monitoring_db.init_monitoring_db）。
- RiskMonitor がドローダウンやポジション上限を検出すると risk_logs に記録し、KillSwitch が条件を満たした場合 data/kill.flag を書き込み ExecutionEngine 停止を促します。
- KillSwitch の書き込みは冪等で、既に存在する場合は上書きしません。

AI 関連
-------
- AI モジュール（kabusys.ai）:
  - news_nlp.score_news: raw_news から銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルに保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルに書き込む
- 必須: OPENAI_API_KEY（引数で渡すことも可能）
- 再試行・フェイルセーフ: レート制限・接続障害・5xx を指数バックオフでリトライし、最終的に失敗しても例外を上位に伝播させずフォールバック動作を行う箇所が多い設計

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings クラス（自動 .env ロード機能含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

パッケージ
- ai/
  - news_nlp.py             — ニュースセンチメント生成（OpenAI）
  - regime_detector.py      — 市場レジーム判定（MA200 + LLM）
- monitoring/
  - monitoring_db.py        — SQLite スキーマ・永続化 API
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — 注文・約定監視（実装参照）
  - risk_monitor.py         — ドローダウン・ポジション上限の監視
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        — 通知管理（LINE 等、実装参照）
- execution/                 — ExecutionEngine 本体・ブローカーファクトリ等（詳細はコード参照）
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数決定・資金配分ロジック
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py  — 将来リターン / IC / 統計要約
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度・CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- data/ (runtime)
  - *.db, *.pid, stop_requested.flag, kill.flag, etc.

運用上の注意
------------
- 本番（live）では Kill Switch・LINE 通知などの設定を必ず確認してください（validate_config は live の特別チェックを行います）。
- .env は絶対にリポジトリにコミットしないでください。
- Monitoring は sqlite_path（本番用）を参照するため、監視対象の DB パスに注意してください。
- OpenAI API を使う処理は API 利用料が発生します。API キーと使用量に注意してください。
- プロセス優先度や CPU affinity の設定は権限が必要な場合があります（psutil の AccessDenied により失敗することがありますが安全にログ出力されます）。

よく使うコマンド一覧
-------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視エンジン起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパー検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 直接モジュールを利用して研究（例）:
  - Python REPL で duckdb 接続を作成し kabusys.research.calc_momentum 等を呼び出す

最後に
------
この README はコードベースの主要設計と運用手順の概要を示しています。実際の運用・拡張時は各モジュールの docstring / コメント（コード中に詳細な説明があります）を参照してください。質問や改善点があればお知らせください。