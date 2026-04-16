KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なトレーディング基盤です。  
主な機能はシグナル→ポートフォリオ構築→発注（ExecutionEngine）、監視（MonitoringEngine）、
市場・ニュースの AI 評価、リサーチ用ファクター計算などを含みます。

主な特徴
--------
- Execution:
  - 発注エンジン（ExecutionEngine）と OrderManager / Reconciler による自動発注・再同調
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を用い、紙上で data/paper_trading.db に記録
- Monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine（ポーリング監視）
  - 監視ログを SQLite に永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - LINE Push によるアラート通知（AlertManager）
  - Kill Switch（条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止）
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Portfolio:
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - ポートフォリオ構築・重み付け・ポジションサイズ計算（純粋関数群）
- AI:
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア生成（ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector）
- ツール:
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

必須要件
--------
- Python 3.10+
- 外部ライブラリ（例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
- SQLite（Python 標準ライブラリに同梱）
- ネットワーク（OpenAI API / LINE API を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai requests psutil streamlit
   - （ある場合は requirements.txt を利用: pip install -r requirements.txt）
4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data
5. 必要な環境変数を設定（.env または OS 環境変数）
   - 必須（運用に応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI / レジーム / ニュース利用:
     - OPENAI_API_KEY
   - LINE 通知（任意）:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - 動作モード:
     - KABUSYS_ENV = development | paper_trading | live  （デフォルト: development）
   - DB パス（デフォルトを上書きしたい場合）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
   - その他:
     - LOG_LEVEL (INFO 等)
     - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動
6. 自動 .env ロードについて
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

基本的な使い方
-------------

1) ExecutionEngine（発注エンジン）を起動する
- デフォルト（環境変数に従う）:
  - python -m kabusys.run_execution
- Paper Trading モード:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 動作:
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む。
  - 実行中は data/execution.pid を書き、停止は data/stop_requested.flag や data/kill.flag によって制御可能。

2) Monitoring（監視）を起動する
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。
- 重要: Monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（本番監視DB）を使用する設計です。

3) Streamlit ダッシュボード（監視の可視化）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート（CLI）
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  - --from YYYY-MM-DD
  - --to   YYYY-MM-DD
  - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

5) AI モジュール（プログラムから利用）
- ニューススコア算出:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  — OPENAI_API_KEY が必要
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

主要設定（Settings）と環境変数
------------------------------
（主なもの）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが設定推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合（ai.news_nlp / ai.regime_detector）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）

実装上の注意点（運用メモ）
------------------------
- Monitoring の DB は init_monitoring_db() でテーブル作成・マイグレーションを行います。既存 DB へのカラム追加（例: latency_ms, peak_value）に対応したコードが含まれます。
- run_monitoring は stop_requested.flag（data/stop_requested.flag）を検知するとループ終了します。run_execution も同様のフラグで停止処理を実装しています。
- AlertManager は LINE トークンが未設定なら送信をスキップします。送信のクールダウン（デフォルト 30 分）を内蔵。
- OpenAI API 呼び出しはリトライ・バックオフ実装・入力トリミング・レスポンス検証を備えていますが、API キーは必ず安全に管理してください。
- process_priority ユーティリティは psutil に依存します。権限不足で優先度設定が失敗する場合は警告を出します。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / Settings
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py              — ニュース NLP / OpenAI 連携
    - regime_detector.py       — 市場レジーム判定（ETF + マクロニュース）
  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py   — IC / 将来リターン / 統計サマリ等
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - position_sizing.py       — 株数計算・ロット丸め・スケーリング
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層（init / MonitoringDB）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - alert_manager.py         — LINE 通知クライアント
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — 発注 API と DB を繋ぐ外向け管理
    - reconciler.py           — 再起動時のリコンシリエーション
    - (その他 Order / Broker 関連実装)
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - research/__init__.py      — 研究用 API export
  - monitoring/__init__.py    — 監視 API export
  - ai/__init__.py            — ai API export
  - portfolio/__init__.py     — portfolio API export

よくある運用シナリオ
--------------------
- 紙上検証:
  - KABUSYS_ENV=paper_trading を設定して run_execution を起動。結果は data/paper_trading.db に格納。paper_verification_report で検証。
- 本番監視:
  - run_monitoring を常駐させ、Streamlit ダッシュボードで監視。アラートは LINE へプッシュ。
- AI スコアのバッチ運用:
  - 定期ジョブで DuckDB を開き kabusys.ai.score_news を呼ぶ（OPENAI_API_KEY 必須）。成功した銘柄のスコアを ai_scores テーブルへ書き込む。

ライセンス・貢献
----------------
- リポジトリのルートに LICENSE を置いてください（本 README はライセンスに依存しません）。
- バグ報告・機能追加はプルリクエスト歓迎です。変更を加える際はテストとログ出力の確認をお願いします。

付録（短い運用メモ）
-------------------
- 監視 DB と発注 DB（paper_trading 用）は別ファイルとして運用されます（誤って本番 DB に書かないよう注意）。
- 実行中のプロセスが PID ファイルに記録され、システムモニタが PID 存在をチェックします。PID ファイルが stale（存在しないプロセス ID）なら削除され RiskEvent が残ります。
- MONITOR_POLL_INTERVAL は 0 や負値を与えると無効扱いになり 60 秒にフォールバックします。

必要であれば、この README を英語版に翻訳したり、具体的な .env.example や systemd / supervisor 用の unit ファイル例、Dockerfile / docker-compose のテンプレートを追加で作成します。希望があれば教えてください。