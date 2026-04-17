KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。シグナル生成、ポートフォリオ構築、発注エンジン、監視（モニタリング）、リスク管理、研究（ファクター計算）や AI ベースのニュースセンチメント評価など、実運用を想定したコンポーネント群を備えています。

主な設計方針
- DuckDB / SQLite を使ったオンディスクデータ管理（分析と監視を分離）
- Paper Trading（擬似発注）と Live（実際発注）を明確に切り分け
- 外部 API（OpenAI 等）呼び出しはフェイルセーフ設計（失敗時は安全側フォールバック）
- 自動化を前提にした監視・Kill Switch 機構を搭載

機能一覧
--------
- Execution Engine
  - 実口座 / ペーパートレードを切り替え可能
  - リスク管理（ポジション上限、drawdown 等）
  - 発注・注文管理（OrderRepository / OrderManager）
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）監視
  - データ鮮度チェック（DuckDB の最終価格日）
  - 注文滞留や約定異常価格の検出
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - LINE 通知（AlertManager）による一方向アラート
- Portfolio
  - 候補選定、等配分・スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - 株数算出（単元株丸め、aggregate cap 処理）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等
- AI
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存
  - 市場レジーム判定（MA200 とマクロニュースの合成）
- ツール
  - .env 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提 / 必要条件
--------------
- Python 3.9+（型注釈に依存）
- 推奨（最低限インストールが必要なライブラリ）:
  - duckdb
  - psutil
  - requests
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML を使う場合）
- OS: Linux / macOS / Windows（process priority 等で差異あり）

（依存関係はプロジェクトの requirements.txt / pyproject.toml に合わせてインストールしてください）

セットアップ手順
----------------
1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
     （存在しない場合は上記必須パッケージを個別に pip install）
4. 環境変数の作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（ファイルは絶対に Git にコミットしないこと）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL にしたい場合:
     - python -m kabusys.validate_config --strict
6. データディレクトリ
   - デフォルトの DB 等は data/ に作成されます:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
   - 手動で data/ ディレクトリに書き込み権限があることを確認してください

環境変数（主なもの）
-------------------
Settings クラスで定義される主な環境変数（.env で設定）:

必須
- JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

オプション／重要
- KABUSYS_ENV           : 実行環境（development | paper_trading | live）デフォルト: development
  - paper_trading の場合、発注は MockBroker に対して行われ、DB は data/paper_trading.db に分離されます
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE       : ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY        : OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知用（未設定だと通知はスキップ）
- KILL_FLAG_CLEAR_ON_START : Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔秒数（デフォルト 60）

注意点
- run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を参照します（監視用 DB は環境に依存しない運用を想定）
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します
- 停止制御: data/stop_requested.flag（スクリプト内で参照）や data/kill.flag（KillSwitch により作成）を用います

基本的な使い方
--------------

1) .env を作成・編集
- 対話式:
  - python -m kabusys.config_setup
- 作成後、検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

2) 監視ループの起動（Monitoring）
- デフォルトでは MONITOR_POLL_INTERVAL=60 秒でポーリング
- 起動コマンド:
  - python -m kabusys.run_monitoring
- 停止手順:
  - data/stop_requested.flag を作成するとループが検知して終了します
  - または Ctrl+C（KeyboardInterrupt）

3) 実行エンジンの起動（Execution）
- ペーパートレードモードで起動するには KABUSYS_ENV=paper_trading を設定
- 起動コマンド:
  - python -m kabusys.run_execution
- 実行中、data/stop_requested.flag または data/kill.flag の検出で停止処理が行われます
- 実行時は Engine がバックグラウンドスレッドで run_session を回し、PID ファイル（data/execution.pid 等）を利用して状態確認を行います

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI モジュール（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）
- モジュール API を直接呼び出し:
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1), api_key="...")

運用上の補足
-------------
- 監視（Monitoring）側は監視 DB（SQLite）に system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを作成・管理します。初回起動時に自動でテーブル・インデックスを生成します（冪等）。
- Kill Switch は RiskMonitor の結果（ドローダウンやポジション数超過）により data/kill.flag を書き込み、Execution 側がそれを検出して安全停止します。
- process priority（優先度）は起動時に set_process_priority("high") を試みます（psutil による OS 操作、権限不足時は警告でスキップ）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数読み込み / Settings
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主要）
- execution/                   — Execution エンジン関連（broker, order_manager, risk_manager 等）
- monitoring/
  - monitoring_db.py           — SQLite 永続化層（テーブル作成 / MonitoringDB クラス）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                — ニュースセンチメント評価（OpenAI）
  - regime_detector.py         — レジーム判定（MA200 + マクロセンチ）
- utils/
  - process_priority.py        — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

監視 DB（monitoring.db）スキーマ（概略）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1固定行で集計情報: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

トラブルシューティング / よくある注意
-------------------------------------
- .env の自動ロードはルート検出（.git か pyproject.toml）を行います。テストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / 外部 API を使う処理はネットワークエラーやレート制限を考慮したリトライ設計になっていますが、APIキー未設定時は例外やフェイルセーフ値（0.0）を返す実装のため安全に継続できます。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアを有効にすると Kill Switch の保護が弱まる可能性があります。
- モニタリングのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます。1 以上の整数を設定してください（0 や負値は無効でデフォルトに戻る）。

最後に
------
この README はコードベースの主要機能と運用方法をまとめたものです。詳細な設計やアルゴリズムはソースコード内の docstring / コメントに記載されています。実運用の前には必ず設定検証と Paper Trading による検証を行ってください。必要であれば README に追記したい点（例: 追加の CLI、デプロイ手順、CI 設定など）を教えてください。