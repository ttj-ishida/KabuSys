README — KabuSys
=================

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコンポーネント群です。シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine） → 監視（Monitoring） → レポート/リサーチ/AI 補助といった一連の仕組みをモジュール単位で提供します。本リポジトリは純粋関数的なポートフォリオ構築ロジック、Execution 用のリコンシリエーション/OrderManager、監視（System/Trade/Risk）と通知機能、そして OpenAI を用いたニュースセンチメント／レジーム判定などを含みます。

主な特徴（機能一覧）
------------------
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重配分、スコアに基づく配分など（kabusys.portfolio）
  - ポジションサイズ計算（単元株丸め・最大保有比率・コストバッファ対応）
  - セクター集中制限、レジーム乗数適用
- Execution / Order 管理
  - OrderManager / OrderRepository（SQLite）を用いた発注管理
  - Reconciler による起動時の自動復旧（注文照合・ポジション差分検出）
  - Paper Trading（本番 DB と分離して data/paper_trading.db に記録）
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/Disk・プロセス生存・データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch によるフラグファイル停止、AlertManager による LINE 通知
  - Streamlit ベースの監視ダッシュボード
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由で prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）連携
  - ニュース記事のセンチメント評価（gpt-4o-mini、JSON Mode）
  - マクロニュース＋ETF MA200 乖離を使った市場レジーム判定
  - API の失敗や部分失敗に対するフェイルセーフ設計

前提 / 必要条件
---------------
- Python 3.10+
- 利用する機能に応じた外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボードを使う場合）
- SQLite（標準ライブラリで利用可能）
- ネットワーク（OpenAI / LINE API を使う場合）

簡易インストール例
------------------
1. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

（リポジトリに requirements.txt がある場合は pip install -r requirements.txt を使用）

設定（環境変数 / .env）
---------------------
本プロジェクトは .env / .env.local を自動で読み込む（プロジェクトルートが .git または pyproject.toml により特定できる場合）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数：
- KABUSYS_ENV: 起動環境 ("development" / "paper_trading" / "live")。paper_trading 時に発注は MockBroker に切替わり、DB は data/paper_trading.db を使用します。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須となる処理あり）。
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）。
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）。
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）で必要。
- PAPER_FILL_MODE: paper_trading の注文約定動作 ("instant"|"partial"|"never"|"reject")（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等監視関連のパスも環境変数で上書き可能

使い方（代表的な起動・コマンド）
--------------------------------

注意：プロジェクトルートから実行するか、PYTHONPATH に src を含めて実行します。

1) 監視ループ（SystemMonitor 単体実行）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視処理は Settings から指定された sqlite_path（monitoring DB）を使用します。監視は環境にかかわらず本番 sqlite_path を参照します。

2) ExecutionEngine（実際の発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH に保存されます。
   - 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag を作成するか KillSwitch による data/kill.flag で制御されます。

3) Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite DB を開き、Overview / Positions / Orders / System タブを表示します。

4) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD（開始日）
     - --to YYYY-MM-DD（終了日）
     - --db PATH（SQLite パス、環境変数 PAPER_TRADING_SQLITE_PATH より優先して指定可能）
   - 出力: 稼働率、注文成功率、送信率、レイテンシなどのサマリと PASS/FAIL 判定

5) AI 機能（プログラム内 API）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（raw_news, news_symbols, ai_scores テーブル）を渡してニューススコアを生成・書き込みします。
     - api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF 1321 の MA200 乖離 + マクロニュース LLM 評価を合成し market_regime テーブルへ書き込みます。

停止 / 強制停止フロー
--------------------
- 実行エンジンの通常停止: data/stop_requested.flag を作成すると run_execution が検出して停止します（run_monitoring も同様のフラグを監視）。
- KillSwitch: リスクしきい値（ドローダウンなど）に到達した場合、data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（冪等・再書き込みは行いません）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと、起動時に kill.flag をクリアできます（Settings.kill_flag_clear_on_start を参照）。

注意事項 / 実装上のポイント
-----------------------
- Settings は .env/.env.local を自動ロードします（OS 環境変数は保護され上書きされません）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- Monitoring の DB 初期化は init_monitoring_db()（冪等）で行われ、必要に応じてマイグレーション（カラム追加）を行います。
- 実行開始直後にプロセス優先度を set_process_priority("high") で上げる試みを行います（psutil を使用。アクセス権がない場合は警告を出してスキップ）。
- OpenAI 呼び出しはレート制限・ネットワークエラー・5xx に対して指数バックオフでリトライする設計です。失敗時は安全にフォールバック（空スコアや macro_sentiment=0.0）します。
- DuckDB を内部で用いているため、factor/research 系は高速なカラム型分析に適しています。
- Paper Trading と本番 DB は分離されるよう設計されています（KABUSYS_ENV に依存）。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数/Settings の管理（.env 自動読み込み）
- run_monitoring.py              — SystemMonitor のポーリング起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト（paper_trading モード対応）
- tools/
  - paper_verification_report.py  — Paper Trading の検証レポート生成 CLI
- ai/
  - news_nlp.py                   — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py            — レジーム判定（ETF + マクロニュース）
- monitoring/
  - monitoring_db.py              — SQLite 永続化層（テーブル初期化・CRUD）
  - system_monitor.py             — CPU/プロセス/データ鮮度監視
  - trade_monitor.py              — 滞留注文・約定異常監視
  - risk_monitor.py               — ドローダウン/ポジション上限監視
  - kill_switch.py                — kill.flag 書込みロジック
  - alert_manager.py              — LINE 通知ラッパ（送信クールダウン）
  - monitoring_engine.py          — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py        — Streamlit ダッシュボード
- execution/
  - order_manager.py              — OrderManager（状態遷移 / 重複チェック）
  - reconciler.py                 — 起動時リコンシリエーション
  - ...（Broker / Engine / Repository 等の実装が存在）
- portfolio/
  - portfolio_builder.py          — 候補選定・スコア順ソート
  - position_sizing.py            — 株数計算 / aggregate cap
  - risk_adjustment.py            — セクターキャップ / レジーム乗数
- research/
  - factor_research.py            — ファクター計算（momentum/value/volatility）
  - feature_exploration.py        — フォワードリターン / IC / 統計
- utils/
  - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
- data/（実行時に生成される想定の格納先）
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)

補足（ログ・DB）
----------------
- ログは基本的に logging.basicConfig(level=logging.INFO) で INFO レベル以上が標準出力に出ます。LOG_LEVEL は Settings.log_level で制御可能（環境変数 LOG_LEVEL）。
- Monitoring の DB（デフォルト data/monitoring.db）に監視履歴やトレードログ、ダッシュボード集計が保存されます。init_monitoring_db() は起動時に必要なテーブルを作成します。

貢献 / テスト
--------------
- 各モジュールはできるだけ純粋関数や副作用を最小化するよう分離されています。ユニットテストを追加する際は外部依存（OpenAI / Broker / DB）をモックしてテストしてください。
- OpenAI 呼び出し部分はテスト用に _call_openai_api を patch することが容易になる実装になっています。

お問い合わせ
--------------
実装に関する質問やドキュメント補足の要望があれば教えてください。README の改善点（例: 具体的な依存関係ファイル、サンプル .env.example の追加など）も歓迎します。