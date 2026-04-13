README — KabuSys
=================

概要
----
KabuSys は日本株自動売買プラットフォームの一部を模した Python コードベースです。  
主な機能は「取引実行（ExecutionEngine）」「監視（Monitoring）」「ポートフォリオ構築」「リサーチ（ファクター計算）」「ニュースの NLP スコアリング（OpenAI）」などで、実運用／ペーパートレード両対応の設計になっています。

特徴
----
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
  - 本番 / paper_trading 切替（KABUSYS_ENV）
  - Broker クライアントを抽象化し、paper_trading では MockBroker を使用して data/paper_trading.db に記録
- Monitoring（システム状態・注文滞留・ドローダウン監視）
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（フラグファイルによる ExecutionEngine 停止）
  - LINE へのプッシュ通知サポート（AlertManager）
  - Streamlit ダッシュボード
- Portfolio 構築ロジック（候補選定、重み付け、ポジションサイズ決定、セクター制限など） — 純粋関数で DB 参照なし
- Research（DuckDB を用いたファクター計算・統計解析）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
  - OpenAI API（gpt-4o-mini）を利用する処理は API キー必須
- ユーティリティ（プロセス優先度設定、環境変数読み込みなど）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例: pip install duckdb psutil requests openai streamlit
   - 実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨

4. 環境変数 / .env の準備
   - 自動でプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須（モジュールによる）例:
     - JQUANTS_REFRESH_TOKEN — J-Quants（ファクター等で使用）
     - KABU_API_PASSWORD — kabuステーション API（ブローカー接続）
     - OPENAI_API_KEY — OpenAI を使う場合に必須（AI モジュール）
   - 主要設定（デフォルト値）
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - SQLITE_PATH: data/monitoring.db (監視用 DB)
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用 DB)
     - DUCKDB_PATH: data/kabusys.duckdb
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

使い方
------

実行（監視ループ）
- 監視の起動（プロセス優先度を High に設定して polling を始めます）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒、デフォルト 60）

実行（注文エンジン）
- ExecutionEngine を起動して当日セッションを実行:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用します（データは PAPER_TRADING_SQLITE_PATH に記録され、本番 DB と分離されます）

Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- paper_trading DB の統計を集計してレポートを標準出力に出す:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI / レジーム判定・ニューススコアリング
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数 or 関数引数）
- ai.score_news / ai.score_regime を呼び出して DuckDB 接続を渡すことで処理を行います（ライブラリ用途）

プロダクション運用上の注意
- 設定 KABUSYS_ENV により動作が変わります:
  - development: デフォルト
  - paper_trading: 発注は MockBroker に切替、DB は data/paper_trading.db を使う
  - live: 実ブローカー接続（設定に応じて）
- Kill Switch:
  - KillSwitch は監視の条件（ドローダウンやポジション上限）を満たすと data/kill.flag ファイルを書き込み、ExecutionEngine に停止を促します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると開始時にフラグをクリアできます（Settings.kill_flag_clear_on_start）
- PID ファイル:
  - ExecutionEngine は PID を PID_FILE_PATH に書きます（デフォルト data/execution.pid）。SystemMonitor はこの PID をチェックしてプロセス生存を検知します
- モニタリングループの例外はログを残して次ループへ継続する設計です

主要環境変数一覧（抜粋）
- KABUSYS_ENV: development | paper_trading | live (default: development)
- JQUANTS_REFRESH_TOKEN: 必須（ファクター等）
- KABU_API_PASSWORD: 必須（kabu ステーション API）
- OPENAI_API_KEY: OpenAI を使う場合必須
- SQLITE_PATH: data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: instant | partial | never | reject

ディレクトリ構成
----------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動ロード（.env / .env.local）と Settings クラスを提供
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading で MockBroker を使用）

サブパッケージ
- ai/
  - news_nlp.py — ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
  - regime_detector.py — マクロ NEWS + ETF ma200 で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義と MonitoringDB（読み書き API）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル
  - alert_manager.py — LINE Push 通知（クールダウン管理）
  - monitoring_engine.py — 複数 monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 発注フローの高レベル API
  - reconciler.py — 起動時リコンシリエーション（OrderSent 照合、ポジション差分）
  - その他（broker_factory, execution_engine, order_repository などが想定される）
- portfolio/
  - portfolio_builder.py — 候補選定・等重/スコア重み
  - position_sizing.py — 株数決定・単元丸め・リスク調整
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
- tools/
  - paper_verification_report.py — paper_trading DB の検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

補足
----
- SQLite / DuckDB の DB ファイルパスは Settings で定義されたデフォルトを使用します（data/ 以下）。monitoring の初回起動時にスキーマは自動作成されます（init_monitoring_db）。
- AI 関連処理は API 呼び出しで外部依存があるため、API キーの設定と rate-limit 対策（リトライ等）に注意してください。
- 設計上、時間や日付の取り扱いは「ルックアヘッドバイアス防止」を重視しています（内部で date.today()/datetime.today() を安易に参照しない等）。

ライセンス / 貢献
-----------------
（プロジェクトのライセンス情報や貢献ガイドをここに追加してください）

以上がこのコードベースの概要・セットアップ・使い方です。必要であれば、README にサンプル .env, requirements.txt、起動スクリプトの systemd ユニット例なども追記できます。どの情報を追加しますか？