README
======

概要
----
KabuSys は日本株向けの自動売買および運用支援ライブラリです。本リポジトリは以下の主要機能群を提供します。

- 注文発行・状態管理（ExecutionEngine / OrderManager / BrokerClientFactory）
- 発注・約定のリコンシリエーション（Reconciler）
- 監視機構（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視ダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ／ファクター計算（DuckDB を用いたファクター群）
- ニュースに基づく AI スコアリング（OpenAI を用いたセンチメント評価）
- Paper Trading 用の検証レポート生成スクリプト

主な機能
--------
- モニタリング
  - CPU / メモリ / ディスク / 実行プロセスの監視
  - 注文滞留・約定価格異常・ドローダウン・ポジション上限の監視
  - アラート（LINE Push）送信（AlertManager）
  - Kill Switch：条件に応じて ExecutionEngine 停止フラグを書き込む
- Execution
  - ブローカークライアント（本番/モック切替）
  - 注文状態管理、重複検知、キャンセル管理
  - 起動時の自動リコンシリエーション（注文照合／ポジション差分検出）
- ポートフォリオ構築
  - 候補選定、等重／スコア重み付け、リスクベースサイズ計算、セクター上限制御、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースを集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に保存
  - マクロニュース + ETF MA200 偏差を合成して市場レジーム（bull/neutral/bear）を判定
- ツール
  - Paper Trading 検証レポート（paper_verification_report）

前提条件 / 依存
---------------
主要な依存パッケージ（抜粋）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai（OpenAI Python SDK; AI 機能を使う場合）
- streamlit（ダッシュボード起動時）
標準ライブラリの sqlite3 を使用します。

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は duckdb, psutil, requests, openai, streamlit などを個別にインストール）

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成してください。
   - 自動ロード: config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（必須 / 省略時デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能使用時に必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定モード（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB のパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパス（デフォルト data 以下）

5. データディレクトリ
   - 監視やフラグファイル等は data/ 以下に保存されます。必要に応じて作成してください。
   - 例: mkdir -p data

使い方（実行例）
----------------

- ExecutionEngine を起動する（本番または paper_trading）
  - 本番:
    - python -m kabusys.run_execution
  - Paper Trading（MockBroker を使用し、data/paper_trading.db に記録）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  補足:
  - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 停止は stopファイルの作成で行います（data/stop_requested.flag を作成すると監視ループ / 実行ループが検知して終了します）。

- Monitoring（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB を参照）

- Streamlit ダッシュボードを起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - または streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db "file:///…?mode=ro" など

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI 関連
  - ニュースに基づくスコア取得:
    - kabusys.ai.news_nlp.score_news を呼ぶ（スクリプトや cron から呼び出し）
    - OPENAI_API_KEY が必要
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を呼ぶ（OPENAI_API_KEY が必要）

停止・フラグ
------------
- 実行の停止（外部から）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution がループ中に検知して安全に終了します。
- Kill Switch（自動停止シグナル）
  - 条件（ドローダウン超過等）を満たすと data/kill.flag（または設定した KILL_FLAG_PATH）へ理由テキストを書き込み、ExecutionEngine を停止させます。
  - KillSwitch.clear() で kill.flag を削除できます（ExecutionEngine 起動時にクリアするオプションが設定可能）。

設定の読み込み動作（config.py について）
---------------------------------------
- .env と .env.local をプロジェクトルートから自動で読み込みます（OS 環境変数が優先されます）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラスで各種設定値（パス・閾値・モード）にアクセスできます。

ロギング
-------
- スクリプトは logging.basicConfig(level=logging.INFO) を用いて INFO レベルで起動します。詳細が必要な場合は LOG_LEVEL を設定してください。

ディレクトリ構成（主要ファイル）
------------------------------

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数／設定読み込みロジック（.env 自動読み込み、Settings）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
    - regime_detector.py — マクロニュース＋ETF MA200 で市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 用監視ログ永続化層（init / MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留／約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — LINE Push 通知送信器
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - reconciler.py — 起動時のリコンシリエーション
    - order_manager.py — 注文作成／状態遷移管理
    - order_repository.py — Orders DB 操作（SQLite）  ※（ファイルの続きは repo 内にあり）
    - order_record.py, broker_factory.py, execution_engine.py, ...（実行ロジック関連）
  - portfolio/
    - portfolio_builder.py — 候補選定／重み付け
    - position_sizing.py — 株数決定ロジック（ロット丸め等）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

補足 / 実運用上の注意
--------------------
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と完全分離して動作することを意図しています（PAPER_TRADING_SQLITE_PATH を使用）。
- Monitoring は設定により本番 DB を監視するため、監視用 DB のバックアップや切り分けに注意してください。
- OpenAI を使う処理は API 料金やレート制限のリスクがあります。API キー管理と呼び出し頻度に注意してください。
- process priority / cpu affinity の変更は権限が必要な場合があります。適切な権限で実行してください（psutil の例外をハンドリングします）。

ライセンス
----------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在しない場合は管理者に確認してください）。

以上。必要があれば、README に詳しい設定例（.env.example）や運用ガイド（サービス化、systemd ユニット、ログローテーション）を追記します。