# KabuSys

日本株向け自動売買システムのリポジトリ（ミニマルなコア実装）。  
この README はコードベース（src/kabusys 以下）に基づいて作成しています。

概要
----
KabuSys は、価格データ / ファクター計算 / ポートフォリオ構築 / 発注・リスク管理 / 監視 / レポーティングまでをひと通りカバーする日本株自動売買の骨格です。  
主要コンポーネントは次のとおりです。

- データ解析（DuckDB を用いたファクター計算、将来リターン計算など）
- ポートフォリオ構築（候補選定、重み付け、位置サイズ計算、セクター制約）
- 発注系（Broker 抽象、Order 管理、リコンシリエーション）
- モニタリング（システム状態、注文滞留、リスク監視、アラート）
- AI 関連（ニュースのNLUによるセンチメント、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な機能
--------
- duckdb / prices_daily / raw_financials を使ったファクター計算（momentum, volatility, value）
- ファクターの IC 計算・特徴量サマリ
- ポートフォリオ候補抽出・等重/スコア重み計算
- 位置サイズ算出（risk-based / equal / score）・単元株丸め・集計キャップ調整
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
- OrderManager / Reconciler による発注状態管理と再同期ロジック
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE push）
- KillSwitch による外部停止フラグ（data/kill.flag）書き込みで ExecutionEngine を停止
- OpenAI を使ったニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- Streamlit ダッシュボード（監視データの可視化）
- Paper Trading 用検証レポート生成ツール

動作要件（推奨）
----------------
- Python 3.10+
  - PEP 604 の型記法（A | B）などを使用しているため 3.10 以上を推奨
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
  - など（環境に合わせて pip install してください）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 必要パッケージをインストールします（requirements.txt が無い場合は手動で）。
   - 例:
     pip install duckdb psutil openai requests streamlit

3. データディレクトリを作成します（デフォルト DB パスが data 以下のため）。
   - 例:
     mkdir -p data

4. 環境変数を用意します。
   - 自動で .env / .env.local が読み込まれます（プロジェクトルートに .git または pyproject.toml があることが前提）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を使う場合）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種外部 API のトークン/パスワード
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 使用時）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant, partial, never, reject）
     - LINE チャネル情報: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings から参照されます。

5. .env ファイル例（プロジェクトルート）:
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   OPENAI_API_KEY=sk-xxxx
   PAPER_FILL_MODE=instant

使い方（主要コマンド）
--------------------
- 監視ループ起動（SystemMonitor 単体の簡易起動スクリプト）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは共有DB）

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に保存します
  - 実行開始時にプロセス優先度を "high" に設定しようとします（権限がない場合は警告）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開き、Positions / Orders / System / Overview を表示

- AI 機能
  - ニュースをスコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が必要。API 呼び出しはリトライ・フェイルオーバーロジックあり。

運用に関する注意点
------------------
- KABUSYS_ENV:
  - development / paper_trading / live のいずれかを指定可能。paper_trading は発注を本番 DB と分離するためのモードです。
- プロセス優先度:
  - run_monitoring / run_execution は開始時に set_process_priority("high") を呼びます。権限不足や未対応 OS の場合は警告が出てスキップされます。
- KillSwitch:
  - RiskMonitor 等の結果に基づき Kabusys が data/kill.flag に原因テキストを書き、ExecutionEngine に停止シグナルを送ります。flag の既存時は冪等的に書き込みをスキップします。
  - ExecutionEngine 起動時に kill_flag_clear_on_start を有効にする設定があればクリア処理を行います（Settings.kill_flag_clear_on_start）。
- データ鮮度:
  - SystemMonitor は DuckDB の get_last_price_date を参照し、最新価格が _FRESHNESS_DAYS（デフォルト3）以内かを判定します。データ不足はアラート対象になります。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要ファイルと概要です（抜粋）。

- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__）
  - config.py                   — Settings クラス（環境変数 / .env ロード）
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト（paper_trading 支援）
- src/kabusys/ai/
  - news_nlp.py                 — ニュースの OpenAI ベースセンチメント（ai_scores 書き込み）
  - regime_detector.py          — マクロ + ma200 で市場レジーム判定
- src/kabusys/data/              — （データパイプライン・ユーティリティはここに配置想定）
- src/kabusys/research/
  - factor_research.py          — momentum/volatility/value 等のファクター算出
  - feature_exploration.py      — 将来リターン, IC, 統計サマリ
- src/kabusys/portfolio/
  - portfolio_builder.py        — 候補選定 / 重み付け
  - position_sizing.py          — 株数決定 / aggregate cap / lot 単位丸め
  - risk_adjustment.py          — セクター制約 / レジーム乗数
- src/kabusys/execution/
  - order_manager.py            — 発注ワークフロー（create/send/sync 等）
  - reconciler.py               — 起動時リコンシリエーション（broker と突合）
  - その他 broker_factory 等（ブローカー抽象）
- src/kabusys/monitoring/
  - monitoring_db.py            — SQLite による監視ログ永続化（テーブル作成・CRUD）
  - system_monitor.py           — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py            — 注文滞留 / 約定価格異常検出
  - risk_monitor.py             — ドローダウン / ポジション上限監視
  - kill_switch.py              — kill.flag 書き込みユーティリティ
  - alert_manager.py            — LINE によるアラート送信
  - monitoring_engine.py        — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py      — Streamlit ベースの管理ダッシュボード
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト

補足（設計上のポイント）
-----------------------
- 設定は Settings クラスを介して参照する設計で、.env 自動読み込み機能を持ちます。OS 環境変数は保護され .env.local は上書き可能です。
- DB マイグレーションは簡易な手続き（例: monitoring_db.init_monitoring_db が列追加等を行う）で互換性を保ちます。
- AI 呼び出しはリトライや JSON バリデーション等、実運用向けの堅牢化が施されています（429/タイムアウト/5xx の処理）。
- パフォーマンスや可観測性を考慮し、DuckDB と SQLite を使い分けています（分析は DuckDB、監視ログは SQLite）。

よくある運用コマンドのまとめ
----------------------------
- 監視開始:
  python -m kabusys.run_monitoring
- 実行エンジン（発注）開始:
  python -m kabusys.run_execution
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

問題報告 / 貢献
---------------
この README はコードのスナップショットに基づいて作成しています。実際の運用・テストで差異があれば Issue を立ててください。プルリクエスト歓迎です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）

以上。運用や導入で補足が欲しい箇所（例: .env の具体例、Docker 化、CI 設定、Broker の実装例など）があれば教えてください。必要に応じて README を拡張します。