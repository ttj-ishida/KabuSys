README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を統合した小規模なシステムです。
主な機能は以下の通りです:

- 注文実行エンジン（ExecutionEngine） — ブローカークライアント経由で発注を行う（本番／ペーパートレード切替対応）
- 監視（Monitoring） — システム稼働状況・データ鮮度・注文異常・リスク監視と Kill Switch
- ポートフォリオ構築ユーティリティ — 候補選定、重み付け、ポジションサイズ計算、セクター制約など
- リサーチ（Research） — ファクター計算、将来リターン/IC 計算、統計サマリ
- AI 支援（AI） — ニュースを LLM でスコアリング（OpenAI）して銘柄・市場レジーム判定に利用
- ツール群 — ペーパートレード検証レポート生成など
- 設定管理 CLI — .env の対話式生成（config_setup）と設定検証（validate_config）

特徴
----
- 環境に応じた振る舞い:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB に記録（本番 DB と完全分離）
  - KABUSYS_ENV=live で本番モード（各種注意/警告あり）
- .env 自動読み込み（プロジェクトルートの .env / .env.local。必要に応じて無効化可）
- DuckDB を分析用 DB、SQLite を監視・トレードログ用に使用
- OpenAI（gpt-4o-mini 想定）との連携機能（ニュースセンチメント、マクロセンチメント）
- フェイルセーフ設計：LLM 呼び出し失敗時はフォールバックして継続、部分失敗で既存データを保護する仕組みあり

前提条件 / 必要なソフトウェア
-----------------------
- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML のパースを行いたい場合）
  - そのほか実際の execution ブローカー実装に応じた依存

一般的なインストール例:
  python -m pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン / 展開し、プロジェクトルートへ移動する

2. Python 環境を準備し、必要なパッケージをインストールする

3. .env の作成
   - 対話式ウィザードで .env を生成:
     python -m kabusys.config_setup
   - あるいは `.env.example` を参考に手動で作成
   - 自動ロード: Settings モジュールはプロジェクトルートを探して .env/.env.local を自動読み込みします。
     自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

5. DB の準備
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 使用）
   - 必要に応じて環境変数でパスを上書きできます（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）

主要な環境変数
----------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution のモード (development | paper_trading | live)（デフォルト: development）
- PAPER_FILL_MODE: ペーパートレードの注文約定モード (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite ファイルパス
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（コマンド／エントリポイント）
-------------------------------
- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します
  - 起動前に data/stop_requested.flag が存在すると起動しません（停止済扱い）
  - 実行中に data/stop_requested.flag を作成すると Engine を停止させる仕組みがあります

- 監視ループ起動（Monitoring のポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します
  - run_monitoring と run_execution は project/data/stop_requested.flag を検出して終了します

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで SQLite パスを指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

注意事項 / 停止制御
------------------
- 停止用フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring が検出して安全に終了するためのフラグ
  - data/kill.flag: KillSwitch が書き込むフラグで ExecutionEngine に停止シグナルを送る（ExecutionEngine 側でチェックされる想定）
- KILL_FLAG_CLEAR_ON_START が 1 のときは Execution 起動時に kill.flag を自動クリアします（本番では 0 推奨）

主要コンポーネントの説明（抜粋）
--------------------------------
- config.py
  - Settings クラスで環境変数をラップ。自動で .env / .env.local を読み込み。
  - 各種設定プロパティ（DB パス、環境判定、しきい値など）を提供。

- run_execution.py
  - ExecutionEngine の起動スクリプト。環境によりブローカークライアントを生成（実ブローカー or Mock）。
  - Paper trading は専用の paper_sqlite_path に記録。

- run_monitoring.py
  - SystemMonitor をポーリングして system_status 等を記録するシンプルなループ。
  - MONITOR_POLL_INTERVAL で間隔を指定可能。

- monitoring/*
  - monitoring_db.py: SQLite 用の永続化層（シンプルな CRUD / マイグレーション含む）
  - system_monitor.py: プロセス生存確認、CPU/メモリ/ディスク監視、データ鮮度チェック
  - trade_monitor.py: 注文滞留/約定異常の検出
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: 条件に応じて kill.flag を書き込み Execution を停止させる
  - monitoring_engine.py: 上記 Monitor をまとめて定期実行しアラート発行

- portfolio/*
  - portfolio_builder.py: 候補選定と基本的な重み付け関数（等配分／スコア配分）
  - position_sizing.py: 各銘柄の買付株数決定（リスクベースや等配分/スコアベース）、単元株丸め、aggregate cap 調整
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/*
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ等

- ai/*
  - news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.py: ETF（1321）MA とマクロニュースを LLM で評価して market_regime に書き込む
  - 両者とも API キーは OPENAI_API_KEY または引数で指定

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境設定 / .env ロード
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリングスクリプト

packages / サブモジュール:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (アラート送信管理)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

開発・運用上のヒント
-------------------
- Python バージョンは 3.10 以上を推奨（型注釈で | を使用しているため）
- OpenAI を使う機能はネットワークと API キーが必須。LLM 呼び出しは失敗耐性（リトライ・フォールバック）を組み込んでありますが、API キーは必ず設定してください
- local テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを抑止すると再現性が高くなります
- 本番運用では KABUSYS_ENV=live のときに LINE 通知や kill フラグの扱いを慎重に設定してください（validate_config で注意喚起を行います）
- run_execution/run_monitoring のプロセス優先度は起動時に set_process_priority("high") が呼ばれます。権限がないと警告でスキップされます

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（初期バージョン）。ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

問い合わせ / 開発方法
--------------------
- 新しい機能追加やバグ修正はコードを読み、各モジュールの docstring と既存テストを参照して実装してください。
- LLM 呼び出し部分は外部 API に依存するため、ユニットテストではモック化（unittest.mock.patch）してテストすることを推奨します。

以上。README の補足や特定のセクションの拡張を希望する場合は知らせてください。