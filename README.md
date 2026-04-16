KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買システム「KabuSys」の実装（モジュール群）です。  
README ではプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントで構成される自動売買基盤です。

- ExecutionEngine: シグナルに基づく発注・注文管理・リスク管理を行うエンジン（本番／ペーパートレード対応）。
- Monitoring: システム状態・注文滞留・リスク（ドローダウン・保有数上限など）を定期監視し、ログ化・アラート送信・Kill Switch による停止トリガーを提供。
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群。
- Research / AI: ファクター計算・特徴量探索、ニュース NLP によるセンチメントスコア／レジーム判定（OpenAI を利用するモジュール含む）。
- ツール: Paper Trading の検証レポート生成、Streamlit ダッシュボード等。

主な設計方針:
- DuckDB をデータ分析用 DB として使用（prices_daily / raw_financials 等）。
- SQLite を監視ログ・注文履歴に利用（本番 DB とペーパートレード DB は分離）。
- 環境依存設定は環境変数（および .env/.env.local）で管理。
- LLM 呼び出しはフェイルセーフ（失敗時はゼロやスキップ）で設計。

主な機能一覧
------------
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（実ブローカー／モックを環境で切替）
  - OrderManager / OrderRepository / Reconciler による注文管理・再同期
  - RiskManager による発注前チェック（レートリミット、利用率、ドローダウン等）

- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 各 Monitor をまとめてポーリング、KillSwitch 判定、AlertManager 経由で LINE 通知
  - streamlit_dashboard: 監視データを可視化する簡易ダッシュボード

- ポートフォリオ構築
  - 候補選定（スコア順）、等分配/スコア加重、リスクベース配分
  - セクターキャップ適用、レジーム乗数、単元株丸め、aggregate cap のスケーリング

- 研究・AI
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）評価
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント集計・ai_scores 書込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - AI スコア & レジームスコア関数（プログラムから呼び出し可能）

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型注釈等で modern な構文を使用）
- システムに DuckDB、psutil、requests、openai、streamlit 等の依存パッケージをインストール

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - ここに requirements.txt は含まれていませんが、最低限以下を入れてください:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数の準備
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須（実行時に使用される）環境変数例:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
   - 設定例（.env）:
     - KABUSYS_ENV=development
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant
     - MONITOR_POLL_INTERVAL=60

4. 初期データディレクトリ
   - data/ 以下に DB を置く想定です。monitoring モジュールは起動時にテーブル作成（冪等）を行います。
   - 実行前に data/ ディレクトリ作成を推奨: mkdir -p data

使い方（主要コマンド）
--------------------

- 監視ループを起動（Production は監視専用 DB を使用。MONITOR_POLL_INTERVAL で間隔上書き可）
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 停止: data/stop_requested.flag ファイルを作成するとループは次回チェックで終了します。

- ExecutionEngine を起動（本番 or paper_trading 切替）
  - 環境変数に KABUSYS_ENV を設定:
    - export KABUSYS_ENV=paper_trading  → MockBroker を使用し data/paper_trading.db を使う
    - export KABUSYS_ENV=live / development
  - python -m kabusys.run_execution
  - エンジンは起動時に data/execution.pid を書き込む（pid_file の場所は Settings で変更可能）。
  - 停止: data/stop_requested.flag を作成するとエンジンは停止処理を行います（監視系からの kill.flag と組合せて運用）。

- Streamlit ダッシュボード（監視データの確認）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で SQLite ファイルを指定可能（既定: data/monitoring.db）
  - 読み取り専用で接続します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）
  - 出力は標準出力に要約レポートを表示します（稼働率、注文成功率、レイテンシなど）。

- AI モジュール（例）
  - ニューススコアリング（プログラムから呼び出す）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

環境設定（Settings）
-------------------
kabusys.config.Settings 経由で環境変数を参照します。主な設定項目:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード時のモック約定挙動）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager で LINE push を使う場合に設定

注意事項 / 運用メモ
-----------------
- 監視用 DB（monitoring.db）は init_monitoring_db() により起動時にテーブル作成・マイグレーション（例: latency_ms, peak_value）を行います。
- Monitoring はモジュール設計上、本番の sqlite_path を使用する仕様になっている箇所があります（run_monitoring の挙動に注意）。
- プロセス優先度: 起動時に set_process_priority("high") を呼びます（psutil により OS 毎に処理）。
- KillSwitch / stop flag:
  - monitoring.kill_switch.KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ書き込み、ExecutionEngine 停止のトリガーとします。
  - run_monitoring / run_execution は data/stop_requested.flag の存在を見てループ／スレッドを終了します（運用上どちらを使うか合わせてください）。
- OpenAI API 呼び出し箇所（news_nlp, regime_detector）は API エラーに対してリトライやフォールバックを実装していますが、API キーが必要です。テスト時は該当関数の内部呼び出し（_call_openai_api 等）をモックすると良いです。
- DuckDB の接続はモジュールにより想定スキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を参照します。データ投入は別途パイプラインが必要です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env ロード / Settings
- run_monitoring.py        — SystemMonitor のポーリング実行スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）で ai_scores を更新
  - regime_detector.py      — マーケットレジーム判定（ma200 + マクロニュース）
- monitoring/
  - monitoring_db.py        — SQLite ベースの監視ログ CRUD + マイグレーション
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py        — 滞留注文・約定異常検出
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - alert_manager.py        — LINE push 通知ラッパ
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - monitoring_engine.py    — 各 Monitor を統合してポーリング
  - streamlit_dashboard.py  — Streamlit による監視ダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - （他: broker_factory, execution_engine, order_repository 等が含まれる想定）
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

（注）ここに列挙したのはリポジトリ内の重要モジュールの抜粋です。実際のディレクトリにさらに細かな実装ファイルが含まれています。

開発 / テストのヒント
--------------------
- .env/.env.local を用いて環境変数を柔軟に差し替えられます。OS 環境変数は .env の上位にあるため、本番運用では OS 側に設定するのが安全です。
- OpenAI を含む外部 API を使う機能はユニットテスト時にモックすることを推奨します（内部の _call_openai_api を patch）。
- monitoring_db.init_monitoring_db() は冪等でテーブル作成と簡易マイグレーションを行います。既存 DB の互換性を保つための処理があります。

ライセンス / 貢献
-----------------
（ここには実プロジェクトに応じたライセンス表記や貢献方法を追加してください）

以上。セットアップや運用で不明点があれば、実行したいユースケース（監視起動 / エンジン起動 / レポート生成等）を教えてください。具体的なコマンド例や .env サンプルを示します。