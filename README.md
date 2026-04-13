KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント / レジーム判定）などのコンポーネントを含みます。  
設計上、以下を重視しています:

- 本番・ペーパートレードの明確な分離（DB が別）
- 監視と自動停止（kill flag）による安全性
- DuckDB / SQLite を用いた履歴・分析基盤
- OpenAI を用いたニュース NLP（外部API呼び出しはオプション）

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を利用し DB を分離
  - リコンシリエーション、リスク管理、注文管理を含む
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/外部プロセス監視
  - TradeMonitor：滞留注文や約定価格の異常検知
  - RiskMonitor：ドローダウンやポジション上限監視とアラート/kill-switch
  - MonitoringEngine：各 Monitor を束ねて定期ポーリング
  - Streamlit ダッシュボード（監視データ閲覧用）
- ポートフォリオ構築
  - 候補選定、等ウェイト・スコア加重、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- リサーチ / ファクター計算（DuckDB を参照）
  - Momentum / Volatility / Value などの定量ファクター
  - 将来リターン、IC 計算、統計要約
- AI モジュール
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア化（ai_scores テーブルへ書込）
  - regime_detector: ETF の MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - 設定読み込み（.env 自動ロード、Settings クラス）

前提 / 依存関係
----------------
必須（代表例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- requests (LINE 通知)
- streamlit (ダッシュボード)
- sqlite3（標準ライブラリ）

簡易インストール例（仮想環境推奨）:
- pip install duckdb psutil openai requests streamlit

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作る:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install duckdb psutil openai requests streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動ロードされます）
   代表的な変数:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...          # AI 機能を使う場合
   - KABUSYS_ENV=development | paper_trading | live
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LINE_CHANNEL_ACCESS_TOKEN=...  # LINE 通知を使う場合
   - LINE_USER_ID=...
   - MONITOR_POLL_INTERVAL=60       # run_monitoring のポーリング間隔（秒）

   .env のパースはシェル風の形式（コメントや export もサポート）を行います。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ファイルやパスのデフォルト:
- 監視用 SQLite: data/monitoring.db
- DuckDB: data/kabusys.duckdb
- ペーパートレード SQLite: data/paper_trading.db
- PID file: data/execution.pid
- kill flag: data/kill.flag

使い方（コマンド）
-----------------

- 監視ループ起動（SystemMonitor 単体起動スクリプト）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は Settings の sqlite_path を利用（環境にかかわらず本番 sqlite_path を使用する点に注意）

- 実行エンジン起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し Broker に Mock を使います
  - 起動時に PID ファイルを書き、kill.flag の存在で停止する仕組みがあります

- Streamlit ダッシュボード（監視データ可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で DB ファイルの URI に ?mode=ro を付けて開きます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の DB を指定可能（デフォルト data/paper_trading.db）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）など

- AI 機能（ニュース/レジーム）
  - ai.news_nlp.score_news, ai.regime_detector.score_regime を呼んで DuckDB 上のデータを評価・書き込み
  - OpenAI API キー（OPENAI_API_KEY または引数）が必須
  - API コールはリトライ・バックオフや結果バリデーションを行います

主要な設定 / 環境変数（抜粋）
----------------------------
- KABUSYS_ENV: development | paper_trading | live（必須ではないが動作モード判定に使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能使用時）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB パス（default: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

ディレクトリ構成
-----------------
（src/kabusys をルートとした主要ファイル・モジュール）

- src/kabusys/__init__.py
  - パッケージ定義、__version__ 等

- src/kabusys/config.py
  - .env 自動ロード、Settings クラス（環境変数ラッパー）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト

- src/kabusys/run_execution.py
  - ExecutionEngine を組み立ててセッションを実行するスクリプト

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル定義・永続化 API（MonitoringDB）
  - system_monitor.py: システム状態 / データ鮮度チェック
  - trade_monitor.py: 注文滞留 / 約定異常検出
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書込による ExecutionEngine 停止
  - alert_manager.py: LINE Messaging API への通知
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: 監視用 Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py 等（発注・同期・再起動時リコンシリエーション等）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数計算
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書込
  - regime_detector.py: MA200 + マクロニュースで日次レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py: ペーパートレード検証レポート出力スクリプト

注意事項 / 運用上のポイント
--------------------------
- run_monitoring は monitoring 用の sqlite_path を常に使用します（KABUSYS_ENV に依存せず本番の path を参照する実装になっています）。
- run_execution は KABUSYS_ENV=paper_trading のときに紙の DB を使うため、本番 DB を汚染しません。
- PID ファイル / kill.flag によりプロセス間の連携・安全停止を行います。運用時はこれらのファイルパス設定に注意してください。
- AI 機能は外部 API 依存のため、API キー、レート制限、課金に注意してください。失敗時はフェイルセーフで継続する設計ですが、挙動はログで確認してください。
- DuckDB のテーブル設計や期待される prices_daily / raw_financials / raw_news 等のスキーマはモジュール内ドキュメントを参照してください（research / ai モジュールが参照します）。

サンプル .env（例）
-------------------
# .env.example 的な内容
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

サポート / テスト
------------------
- モジュールはユニットテストしやすい設計（外部 API 呼び出しはラップされており、テスト時に差し替え可能）になっています。AI 呼び出し関数は内部で分離実装されているためモックしやすいです。
- Streamlit ダッシュボードは読み取り専用モードで安全に参照できます。

貢献
----
バグ報告や機能提案は Issue を立ててください。プルリクエストは歓迎します。

ライセンス
----------
（必要に応じてライセンス情報を追記してください）

---
必要であれば、各モジュールの詳しい API 使用例や起動時のログ例、運用手順（systemd ユニットやコンテナ化例）も追加します。どの情報を優先的に補足しましょうか？