KabuSys — 日本株自動売買システム
=============================

以下はこのリポジトリ（src/kabusys 以下）の概要と使い方ドキュメントです。  
本READMEは実装された主要モジュール・起動スクリプト・環境変数・セットアップ手順等をまとめたものです。

プロジェクト概要
----------------
KabuSys は日本株自動売買のためのモジュール群を集めたコードベースです。主な機能は以下を含みます。

- 発注/状態管理（OrderManager, OrderRepository 等）
- 実行エンジン（ExecutionEngine 起動スクリプト）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- モニタリング用ダッシュボード（Streamlit）
- ポートフォリオ構築・配分・サイズ計算（portfolio パッケージ）
- リサーチ（ファクター計算、特徴量探索）
- AI補助（ニュースセンチメント解析、レジーム判定）— OpenAI を利用
- Paper Trading 用の分離された DB / モックブローカー
- 各種ユーティリティ（設定読み込み、プロセス優先度設定 等）
- 検証レポート生成ツール（paper_verification_report）

主な特徴・設計方針
- DuckDB をデータ分析用 DB として使用（prices_daily, raw_financials 等を想定）
- 監視ログや取引ログは SQLite（data/monitoring.db / data/paper_trading.db）に永続化
- Paper Trading モードでは本番 DB と分離し安全に検証可能
- AI モジュールは外部 API 呼び出し（OpenAI）を行うが、呼び出し失敗時は安全にフォールバックする設計
- 自動 .env 読み込み（プロジェクトルートにある .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

機能一覧
--------
- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（実際の発注フローを行う）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定）
- 監視
  - SystemMonitor: CPU/メモリ/Disk/プロセス PID/file の監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新とリスクログ記録
  - MonitoringEngine: 各 Monitor をまとめて定期実行、KillSwitch 評価、Alert 発行
  - AlertManager: LINE Messaging API による通知（トークン未設定時はログのみ）
  - streamlit_dashboard.py: Streamlit を使った監視ダッシュボード
- Execution（発注系）
  - OrderManager, OrderRepository, Reconciler（起動時の自動復旧）
  - BrokerClientFactory（Paper/Live の差分を吸収）
- Portfolio（銘柄選定・配分・サイズ計算）
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes（単元株丸め・リスクベース配分・スケールダウン）
- Research（ファクター計算・特徴量解析）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- AI（OpenAI を用いた機能）
  - news_nlp.score_news: ニュースのセンチメント解析 → ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースの合成でレジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して検証レポートを出力

必須 / 主要な環境変数
--------------------
（Settings クラスで参照されるもの、.env に設定する想定）

必須（少なくとも実運用で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）で必要
- PAPER_FILL_MODE — paper_trading の執行モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1"で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（%）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（"1"）

注意: 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。

セットアップ手順
--------------
1. Python 環境
   - Python 3.9+ を想定（プロジェクト固有の要件があれば pyproject.toml を参照）
   - 仮想環境を作成して有効化することを推奨

2. 依存ライブラリ（代表的なもの）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （sqlite3 は標準ライブラリ）
   - インストール例:
     pip install duckdb psutil requests openai streamlit

3. データディレクトリの準備
   - data/ を作成（デフォルトでは data/kabusys.duckdb, data/monitoring.db 等を使用）
     mkdir -p data

4. .env の用意（任意）
   - リポジトリルートに .env を置くと自動で読み込まれます（.env.example を参照）
   - 例:
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

5. DB 初期化
   - 監視用 SQLite は起動スクリプト内で init_monitoring_db が呼ばれて自動で初期化されます。
   - DuckDB のテーブル（prices_daily, raw_financials など）はデータ投入プロセスに依存します。

使い方
------

起動スクリプト
- 実行エンジン（発注）
  - 本番または paper_trading の ExecutionEngine を起動:
    - KABUSYS_ENV を適切に設定（例: export KABUSYS_ENV=paper_trading）
    - python -m kabusys.run_execution
  - paper_trading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。

- 監視ループ
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しません）。

- Streamlit ダッシュボード（監視の可視化）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザでダッシュボードが開き、Positions / Orders / System / Overview を確認できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD  （開始日）
    --to   YYYY-MM-DD  （終了日）
    --db PATH          （SQLite DB ファイルパス、環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - 検証指標（閾値）はスクリプト内に定義（稼働率、注文成功率、送信率、P95 レイテンシ等）されています。

AI 関連
- news_nlp.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（api_key 引数で上書き可）
  - raw_news と news_symbols を集計し、gpt-4o-mini を用いて銘柄ごとのセンチメントを ai_scores に書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA 乖離とマクロニュースを合わせて市場レジーム（bull/neutral/bear）を算出・保存します。
- API 呼び出しはレート制限や一時エラーを考慮したリトライが実装されていますが、API キー未設定時は例外が発生します。

運用上の注意
- Execution 起動時にプロセス優先度を "high" に設定する処理が含まれています（set_process_priority）。
  - OS により設定できない場合は警告が出ますが継続します。
- KillSwitch は data/kill.flag を作成して ExecutionEngine 停止シグナルを送ります。必要に応じて KILL_FLAG_CLEAR_ON_START を設定してください。
- 監視ログのスキーマは init_monitoring_db にて冪等に作成され、マイグレーション（列追加）処理も含まれます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py — 環境変数／設定読み込みロジック
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

パッケージ
- execution/
  - order_manager.py
  - order_repository.py (参照される)
  - reconciler.py
  - broker_factory.py (参照される)
  - execution_engine.py (参照される)
  - ...（発注フロー関連）
- monitoring/
  - monitoring_db.py — SQLite の永続化層（テーブル作成・CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- tools/
  - paper_verification_report.py
  - __init__.py
- utils/
  - process_priority.py
  - __init__.py

補足（開発者向け）
- .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env を上書きする仕様です。
- ログ出力は標準 logging を使用（Settings.log_level を参照）
- DuckDB 接続は research/ai モジュール等で直接 SQL を発行する設計です（prices_daily / raw_financials 等のテーブルを想定）

問い合わせ / 開発メモ
- 各モジュール内に詳細な docstring / コメントがあるため、機能や引数の仕様はそちらを参照してください。
- AI 呼び出し部（news_nlp, regime_detector）はテスト時に _call_openai_api をモックすることを想定して設計されています。

以上がこのコードベースの概要と基本的な使い方です。実運用前に .env と DB の状態、OpenAI キー、kabu API 設定等を必ず確認してください。必要であれば README に追記する項目（依存パッケージ厳密版、テスト方法、CI 設定等）を指示してください。