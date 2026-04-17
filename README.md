KabuSys — 日本株自動売買（ライブラリ / 実行 / 監視）  
README（日本語）

概要
- KabuSys は日本株向けの自動売買 / 監視 / 研究ツール群です。取引エンジン（ExecutionEngine）、監視 (Monitoring) コンポーネント、ポートフォリオ構築・リスク計算、研究用ファクター計算、ニュース NLP（OpenAI）連携などの機能を含みます。
- 設計方針として、本番と paper_trading（検証）を分離する仕組み、DuckDB を使った履歴・ファクター計算、SQLite を使った監視ログ永続化、外部 API 呼び出しのフェイルセーフ化（バックオフ等）などが組み込まれています。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理（OrderManager）、リポジトリ（OrderRepository）、リコンシリエーション（Reconciler）、リスク管理（RiskManager）
  - live / paper_trading の分離（paper_trading は専用 SQLite を使用）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - MonitoringEngine（監視ポーリングの集約）
  - 監視ログ永続化（SQLite via monitoring_db）
  - アラート（LINE push）送信（AlertManager）
  - KillSwitch（条件に応じて停止フラグを書き出し ExecutionEngine を停止）
  - Streamlit ダッシュボードでの可視化（streamlit_dashboard.py）
- Portfolio（銘柄選定 / 重み付け / 衝突回避 / 株数決定）
  - select_candidates / calc_equal_weights / calc_score_weights
  - apply_sector_cap / calc_regime_multiplier
  - calc_position_sizes（リスクベースや等配分等）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
  - DuckDB 経由で prices_daily / raw_financials を参照
- AI
  - ニュースのセンチメントスコアリング（OpenAI: gpt-4o-mini を想定）
  - 市場レジーム判定（ETF ma200 乖離 + マクロニュース LLM センチメント）
  - API のリトライ・バリデーション・部分書き込みで頑健に動作
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等を集計）

セットアップ（ローカル実行向け）
1. 必要な Python バージョン
   - Python 3.10 以上を推奨（| 型注釈などを使用）

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit（ダッシュボード使用時）
   - sqlite3 は標準ライブラリ
   例（pip）:
     pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt がある場合はそちらを使用してください。

3. プロジェクトルートに .env を配置（自動ロード）
   - .env/.env.local を使って環境変数を定義できます（読み込みは自動、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 代表的な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — environment: development | paper_trading | live（デフォルト development）
     - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - その他監視閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

4. データディレクトリ
   - デフォルトでは data/ 以下に DB・PID・フラグファイル等を作成します。必要に応じてディレクトリを作成してください（実行時に自動で mkdir される箇所もありますが、権限に注意）。

使い方（主要コマンド例）
- 監視ループを起動（デフォルトポーリング 60秒、MONITOR_POLL_INTERVAL で上書き可能）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  注意: run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」実装になっています（監視は本番 DB に対して行う想定）。

- 実行エンジンを起動（paper_trading モードの例）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。

- Streamlit ダッシュボード起動（監視 DB を参照、読み取り専用推奨）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または各関数の api_key 引数）。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用して実行できます。

運用上のポイント / 環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
  - run_execution は is_paper を判定して paper_sqlite_path を使用。
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- PID / stop / kill フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（run_monitoring/run_execution が起動終了を判断するためのフラグ）
  - data/kill.flag（KillSwitch が書き込むと ExecutionEngine に停止シグナルを与える）
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を順に読み込みます。
  - OS 環境変数は上書きされません（ただし .env.local は override=True で上書きする挙動）。

ディレクトリ構成（主要ファイル/フォルダ）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — Settings クラス（環境変数の読み込み / バリデーション）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - execution_engine.py (起動ロジック、Session 実行)
    - broker_factory.py, broker_api.py (ブローカー抽象化)
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py, order_repository.py, order_manager.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成 / 永続化 API
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ書込み
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor の統合ポーリング
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補抽出・重み付け
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / サマリー
  - ai/
    - news_nlp.py — ニュースを集約して OpenAI でスコアリング、ai_scores へ書込
    - regime_detector.py — ETF ma200 + マクロニュースでレジーム判定
  - data/ （実行時に利用する既定の場所）
    - monitoring.db（SQLite, 監視ログ）
    - paper_trading.db（paper_trading 用 DB）
    - kabusys.duckdb（DuckDB）
    - stop_requested.flag, kill.flag, execution.pid 等

テスト / 開発メモ
- 多くのモジュールは純粋関数または外部依存を引数で受け取る設計（DuckDB 接続 / sqlite3.Connection / ブローカークライアント等）なのでユニットテストが書きやすい設計になっています。外部 API 呼び出しは差し替え可能（例: _call_openai_api のパッチ）。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境変数をセットアップすることを推奨します。

運用上の注意
- OpenAI やブローカー API の呼び出しは失敗することを前提とした実装（リトライ、フォールバック）ですが、API キーやレート制限には十分注意してください。
- run_monitoring は監視対象 DB を書き換えるため、テスト環境と本番環境の DB を明確に分けてください。run_execution は paper_trading で DB を分離できますが、監視はデフォルトで本番 sqlite_path を参照する点に留意してください。
- プロセス優先度設定や CPU affinity は psutil を介して設定します。権限のない環境では警告が出てスキップされます。

さらに知りたいこと / カスタマイズ
- 実際のブローカー実装（BrokerClient）の差し替え方法、ExecutionEngine の設定（EngineConfig）、RiskManager の閾値調整、streamlit ダッシュボードのカスタマイズなど、特定の箇所について詳細が必要であれば教えてください。具体的な利用ケースに合わせた設定例やデプロイ手順（systemd / Docker / コンテナ運用）も案内できます。

以上。必要であれば README を Markdown ファイルとして出力したり、環境変数の .env.example を作成するテンプレートも用意します。どちらをご希望ですか？