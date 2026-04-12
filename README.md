KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向け自動売買エンジン（KabuSys）のコアライブラリ群です。
バックエンドの実行／監視、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価などのコンポーネントを含みます。

以下ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

プロジェクト概要
--------------
KabuSys は以下を主要機能とする自動売買基盤です。

- ExecutionEngine：ブローカーと連携して注文を発行・管理（本番・ペーパー両対応）
- MonitoringEngine：システム状態 / 注文滞留 / ドローダウン等を定期監視しログ化・アラート送信
- Portfolio construction：銘柄選定・重み付け・株数決定ロジック（純粋関数）
- Research：DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI モジュール：OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ユーティリティ：プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成 等

設計方針の一部：
- DuckDB / SQLite をローカル DB に使用（データ解析用に DuckDB、監視ログに SQLite）
- 本番 DB とペーパー口座は分離（KABUSYS_ENV により behavior が切替）
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフで実装（失敗時はスキップ or 中立値）

主な機能一覧
-------------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker を選択）
  - Reconciler：起動時の注文/ポジション突合（自動リカバリ）
  - OrderManager / OrderRepository：注文状態管理・永続化

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - MonitoringEngine: System / Trade / Risk の統合ポーリングとアラート発行
  - MonitoringDB: SQLite に監視ログ・トレードログ・リスクログ等を保持
  - streamlit_dashboard.py: Streamlit による監視ダッシュボード
  - KillSwitch: 条件により ExecutionEngine 停止フラグ（data/kill.flag）を書き込む

- ポートフォリオ構築
  - portfolio_builder: 候補選定・重み計算
  - risk_adjustment: セクターキャップ、レジーム乗数
  - position_sizing: 株数決定・投下資金スケール調整

- リサーチ / ファクター計算
  - research.calc_momentum / calc_volatility / calc_value
  - feature_exploration: 将来リターン計算、IC 計算、統計要約

- AI（OpenAI）
  - ai.news_nlp.score_news: ニュースを LLM でスコア化して ai_scores テーブルへ書き込み
  - ai.regime_detector.score_regime: ETF の MA とマクロニュースを組合せて日次レジーム判定

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------

1. Python 環境
   - 本リポジトリは Python 3.10+ を想定しています（型ヒントに | を使用）。
   - 仮想環境を作成してアクティベートすることを推奨します。

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows (PowerShell 等)
   ```

2. 必要パッケージのインストール（目安）
   - 実行／監視／AI／ダッシュボードに必要な主要パッケージ:
     - duckdb, psutil, requests, openai, streamlit
   - インストール例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - 実運用では requirements.txt を用意して pip install -r requirements.txt することを推奨します。

3. データディレクトリ準備
   - デフォルトでは data/ に各 DB や pid/flag ファイルが置かれます。存在しない場合は作成してください。
   ```
   mkdir -p data
   ```

4. 環境変数設定
   - .env / .env.local に環境変数を置くことができます（config.py が自動でルートの .env を読み込みます）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（主なもの）
- 必須（使用する機能により必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（使用時）
  - KABU_API_PASSWORD — kabuステーション API パスワード（ブローカー連携時）
- 実行環境切替
  - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
    - paper_trading の場合は MockBrokerClient を使い、SQLite DB: data/paper_trading.db を使用
- DB 関連
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- AI / 通知
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで必要）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（AlertManager）
  - LINE_USER_ID — LINE Push 先ユーザ ID
- 実行/監視
  - PID_FILE_PATH — ExecutionEngine 用 pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- Paper Trading 設定
  - PAPER_FILL_MODE — MockBroker の約定モード ("instant" | "partial" | "never" | "reject")

使用方法
--------

1. 監視ループを起動（Monitoring）
   - run_monitoring.py は SystemMonitor をポーリングします。
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を指定できます（デフォルト 60）。
   - 実行:
   ```
   python -m kabusys.run_monitoring
   ```
   - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依らず）。

2. 実行エンジンを起動（ExecutionEngine）
   - run_execution.py は ExecutionEngine を組み立てて取引セッションを開始します。
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB に記録されます。
   - 実行:
   ```
   python -m kabusys.run_execution
   ```
   - 起動時にプロセス優先度が High に設定されます（set_process_priority）。

3. Streamlit ダッシュボード（監視 UI）
   - 監視 DB を read-only で開いてダッシュボードを表示します。
   - 実行:
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

4. Paper Trading 検証レポート
   - tools.paper_verification_report により期間指定で検証レポートを生成できます。
   - 実行例:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - DB パスを明示する場合:
   ```
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

5. AI スコアリング / レジーム判定（プログラム的利用）
   - ai.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーを受け取ります。
   - 例（Python REPL / スクリプト内）:
   ```
   import duckdb
   from datetime import date
   from kabusys.ai import score_news
   conn = duckdb.connect("data/kabusys.duckdb")
   score_news(conn, date(2026,4,11), api_key="sk-...")
   ```

注意事項・安全設計
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 SQLite と分離されます（PAPER_TRADING_SQLITE_PATH）。
- KillSwitch は条件を満たすと data/kill.flag を作成し ExecutionEngine に停止を促します。ExecutionEngine 側は flag を監視している設計が期待されます。
- OpenAI の呼び出しはリトライやパース失敗に対してフェイルセーフになっています（失敗時は中立値 or スキップ）。
- config.py はプロジェクトルートの .env / .env.local を自動で読み込みます。OS 環境変数の上書きを防ぐ保護機構があります。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
-----------------
（src/kabusys 以下を想定した主要ファイル / モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - data/                          — （別モジュール）DuckDB / データパイプライン関連
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...（ブローカー抽象等）
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ定義・CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

補足：主要ファイルの役割（抜粋）
- config.py: .env 自動ロード、Settings クラスで環境変数を型付きで参照
- monitoring/monitoring_db.py: 監視用 SQLite のテーブル初期化・読み書きユーティリティ
- monitoring/system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度チェック
- monitoring/trade_monitor.py: 滞留注文・約定異常検出
- monitoring/risk_monitor.py: ドローダウン・ポジション上限監視（ダッシュボードへの書き込み／リスクログ）
- ai/news_nlp.py: raw_news を LLM に渡して銘柄ごとの ai_score を ai_scores テーブルへ書き込み
- ai/regime_detector.py: ETF の MA200 とマクロニュースの LLM スコアを合成して market_regime を算出
- portfolio/*: ポートフォリオ構築に関する純粋関数群（DB 参照なし）

開発上のヒント
- DuckDB/SQLite のファイルパスは Settings で管理されています。テスト時は別ファイルを指定して隔離してください。
- Settings はプロジェクトルートの .env/.env.local を自動読み込みします。テストで自動読み込みを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- AI 呼び出し部分はテストで差し替えやすいように _call_openai_api をモック可能に設計しています。

ライセンス・貢献
----------------
- 本リポジトリのライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本 README には含まれていません）。

以上がプロジェクトの概要と基本的な使い方です。必要であれば、README に含めるコマンド例（systemd ユニット例、Dockerfile、CI 設定等）や、より詳細な環境変数一覧・.env.example を追加します。どの情報を追加したいか教えてください。