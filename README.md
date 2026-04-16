KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。  
シグナル生成・ポートフォリオ構築・発注実行・監視・リサーチ・AI (ニュース NLP / レジーム判定) といった機能群をモジュール化して提供します。  
このリポジトリは主に下記を含みます：

- ExecutionEngine：ブローカーに対する注文発行・状態管理・リコンシリエーション
- Monitoring：システム稼働・注文状況・リスク監視・アラート送信（LINE）
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：OpenAI を利用したニュースセンチメント（ai_scores）と市場レジーム判定
- Tools：Paper Trading 検証レポート生成・Streamlit ダッシュボードなど

主な特徴
--------
- モジュール分離された設計（execution / monitoring / research / ai / portfolio 等）
- 本番 DB と paper_trading を明確に分離（KABUSYS_ENV=paper_trading）
- DuckDB を使ったオンメモリ/分析用クエリと SQLite を監視 / 取引ログ保存に使用
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント付与とレジーム判定（API キー必要）
- LINE によるアラート（AlertManager）
- Streamlit ベースの監視ダッシュボード
- フラグファイル（data/kill.flag, data/stop_requested.flag）でプロセス制御可能

依存（代表）
--------------
以下パッケージが必要です（環境により異なる場合があります）：
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit

（実際の requirements.txt があればそちらを使用してください）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading の場合、MockBrokerClient が使用され、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に保存されます。
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用（必須となる機能あり）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などの監視設定

4. データディレクトリ
   - data/ 配下に DB や flag/pid ファイルが置かれます。存在しない場合はモジュールが作成します。

基本的な使い方
--------------

実行系
- ExecutionEngine（実際の発注セッション）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient と paper_trading DB を使用します。
  - 既に data/stop_requested.flag があると起動をスキップします（停止フラグ機構）。

- Monitoring（SystemMonitor ポーリング）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番監視 DB を参照する設計）。

ツール
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to YYYY-MM-DD （終了日）
    - --db PATH （SQLite ファイルパス、PAPER_TRADING_SQLITE_PATH 環境変数で代替可能）
  - 出力は稼働率・注文成功率・レイテンシ等の簡易判定（PASS/FAIL）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で監視 DB を開き、ダッシュボード表示（Overview / Positions / Orders / System）。

AI / リサーチ
- ニュース NLP スコアリング（ai）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要。結果は DuckDB の ai_scores テーブルに書き込まれます。
- レジーム判定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要。結果は market_regime テーブルに書き込まれます。

監視・停止フラグ
- 停止要求（外部から実行エンジン等を停止させる）:
  - data/stop_requested.flag を作成すると run_execution や run_monitoring のループが検知して終了します。
- Kill Switch:
  - data/kill.flag は KillSwitch が書き込み、ExecutionEngine に停止シグナルを送るために使用します。
  - KillSwitch は drawdown や position limit 等の条件でフラグを作成します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 なら起動時にクリアします。

環境設定の挙動（補足）
- .env ファイルのロード順:
  - OS 環境変数 > .env.local（上書き） > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化
- PAPER_FILL_MODE（paper_trading の振る舞い）:
  - instant | partial | never | reject（それ以外は ValueError）

よく使うコマンド例
------------------
- 監視ループを 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- paper_trading モードでエンジンを起動（MockBroker を使用）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（2026-04-01 から 2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ディレクトリ構成（要約）
-----------------------
src/kabusys/
- __init__.py                      — パッケージ初期化、バージョン等
- config.py                        — 環境変数 / 設定管理（.env 自動ロード含む）
- run_execution.py                 — ExecutionEngine 起動スクリプト
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py, reconciler.py, ... — 発注ロジック、リコンシリエーション等
- monitoring/
  - monitoring_db.py                  — SQLite の監視用永続化層（テーブル作成・CRUD）
  - system_monitor.py                 — システム状態 / データ鮮度監視
  - trade_monitor.py                  — 注文滞留 / 約定異常監視
  - risk_monitor.py                   — ドローダウン / ポジション上限監視
  - kill_switch.py                    — kill.flag 制御ロジック
  - alert_manager.py                  — LINE 通知
  - monitoring_engine.py              — モニタ群の統合ポーリング
  - streamlit_dashboard.py            — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 銘柄選定・配分・サイズ計算
- research/
  - factor_research.py, feature_exploration.py — DuckDB を使ったファクター／解析機能
- ai/
  - news_nlp.py, regime_detector.py   — OpenAI 利用のニュース NLP / レジーム判定
- tools/
  - paper_verification_report.py      — Paper Trading の検証レポート
- utils/
  - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ
- data/ (実行時生成)
  - monitoring.db, paper_trading.db, kabusys.duckdb, *.flag, *.pid 等

開発上の注意点 / トラブルシューティング
----------------------------------------
- プロセス優先度設定（set_process_priority）は psutil を使います。権限不足で設定できないと警告になりますが処理は継続します。
- DuckDB / SQLite の接続はファイルパスを指定して使用します。複数プロセスが書き込む場合はロックに注意してください（モジュールは基本的に排他的な利用を前提としない実装を心掛けていますが、運用での検証が必要です）。
- OpenAI API 呼び出しはレート制限や一時エラーを考慮して指数バックオフでリトライしますが、API キー未設定時はエラーとなります。
- monitoring の初回実行時は init_monitoring_db() により必要テーブルと簡易マイグレーションを実行します。
- .env のパースはシェルの export 形式やクォート、コメントをある程度扱います。複雑な .env を使う場合は注意してください。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献ガイドラインを追記してください）

お問い合わせ
-------------
問題報告や質問はリポジトリの Issue へお願いします。README の改善提案も歓迎します。

---
以上。README に含めるべき追加情報（例: requirements.txt の内容、実運用上の注意、CI / テスト方法など）があれば教えてください。必要に応じて追記します。