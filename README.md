# KabuSys — README

概要
---
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python コードベースです。ファクター計算、ポートフォリオ構築、ポジションサイズ計算、注文発行・管理、監視（System / Trade / Risk）や、AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定などのコンポーネントを含みます。データは DuckDB（時系列・ファクターデータ）と SQLite（監視ログ / 注文履歴 / ペーパートレード）で保持します。

主な機能
---
- ファクター計算（モメンタム、ボラティリティ、バリュー）
- ファクターと将来リターンの解析（ICなど）
- ポートフォリオ候補抽出・重み計算（等金額・スコア重み）
- ポジションサイズ計算（risk-based 等）および単元調整
- ExecutionEngine：ブローカー経由の注文管理、リスク管理、再同期（Reconciler）
- Paper Trading 対応（本番 DB と分離した専用 SQLite）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE push）
- kill.flag による Execution 停止シグナル
- AI モジュール：ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- Streamlit ダッシュボードによる監視ビュー
- 検証ツール：Paper Trading の検証レポート生成

前提条件
---
- Python 3.9+
- 以下の主要依存ライブラリ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- OS により process priority / cpu affinity の設定に管理者権限が必要になる場合があります。

セットアップ手順
---
1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt が無い場合は代表的なパッケージをインストール）
   - pip install duckdb psutil requests openai streamlit
4. データディレクトリの作成
   - mkdir -p data
5. 環境変数設定 / .env
   - プロジェクトルートに .env（または .env.local）を配置すると自動でロードします（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN （J-Quants 用トークン）
     - KABU_API_PASSWORD （kabuステーション API 用パスワード）
   - その他の主要な環境変数（省略時はデフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパー取引用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading のモック約定モード（instant | partial | never | reject）
     - PID_FILE_PATH, KILL_FLAG_PATH など（監視・停止用）

重要な挙動（.env の自動ロード）
- config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env を読み込みます。
- 読み込み優先順は OS 環境変数 > .env.local > .env。OS の既存変数は保護されます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要なエントリポイント）
---
- 監視プロセスの起動（SystemMonitor 単体の簡易起動）
  - 目的: system / trade / risk のチェックを一定間隔で実行して監視ログを記録
  - 実行:
    - python -m kabusys.run_monitoring
    - 環境変数でポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30
  - 備考: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- ExecutionEngine の起動（発注エンジン）
  - 実行:
    - python -m kabusys.run_execution
  - ペーパートレードモード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
  - 起動時にプロセス優先度を高く設定し、PID ファイルを利用します（Settings.pid_file_path）。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード（監視画面）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を読み取り専用で開いて表示します。

- AI モジュールの利用例（Python REPL / スクリプト内）
  - ニュースセンチメント（ai.news_nlp.score_news）
    - 例:
      - from datetime import date
      - import duckdb
      - from kabusys.ai.news_nlp import score_news
      - conn = duckdb.connect("data/kabusys.duckdb")
      - score_news(conn, date(2026, 4, 11), api_key="sk-...")
  - 市場レジーム（ai.regime_detector.score_regime）
    - 例:
      - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, date(2026,4,11), api_key="sk-...")

運用上のメモ
- 監視の kill_switch は RiskMonitor の結果（ドローダウンやポジション上限等）により data/kill.flag を作成し、ExecutionEngine 停止のシグナルとします。既存フラグは上書きされません。
- Monitoring の DB スキーマやマイグレーションは monitoring_db.init_monitoring_db() により冪等に適用されます。
- Paper Trading を実行するときは本番用の SQLite（monitoring.db）と分離していることを必ず確認してください（PAPER_TRADING_SQLITE_PATH を利用）。

ディレクトリ構成（抜粋）
---
- src/
  - kabusys/
    - __init__.py
    - config.py                          # 環境変数・.env 管理
    - run_monitoring.py                  # SystemMonitor ポーリングスクリプト
    - run_execution.py                   # ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                      # ニュース NLP スコアリング
      - regime_detector.py               # 市場レジーム判定
    - data/ (モジュールは別途存在想定)   # DuckDB 用スキーマ・ETL 用コード等
    - execution/
      - order_manager.py
      - reconciler.py
      - ...                              # ブローカー連携・OrderRepository 等
    - monitoring/
      - __init__.py
      - monitoring_db.py                 # SQLite スキーマ + MonitoringDB API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - process_priority.py
      - __init__.py

開発・拡張メモ
---
- DuckDB 接続を受け取って分析処理を行う設計なので、テスト時は in-memory / テスト用 DB を用意して関数を呼び出すと良いです。
- OpenAI 呼び出し部分はリトライやバリデーションを行いますが、テストでは _call_openai_api をモックしてください（コード内コメントあり）。
- 設定は Settings クラス経由で取得する設計です。必須変数が未設定の場合は ValueError が投げられます。
- process priority / cpu affinity の設定はユーティリティで抽象化されていますが、OS 権限により失敗することがあり、その場合は警告ログを出してスキップします。

ライセンス・著作権
---
（この README ではライセンス情報を含めていません。必要に応じてプロジェクトに LICENSE ファイルを追加してください。）

問い合わせ・コントリビュート
---
- バグ報告や機能要望は Issue を作成してください。
- ローカルでの開発は仮想環境を使い、依存パッケージは requirements.txt を用意して管理することを推奨します。

以上。必要があればサンプル .env.example、requirements.txt、起動スクリプトの systemd ユニット例なども追記できます。どの情報がさらに必要か教えてください。