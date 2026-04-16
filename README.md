KabuSys — 日本株自動売買フレームワーク
====================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした Python コードベースです。  
主な機能は取引エンジンの起動・自動復旧（Reconciler）、監視（System / Trade / Risk）、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント / レジーム判定）、および検証用ユーティリティです。設計方針として「本番コードと研究コードの分離」「ルックアヘッドバイアスの回避」「外部 API 呼び出しは限定的（AI モジュールのみ）」が採られています。

主な特徴
--------
- ExecutionEngine 起動スクリプト（実際のブローカー or Paper Trading を切替可能）
- 監視デーモン（SystemMonitor / TradeMonitor / RiskMonitor, kill switch, LINE 通知）
- 監視データの永続化（SQLite）と簡易ダッシュボード（Streamlit）
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算）
- リサーチモジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール（ニュースを OpenAI でスコアリング / 市場レジーム判定）
- 検証用ツール（Paper Trading 検証レポート生成スクリプト）

前提 / 必要環境
---------------
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨パッケージ（一例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil requests openai streamlit

（プロジェクトには requirements.txt が無い想定のため、上記パッケージを利用環境に合わせて追加してください。）

設定（環境変数）
----------------
Settings クラスは .env / .env.local /OS環境変数を読み込みます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主な環境変数:

- KABUSYS_ENV: 起動環境 (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 監視アラート用（未設定時は送信スキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading DB パス（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH / PID_FILE_PATH 等も Settings で取得可能

セットアップ手順（ローカル開発・実行例）
-------------------------------------
1. リポジトリをクローンし、プロジェクトルートに移動（src 配下にパッケージがある想定）。
2. 仮想環境を作成して有効化。
3. 必要パッケージをインストール（上記参照）。
4. data ディレクトリを作成:
   mkdir -p data
5. 環境変数を設定（例: .env を作成）:
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   OPENAI_API_KEY=your_openai_key   # AI 機能を使う場合
   （必要に応じて DUCKDB_PATH / SQLITE_PATH 等）
6. (初回) 監視 DB の初期化は run_monitoring/run_execution が自動で行います（init_monitoring_db）。

使い方（主なコマンド）
--------------------

- 監視デーモン（SystemMonitor の単独実行を含む）
  PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、例: MONITOR_POLL_INTERVAL=30）
  - 停止はプロジェクトルート data/stop_requested.flag ファイル作成で検出して終了

- 実行エンジン（ExecutionEngine）
  PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に書き込む（data/paper_trading.db）
  - 停止シグナル: data/stop_requested.flag を作るとエンジンを安全停止
  - 実行中は data/execution.pid に PID を記録

- Streamlit ダッシュボード（監視データ参照）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  もしくは --db で DB パスを指定

AI / レジーム判定・ニューススコアリング
-------------------------------------
- ニューススコアリング:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

どちらも OPENAI_API_KEY が必要（引数で渡すか環境変数で指定）。API 呼び出しで失敗した場合はフェイルセーフの扱い（ゼロやスキップ）で続行する設計です。

監視・キルスイッチについて
---------------------------
- KillSwitch: リスク条件（ドローダウン超過、ポジション数上限など）により data/kill.flag を書き込み、ExecutionEngine 側で検知して停止させます。
- stop_requested.flag: run_* スクリプトは data/stop_requested.flag の有無を確認してグレースフルに終了します。
- kill/stop ファイルは Settings で上書き可能なパスを使用します。

主要ディレクトリ構成（概要）
--------------------------
src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — 環境変数 / .env ロード / Settings
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- ai/
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite テーブル定義と永続化 API
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の生成ロジック
  - alert_manager.py — LINE Push による通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - reconciler.py — 起動時の注文・ポジション同期処理
  - order_manager.py — 注文作成・管理の外向 API
  - （他に broker_factory, execution_engine, order_repository 等が存在する想定）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 株数計算・単元丸め・集約キャップ
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
- data/ (実行時に生成される想定)
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite, paper_trading 環境用)
  - kabusys.duckdb (DuckDB)

開発上の注意事項
----------------
- Settings は .env/.env.local の自動読み込みを行います。テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番の DB は分離されます（KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用）。
- AI モジュールは外部 API に依存するため、API キーや通信障害に配慮した設計（リトライ・フォールバック）となっています。
- process_priority.set_process_priority により実行開始時に優先度を上げますが、環境によっては設定に失敗し警告を出します（実行は継続）。

トラブルシューティング / よくある質問
-----------------------------------
- .env が読み込まれない:
  - プロジェクトルートの判定は .git または pyproject.toml を基準に行われます。配布後にルートが判定できない場合は自動ロードをスキップします。手動で環境変数を設定してください。
- run_monitoring がすぐ終了する:
  - data/stop_requested.flag が存在していないか確認してください。
- AI 呼び出しで失敗する:
  - OPENAI_API_KEY が設定されているか、API レスポンスが正常かを確認してください。失敗時はログを参照すると詳細がわかります。

ライセンス・貢献
----------------
（このリポジトリのライセンス・貢献ガイドラインをここに記載してください。サンプル README には含まれていません。）

以上が README の要点です。必要であれば「実行例」「.env.example」「requirements.txt」や「開発用の docker-compose」「ユニットテスト実行方法」などを追記できます。どの項目を優先して補足しますか？