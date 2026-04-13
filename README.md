KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視機能を備えた軽量な Python パッケージです。本コードベースは以下の機能群を提供します。

- 注文作成〜送信〜状態同期を行う ExecutionEngine（本番／ペーパー分離）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 検証レポート生成ツール
- 監視ダッシュボード（Streamlit）
- ファクター計算・特徴量探索などのリサーチユーティリティ
- ニュースの LLM ベースセンチメントや市場レジーム判定（OpenAI 経由）
- ポートフォリオ構築・ポジションサイズ計算ロジック
- 補助ユーティリティ（プロセス優先度設定等）

主な仕様・設計方針
- 設定は環境変数（.env / .env.local 自動読込あり）で管理。自動読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番DBと分離して data/paper_trading.db を使用。
- 監視系は SQLite（monitoring DB）にログを永続化。init_monitoring_db がスキーマ作成・マイグレーションを行う（冪等）。
- OpenAI を用いる機能は API キー（OPENAI_API_KEY）が必要。API の障害にはフェイルセーフ設計（スコア 0 へのフォールバック等）。

機能一覧
--------
- Execution
  - 注文作成・送信・状態管理（OrderManager, Reconciler）
  - Broker クライアントの抽象化（本番/モックの切替）
  - リスク管理（RiskManager 等、設定に基づく制約）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態/データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の検出と記録
  - KillSwitch：危険事象時にフラグファイルを書き ExecutionEngine 停止を促す
  - AlertManager：LINE へ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
  - 銘柄選定、ウェイト計算、セクター制限、ポジションサイズ計算
- AI
  - news_nlp.score_news：ニュースを集約して OpenAI により銘柄別センチメントを取得・保存
  - regime_detector.score_regime：マクロ記事 + ETF MA を用いて市場レジーム判定・保存
- Tools
  - paper_verification_report：Paper Trading DB を解析して検証レポートを出力

セットアップ手順
----------------
前提
- Python 3.10+（型ヒントの | 記法を使用）
- SQLite（ローカルファイル利用）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）

例: pip でインストール
- (仮想環境を推奨)
  pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt があればそちらを利用してください）

重要な環境変数（主なもの）
- KABUSYS_ENV: 起動モード（development / paper_trading / live）（デフォルト: development）
  - paper_trading: MockBroker を使用し、 paper_sqlite_path を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API 用
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか ("1" で有効)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: INFO 等

使い方
------
1) 監視（MonitoringEngine）を起動
- 環境変数を設定した上で:
  python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- run_monitoring は本番 sqlite_path を使って監視ログを書き込みます（KABUSYS_ENV に依らず本番 DB を使用）。

2) 実行エンジン（ExecutionEngine）を起動
- 本番 / ペーパーを切り替えるには KABUSYS_ENV を設定:
  - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパー: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、 data/paper_trading.db に記録されます（本番 DB と完全分離）。
- 起動時、プロセス優先度を "high" に設定します（可能な場合）。

3) Paper Trading 検証レポートを生成
- コマンド:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション --db で SQLite ファイルを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

4) Streamlit ダッシュボードを起動
- コマンド例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で SQLite を開き、Overview / Positions / Orders / System タブを提供します。

5) AI 系（ニューススコア / レジーム判定）
- Python API として次を呼び出せます（DuckDB 接続と target_date を渡す）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡します。
- LLM 呼び出しはリトライ・フェイルセーフ実装あり（一定の障害は 0 やスキップで継続）。

運用上の注意
- .env / .env.local はプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込みされます。OS 環境変数が優先されます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト時に便利）。
- OpenAI 連携機能を利用する場合は API キーの管理に注意してください。
- kill.flag による停止は KillSwitch が評価して書き込みます。flag の存在は ExecutionEngine 停止の合図です。
- SQLite / DuckDB のパスは Settings から管理され、既定は data/ 配下です。適宜ディレクトリを作成してください。

ディレクトリ構成（主なファイル・モジュール）
-------------------------------------
src/kabusys/
- __init__.py — パッケージ定義、__version__
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_execution.py — ExecutionEngine 起動スクリプト（if __main__）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ / モジュール
- ai/
  - news_nlp.py — ニュースの LLM センチメント取得と ai_scores への書き込み
  - regime_detector.py — マクロニュース + ETF MA によるレジーム判定
- monitoring/
  - monitoring_db.py — 監視ログ用 SQLite スキーマと MonitoringDB（読み書きユーティリティ）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限のチェック
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード（実行スクリプト）
- execution/
  - reconciler.py — 再起動時の注文・ポジション照合
  - order_manager.py — 注文の作成／送信フローと状態遷移管理
  - order_repository.py, order_record.py, broker_* など（実装の一部は抜粋）
- portfolio/
  - portfolio_builder.py — 銘柄選定・スコア順ソート
  - position_sizing.py — 発注株数計算・単元丸め・aggregate cap
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

バージョン
---------
パッケージバージョンは kabusys.__version__ で管理されています（現状: 0.1.0）。

サポート / 拡張のヒント
-----------------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news など）を用意すれば、research / ai 機能が動作します。
- Broker クライアントは抽象化されているため、実際のブローカー実装を BrokerClientFactory に追加して差し替え可能です。
- Streamlit ダッシュボードは read-only URI で開いているため、本番監視 DB に安全に接続できます。

お問い合わせ
------------
コードや仕様についての質問や改善提案があれば、リポジトリ内の issue や PR を通して共有してください。

-----  
以上。必要であれば「導入手順の詳細（systemd ユニット例、Docker 化、CI でのテスト方法）」や「環境変数のサンプル .env.example」を追記します。どの情報を優先して追加しますか？