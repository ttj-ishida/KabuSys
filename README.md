README
======

概要
----
KabuSys は日本株の自動売買・監視・リサーチを目的とした Python コードベースです。  
主な機能は戦略のためのファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視コンポーネント、Paper Trading 検証ツール、LLM を用いたニュースセンチメント/レジーム判定などを含みます。

特徴（機能一覧）
----------------
- 株価ファクター計算（Momentum / Volatility / Value など）
- ポートフォリオ構築（候補抽出、等配分・スコア加重、リスク調整、ポジションサイズ算出）
- ExecutionEngine（ブローカー抽象化・発注管理・リコンシリエーション）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 向けの分離された SQLite DB と検証レポート生成ツール
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（銘柄ごとのセンチメント）および市場レジーム判定
- プロセス優先度・CPU affinity 設定ユーティリティ（psutil 使用）

動作要件（主な依存ライブラリ）
-----------------------------
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
- その他プロジェクトで利用するライブラリ（requirements.txt があればそちらを参照）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （追加の依存がある場合はプロジェクトの requirements.txt を利用してください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV = development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (ニュース/レジーム機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （AlertManager）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db) — なお Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading のとき実行エンジンが使用
     - PAPER_FILL_MODE = instant | partial | never | reject（Paper Trading の約定挙動）
     - LOG_LEVEL = DEBUG | INFO | ...
     - MONITOR_POLL_INTERVAL = ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
   - 参考の .env 例（.env.example が無い場合は以下をベースに作成）:
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
     - KABU_API_PASSWORD=xxxxxxxx
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=development

使い方（主要スクリプト）
-----------------------

1) 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 挙動:
     - プロセス優先度を "high" に設定（psutil を使用）
     - Settings から sqlite_path（monitoring DB）と duckdb_path を取得して接続
     - SystemMonitor を定期実行（間隔: MONITOR_POLL_INTERVAL 環境変数、デフォルト 60 秒）
     - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知して終了

   - 注意:
     - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を利用します（監視ログは一元管理）。

2) 発注エンジンを起動（Execution）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）へ記録して本番 DB と分離
     - プロセス優先度を "high" に設定
     - Reconciler による起動時リコンシリエーション、ExecutionEngine の run_session を別スレッドで実行
     - 停止は data/stop_requested.flag を作成（監視コンポーネントからの kill.flag とは別）または ExecutionEngine 停止シグナルで制御

3) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）
   - レポートは ai_scores / trade_logs / system_status 等から稼働率、注文成功率、レイテンシ等を算出し PASS/FAIL 判定を出力します。

4) Streamlit ダッシュボード（監視 GUI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開いてダッシュボードを表示します。

5) AI 関連（ニューススコアリング / レジーム判定）
   - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡して指定日分のニュースセンチメントを ai_scores に書き込み
     - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルへレジーム判定結果を格納
   - 注意:
     - OPENAI API 呼び出しはレート制限・エラーに対してリトライ／フォールバックの処理が組み込まれていますが、API キーは必須です。

監視・停止・フラグ
-------------------
- 停止フラグ（run_monitoring / run_execution が参照）
  - data/stop_requested.flag を作るとループが安全に終了します（run_monitoring/run_execution 共通で使用）。
- 強制停止（KillSwitch）
  - RiskMonitor 等が条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine 停止シグナルとして機能します。KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）でパスを取得します。
  - KillSwitch は冪等（既存ファイルがある場合は上書きしない）。
- PID 管理
  - ExecutionEngine は data/execution.pid を使ってプロセス存否を検出します。SystemMonitor は stale PID を検出してログに残します。

設定ロジック（Settings）
-----------------------
- 設定は環境変数およびプロジェクトルートの .env / .env.local を自動で読み込みます。読み込みの優先度は OS 環境変数 > .env.local > .env です（※ KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- KABUSYS_ENV の有効値: development, paper_trading, live
- Paper Trading モードでは run_execution が paper_sqlite_path を使用して本番と完全に分離されます。
- PAPER_FILL_MODE の有効値: instant | partial | never | reject

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下。主要モジュールと概要を併記）

- src/kabusys/
  - __init__.py                       — パッケージ定義、バージョン
  - config.py                         — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト（paper_trading 切替あり）
- src/kabusys/monitoring/
  - monitoring_db.py                  — SQLite 用の永続化層（テーブル初期化 / CRUD）
  - system_monitor.py                 — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py                  — 注文滞留・約定異常監視
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - kill_switch.py                     — kill.flag の作成 / 破棄
  - alert_manager.py                  — LINE 通知ラッパー
  - monitoring_engine.py              — 各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py            — Streamlit ダッシュボード（監視用）
- src/kabusys/execution/
  - order_manager.py                  — 発注制御（OrderState 管理、Duplicate チェック）
  - reconciler.py                     — 起動時リコンシリエーション（注文・ポジション突合）
  - （その他ブローカー関連・エンジン等の実装ファイル）
- src/kabusys/portfolio/
  - portfolio_builder.py              — 候補選定・重み計算
  - risk_adjustment.py                — セクター上限・レジーム乗数
  - position_sizing.py                — 株数（ロット）算出・投下資金スケール
- src/kabusys/research/
  - factor_research.py                — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py            — 将来リターン計算・IC/統計サマリ
- src/kabusys/ai/
  - news_nlp.py                       — ニュースセンチメント（OpenAI を用いた銘柄別スコア）
  - regime_detector.py                — ETF MA + マクロニュースで市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py      — Paper Trading 検証レポート生成スクリプト
- src/kabusys/utils/
  - process_priority.py               — プロセス優先度・CPU affinity 設定ユーティリティ

運用上の注意
------------
- Monitoring DB のパス（SQLITE_PATH）は監視ログの中心です。バックアップやアクセス権に注意してください。
- Paper Trading は本番 DB とは分離されていますが、設定ミスで上書きしないよう .env 等でパスを明示してください。
- OpenAI API を利用する機能は API キーと利用料が必要です。鍵の管理・レート制限に注意してください。
- psutil 等のシステム操作系は権限不足で機能制限される場合があります（優先度設定など）。

トラブルシューティング
-----------------------
- .env が自動読み込みされない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を確認（1 なら無効化されています）。
  - プロジェクトルート特定は .git または pyproject.toml を基準に行われます。ルートが検出できないと自動ロードはスキップされます。
- Monitoring が起動するがデータが増えない:
  - monitoring DB パス（SQLITE_PATH）と duckdb_path を確認してください。
  - SystemMonitor は get_last_price_date（DuckDB 内）でデータ鮮度をチェックします。DuckDB の prices_daily テーブルの更新状況を確認してください。

ライセンス・貢献
----------------
- この README はコードベースの利用説明を目的としています。ライセンスや貢献方法はリポジトリルートの LICENSE / CONTRIBUTING ドキュメントを参照してください。

以上。README の内容について補足が必要であれば、実行シナリオ（本番構成 / テスト構成 / CI 用コマンドなど）や .env の具体例を追加できます。