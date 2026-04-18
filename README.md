KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコードベースです。
ライブラリ／実行スクリプト／運用ツール群を含み、以下の主要機能を提供します。

- 実口座／ペーパートレード（完全分離）対応の ExecutionEngine
- システム監視（CPU/メモリ/ディスク／データ鮮度）とリスク監視（ドローダウン・ポジション数）
- Kill Switch（条件を満たしたら Execution を停止するフラグ）
- ポートフォリオ構築、ポジションサイジング、セクター制限ロジック（純粋関数群）
- 研究用モジュール（ファクター計算・IC 計算・特徴量解析）
- ニュースの NLP スコアリング（OpenAI を利用）・市場レジーム判定
- ペーパートレード検証レポート生成ツール
- 起動時のログ設定・プロセス優先度ユーティリティ等の共通ユーティリティ

主要な機能
---------

- 実行・監視スクリプト
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db を使用（本番 DB と分離）。
  - run_monitoring: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を上書き可能。監視は常に本番 sqlite_path（デフォルト data/monitoring.db）を使用。

- 設定管理
  - config_setup: 対話式ウィザードで .env を作成/更新
  - validate_config: .env や config/*.yaml の事前検証（--strict で警告も fail 扱い）

- 監視（monitoring）
  - MonitoringDB: SQLite に監視ログを永続化（system_status/trade_logs/positions/risk_logs/dashboard 等）
  - SystemMonitor / TradeMonitor / RiskMonitor: 各種チェックを実行して DB に記録
  - KillSwitch: 条件を満たすと data/kill.flag を作成して Execution を止める
  - MonitoringEngine: 各 Monitor を束ねたポーリング実行とアラート送信（AlertManager 経由）

- ポートフォリオ（portfolio）
  - 銘柄選定、等重・スコア重み、セクター上限、レジーム乗数、ポジションサイズ決定（単元株丸め・資金スケール処理）

- リサーチ（research）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン・IC（スピアマン）・統計サマリー等

- AI モジュール（ai）
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に格納
  - regime_detector: ETF（1321）MA200 とマクロニュースを組合せて日次の market_regime を判定・永続化

セットアップ手順
---------------

前提
- Python 3.9+（ソースは型アノテーションで新しめの機能を利用）
- SQLite / DuckDB の利用（ローカルファイルに書き込み）
- OpenAI API を利用する機能は OPENAI_API_KEY が必要
- 実口座連携には Kabu ステーションや J-Quants のトークン等が必要

推奨インストール例（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 追加で検証や YAML ファイル検証が必要なら: pip install pyyaml

（注）requirements.txt は本リポジトリに含まれていないため、必要に応じて適宜パッケージを追加してください。

環境変数と .env
- 初期設定は対話式ウィザードで用意できます:
  - python -m kabusys.config_setup
- 自動ロード:
  - プロジェクトルートにある .env / .env.local は自動で読み込まれます（OS 環境変数が優先）
  - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 重要な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - OPENAI_API_KEY: OpenAI アクセスキー（ai 機能で使用）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
  - LOG_LEVEL（デフォルト INFO）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする: 0/1。production は 0 推奨）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数、デフォルト 60）

設定検証
- .env と config/*.yaml の検証:
  - python -m kabusys.validate_config
  - 警告も失敗と見なす場合: python -m kabusys.validate_config --strict

使い方（実行例）
----------------

1. ExecutionEngine を起動
- 本番/ペーパーの切替は KABUSYS_ENV で制御
  - 本番例（環境変数設定後）:
    - python -m kabusys.run_execution
  - ペーパートレード（例: .env に KABUSYS_ENV=paper_trading）:
    - python -m kabusys.run_execution
  - 実行時は data/execution.pid が作成され、停止信号は data/stop_requested.flag / data/kill.flag 等を利用します。

2. Monitoring を起動
- python -m kabusys.run_monitoring
- ポーリング間隔を上書きする場合:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3. 停止・Kill Switch
- KillSwitch は data/kill.flag を作成して ExecutionEngine 停止を要求します（自動的に作成されることがある）。
- 手動で監視ループ停止フラグを立てる（運用上の止め方）:
  - touch data/stop_requested.flag  （監視ループや engine 起動スレッドはこのファイルを検知して終了します）
- 実行開始時に Kill Flag を自動的にクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では推奨しません）。

4. ペーパートレード検証レポート
- DB を指定してレポートを生成:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
- デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

5. AI / リサーチ機能の利用（プログラムから）
- ニュースセンチメントやレジーム判定はライブラリ関数として利用:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
- DuckDB 接続オブジェクト（duckdb.connect(...)）を渡して実行します。

運用上の注意
------------

- run_monitoring は監視用 DB（SQLITE_PATH）を使用します。Monitoring は常に本番 sqlite_path を使う設計のため、環境に依らず同一監視 DB に記録されます。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ書き込みし、本番 DB とは分離されます。
- ログは logs/<app_name>.log に日次ローテーションで出力されます（utils.logging_setup）。
- process_priority.set_process_priority により起動時に優先度を high に設定します（権限により失敗する場合があります）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup も同様に警告して書き出します）。

ディレクトリ構成（主要ファイル）
-------------------------------

リポジトリの主要なソース構成（src 以下）:

- src/kabusys/__init__.py
- src/kabusys/config.py               — 環境変数 / Settings クラス、自動 .env ロード
- src/kabusys/config_setup.py         — .env 対話式ウィザード
- src/kabusys/validate_config.py      — 設定検証 CLI

- src/kabusys/run_execution.py        — ExecutionEngine 起動スクリプト
- src/kabusys/run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

- src/kabusys/utils/
  - logging_setup.py                  — ログ設定ユーティリティ
  - process_priority.py               — プロセス優先度 / CPU affinity 設定

- src/kabusys/monitoring/
  - monitoring_db.py                  — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py                 — システム状態・データ鮮度チェック
  - trade_monitor.py                  — 注文系監視（存在）
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - kill_switch.py                    — Kill Switch（flag ファイル管理）
  - monitoring_engine.py              — Monitor の統合制御

- src/kabusys/execution/                 — Execution 関連コンポーネント（Engine, OrderManager, BrokerFactory 等）
- src/kabusys/portfolio/                 — portfolio_builder, position_sizing, risk_adjustment（純粋関数群）
- src/kabusys/research/                  — factor_research, feature_exploration（DuckDB ベース）
- src/kabusys/ai/
  - news_nlp.py                        — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py                 — レジーム判定（MA200 + マクロセンチメント）
- src/kabusys/tools/
  - paper_verification_report.py       — ペーパートレード検証レポート生成

- config/
  - system_config.yaml, data_config.yaml, ... （テンプレート/生成スクリプトで作成）
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kill.flag / stop_requested.flag / execution.pid
- logs/
  - execution.log, monitoring.log, ...（デフォルト出力先）

補足メモ
--------

- DuckDB は分析用（prices_daily / raw_financials / raw_news 等のクエリ）に使います。DB スキーマやデータの投入は別途用意してください。
- OpenAI を利用する機能は APIキーと利用量が必要です。利用時は API の料金とレート制限に注意してください。
- config/*.yaml の実体は存在しない場合があります。validate_config は PyYAML がある場合に内容検証を行います。
- テストや CI で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

問題や改善提案
--------------

不具合・改善提案・ドキュメント追記のプルリクエスト歓迎です。リポジトリ内の各モジュールに詳細な docstring と注意書きが付いていますので、実装の理解や拡張の際はソースを参照してください。