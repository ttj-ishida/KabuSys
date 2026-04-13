README — KabuSys
=================

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコアライブラリ群です。  
売買実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、および AI（ニュースセンチメント / レジーム判定）などの機能を持ちます。  
設計方針として、可能な限り副作用を排した純粋関数群（ポートフォリオ計算など）と、永続化層（SQLite / DuckDB）を分離しています。

主な機能一覧
-------------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント選択（paper_trading 環境では MockBrokerClient を使用）
  - 注文マネジメント（OrderManager / OrderRepository / Reconciler）
  - リスク制御（RiskManager）
- Monitoring
  - 定期監視ループ（run_monitoring.py）
  - SystemMonitor: CPU / メモリ / ディスク / PID チェック / データ鮮度
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag 発行
  - AlertManager: LINE Push による通知（オプション）
  - Streamlit ダッシュボード（監視結果の可視化）
- Portfolio
  - 銘柄候補選定 / 重み計算（等分配・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数計算（ポジションサイジング、lot 単位で丸め）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP（OpenAI を用いた銘柄別センチメントスコアの生成）
  - レジーム判定（ETF MA とマクロニュースの LLM センチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提条件（概略）
----------------
- Python 3.9+（typing の記法や一部ライブラリ前提）
- SQLite（標準で同梱）
- DuckDB Python バインディング
- psutil（プロセス優先度 / CPU affinity / システム情報取得）
- requests（LINE API 呼び出し）
- openai（OpenAI クライアント、AI 機能を使う場合）
- streamlit（ダッシュボードを使う場合）

セットアップ手順
---------------
1. リポジトリをチェックアウト（プロジェクトルートに pyproject.toml または .git が存在する想定）。
2. Python 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit
   実際の依存パッケージはプロジェクトの要件ファイルに合わせてください。
4. 環境変数を設定するか、プロジェクトルートに .env（および .env.local）を配置します。
   - 自動ロードは既定で有効（.env / .env.local をプロジェクトルートから読み込み）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（Settings）
-------------------------
（Settings クラスで参照される主要キー）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABU_API_BASE_URL — (任意) デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI を使う AI 機能で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject）
- PID_FILE_PATH — ExecutionEngine 用 pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を削除するか ("1" で有効)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

簡単な .env 例
---------------
（.env.example を参考にしてください。サンプル）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

実行方法
--------
- ExecutionEngine の起動（本番 / Paper を Settings に従って切り替え）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB・MockBroker を使用します。

- Monitoring の起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用する設計です。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で監視 DB を指定できます（デフォルト: data/monitoring.db）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - SQLite パスを明示する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

動作上のポイント・注意事項
--------------------------
- run_execution.py / run_monitoring.py は起動直後にプロセス優先度を "high" に設定しようとします（psutil による操作、権限がない場合は警告で継続）。
- Paper Trading モードは本番 DB と分離するため、PAPER_TRADING_SQLITE_PATH を使用します。
- AI 機能（news_nlp, regime_detector）は OpenAI API キーが必要です。API エラー（rate-limit / 5xx 等）に対してリトライやフォールバックを含む設計になっています。
- Monitoring の kill.flag を用いた ExecutionEngine 停止シグナル機構があり、RiskMonitor の判定で kill.flag を書き込みます（ExecutionEngine は起動時に kill.flag をクリアする挙動を制御できます）。
- .env の自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - OS 環境変数 > .env.local > .env の順でマージされます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py                         — パッケージ定義
- config.py                           — 環境変数 / Settings 管理
- run_execution.py                    — ExecutionEngine 起動スクリプト
- run_monitoring.py                   — Monitoring ポーリング起動スクリプト

サブパッケージ:
- execution/                          — 注文実行関連（Engine, OrderManager, Reconciler, broker_factory 等）
- monitoring/
  - monitoring_db.py                  — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py                 — システム状態監視
  - trade_monitor.py                  — 注文滞留・約定異常監視
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - kill_switch.py                     — kill.flag 管理
  - alert_manager.py                  — LINE 通知
  - monitoring_engine.py              — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py            — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py              — 候補選定・重み計算
  - risk_adjustment.py                — セクター上限・レジーム乗数
  - position_sizing.py                — 株数計算
- research/
  - factor_research.py                — Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py            — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py                       — ニュースセンチメント（OpenAI 連携）
  - regime_detector.py                — 市場レジーム判定（ETF + マクロニュース）
- tools/
  - paper_verification_report.py      — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/monitoring_db.py         — 監視 DB 定義（テーブル作成・マイグレーション含む）

補足
----
- DuckDB はリサーチ・価格テーブル（prices_daily / raw_financials 等）を格納する想定です。データ投入・スキーマは別途用意してください。
- 本 README はコード内の docstring / 設計コメントに基づいて作成しています。詳細な API 仕様や実装の前提条件（外部ブローカー、データスキーマ等）は該当モジュールの docstring を参照してください。

貢献・開発
----------
テストやローカル開発を行う場合は、KABUSYS_ENV を development にして実行し、必要に応じて .env.local で上書きしてください。Pull request の際はユニットテスト・静的解析（flake8 / mypy 等）を追加することを推奨します。