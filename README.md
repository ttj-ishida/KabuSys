KabuSys — README
=================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。  
主な役割は以下の通りです。

- 信号 → 注文発行 → ブローカー同期（Execution Engine）
- モニタリング（システム状態・注文滞留・リスク監視）とアラート（LINE push）
- Paper Trading 用の分離された DB とモックブローカー
- ファクター計算・リサーチユーティリティ（DuckDB を想定）
- ニュースを用いた LLM（OpenAI）によるセンチメント評価・市場レジーム判定
- Streamlit ベースの簡易監視ダッシュボード
- 検証レポート（Paper Trading 実行結果のサマリ出力）

特徴（機能一覧）
----------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を切り替え可（KABUSYS_ENV）
  - Paper Trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
  - 起動前に stop フラグ（data/stop_requested.flag）を確認
  - プロセス優先度を上げる（psutil 経由）
- Monitoring（run_monitoring.py / MonitoringEngine）
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - ポーリング間隔を MONITOR_POLL_INTERVAL で上書き（デフォルト 60 秒）
  - 停止フラグの検出で安全にループ終了
- Kill Switch（kill.flag）による ExecutionEngine 停止シグナル発行
- AlertManager による LINE Push 通知（チャンネルアクセストークン / ユーザーID 必須）
- Streamlit 監視ダッシュボード（streamlit_dashboard.py）
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- 研究用ファクター計算（research.calc_momentum / calc_volatility / calc_value）
- ニュース NLP（ai.news_nlp.score_news） & レジーム判定（ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を使って銘柄・マクロセンチメントを算出
- ポートフォリオ構築ユーティリティ（portfolio.*：候補選定、重み計算、ポジションサイズ計算等）
- utils: プロセス優先度 / CPU affinity 等のユーティリティ

セットアップ手順
----------------
1. Python（3.10+ を想定）を用意します。

2. 必要ライブラリをインストール（代表的なパッケージ）
   - duckdb, psutil, requests, openai, streamlit
   例:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がない場合は上記を参照してください。実行環境に応じて追加パッケージが必要です）

3. データディレクトリを準備（任意）
   - デフォルトで data/*.db、data/*.flag、data/execution.pid などを使用します。
   - 例: mkdir -p data

4. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置けば自動ロードされます（OS 環境変数が優先）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（要確認）
- 必須（実行する機能により必須／任意がある）
  - JQUANTS_REFRESH_TOKEN — （研究系 API 用）
  - KABU_API_PASSWORD — kabuステーション API 用
- 実行制御・ログ等
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/...
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring 用、デフォルト 60）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db） ※ monitoring は常に sqlite_path を参照
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 時の専用 SQLite（デフォルト data/paper_trading.db）
- Paper Trading/Mock ブローカー
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト "instant"）
- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- OpenAI
  - OPENAI_API_KEY — ai.news_nlp / ai.regime_detector を使う場合に必要

使い方（主要コマンド / 実行例）
----------------

1) 監視ループを起動（Monitoring）
- デフォルトのポーリング間隔 60 秒:
  - python -m kabusys.run_monitoring
- ポーリング間隔を 30 秒に変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- run_monitoring は起動時にプロセス優先度を High にし、data/stop_requested.flag の存在で終了します。
  - 止めたい場合は data/stop_requested.flag を作成してください（起動・終了の合図）。

2) 実行エンジン起動（ExecutionEngine）
- 本番モード（KABUSYS_ENV=live）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading（MockBroker を使用し data/paper_trading.db に記録）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 停止方法:
  - data/stop_requested.flag を作成すると安全に停止処理が行われます。
  - Kill Switch（kill.flag）が作動すると ExecutionEngine 側で停止処理が行われます（kill.flag は監視・リスク評価から書き込まれます）。

3) Streamlit ダッシュボード
- 監視 DB を読み込んで Web ダッシュボードを起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
- モジュール実行:
  - python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB ファイルを指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI 関連（ニューススコア / レジーム判定）
- これらはライブラリ関数として提供されます。実行には OPENAI_API_KEY が必要です。
  - ai.news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)
- 注意: 実行中は外部 API（OpenAI）へアクセスし、429/ネットワーク障害等は内部でリトライされます。APIキーは引数か環境変数で指定してください。

ライブラリの利用例（研究用）
- DuckDB 接続を作り、ファクター計算を呼ぶ:
  - from kabusys.research import calc_momentum
  - result = calc_momentum(duckdb_conn, date(2026,4,1))

ディレクトリ構成（主要ファイル）
----------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings（.env 自動ロード・検証）
- run_monitoring.py — Monitoring の起動スクリプト
- run_execution.py — ExecutionEngine の起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py — ニュースから LLM で銘柄スコア算出
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite スキーマ / CRUD（init_monitoring_db, MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種チェック
  - monitoring_engine.py — 各モニタをまとめる実行エンジン
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ... — 発注関連ロジック（OrderRepository 等は別ファイル）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算、リスク/lot の考慮
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラ / バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

その他
- data/ 以下に DB ファイル・PID・flag ファイルなどを配置する想定（リポジトリには含まれない場合あり）。
- monitoring_db.init_monitoring_db() は冪等で実行でき、既存 DB に対する簡易マイグレーション（カラム追加）処理を含みます。

トラブルシューティング
-----------------------
- 起動時に ValueError: 環境変数 'XXX' が設定されていません。
  - 必須の環境変数が未設定です。.env.example を参照して .env を作成してください（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）。
- OpenAI 関連で API キー未設定:
  - OPENAI_API_KEY を環境変数または関数引数で指定してください。
- psutil による優先度設定で AccessDenied:
  - 権限不足のため警告が出ますが、これは致命的ではなく処理は継続します。
- Streamlit で DB を読み込めない:
  - monitoring ダッシュボードは読み取り専用で DB を開こうとします。MonitoringEngine を実行して DB が存在することを確認してください。
- Paper Trading と本番 DB の混同防止:
  - KABUSYS_ENV=paper_trading を設定すると run_execution は paper_sqlite_path を使用します。監視は常に sqlite_path を使う点に注意してください。

ライセンス・貢献
----------------
この README はコードに基づく概要説明です。実運用や資金を扱う際は十分なテストと監査を行ってください。貢献や問題報告はリポジトリの ISSUE / PR をご利用ください。

補足
----
- ここに記載のコマンドはプロジェクトルート（pyproject.toml や .git がある場所）をカレントにして実行することを想定しています。
- 実環境では systemd / supervisor 等でプロセスマネージャにより起動・監視することが想定されます（PID ファイル / stop flag の取り扱いを確認してください）。

以上。必要であれば README に含めるコマンド例や env.example のテンプレートを作成します。