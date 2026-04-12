README
======

概要
----
KabuSys は日本株の自動売買および関連ユーティリティ群を含む Python コードベースです。  
主な用途は以下です:

- 注文作成〜送信〜状態同期を行う ExecutionEngine（本番 / ペーパー切替対応）
- 実行状況・システム状態を監視してログ・アラート出力する Monitoring コンポーネント
- ポートフォリオ構築（候補選定、重み算出、単元丸め、リスク調整）
- リサーチ向けのファクター計算・特徴量解析（DuckDB を利用）
- ニュースに対する LLM（OpenAI）を使ったセンチメント評価・レジーム判定
- ペーパートレード検証レポート生成・Streamlit ダッシュボード等のツール群

機能一覧
--------
主な機能・モジュール:

- execution/
  - 注文作成・送信・状態管理（OrderManager、OrderRepository、Reconciler など）
  - ブローカーファクトリで paper_trading と live を切替可能
- monitoring/
  - SystemMonitor: CPU/メモリ/Disk/プロセス・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch: 条件で ExecutionEngine 停止フラグを書き込む
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - MonitoringEngine: これらの監視をポーリングでまとめて実行
  - SQLite ベースの監視 DB 初期化 / 操作層 (monitoring_db)
  - Streamlit ダッシュボード表示スクリプト
- portfolio/
  - 候補選定（select_candidates）
  - 重み計算（等分配 / スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、集約キャップ、リスクベース等）
- research/
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - DuckDB を利用して prices_daily / raw_financials などから計算
- ai/
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄ごとに ai_score を DuckDB に書き込み
  - regime_detector.score_regime: ETF の MA200 乖離とマクロ記事センチメントを合成して market_regime を算出/永続化
- tools/
  - paper_verification_report: paper_trading の SQLite（data/paper_trading.db）を参照して検証レポートを出力

セットアップ手順
----------------

前提
- Python 3.10+ 推奨（typing の構文を利用）
- DuckDB, psutil, requests, openai, streamlit 等の外部パッケージが必要

手順（開発環境向けの例）
1. リポジトリルートへ移動（この README はプロジェクト直下を想定）
2. 仮想環境作成 & 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt がない場合は個別に）
   - pip install duckdb psutil requests openai streamlit
   - （テストや追加機能により他パッケージが必要になる場合があります）
4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くことで自動読み込みされます（load順: OS > .env.local > .env）。
   - 重要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI の API キー（ai モジュール使用時必須）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各 API トークン（Execution 使用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用（任意）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
     - PID_FILE_PATH / KILL_FLAG_PATH：プロセス管理用ファイルパス
     - PAPER_FILL_MODE: paper_trading の約定動作（instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
   - .env.example がある場合はそれを参考にしてください（本リポジトリには .env.example を期待しています）。

注意事項
- process priority / CPU affinity の設定は OS 権限に依存します。psutil の呼び出しで AccessDenied が出る場合はログに警告が出てスキップされます。
- AI 機能を使用するには OPENAI_API_KEY が必要。API 料金・レート制限に注意してください。

使い方
------

実行コマンド例（プロジェクトルートから、src を PYTHONPATH に含める）

- ExecutionEngine を起動（デフォルトは KABUSYS_ENV による切替）
  - PYTHONPATH=src python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存され、本番 DB と分離されます。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを利用します。

- Monitoring ポーリングを開始
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path を参照（KABUSYS_ENV に依らず）

- Streamlit ダッシュボードを起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既に MonitoringEngine が監視 DB を作成・更新していることが前提

- Paper Trading 検証レポートを生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで paper_trading DB を指定可能（デフォルト: data/paper_trading.db）

- AI モジュールをプログラムから呼び出す
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date, api_key を受け取る関数です。
  - 例（REPL やスクリプト）:
    - from pathlib import Path; import duckdb; from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026,4,10), api_key="sk-...")

- 開発用単体実行（監視エンジンの1回実行など）
  - MonitoringEngine インスタンスをテストし、run_once を呼ぶことで一回分の監視処理を実行できます（ユニットテスト向け設計）。

動作上の注記
- KABUSYS_ENV による振る舞い:
  - development: 開発用（多くのチェックは有効）
  - paper_trading: ブローカーはモック、DB は PAPER_TRADING_SQLITE_PATH で分離
  - live: 本番運用
- Monitoring は常に本番 sqlite_path を使用する設計（監視は本番 DB を監視するべきため）
- OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証等の耐障害処理が組み込まれていますが、料金・速度・API 変更には注意してください。

ディレクトリ構成
----------------

代表的なファイルツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / 設定管理
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュースセンチメント（OpenAI）
      - regime_detector.py          — 市場レジーム判定（MA + LLM）
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連コード: broker, order_repository, etc.)
    - monitoring/
      - monitoring_db.py            — SQLite schema + MonitoringDB
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/ (想定される実行時データディレクトリ)
      - kabusys.duckdb (DuckDB、デフォルト path: data/kabusys.duckdb)
      - monitoring.db (監視 SQLite、デフォルト path: data/monitoring.db)
      - paper_trading.db (paper_trading 用 SQLite、PAPER_TRADING_SQLITE_PATH)

補足・運用上のヒント
--------------------
- .env の自動読み込みは config.py による実装で、プロジェクトルートの .git または pyproject.toml を基準に探索します。CI/テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PID ファイル / kill.flag を使用したプロセス制御が組み込まれています。Execution 起動時に kill.flag をクリアする設定（KILL_FLAG_CLEAR_ON_START）を ON にすると、古いフラグを起動時に削除できます。
- Streamlit を使う際は開発環境の Python 仮想環境内で実行するか、path 解決に注意してください。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）はリサーチ・AI 機能で必要です。データ投入がなければ一部の機能は動作しません（null / 空チェックは各モジュールで取り扱い済み）。

ライセンス / 貢献
-----------------
この README はコードベースの概要説明用です。実際のライセンスやコントリビュート手順はリポジトリのトップレベルにある LICENSE や CONTRIBUTING を参照してください（存在しない場合はプロジェクト管理者に問い合わせてください）。

以上。運用時の具体的な質問（例: 特定の設定項目の意味、実行時エラーのトラブルシュート、テスト方法など）があれば教えてください。必要に応じて README に追記します。