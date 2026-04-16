KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
本リポジトリには、以下の主要機能を持つモジュール群が含まれます:

- 実行エンジン（ExecutionEngine）関連の注文管理 / リコンシリエーション
- 監視（Monitoring）: システム状態／注文異常／リスク監視、LINE 通知、ダッシュボード
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索（DuckDB を利用）
- AI を用いたニュース NLP / 市場レジーム判定（OpenAI API 経由）
- 各種ユーティリティとツール（Paper Trading 検証レポート等）

主な設計方針:
- DuckDB/SQLite をデータ層に使い、ロジックは可能な限り純粋関数または副作用を明示した層に分離。
- 本番／Paper Trading を切り分ける仕組み（DB・ブローカークライアントの切替等）。
- LLM 呼び出しは失敗時にフェイルセーフ（スコア 0 やスキップ）で続行する。

機能一覧
--------
- Execution:
  - 注文生成 / ブローカー同期 / リスク管理 / 起動時リコンシリエーション（Reconciler）
  - Paper Trading モード（モックブローカー・paper_trading.db に記録）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン監視、ポジション数上限
  - KillSwitch: 条件に応じた停止フラグ書き込み（data/kill.flag）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード (read-only)
- Portfolio:
  - 候補選定、等重・スコア重み付け、セクター制限、ポジションサイズ決定
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）等の統計ユーティリティ
- AI:
  - ニュースを LLM でスコアリングして ai_scores に書き込み
  - ETF (1321) MA とマクロニュースを合成した市場レジーム判定
- Tools:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提 / 依存
------------
- Python 3.9+（型アノテーションで | を使うため 3.10+ を想定する箇所がありますが、3.9 でも typing の backport 等で対応可）
- 主な依存ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで可）
- 環境によってはプロセス優先度設定で管理者権限が必要になることがあります。

セットアップ手順
----------------
1. リポジトリをクローン:
   git clone <repo-url>
2. 仮想環境を作成して有効化:
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
3. 依存をインストール（例）:
   pip install duckdb psutil requests openai streamlit
   （実際は requirements.txt があればその内容に従ってください）
4. .env ファイル:
   - プロジェクトルートの .env および .env.local が自動で読み込まれます（OS 環境変数より下位）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - .env.example があれば参照して必要な変数を設定してください。

主要環境変数（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時、必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (LINE 通知)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
- PAPER_TRADING_SQLITE_PATH（paper trading 用 DB、デフォルト data/paper_trading.db）
- SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
- DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH などのパス設定
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

実行方法（代表的なコマンド）
----------------------------
- 監視ループ起動（SystemMonitor をポーリング）:
  python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: 環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に Settings.sqlite_path（本番 DB）を使用します（環境にかかわらず）。
  - 停止はプロジェクトの data/stop_requested.flag を作成するか Ctrl+C。

- 実行エンジン起動（ExecutionEngine）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い paper_trading DB に記録します。
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します。
  - 実行中は PID ファイル (data/execution.pid) が作成されます。停止は stop フラグの作成で行います。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

- Streamlit ダッシュボード（監視 DB を読み取り専用で表示）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 機能（プログラム呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡します。
  - LLM 呼び出しはレート制限・5xx などでリトライを行いますが、失敗時はフェイルセーフ動作（スコア 0 やスキップ）します。

運用に関する注意
----------------
- Paper Trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- kill.flag / stop_requested.flag:
  - kill.flag は KillSwitch による ExecutionEngine 強制停止指示用（data/kill.flag 等）。
  - stop_requested.flag（data/stop_requested.flag）を置くと run_monitoring / run_execution が停止します。
- プロセス優先度設定:
  - 実行開始時に set_process_priority("high") を試みます。psutil による権限エラーは警告でスキップされます。
- OpenAI API キー・利用:
  - コストやレイテンシに注意してください。API 呼び出しはバッチ化／リトライロジックを持ちますが、API 利用は運用上の責任で管理してください。

よく使うパターン（例）
---------------------
- 開発環境で Paper Trading を動かす例:
  export KABUSYS_ENV=paper_trading
  export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  python -m kabusys.run_execution

- 監視を常時実行:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボードをローカルで見る:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ディレクトリ構成
----------------
以下は主なファイル・モジュールの構成（src/kabusys 配下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理 (Settings)
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - data/                            — (実行時に利用するデータディレクトリ: monitoring.db 等)
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...                            — ブローカ API, execution engine 等
  - monitoring/
    - monitoring_db.py              — SQLite テーブル作成 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
    - ...

開発者向けメモ
----------------
- .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env よりも後で読み込まれ（上書き可能）ます。
- DuckDB / SQLite スキーマ:
  - monitoring_db.init_monitoring_db(conn) は冪等でテーブルと一部カラムのマイグレーションを実行します。
- テスト／ユニットテスト:
  - OpenAI 呼び出しや外部 API はテスト時に差し替えられるよう設計されています（モック可能）。

ライセンス / 貢献
-----------------
- 本 README ではライセンスや貢献手順は記載していません。リポジトリのトップレベルに LICENSE / CONTRIBUTING.md があればそちらを参照してください。

問い合わせ / 注意
-----------------
本ドキュメントはソースコードを参照してまとめた概要です。細かな挙動や API の詳細は実装ファイル（src/kabusys 以下）を参照してください。運用時は API キーやブローカー認証情報の取り扱いに十分注意してください。