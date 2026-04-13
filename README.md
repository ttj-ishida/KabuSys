KabuSys — 日本株自動売買システム
================================

以下はこのリポジトリ（src/kabusys）に含まれる主要な機能・起動方法・ディレクトリ構成の概要です。開発者向けドキュメントとして README.md を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。主な機能は次のとおりです。

- 注文発行・状態管理（ExecutionEngine、OrderManager、Reconciler）
- ポートフォリオ構築（候補選定、重み計算、位置サイズ決定、セクター制限）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI を使ったニュースセンチメント／レジーム判定（OpenAI）
- 監視・アラート（SystemMonitor、TradeMonitor、RiskMonitor、AlertManager）
- モニタリング用の DB 層（SQLite に永続化）と Streamlit ダッシュボード
- Paper Trading 用の検証ツール（レポート生成スクリプト等）

特徴
----
- モジュール単位で純粋関数・副作用を分離（ポートフォリオ計算やリサーチは DB に依存しない）
- 本番／ペーパートレードモードを切替可能（KABUSYS_ENV）
- DuckDB を用いた大規模データ処理（prices_daily, raw_financials 等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP とレジーム判定（API キー必須）
- LINE Push による監視アラート（設定がある場合）
- 監視ループは MONITOR_POLL_INTERVAL による間隔指定（デフォルト 60 秒）

前提・依存
-----------
- Python 3.10+（typing の一部表現等を使用）
- 必要な主なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使用する場合）
- SQLite（標準ライブラリ sqlite3 を使用）
（実際の requirements.txt はプロジェクトに合わせて用意してください）

セットアップ手順
----------------

1. リポジトリをクローン／配置
   - この README は src/kabusys 配下のコードベースを前提としています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトで requirements.txt があれば pip install -r requirements.txt）

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - ルートの .env または .env.local に必要な変数を設定できます（自動ロードあり）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

.env（例）
----------
以下は最低限よく使う環境変数の例（実際は .env.example を参照して適切に設定してください）。

JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development            # development | paper_trading | live
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
PAPER_FILL_MODE=instant            # instant|partial|never|reject

重要ポイント
- KABUSYS_ENV は development / paper_trading / live のいずれかで、paper_trading の場合は ExecutionEngine は MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
- 監視（Monitoring）は KABUSYS_ENV にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用します（監視ログは常に本番 DB パスで扱われる仕様）。
- MONITOR_POLL_INTERVAL 環境変数で監視ループの間隔を秒数で上書き可能（デフォルト 60）。1 未満の値は無効としてデフォルトにフォールバックします。

使い方（主要スクリプト）
-----------------------

1. 監視ループ起動（SystemMonitor の簡易起動スクリプト）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更可能。
   - 起動時にプロセス優先度を "high" に設定しようとします（set_process_priority）。

2. ExecutionEngine 起動（発注・実行エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパー口座）を使い、PAPER_TRADING_SQLITE_PATH に書き込みます。
   - 実行前に必要な環境変数（認証情報など）を設定してください。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視用 sqlite DB を read-only で開いてダッシュボード表示します（MonitoringEngine を先に起動してデータを作る必要があります）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - データベース指定:
     - --db /path/to/paper_trading.db
   - レポートは stdout に印字され、稼働率・注文成功率・レイテンシ等を判定します。

5. AI バッチ処理（ニューススコア / レジーム）
   - モジュール関数として提供されます。スクリプト実行エントリは同梱されていませんが、簡単に呼び出せます。例（Python から）:
     - from kabusys.ai.news_nlp import score_news
       score_news(conn, target_date, api_key="...")

     - from kabusys.ai.regime_detector import score_regime
       score_regime(conn, target_date, api_key="...")

   - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定してください。未設定なら例外になります。

監視・アラート関連の挙動・フラグ
--------------------------------
- pid_file_path（デフォルト data/execution.pid）: ExecutionEngine が稼働しているかを判定するために用いるファイル。
- kill_flag_path（デフォルト data/kill.flag）: KillSwitch が条件を満たすとファイルを書き込み、ExecutionEngine に停止シグナルとして機能します。
- AlertManager は LINE のチャネルアクセストークンとユーザー ID を使ってプッシュ通知を送信します（未設定なら送信は行わずログのみ）。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数読み込み・Settings クラス（KABUSYS_ENV 等）
- run_monitoring.py — SystemMonitor の簡易ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading の扱いを含む）

subpackages:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + MA200 から市場レジームを判定して market_regime に書き込む
- monitoring/
  - monitoring_db.py — SQLite 上の永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定価格異常チェック
  - risk_monitor.py — ドローダウン監視・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE Push 送信とクールダウン管理
  - monitoring_engine.py — 各 Monitor を束ねるポーリング実行エンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文状態遷移・OrderManager
  - reconciler.py — 起動時の注文/ポジション突合
  - （その他 Broker 関連、OrderRepository 等は実装に応じて存在）
- portfolio/
  - portfolio_builder.py — 候補選定（score / rank）
  - position_sizing.py — 株数・単元株丸め、リスク制限、aggregate cap
  - risk_adjustment.py — セクター制限、レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading レポート生成用スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項・運用上のヒント
-----------------------
- DuckDB の接続は read/write どちらでも使われます。大きなデータ処理ではファイルパスの配置に注意してください。
- OpenAI を使う機能は API のレート制限・コストに注意し、API キー漏洩に注意してください。
- psutil を使ってプロセス優先度や CPU affinity を変更します。権限によっては設定に失敗する可能性があります（ログに警告されます）。
- Paper Trading モードは本番 DB と分離するよう設計されています。実運用時は env 設定を慎重に扱ってください。
- monitoring_db.init_monitoring_db はマイグレーションを簡易的に行う（カラム追加等）ため、既存 DB への互換性に注意してください。

貢献 / 開発
-----------
- 新しい機能を実装する場合はモジュール分割の設計方針（副作用の分離、純粋関数設計）に従ってください。
- 環境変数の取り扱いは config.Settings 経由で行うと一貫性が保てます。
- テストを書く際は .env 自動ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。

---
この README はコードベース（src/kabusys 以下）から抽出した情報を基に作成しています。実際の運用・デプロイにはセキュリティ（API キーの管理）、バックアップ、モニタリング運用手順の整備を行ってください。必要であれば README を拡張してサンプル .env.example、systemd サービス定義、Dockerfile、CI 設定などの運用ガイドを追加できます。