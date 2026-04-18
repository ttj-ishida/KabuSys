KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買および関連ツール群（監視 / ポートフォリオ構築 / リサーチ / AI 補助機能 等）をまとめた Python パッケージです。以下はコードベースを参照して作成した README です。

概要
----
KabuSys は以下の機能を備えたモジュール群から構成されます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理・照合を実行  
- 監視（Monitoring）: システム状態、注文滞留、ドローダウン等を定期監視しアラートや Kill Switch を発動  
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群  
- リサーチ: DuckDB を使ったファクター計算（Momentum/Volatility/Value）、特徴量解析、IC 計算等  
- AI 支援: ニュースを LLM（OpenAI）でスコアリングし銘柄やマクロのセンチメントを算出  
- 開発用ツール: .env ウィザード、設定検証、ペーパートレード検証レポートなど

主な機能一覧
--------------
- 環境セットアップ支援: 対話式 .env 作成スクリプト（kabusys.config_setup）
- 設定検証: 環境変数や config/*.yaml の検証（kabusys.validate_config）
- 実行エンジン起動: live / paper_trading に対応。paper_trading 時は MockBroker を使用し DB を分離（kabusys.run_execution）
- 監視ループ: SystemMonitor / TradeMonitor / RiskMonitor を定期実行（kabusys.run_monitoring）
- Kill Switch: 指定閾値到達時に data/kill.flag を書き込み ExecutionEngine を安全停止
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- DuckDB ベースのファクター計算・リサーチ関数群（kabusys.research）
- ニュース NLP（OpenAI）による銘柄/マクロセンチメント評価（kabusys.ai）
- ユーティリティ: プロセス優先度・CPU affinity 設定（psutil を利用）

前提 / 必要パッケージ
--------------------
（実環境に合わせて調整してください）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML（config/*.yaml の構文検証を行いたい場合）
上記を pip でインストールしてください。例:
pip install duckdb psutil openai pyyaml

セットアップ手順（クイックスタート）
----------------------------------
1. リポジトリをクローン／取得
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup
   - J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV（development / paper_trading / live）等を設定
5. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も FAIL 扱いになります
6. 必要に応じて config/*.yaml を準備（scripts/generate_config.py 等を参照）

主要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）、デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（分離用、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

使い方（代表コマンド）
---------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60）
  - 監視は常に（KABUSYS_ENV にかかわらず）本番の sqlite_path を使用します
  - 停止: data/stop_requested.flag を作成する（run_monitoring はこのファイルを検知して終了）

- 実行エンジン起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - 起動前に data/stop_requested.flag が存在する場合は起動しません
  - 停止: data/stop_requested.flag を作成すると実行中のエンジンが停止します
  - 実行エンジンは起動時にプロセス優先度を high に設定しようとします（psutil が必要）

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

- AI / レジーム判定 / スコアリング（プログラムから利用）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OpenAI API キーを api_key 引数または OPENAI_API_KEY 環境変数で渡してください。

停止 / Kill Switch / PID
------------------------
- 停止フラグ: data/stop_requested.flag
  - run_monitoring / run_execution はこのフラグをポーリングして終了または停止します
- Kill Switch: data/kill.flag（Settings.kill_flag_path で変更可）
  - RiskMonitor → KillSwitch の評価により書き込まれます。ExecutionEngine は起動時にこのフラグをクリアするオプションを持ちます（KILL_FLAG_CLEAR_ON_START）
- PID ファイル: data/execution.pid（ExecutionEngine の PID を出力）
  - SystemMonitor は PID ファイルが stale（プロセス不存在）なら削除してアラートを記録します

注意事項 / 動作方針
------------------
- Paper Trading と本番 DB（monitoring）は明確に分離されます（paper_trading 実行時は paper_sqlite_path を使用）。
- 監視（run_monitoring）は監視 DB（sqlite_path）を使います。run_monitoring ドキュメントでは「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明記されています。
- AI 機能は OpenAI に依存します。API 呼び出しはリトライ・バックオフを行い、失敗時はフェイルセーフ（ゼロまたはスキップ）で継続する設計です。
- .env の自動読み込みはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- プロセス優先度 / CPU affinity 設定は psutil に依存し、権限や OS によっては失敗しても警告を出してスキップします。

ディレクトリ構成（主要部分）
----------------------------
src/kabusys/
- __init__.py : パッケージ定義（バージョン等）
- config.py : 環境変数 / Settings 管理、自動 .env ロード機能
- config_setup.py : .env 対話式ウィザード（CLI）
- validate_config.py : 設定検証 CLI
- run_monitoring.py : SystemMonitor ポーリングループ起動スクリプト
- run_execution.py : ExecutionEngine 起動スクリプト

サブパッケージ（主要）
- kabusys/execution/ : 発注エンジン・OrderManager・RiskManager・Reconciler 等（実行ロジック）
- kabusys/monitoring/ :
  - monitoring_db.py : SQLite テーブル初期化・読み書きラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- kabusys/portfolio/ :
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/ :
  - factor_research.py, feature_exploration.py
- kabusys/ai/ :
  - news_nlp.py（ニューススコアリング）, regime_detector.py（市場レジーム判定）
- kabusys/tools/ :
  - paper_verification_report.py
- kabusys/utils/ :
  - process_priority.py（プロセス優先度 / CPU affinity）

設定ファイル / データ
- .env（プロジェクトルート）: 環境変数ファイル（絶対に Git にコミットしない）
- config/*.yaml: 各種設定ファイル（存在しない場合は警告。generate_config.py で生成する想定）
- data/: デフォルトで DuckDB/SQLite/PID/flag を置くディレクトリ

開発時のヒント
----------------
- config_setup で .env を作成後、validate_config で問題がないかを確認してください。
- paper_trading を使うときは KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を確認してください（本番 DB と分離されます）。
- AI 機能をローカルでテストする場合は OPENAI_API_KEY を設定してください。テストでは _call_openai_api をモックして外部依存を切ることができます。
- DuckDB に取り込むデータ（prices_daily / raw_financials / raw_news 等）が整っていることがリサーチ・AI 機能の前提です。

ライセンス / 貢献
-----------------
本ドキュメントはコードベースから抽出した情報に基づく README 例です。実際のライセンスや貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING を参照してください。

最後に
------
不明点や追加したいセクション（例: API リファレンス、コンポーネント図、詳細な運用手順など）があれば教えてください。README を目的（開発者向け / 運用担当者向け / エンドユーザ向け）に合わせてさらに整備できます。