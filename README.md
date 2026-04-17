KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買システムのコアモジュール群です。本リポジトリは取引実行・監視・ポートフォリオ構築・ファクターリサーチ・AI（ニュースセンチメント／レジーム検出）など、運用に必要な純粋関数群と運用スクリプトを提供します。  
コードは SQLite（監視用）と DuckDB（時系列・ファクタ計算用）にデータを保存・参照します。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - live / paper_trading / development の環境をサポート
  - paper_trading 時は MockBrokerClient を使用し、専用の DB に記録（本番 DB と分離）
- 監視ポーリング（run_monitoring.py）
  - CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック、監視ログ永続化
  - KillSwitch（ドローダウンやポジション上限超過で停止フラグを書き込み）、LINE 通知によるアラート
- 監視 DB 永続化レイヤ（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを冪等に初期化
- モニタリングコンポーネント群
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch
- ポートフォリオ構築ユーティリティ（純粋関数）
  - 候補選定、等重・スコア重み配分、セクター上限適用、レジーム乗数、株数算出（単元丸め）
- 研究用モジュール（DuckDB 経由）
  - ファクター計算（momentum / value / volatility）、将来リターン、IC 計算、統計サマリ
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores へ書き込み）
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の稼働・注文成功率・レイテンシ等の検証レポート出力
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

前提・依存
-----------
主に以下の依存パッケージが必要です（バージョンは適宜調整してください）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai (AI 機能を使う場合)
- streamlit (ダッシュボードを使う場合)

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成して有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install -r requirements.txt
   （requirements.txt が無い場合は上の依存を個別に pip install してください）

3. data ディレクトリを作成:
   - mkdir -p data

4. 環境変数を設定:
   - プロジェクトルートの .env/.env.local を用意すると自動で読み込まれます（config.py の自動ロード）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必要に応じて）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（実行時必須）
     - OPENAI_API_KEY: OpenAI を利用する場合に必須
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
     - KILL_FLAG_PATH: KillSwitch が書き込む flag ファイル（デフォルト data/kill.flag）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: paper_trading 時の fill モード（instant / partial / never / reject）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   - 簡単な .env 例:
     KABUSYS_ENV=development
     KABU_API_PASSWORD=your_password
     OPENAI_API_KEY=sk-xxxxx

5. DB 初期化:
   - run_monitoring や run_execution の起動時に monitoring DB のテーブルは自動で作成されます（init_monitoring_db）。DuckDB のテーブル（prices_daily 等）は別途 ETL スクリプト等で準備してください。

使い方（実行コマンド例）
----------------------

- 監視ループ（ローカルで常時稼働させる場合）
  - python -m kabusys.run_monitoring
  - 動作: Settings で指定した sqlite_path（監視 DB）に接続し、SystemMonitor.check_once() をポーリング。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 停止方法: data/stop_requested.flag ファイルを作成すると graceful にループを終了します（run_monitoring と run_execution 両方がこのファイルを監視します）。

- 実行エンジン（Execution）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Settings.paper_sqlite_path（デフォルト data/paper_trading.db）に書き込みます（本番 DB と分離）。
  - エンジンは開始時に data/execution.pid を書き、停止時に削除します。外部から停止するには data/kill.flag を作成する（KillSwitch が書くのと同じ効果）か、run_execution を停止してください。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブで可視化します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先して適用）。

- AI モジュールの利用
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡すことで ai_scores テーブルに結果を書き込みます。api_key を未指定の場合は OPENAI_API_KEY 環境変数を使用します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込みます。
  - 注意: OpenAI API 呼び出しはネットワーク・課金が発生するため、API キーと利用制限に注意してください。

フラグ・停止機構
----------------
- data/stop_requested.flag
  - run_monitoring と run_execution が周期的に存在をチェックし、あれば安全に終了します（手動で作成してプロセスを停止できます）。
- data/kill.flag
  - KillSwitch が特定のリスク条件（ドローダウン超過・ポジション上限超過など）を検出した際に書き込み、ExecutionEngine に停止を促します。Execution 起動時に Settings.kill_flag_clear_on_start が "1" の場合は起動時に自動でクリアする等の挙動を制御できます（設定を確認してください）。

設定管理
--------
- config.Settings クラスにより環境変数を統合管理します。
- .env / .env.local がプロジェクトルートに存在すれば自動で読み込まれます（OS 環境変数が優先され、.env.local は .env を上書きします）。
- KABUSYS_ENV の有効値: development, paper_trading, live

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / Settings 管理
- run_monitoring.py — 監視ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM センチメントスコアリング
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — 監視 DB（テーブル定義・永続化 API）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション数監視（KillSwitch トリガ）
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE への通知送信
  - monitoring_engine.py — 各モニタを束ねるループ / run_once 用
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - （その他: broker_factory, execution_engine, order_repository 等）
- portfolio/
  - portfolio_builder.py — 候補選定／重み計算
  - position_sizing.py — 株数算出／制限適用
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

開発メモ / 注意事項
-------------------
- process priority / cpu affinity は psutil 経由で設定します。権限不足（Linux の負の nice 値や Windows の特権）があると設定に失敗することがありますが、警告を出してスキップします。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB に対する軽微なマイグレーション（カラム追加）も行います。
- DuckDB を用いる研究・AI モジュールは時系列テーブル（prices_daily, raw_financials, raw_news 等）を前提としています。ETL によりこれらのテーブルを構築して利用してください。
- OpenAI 呼び出しは一時エラーに対して指数バックオフでリトライする実装です。API レスポンスのバリデーションや値クリップ（±1.0）などの安全措置を実装済みです。
- Paper Trading モードは本番口座から完全に分離して動作するよう設計されています。実行前に KABUSYS_ENV を確認してください。

トラブルシューティング（よくある事例）
---------------------------------------
- 「PID ファイルが stale になっている」「プロセスが起動しない」:
  - data/execution.pid の内容を確認し、プロセスが存在しない場合は該当ファイルを削除してください。SystemMonitor は stale PID を検出して削除します。
- LINE 通知が届かない:
  - LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID の確認。AlertManager は未設定時、ログ出力のみ行います。
- OpenAI API エラー:
  - OPENAI_API_KEY の有無、ネットワーク、API 利用上限を確認。エラーはログに詳細が出ます。

ライセンス・貢献
----------------
- 本 README にライセンス情報は含まれていません。実運用・公開時は適切な LICENSE ファイルを追加してください。バグ修正・機能追加はプルリクエストを歓迎します。

付録: よく使うコマンドまとめ
---------------------------
- 仮想環境作成・依存インストール:
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要であれば README にサンプル .env.example や systemd / supervisor 用のユニット定義のテンプレート、より詳細なデータモデリング（DuckDB スキーマ）を追加できます。どのドキュメントを優先して拡充するか教えてください。