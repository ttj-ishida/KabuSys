KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買のためのモジュール群です。主な機能は以下のとおりです。

- 注文発行・状態管理を行う ExecutionEngine（ブローカー抽象化を備える）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算・将来リターン・IC 等の統計解析）
- AI 製品（ニュースセンチメントによる銘柄スコアリング、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 設定管理（.env 自動ロード、環境ごとの DB 分離 etc.）

主な特徴
--------
- 環境（development / paper_trading / live）に応じた挙動切替
  - paper_trading 環境ではブローカーがモックになり、Paper 用 SQLite DB（data/paper_trading.db）を使用
- DuckDB（時系列価格やファイナンスデータ用）と SQLite（監視・注文ログ用）を併用
- OpenAI を用いたニュース NLP 集約スコアリング（ai/news_nlp.py）
- 市場レジーム判定（ETF MA とマクロニュースを合成：ai/regime_detector.py）
- 監視エンジンは kill.flag による Execution 停止指示や LINE 通知を発行可能
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

セットアップ手順
----------------
1. リポジトリをチェックアウトし、作業ディレクトリに移動します。
   - 推奨: 仮想環境を作成して有効化してください。
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストールします（例）。
   - pip install duckdb psutil requests streamlit openai

   ※ 実際にはプロジェクトに requirements.txt があればそれを使用してください。

3. データディレクトリを作成します。
   - mkdir -p data

4. 環境変数を設定します（.env をプロジェクトルートに置くことが可能）。
   必須 / 推奨される主な環境変数:
   - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
   - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必要な場合）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実運用時）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を使う場合
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用）

   .env 自動読み込み:
   - プロジェクトルートに .env, .env.local があれば自動で読み込まれます（OS 環境変数が優先）
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

使い方
------
以下は代表的な起動方法とユーティリティの使い方です。

- ExecutionEngine を起動（本番 / paper_trading 共通エントリポイント）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB / MockBroker を使用します。

- Monitoring（System / Trade / Risk）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を参照します（監視 DB は環境に依存しません）。

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- AI 機能（プログラムから利用）
  - ニュースセンチメント（ai/news_nlp.py）の呼び出し:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  — DuckDB 接続と日付を渡す
  - レジーム判定（ai/regime_detector.py）の呼び出し:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

注意点 / 運用メモ
- run_execution / run_monitoring は起動時にプロセス優先度を high に設定しようとします（psutil が必要）。
- run_execution は paper_trading 環境で本番 DB を汚さないよう paper_trading 用 SQLite を使用します。
- AI 呼び出しは OpenAI API を利用し、429 や一時的な失敗に対してリトライロジックを備えています。
- monitoring は kill.flag による外部停止シグナルを評価します（KillSwitch）。
- DB マイグレーション: monitoring DB は初回起動時に必要なテーブルとインデックスを作成します（冪等）。

ディレクトリ構成（概要）
-----------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - 環境変数/.env 読み込み・Settings クラス
  - 自動ロードの挙動、必須チェック、env のバリデーションを提供

- run_execution.py
  - ExecutionEngine 起動スクリプト（ブローカー、OrderManager、RiskManager 組立て）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- execution/
  - order_manager.py, reconciler.py, ...（注文ライフサイクル、リコンシリエーション等）
  - Broker クライアントは抽象化されており、BrokerClientFactory を経由して実体が生成されます（実装は別途）

- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 複数 Monitor を束ねる実行エンジン
  - alert_manager.py — LINE 通知送信
  - kill_switch.py — kill.flag 制御
  - streamlit_dashboard.py — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け（等重・スコア重み）
  - position_sizing.py — 発注株数算出（risk_based / equal / score）
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — momentum/value/volatility ファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC 計算、統計サマリ

- ai/
  - news_nlp.py — ニュースを集約し OpenAI で銘柄別センチメントを算出・書込
  - regime_detector.py — MA とマクロニュースで市場レジームを判定

- data/（実運用ではリポジトリ外に置くことを推奨）
  - kabusys.duckdb (DuckDB データベース)
  - monitoring.db / paper_trading.db (SQLite)

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

追加情報
--------
- テスト / CI 用に .env 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モジュールは基本的に副作用を少なく設計されています（DB コネクションを呼び出し元に任せる等）。API レイヤーとビジネスロジックは分離されています。
- 実際の運用ではブローカー実装（BrokerClientFactory）や OrderRepository の永続化スキーマ、手数料・スリッページの見積り等を環境に合わせて設定してください。

問題・拡張
-----------
- Paper Trading の約定挙動（PAPER_FILL_MODE）や lot_size の銘柄別対応は今後拡張可能です。
- セクターエクスポージャー計算は欠損価格の扱いで過小評価が生じる可能性があるため、フォールバック価格の導入を検討してください。

問い合わせ
---------
この README の内容に関する質問、実行上の問題や追加ドキュメントの要望があれば教えてください。README を環境固有のセットアップ例（.env.example、requirements.txt、systemd ユニット など）で拡張できます。