README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定したライブラリ群です。
本リポジトリには以下の主要機能を含みます：

- 発注実行エンジン（ExecutionEngine）起動スクリプト
- 監視プロセス（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数計算）
- リサーチ（ファクター計算、特徴量解析）
- AI を用いたニュースセンチメント評価 / レジーム判定
- Paper Trading 向け検証レポート生成ツール
- .env 対話式セットアップ・設定検証ツール

主な機能
-------
- 実行環境切替（KABUSYS_ENV: development / paper_trading / live）
  - paper_trading では MockBroker を使用し、本番 DB と分離された paper_trading DB に記録
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送出の仕組み
- Kill Switch（data/kill.flag）による外部からの緊急停止
- DuckDB を使った研究用ファクター計算（prices_daily / raw_financials 参照）
- OpenAI を利用したニュース NLP（gpt-4o-mini を想定、JSON mode で結果取得）
- Paper Trading 検証レポート（稼働率・約定率・レイテンシ等の評価）

前提条件（依存ライブラリ）
-------------------------
主に以下のパッケージが必要になります（プロジェクトに requirements.txt がある場合はそちらを参照してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合、任意）

例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. リポジトリをクローン
    git clone <repo-url>
    cd <repo-root>

2. 仮想環境作成・依存インストール（上記参照）

3. .env 作成（対話式ウィザード推奨）
   対話式ウィザードで .env を作成・更新できます:
       python -m kabusys.config_setup
   ウィザードはプロジェクトルートの .env を作成します。重要項目（必須）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
   - LOG_LEVEL (DEBUG/INFO/...)
   .env は絶対に Git にコミットしないでください。

4. 設定検証
   .env や config/*.yaml の整合性をチェックできます:
       python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
       python -m kabusys.validate_config --strict

使い方（起動・ツール）
---------------------

一般的なコマンド（パッケージをプロジェクトルート内で実行する想定）:

- ExecutionEngine 起動（発注エンジン）
    python -m kabusys.run_execution

  ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、書き込み先は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）になります。
  - 実行中は data/execution.pid に PID を書く/参照します。
  - 停止フラグ data/stop_requested.flag が存在すると Engine の起動を抑止 / 停止するロジックがあります。

- Monitoring（監視）起動
    python -m kabusys.run_monitoring

  ポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は Settings.sqlite_path（data/monitoring.db のデフォルト）を使用してログを永続化します（監視は env に依存せず本番 sqlite_path を使用）。
  - 停止フラグ（data/stop_requested.flag）や kill.flag による制御あり。

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または DB パスを明示する:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI (ニューススコア / レジーム判定)
  - ニューススコアリング: kabusys.ai.score_news（プログラムから呼ぶ API）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  どちらも OpenAI API キー（環境変数 OPENAI_API_KEY）を必要とします。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB。デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- OPENAI_API_KEY (AI 機能を使う場合)
- PAPER_FILL_MODE (paper_trading のモック約定挙動: instant | partial | never | reject)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔（秒）。run_monitoring で利用。デフォルト 60)
- PID_FILE_PATH / KILL_FLAG_PATH (デフォルトは data/ 内のパス)
- KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に kill.flag を自動クリア（本番は 0 推奨）

運用上のポイント
----------------
- Kill Switch
  - Kill Switch は data/kill.flag を書くことで ExecutionEngine に停止を指示します。KillSwitch クラスが評価・書き込みします。
  - KILL_FLAG_CLEAR_ON_START を 1 に設定すると、Engine 起動時に kill.flag を自動的に削除します（本番では 0 推奨）。

- stop_requested.flag
  - data/stop_requested.flag が存在すると run_execution/run_monitoring は起動を抑止したり実行中に停止します。手動でのメンテナンス停止に使用できます。

- PID / ログ
  - 実行スクリプトは logs/<app_name>.log に日次ローテーションでログを出力します（logs ディレクトリを作成しておくか、setup_logging が自動作成します）。
  - PID ファイルは data/execution.pid（デフォルト）に出力されます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブル作成・簡易マイグレーション（カラム追加）を行います。初回起動時にテーブルが自動作成されます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings 管理（自動 .env ロード機能あり）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングするロジック
  - regime_detector.py — マクロ + MA200 による市場レジーム判定
- monitoring/
  - monitoring_db.py — 監視用 SQLite への永続化レイヤ
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 監視コンポーネント
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py, alert_manager.py（アラート管理）
- execution/ — ExecutionEngine 周り（broker_factory, order_manager, 等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（lot 単位丸め、aggregate cap）
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB 使用）
  - feature_exploration.py — IC / 将来リターン / 統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py — ロギング設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発メモ / 注意点
----------------
- .env 自動ロードは Settings モジュール実行時にプロジェクトルートを検出できれば .env/.env.local を読み込みます。テスト時などで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 機能は外部 API（OpenAI）に依存します。API エラー時は多くの場合フォールバック動作（ゼロスコアやスキップ）するように設計されていますが、API キーの設定は必須です（呼び出し側で例外を受け取る設計の箇所もあります）。
- Paper Trading モードは本番 DB と分離する設計です。環境変数を正しく設定してから起動してください。
- ログ・DB などのパスはデフォルトで data/ や logs/ を使用します。運用環境では永続ストレージのパスへ変更してください。

お問い合わせ / 貢献
------------------
バグ報告・機能要望は issue を作成してください。プルリクエスト歓迎です。

以上。README の内容は実装済みのモジュール群に基づく概要・起動手順のまとめです。追加で「設定例の .env のテンプレート」や「システム図」「起動スクリプトの systemd 例」などが必要であれば作成します。