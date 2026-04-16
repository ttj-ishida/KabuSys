KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。市場データ処理（DuckDB）、ポートフォリオ構築、発注管理、監視（SQLite ベース）、
LLM を用いたニュースセンチメント評価（OpenAI）などの機能を含みます。実行用のエンジン起動スクリプトと監視用コンポーネントが同梱されており、
paper trading（検証）環境と本番を分離して運用できる設計になっています。

主な機能
--------
- 設定管理
  - Settings クラスで環境変数 / .env(.env.local) を読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
  - KABUSYS_ENV: development / paper_trading / live をサポート。
- Execution（発注実行）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler による発注・再同期ロジック
  - paper_trading 環境では MockBroker を使用し DB を完全分離（PAPER_TRADING_SQLITE_PATH）
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - 監視ログ永続化（SQLite）用モジュール monitoring_db
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- 研究・リサーチ
  - ファクター計算（momentum / volatility / value 等） — DuckDB 経由
  - 特徴量探索（forward returns, IC 計算 等）
- AI (LLM) 関連
  - ニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector） — MA200 とマクロニュースを合成
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクター制限、ポジションサイズ計算（単元調整、aggregate cap）

セットアップ
-----------
1. Python と依存パッケージ
   - 推奨: Python 3.9+
   - 必要な主要パッケージ（プロジェクトの用途に応じて）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例（pip で一括インストールする場合）:
     pip install duckdb psutil requests openai streamlit

2. プロジェクトルートと .env
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。
   - 環境変数は OS 環境変数 → .env.local → .env の順で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI を利用する場合に必要
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - 省略時は多くのパスが data/ 以下のデフォルトにフォールバックします（下記参照）。

4. 主要パスのデフォルト
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - PID_FILE_PATH: data/execution.pid
   - KILL_FLAG_PATH: data/kill.flag

簡単な .env の例
-----------------
（実際のシークレットは .env をバージョン管理しないでください）
例:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=paper_trading
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
MONITOR_POLL_INTERVAL=60

使い方
------
- 監視ループの起動（本機能はデフォルトで本番 sqlite_path を使用）
  - モジュール実行:
    python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    export MONITOR_POLL_INTERVAL=30

  run_monitoring の挙動:
    - プロセス優先度を "high" に設定しようとします（psutil を使用、権限がない場合は警告）。
    - data/stop_requested.flag が作成されるとループを終了します。

- ExecutionEngine（発注エンジン）起動
  - コマンド:
    python -m kabusys.run_execution
  - KABUSYS_ENV によって以下の挙動が変わります:
    - paper_trading: MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存
    - live: 本番 DB（SQLITE_PATH）を使用
  - 停止制御:
    - 起動前 / 起動中に data/stop_requested.flag が存在するとエンジンは起動しない / 停止します。
    - 実行中は data/execution.pid に PID を書きます。

- Streamlit ダッシュボード（監視 UI）
  - コマンド:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開きます。MonitoringEngine を先に動かしてデータを作成してください。

- Paper Trading 検証レポート生成ツール
  - コマンド例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 集計に使うデフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- AI（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY が必要（引数で渡すことも可能）。
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 両モジュールは OpenAI のレスポンスを厳密に検証し、失敗時はフェイルセーフ（0.0 等）で続行します。

運用上のポイント
----------------
- stop / kill フラグ
  - 停止ループ用: data/stop_requested.flag（存在すれば run_monitoring / run_execution が停止）
  - 強制停止候補: data/kill.flag（KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る）
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルやカラムを作成・追加します（起動スクリプトで自動実行）。
- プロセス優先度
  - set_process_priority("high") を呼びます。psutil の権限不足で設定できない場合は警告を出して続行します。
- Paper Trading の動作
  - PAPER_FILL_MODE で注文約定挙動を制御できます（instant / partial / never / reject）。
  - paper_trading 環境では本番 DB に影響しないよう専用 SQLite を使用します。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py                — パッケージ定義（バージョンなど）
- config.py                  — 環境変数 / .env 読み込みと Settings
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py          — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- trade_monitor.py           — 滞留注文・約定異常チェック
- risk_monitor.py            — ドローダウン、ポジション数監視
- kill_switch.py             — kill.flag の作成/評価
- alert_manager.py           — LINE へ通知（push）
- monitoring_engine.py       — 各 Monitor の統合ポーリング
- streamlit_dashboard.py     — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py           — 発注の高レベル API（重複防止・state machine 管理）
- reconciler.py              — 起動時の再同期（OrderSent の突合、ポジション整合性チェック）
- その他: broker_* / engine / order_repository 等（発注周りの実装）

src/kabusys/portfolio/
- portfolio_builder.py       — 候補選定・重み（等重・スコア重み）
- position_sizing.py         — 株数計算、aggregate cap、単元丸め
- risk_adjustment.py         — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py         — momentum / volatility / value 等のファクター計算（DuckDB）
- feature_exploration.py     — forward returns, IC, 統計サマリー 等

src/kabusys/ai/
- news_nlp.py                — ニュースセンチメント（OpenAI）→ ai_scores 書き込み
- regime_detector.py         — マクロセンチメント + MA200 合成によるレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート出力ツール

備考・開発メモ
--------------
- DuckDB 接続を受け取る設計のため、テストやオフライン分析が容易です。
- LLM 呼び出し部分はリトライ/エラー処理を備えていますが、API キーや課金に注意してください。
- 実行環境で PID ファイルや flag ファイルを利用するため、data/ 以下の書き込み権限が必要です。
- ログは logging を利用しており、Settings.log_level を参照する設計になっています。

質問・拡張
----------
- 追加したい機能、CI/デプロイ手順、パッケージ化（setup/pyproject）やユニットテストの整備などの相談があればお知らせください。README を用途（開発者向け / 運用向け）に合わせて拡張できます。