# KabuSys

日本株自動売買システムの軽量ライブラリ / 実行スクリプト群

このリポジトリは、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含む、モジュール化された自動売買システムです。

---

## プロジェクト概要

- 設計方針は「フェイルセーフ」「ルックアヘッドバイアス防止」「本番と検証（paper_trading）の明確な分離」。
- データ永続化には SQLite（監視ログ等）と DuckDB（時系列データ / リサーチ用）を使用。
- OpenAI を用いたニュース NLP（センチメント）とレジーム判定をサポート。
- 監視コンポーネントはプロセス健全性・注文の滞留・ドローダウン等を検出し、LINE 通知や kill flag により ExecutionEngine を安全停止できます。

主要な実行スクリプト：
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Streamlit ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## 機能一覧

- Execution
  - Broker クライアントの抽象化（実環境 / paper_trading の切替）
  - 注文作成・送信・同期・リコンシリエーション（再起動後の自動同期）
  - リスク管理（利用率、ポジション制限、サーキットブレーカー等）
- Monitoring
  - システムリソース（CPU / メモリ / ディスク）監視
  - 実行プロセスの生存チェック（PID ファイル）
  - 注文滞留・約定価格異常検出
  - ドローダウン・ポジション上限監視と kill flag 書き込み
  - LINE プッシュ通知（冷却時間あり）
  - Streamlit ダッシュボード表示
- Portfolio
  - 候補選定（スコア降順）
  - 重み算出（等金額 / スコア重み）
  - ポジションサイズ算出（リスクベース / allocation）
  - セクターキャップ適用・レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 前方リターン計算・IC（Information Coefficient）等の統計ユーティリティ
- AI
  - ニュース記事を LLM でセンチメント化して ai_scores に格納（OpenAI）
  - マクロ記事 + ETF ma200 を用いた市場レジーム判定（bull / neutral / bear）
- Tools
  - paper_trading の検証レポート生成スクリプト（稼働率 / 注文成功率 / レイテンシなど）

---

## セットアップ手順

前提
- Python 3.9+ を推奨（プロジェクトの依存に合わせて適宜）
- システムに duckdb, sqlite3 サポートが必要
- OpenAI API を利用する場合はネットワーク接続と API キーが必要

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 依存関係をインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも以下をインストールしてください：
     - duckdb
     - psutil
     - requests
     - streamlit (ダッシュボード利用時)
     - openai (AI 機能利用時)

4. データディレクトリの作成
   - mkdir -p data

5. 環境変数 / .env の設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます。
   - 自動読み込みは OS 環境変数 > .env.local > .env で行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます。
   - 代表的な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - MONITOR_POLL_INTERVAL=60  (監視ポーリング間隔秒)
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

6. DB 初期化
   - 監視用 DB（SQLite）は実行スクリプト起動時に自動でテーブル作成 / マイグレーションされます（init_monitoring_db を参照）。

注意：
- Paper Trading（KABUSYS_ENV=paper_trading）では本番の監視 DB と分離して paper_sqlite_path（既定: data/paper_trading.db）を使用します。
- 監視 (monitoring) は明示的に production sqlite_path を使用する設計の箇所があります（run_monitoring は本番 sqlite_path を参照）。

---

## 使い方

基本的な起動・操作方法を示します。

1. 実行エンジン（ExecutionEngine）起動
   - 通常実行（env が live / development 等に応じて挙動が変わります）:
     - python -m kabusys.run_execution
   - Paper trading（DB を分離、Mock ブローカー使用）:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

2. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
   - 監視は monitoring DB（デフォルト: data/monitoring.db）へ記録します。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは read-only モードで SQLite を開きます（MonitoringEngine を先に起動してください）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH で既定を上書きできます。

5. AI 系（ニュースセンチメント / レジーム判定）
   - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡します。
   - 例: Python セッション内で
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key="sk-...")
   - run_execution / run_monitoring とは独立して任意に実行可能。ただし DuckDB に prices_daily / raw_news 等のデータが必要です。

6. Kill Switch / 停止フラグ
   - RiskMonitor 等の判定により KillSwitch が data/kill.flag を書き込みます。
   - ExecutionEngine は起動時に kill_flag_clear_on_start 設定（環境変数）によりフラグをクリアするオプションがあります。

運用時の注意点
- 本番運用時は KABUSYS_ENV=live を使用してください。paper_trading ではモックブローカーと専用 DB を使うため安全に検証できます。
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア=0 など）で継続する設計ですが、API 料金・レート制限に注意してください。
- process priority / CPU affinity はプラットフォーム依存で、権限不足時は警告でスキップされます。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージ内の主要ファイルと説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動読み込み、各種設定プロパティ）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて挙動分岐）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - paper_trading DB の検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成 / MonitoringDB ラッパー（log_system_status, upsert_dashboard 等）
    - system_monitor.py
      - システムリソース・データ鮮度・PID チェック
    - trade_monitor.py
      - 注文滞留・約定異常検出
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（kill flag の候補生成）
    - kill_switch.py
      - kill.flag の書き込み / クリア
    - alert_manager.py
      - LINE push 通知（クールダウン管理）
    - monitoring_engine.py
      - 上記モニタを束ねるランナー
    - streamlit_dashboard.py
      - Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (DB 操作)
    - execution_engine.py (Engine 実行ロジック) —（存在前提）
    - broker_factory.py, broker_api.py (ブローカー抽象 / 実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py, stats.py 等（DuckDB 用ユーティリティ、prices_daily 取得など）
  - utils/
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ
  - その他モジュール群（order_record, order_repository, ...）

（上記は主要モジュールの抜粋です。コードを参照して詳細をご確認ください。）

---

## 重要な設計上のポイント・運用メモ

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper trading（検証環境）は本番 DB と完全分離する設計です。PAPER_FILL_MODE によりモックの約定挙動を制御できます（instant / partial / never / reject）。
- Monitoring の DB 初期化（テーブル作成 / マイグレーション）はスクリプト起動時に安全に行われます（冪等）。
- AI 呼び出し (OpenAI) はレスポンス検証・クリップ・リトライ等の保護処理を行っていますが、API エラーやレート制限は発生するため運用監視が必要です。
- プロセス優先度設定はプラットフォーム依存かつ権限が必要な場合があるため、権限不足時はログに警告を出しスキップします。

---

必要であれば、README に含める「インストール用 requirements.txt の推奨一覧」や、実行時の具体的なログ例、設定ファイル（.env.example）テンプレートなども追記できます。どの情報を追加したいか教えてください。