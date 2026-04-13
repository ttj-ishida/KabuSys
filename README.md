KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。  
主に以下の機能を含みます:

- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- Monitoring（システム状態 / 注文監視 / リスク監視 / アラート送信）
- Portfolio construction（候補選定・重み付け・サイズ算出・リスク調整）
- Research（ファクター計算・将来リターン・IC・統計サマリー）
- AI モジュール（ニュースの NLP によるセンチメント評価、レジーム判定）
- ツール（Paper Trading の検証レポート等）
- ユーティリティ（設定読み込み、プロセス優先度設定 等）

このリポジトリは、取引ロジックと監視・運用周りの実装を提供します。実際のブローカー接続は環境（本番 / ペーパー）に応じて差し替えられます。

主な機能一覧
------------
- Execution
  - 注文作成 → ブローカー送信 → 状態同期のフロー（OrderManager / OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager 等）
- Monitoring
  - システムリソース（CPU/Memory/Disk）監視（SystemMonitor）
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - kill.flag による ExecutionEngine 停止指示（KillSwitch）
  - LINE Push によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio 建設
  - 候補選定（score 降順）、等分配・スコア加重配分
  - ポジションサイズ算出（risk_based / equal / score）
  - セクターキャップ、レジーム係数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン、IC、統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメント評価 → ai_scores に書き込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. Python 環境を作成
   - 推奨: venv / pyenv / poetry 等で仮想環境を作成してください。

   例:
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存ライブラリをインストール
   - 必要なライブラリ（主なもの）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は個別に:
     - pip install duckdb psutil requests openai streamlit

3. ディレクトリ作成
   - デフォルトでは data/ 配下に DB やファイルを作成します:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite: 監視ログ)
     - data/paper_trading.db (Paper trading 用 SQLite)
     - data/execution.pid (PID ファイル)
     - data/kill.flag (Kill スイッチ)
   - 必要に応じて data/ ディレクトリを作成:
     - mkdir -p data

4. 環境変数設定 (.env)
   - このプロジェクトは .env / .env.local を自動読込します（プロジェクトルート検出: .git / pyproject.toml）。
   - 自動読込を無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（必須/任意とデフォルト）:

     必須（実行に応じて必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード

     OpenAI (AI 機能を使う場合):
     - OPENAI_API_KEY — OpenAI API キー

     監視 / 実行全般:
     - KABUSYS_ENV — 開発環境。値: development / paper_trading / live（default: development）
       - paper_trading の場合、MockBroker を使用し paper 用 DB に書き込む
     - LOG_LEVEL — ログレベル（DEBUG/INFO/…、default: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 SQLite パス（default: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
     - PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject、default: instant）
     - PID_FILE_PATH — ExecutionEngine の PID ファイル（default: data/execution.pid）
     - KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）
     - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を消す（"1" で有効）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（パーセント）

   - 監視ループ固有:
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）

   - LINE 通知（任意）:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID

5. DB 初期化
   - monitoring 用のテーブルは init_monitoring_db() で作成されます。
   - run_monitoring を実行すると自動で初期化されます。

使い方
------
- ExecutionEngine を起動（本番/ペーパー共通）:
  - paper_trading モード（MockBroker, data/paper_trading.db を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番モード:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行開始時にプロセス優先度を「high」に設定します（set_process_priority）。

- Monitoring（ポーリング監視）を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を読み取り専用で開き、ポートフォリオ/ポジション/注文/システム状態を表示します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力します。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

設定の自動ロード
----------------
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読込を無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主要ファイル・モジュールの説明です（完全な一覧はコードツリーを参照してください）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込みと設定取得のユーティリティ
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による挙動差分あり）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite スキーマと永続化層（MonitoringDB）
    - system_monitor.py — システムリソース・データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 監視コンポーネント統合ループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 株数算出 / aggregate cap
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - execution/
    - reconciler.py — 起動時リコンシリエーション
    - order_manager.py — 注文の作成/送信/状態管理（OrderManager）
    - （その他、broker / order_repository 等の実装が想定）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

運用上の注意
------------
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は KABUSYS_ENV に関係なく本番の sqlite_path（監視 DB）を使用します（監視ログは本番を参照する想定）。
- Execution 起動時に PID ファイルを書き、SystemMonitor は PID 存在でプロセス稼働判定を行います。stale PID が検出された場合は削除してアラートを上げます。
- AI（OpenAI）呼び出しは外部 API を使用するため、レート制限や障害を考慮したリトライ機構・フェイルセーフが組み込まれています。API キー管理に注意してください。
- 重要なしきい値（CPU/MEM/DISK、ドローダウン閾値など）は環境変数で調整可能です。

トラブルシューティング
---------------------
- .env が読み込まれない場合:
  - プロジェクトルートが正しく検出されているか確認（.git または pyproject.toml があるか）。
  - 自動読み込みを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD の解除を検討。
- DB 初期化エラー:
  - monitoring 用テーブルは init_monitoring_db() で作成されます。run_monitoring を一度実行して初期化してください。
- OpenAI 呼び出しでエラーが出る場合:
  - OPENAI_API_KEY が設定されているか確認。
  - ネットワークやレート制限、レスポンスの JSON 構造に注意。該当モジュールにはリトライ・パース対処が実装されています。

ライセンス・貢献
----------------
本 README はコードを説明するためのものであり、実際のライセンス表記や貢献ガイドラインがある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

以上。必要であればセクションを追記（例: 依存パッケージの正確なバージョン、実行時のログ設定例、詳細設計ドキュメントの参照）します。