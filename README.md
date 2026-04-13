KabuSys — 日本株自動売買システム
================================

この README は与えられたソースツリー（src/kabusys 以下）を基に作成した簡易ドキュメントです。
本プロジェクトは戦略・ポートフォリオ構築・注文実行・監視・リサーチ・AI（ニュース NLP）などを統合した自動売買基盤の一部です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な責務は以下の通りです。

- 戦略に基づく銘柄選定・配分・株数決定（portfolio）
- 定量ファクター計算・リサーチ（research）
- 注文の生成・送信・状態管理・再同期（execution）
- システム状態・注文状態・リスク（ドローダウン等）の監視（monitoring）
- ニュースを用いた NLP スコアリング／市場レジーム判定（ai）
- 検証用ツール（paper trading の検証レポート 等）

特徴（主な機能）
----------------
- ポートフォリオ構築：候補選定、等金額・スコア加重、リスクに基づくポジションサイジング
- リスク調整：セクター上限チェック、レジーム乗数による投下資金調整
- リサーチ：Momentum / Volatility / Value 等のファクター計算、将来リターンや IC 計算
- 実行系：OrderManager / Reconciler によるクラッシュ耐性のある注文管理と再同期
- 監視：SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine による定期チェック
- アラート：LINE Messaging API を使ったプッシュ通知（AlertManager）
- AI：OpenAI を使ったニュースセンチメントスコアリング（news_nlp）と市場レジーム判定（regime_detector）
- ツール：paper_trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- Streamlit ダッシュボード（監視情報の可視化）

セットアップ手順
----------------
以下はローカルで動かすための最小手順例です（プロジェクトルートに pyproject.toml があることを想定）。

1. リポジトリをクローン / 取得
   - プロジェクトルートに移動してください。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. インストール
   - pip install -e .            # 開発インストール（pyproject.toml がある場合）
   - 依存が明示されていない場合は手動でインストール：
     pip install duckdb psutil requests streamlit openai

4. 環境変数設定
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABU_API_BASE_URL（任意、デフォルト http://localhost:18080/kabusapi）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（INFO 等）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に使用）

5. データディレクトリ作成
   - data/ を作成し、必要なら DB ファイルなどを配置します。

使い方（主なコマンド / スクリプト）
-----------------------------------
※ 実行はプロジェクトルートから行うか、パッケージをインストールして python -m kabusys.xxx を使用してください。

- 監視ループを起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は Settings に基づき sqlite（monitoring DB）にログを残す。monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
  - 起動時にプロセス優先度を "high" に設定します（psutil を使用）。

- 実行エンジンを起動（Execution）
  - Paper trading モード:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、data/paper_trading.db に記録されます（本番 DB と分離）。
  - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Positions / Orders / System / Overview を表示します。

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI API（gpt-4o-mini）を用いてニュースをスコア化し ai_scores テーブルへ書込
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
  - OpenAI キーは引数または環境変数 OPENAI_API_KEY を使用。未設定の場合は例外を投げます（score_news/score_regime）。

環境設定の挙動（config.py について）
------------------------------------
- .env / .env.local を自動でロード（OS 環境変数が優先）。プロジェクトルートが検出できない場合は自動ロードをスキップします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを停止します（テスト等で使用）。
- Settings クラスを通じて各種設定を取得します（例: sqlite_path, duckdb_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値, env 判定など）。
- PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"（不正値は ValueError）。

注意点 / 実運用でのポイント
----------------------------
- MonitoringDB（init_monitoring_db）は必要テーブルの作成および簡易マイグレーション（カラム追加）を行うため、起動前に DB ファイルが無くても初回起動で作成されます。
- run_monitoring は監視専用の DB（settings.sqlite_path）を参照します。paper_trading モードを実行するときは paper_sqlite_path が使われます（実行エンジン側）。
- Kill switch（data/kill.flag）を監視して ExecutionEngine の停止を促す仕組みがあります（kill_flag_clear_on_start で起動時に自動クリア可）。
- プロセス優先度設定はプラットフォームにより振る舞いが異なります（Windows / POSIX 対応、権限不足では警告を出してスキップ）。
- AI の呼び出しは外部 API（OpenAI）に依存します。429 やネットワークエラーに対しては指数バックオフでリトライする実装がありますが、API キーや料金体系には注意してください。
- Streamlit ダッシュボードは DB を read-only モードで開く指示をしているため、監視プロセスと安全に共存できます。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュールと役割の一覧です（提供されたコードに基づく）。

- src/kabusys/
  - __init__.py            — パッケージメタ情報
  - config.py              — 環境変数 / 設定管理（Settings）
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト（paper_trading サポート）
- src/kabusys/portfolio/
  - portfolio_builder.py   — 候補選定・重み計算（equal / score）
  - position_sizing.py     — 株数決定・資金配分・lot 単位処理
  - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - __init__.py
- src/kabusys/research/
  - factor_research.py     — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - __init__.py
- src/kabusys/ai/
  - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（ma200 + macro sentiment）
  - __init__.py
- src/kabusys/monitoring/
  - monitoring_db.py       — SQLite ベースの永続化層（テーブル作成・CRUD）
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py       — 注文滞留・約定価格異常チェック
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の読み書きと評価
  - alert_manager.py       — LINE プッシュ通知送信ロジック
  - monitoring_engine.py   — 複数 Monitor をまとめてポーリング
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - __init__.py
- src/kabusys/execution/
  - order_manager.py       — 注文作成/送信/状態管理
  - reconciler.py          — 起動時の復旧・ポジション照合
  - （その他: broker_factory 等、実際のブローカー連携は別ファイル群）
- src/kabusys/tools/
  - paper_verification_report.py — Paper trading の検証レポート生成
  - __init__.py
- src/kabusys/utils/
  - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

付録（よくあるコマンド例）
--------------------------
- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（paper）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
------
この README はソース中の docstring / コメントをもとに要点をまとめたものです。実運用前には必須環境変数の設定、権限・API キーの管理、ブローカ接続の動作確認、DB バックアップ等を必ず行ってください。必要であれば、さらに詳しいセットアップ手順（Dockerfile / systemd ユニット / CI 設定 等）や API 使用例を追加で作成できます。