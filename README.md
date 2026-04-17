KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。マーケットデータ集計（DuckDB）、発注実行（kabuステーション 連携／ペーパートレード対応）、監視・アラート、ポートフォリオ構築、ファクター研究、LLM を使ったニュースセンチメント評価などの機能を備えています。設計上は本番とペーパートレード（完全分離）をサポートし、監視・キルスイッチや各種安全弁（ドローダウン監視、ポジション上限、注文滞留検知）を提供します。

主な機能
--------
- 発注エンジン（ExecutionEngine）
  - 本番／ペーパートレード切替（KABUSYS_ENV）
  - Broker クライアント抽象化（MockBroker 対応）
  - 注文管理、リスク管理、リコンサイラー等の組み込み
- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視ログ（monitoring.db）
  - Kill Switch（条件により data/kill.flag を作成して Execution を停止）
  - LINE によるアラート送信機能（AlertManager）
- ポートフォリオ構築
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ（DuckDB）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC、統計サマリー等
- AI（OpenAI）
  - ニュースを LLM で評価して銘柄ごとの ai_score を生成（ai/news_nlp.py）
  - マクロと ETF を組み合わせた市場レジーム判定（ai/regime_detector.py）
- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report）

動作要件（推奨）
----------------
- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（config YAML のパース検証時に必要）
- SQLite（標準ライブラリで利用）
- kabuステーション API（本番実行時／テスト用にモックを用意）

導入（インストール）
--------------------
1. リポジトリをクローン／配置し、作業ディレクトリをプロジェクトルートにする。
2. Python 仮想環境を作成・有効化する（推奨）。
3. 必要パッケージをインストールする（requirements.txt がない場合は下記を例示）:
   - pip install duckdb psutil openai requests pyyaml
4. DuckDB / SQLite のデフォルト DB ファイルは data/ 以下に作成されます。手動でディレクトリを作成しておいても良いです。

設定（.env）
-----------
環境変数で設定を行います。対話式ウィザードを使うと .env を生成できます。

- 対話ウィザード:
  - python -m kabusys.config_setup
- 生成された .env を読み込んで実行できます（自動ロード機能あり。不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

最低限必要な環境変数（validate_config の REQUIRED）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他の主要な環境変数（代表）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading 時に使用、デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用（任意）

設定検証
-------
起動前に設定を検証できます:
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いになります（exit code 1）。

実行方法
--------
1. 実行エンジン（ExecutionEngine）
   - 本番／ペーペートレードを含む発注エンジンを起動します。
   - モジュール実行:
     - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と完全に分離されます。
     - 起動時に data/stop_requested.flag が存在すると起動しません。
     - 実行中は data/execution.pid に PID が書き込まれます（SystemMonitor が参照）。

2. 監視ループ（Monitoring）
   - システム指標・注文状況・リスク指標を定期チェックします。
   - モジュール実行:
     - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可能。
   - 監視は常に本番の sqlite_path を参照します（監視データは環境に依存せず一箇所に集約される設計）。

3. ペーパートレード検証レポート
   - 過去期間のパフォーマンス・安定性指標を出力します。
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

停止・キルスイッチ
------------------
- Kill Switch: risk_monitor 等の評価結果に応じて KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動停止や CI 等で外部から停止を指示する場合には data/stop_requested.flag を作成すると、監視ループと実行エンジンの起動ループが検知して終了します。
- 実行エンジンは data/execution.pid に PID を書き込みます。SystemMonitor はこの PID を参照してプロセス死活を判定します。

デフォルトのデータパス
--------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
（.env で上書き可能）

OpenAI の利用
--------------
- ニュース NLP（ai/news_nlp.py）やレジーム判定（ai/regime_detector.py）は OPENAI_API_KEY を参照します。API キーを設定してください。
- LLM 呼び出しは再試行・バックオフや入力トリミング、レスポンス検証を組み込んでいます。API 費用やレート制限に注意してください。

注意点 / 運用メモ
-----------------
- KABUSYS_ENV=live の場合は本番口座で実際に発注されます。必須設定や LINE 通知の有無などを入念に確認してください（validate_config に live 時の追加チェックあり）。
- process 優先度を上げる処理を行います（psutil を使用）。権限が不足すると警告が出ますが処理は続行します。
- DuckDB のクエリや AI 呼び出しはルックアヘッドバイアス回避のため日付フィルタ等に注意して設計されています。
- .env を絶対に Git にコミットしないでください（config_setup で明示）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / .env 自動ロード / Settings
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/ai/
- news_nlp.py — ニュースの LLM スコアリング
- regime_detector.py — レジーム判定

src/kabusys/monitoring/
- monitoring_db.py — SQLite テーブル初期化と永続化 API
- system_monitor.py — システム・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション数監視
- monitoring_engine.py — 各 Monitor を束ねてポーリング
- kill_switch.py — Kill Switch（flag 書き込み）
- alert_manager.py — LINE Push 通知

src/kabusys/execution/  (発注関連の実装群)
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ... （発注ロジックはここに含まれます）

src/kabusys/research/
- factor_research.py, feature_exploration.py, ... （DuckDB を使った研究用関数）

src/kabusys/portfolio/
- portfolio_builder.py, position_sizing.py, risk_adjustment.py

src/kabusys/utils/
- process_priority.py — プロセス優先度・CPU affinity ヘルパ

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

よく使うコマンドまとめ
--------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（このリポジトリにライセンスファイルがあればそこを参照してください。運用ルールやコントリビューション方針はプロジェクト固有に設定してください。）

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。実運用前に必ず validate_config を実行し、.env とデータベースのバックアップ／テスト環境での検証を行ってください。質問やドキュメント追加の要望があればお知らせください。