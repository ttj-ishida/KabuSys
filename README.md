KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を含む小規模なシステム群です。本リポジトリには下記の主要機能を持つモジュールが含まれます。

- 注文作成・管理・実行（ExecutionEngine / OrderManager / Reconciler 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI を用いたニュースセンチメント（OpenAI）およびレジーム判定
- Paper Trading 用検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

主な特徴
--------
- モジュール化された純粋関数群（portfolio, research など）は副作用を持たずテストしやすい設計
- SQLite（監視 / paper_trading 用） + DuckDB（時系列価格など分析用）を併用
- 環境変数 / .env による設定管理（自動読み込み。無効化可能）
- Execution と Monitoring は独立してプロセス起動でき、監視から Execution を強制停止する kill.flag 機構あり
- OpenAI を利用したニュースセンチメント / マクロ判定を実装（API リトライ・検証ロジックあり）
- Streamlit ダッシュボードで状態を可視化

前提・依存
----------
推奨 Python バージョン: 3.10 以上（Union 型 | を使用）

主な依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例:
- requirements.txt がない場合:
  pip install duckdb psutil requests openai streamlit

セットアップ手順
--------------
1. リポジトリをクローン / 展開
2. Python 仮想環境作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール:
   pip install duckdb psutil requests openai streamlit
4. 環境変数を設定（.env または直接 export）。自動ロードされる .env はプロジェクトルートに配置します。
   - 必須（実運用時）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - オプション / 重要な設定:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading 時に使用）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

※ 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

起動・使い方
------------

1) 監視プロセスの起動
- デフォルトのポーリング間隔（秒）は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
- 実行:
  python -m kabusys.run_monitoring
- 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用して monitoring DB を初期化します。
- 停止: プロジェクトルート/data/stop_requested.flag を作成するか Ctrl+C。

2) 実行（ExecutionEngine）の起動
- Paper trading（モックブローカー＋別DB）で起動する例:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 本番（live）環境では本番 DB を使用します。
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
- 実行中に停止するには stop flag を作成（data/stop_requested.flag）するとエンジンが検知して停止します。
- 実行プロセスは data/execution.pid を PID ファイルとして扱います（SystemMonitor が死活監視で使用）。

3) Paper Trading 検証レポート
- SQLite（paper_trading DB）から検証レポートを生成します。
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH より優先されます。

4) Streamlit ダッシュボード（監視可視化）
- 起動例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開いてダッシュボードを表示します。

5) AI 機能
- ニュース NLP（銘柄ごとの ai_score 計算）:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY を環境変数に設定するか api_key 引数で渡します。
- レジーム判定（市場レジーム）:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: OpenAI 呼び出しはリトライやレスポンス検証を行いますが、API キーや課金に注意してください。

監視／停止関連ファイル
--------------------
- data/stop_requested.flag: run_*.py がポーリングループ内でチェックする停止フラグ。
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に停止シグナルを送る用途。
- data/execution.pid (デフォルト): ExecutionEngine の PID ファイル（SystemMonitor がプロセス生存をチェック）。

設定の読み込み挙動
-----------------
- .env / .env.local をプロジェクトルートから自動的に読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env のパースはシェル風（export 付き、クォート、コメント対応）です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数/設定管理（Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマ初期化・永続化 API（MonitoringDB）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — 注文滞留・約定価格異常監視
- risk_monitor.py — ドローダウン・ポジション上限判定
- kill_switch.py — kill.flag 管理・評価ロジック
- alert_manager.py — LINE push による通知（クールダウン管理）
- monitoring_engine.py — 各モニタを束ねるループ / run_once
- streamlit_dashboard.py — Streamlit UI（監視表示）

src/kabusys/execution/
- order_manager.py — 発注フロー・ステート管理
- reconciler.py — 起動時の再同期 / ポジション突合（Reconciler）
- その他: broker_factory, execution_engine, order_repository 等（発注関連実装）

src/kabusys/portfolio/
- portfolio_builder.py — シグナル選定 / スコア並び替え
- position_sizing.py — 株数計算・資金配分ロジック
- risk_adjustment.py — セクターキャップ / レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン計算・IC など

src/kabusys/ai/
- news_nlp.py — ニュースを OpenAI で評価して ai_scores に書き込む
- regime_detector.py — ETF MA + マクロセンチメントでレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ（psutil 使用）

データディレクトリ（ランタイム）
- data/monitoring.db (デフォルト) — 監視ログ（SQLite）
- data/paper_trading.db — paper_trading 用 DB（設定でカスタマイズ可）
- data/kabusys.duckdb — DuckDB ファイル（価格データ等）

注意事項 / 運用上のポイント
--------------------------
- Settings クラスは起動時に環境変数を検証します。無効な値があると例外で起動が止まります。
- Paper Trading 環境は本番 DB と完全に分離するため KABUSYS_ENV=paper_trading を利用してください。
- OpenAI を使う機能は API キーが必須です。呼び出し回数・課金に注意してください。
- SystemMonitor は実行プロセスの PID ファイルを参照して稼働可否を判定します。pid ファイルの整合性に注意してください。
- monitoring_db.init_monitoring_db は冪等で、既存 DB に対するマイグレーション（カラム追加）も実施しますが、重要データはバックアップ推奨です。

開発・テスト
-------------
- 各モジュールは外部副作用を最小化する設計になっています。ユニットテストは isolated に書きやすいです（OpenAI 呼び出しはモック推奨）。
- news_nlp / regime_detector の API 呼び出し部分はテスト時に差し替え可能な設計になっています（関数を patch する等）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在: 0.1.0）。
- ライセンス情報はリポジトリルートに LICENSE ファイルがあればそちらを参照してください（本 README には含めていません）。

問い合わせ
----------
実装や各モジュールの仕様に関する質問があれば、具体的なファイル名・関数名・期待する挙動を添えて問い合わせてください。

--- 
以上が本コードベースの概要と運用ガイドです。必要であればセットアップ手順の詳細スクリプト化（requirements.txt / docker-compose 等）や、よく使う運用コマンド集（systemd ユニット例、log ローテーション）を追加で作成します。どの情報が欲しいか教えてください。