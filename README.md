README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なフレームワークです。本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: 実際の/ペーパートレード発注を行う。kabuステーション／MockBroker を切替可能。
- Monitoring（監視）: システム稼働性、データ鮮度、注文状態、リスクを定期チェックしてログ・アラート・Kill Switch を制御。
- Portfolio 構築: 候補選定、重み算出、ロット丸め、セクター制約、ポジションサイズ計算などの純粋関数群。
- Research（研究）: DuckDB 上の株価・財務データを用いたファクター計算・特徴量解析。
- AI モジュール: ニュース NLP による銘柄毎センチメント評価（OpenAI）や市場レジーム判定。
- ユーティリティ: ロギング設定、プロセス優先度制御、.env 対話式ウィザード、設定検証、各種ツール（Paper Trading レポート生成など）。

主な特徴
--------
- 環境切替対応（development / paper_trading / live）
  - paper_trading では MockBroker を使用し、paper_trading 用の SQLite DB に完全分離して記録。
- DuckDB を使った高速な研究用クエリ実行（prices_daily / raw_financials 等を前提）
- OpenAI を使ったニュースセンチメント生成（batch / retry / JSON バリデーション付き）
- 監視用 SQLite（monitoring.db）に各種ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- 実行スクリプトはモジュールとして提供（python -m kabusys.run_execution 等）
- .env 対話式ウィザード（config_setup）／設定検証 CLI（validate_config）が同梱

セットアップ手順
----------------
1. Python 仮想環境を作成・有効化
   - 例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - requirements.txt がない場合は最低限以下をインストールしてください:
     pip install duckdb psutil openai
   - YAML 検証を行いたい場合:
     pip install PyYAML

3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考にすること）

4. 設定の検証
   - python -m kabusys.validate_config
   - 本番前の厳格チェック:
     python -m kabusys.validate_config --strict

必須／重要な環境変数（主要）
--------------------------------
（validate_config でチェックされる主な変数）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨／任意:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 用）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - OPENAI_API_KEY: AI 機能を使う場合に必須
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番通知（任意）
  - PAPER_FILL_MODE: ペーパートレード時のフィルモード（instant|partial|never|reject）

起動・使い方
------------

.env 作成・検証
- 対話式ウィザードで .env を作成:
  python -m kabusys.config_setup
- 作成後に必ず検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  （警告もエラー扱い）

ExecutionEngine（発注エンジン）起動
- 実行コマンド:
  python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV により本番/ペーパーを切替。
  - ペーパートレード時は settings.paper_sqlite_path に記録し、本番 DB と分離。
  - 起動時に data/stop_requested.flag が存在すると起動を中止。
  - 実行中は data/execution.pid に PID を書き込む（設定により変更可）。
  - 停止は data/stop_requested.flag を作成することで実現（Monitoring の KillSwitch 等から書き込まれる）。

Monitoring（監視）起動
- 実行コマンド:
  python -m kabusys.run_monitoring
- 挙動:
  - 定期ポーリングで SystemMonitor / TradeMonitor / RiskMonitor を実行し、必要に応じて Kill Switch を書き込む。
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録します（監視は常に本番 DB を見る設計）。

Paper Trading 検証レポート
- コマンド:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可能）
- 出力: 稼働率、注文成功率、送信率、レイテンシ等の集計と PASS/FAIL 判定

AI 機能
- ニュースセンチメント付与:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: OpenAI API キーとネットワーク接続が必要。API の失敗はフェイルセーフ（多くのケースで 0.0 等にフォールバック）で処理します。

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- setup_logging を各起動スクリプトが呼び出します（例: app_name="execution" / "monitoring"）。
- 標準出力にもログを出すため、コンテナ/cron 等でも追いやすい設計です。

停止方法
-------
- 即時停止 (監視/実行): data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
- Kill Switch（リスクトリガー）: 監視が判定すると data/kill.flag を作成して ExecutionEngine に停止を促します。KillSwitch が既に存在する場合は上書きしません。Execution 起動時に KILL_FLAG_CLEAR_ON_START を 1 にしていると自動で消される点に注意（本番では 0 推奨）。

ディレクトリ構成（主要）
---------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）処理
  - regime_detector.py      — 市場レジーム判定
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数計算・スケールダウン処理
  - risk_adjustment.py      — セクター上限・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum / value / volatility）
  - feature_exploration.py  — 将来リターン・IC・統計解析
- monitoring/
  - monitoring_db.py        — SQLite 監視 DB のスキーマ & ラッパー
  - monitoring_engine.py    — 複数 Monitor を束ねるランナー
  - system_monitor.py       — システム・データ鮮度監視
  - risk_monitor.py         — ドローダウン・ポジション監視
  - trade_monitor.py        — （注文関連監視, ファイル内にあり）
  - kill_switch.py          — kill.flag の作成・評価
  - alert_manager.py        — （アラート送信管理）
- execution/
  - execution_engine.py     — 実行エンジン本体
  - order_manager.py, ...   — 発注・リポジトリ・リスク管理等（個別ファイル）
- data/
  - pipeline.py (参照するモジュール) — データ取得/更新ユーティリティ 等
- utils/
  - logging_setup.py        — 統一ログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py — Paper Trading レポート生成

備考 / 運用上の注意
-------------------
- 本プロジェクトは実際の発注処理を伴うため、本番（KABUSYS_ENV=live）では設定を慎重に検証してください。validate_config によるチェックを必ず通してください。
- .env は決してバージョン管理にコミットしないでください（config_setup も同注意書きを付与しています）。
- OpenAI を利用する機能はトークン消費が発生します。API 呼び出し量に注意してください。
- Monitoring は監視用 DB を用いて本番プロセスを観察します。monitoring は本番監視用に sqlite_path（デフォルト data/monitoring.db）を参照します。
- PaperTrading 用データベースは paper_trading 環境専用に分離されています（settings.paper_sqlite_path）。

開発者向け
----------
- ユニットテスト／モック:
  - AI 呼び出し部は _call_openai_api をパッチすることでテスト可能（news_nlp / regime_detector 内で明示的に設計）。
- コード設計:
  - 研究・ポートフォリオ計算関数は純粋関数（副作用なし）を目標としており、DuckDB 接続を必要とする関数は引数で受け取ります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルとカラムを作成・追加する（簡易的なマイグレーションを含む）。

問い合わせ・貢献
----------------
- バグ報告・機能提案は Issue に記載してください。
- 変更の提案は PR（ユニットテスト・簡単な説明付き）が望ましいです。

以上。必要であれば README にサンプル .env、簡単なデプロイ手順（systemd ユニット例や Dockerfile）を追記できます。どの情報を追加しますか？