README — KabuSys（日本株自動売買システム）
====================================

概要
----
KabuSys は日本株の自動売買／研究／監視を想定した小規模なシステム群です。  
主な目的は次のとおりです。

- 自動売買の実行エンジン（ExecutionEngine）
- 発注・注文状態管理（OrderManager / OrderRepository）
- 発注検証（Reconciler）とリスク管理（RiskManager）
- ポートフォリオ構築（候補選定・重み算出・株数決定・リスク調整）
- データ解析・研究（ファクター計算、将来リターン、IC 等）
- AI を使ったニュースセンチメント（OpenAI）と市場レジーム判定
- 監視／アラート（SQLite に監視ログを保存、LINE へ通知、Streamlit ダッシュボード）
- Paper Trading モード（本番 DB と分離して検証）

主な設計方針:
- DuckDB（時系列・ファクタ計算）と SQLite（監視・注文ログ）を併用
- 環境変数 / .env による設定（自動ロード機能あり）
- Paper Trading と Live を環境変数で切替え（KABUSYS_ENV）
- フェイルセーフ重視（API 失敗時のフォールバック、冪等操作、部分失敗の保護）

機能一覧
--------
- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須 / 任意設定のラッパー
- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用して paper DB に記録
  - プロセス優先度設定、DB 初期化、各コンポーネント組み立て
- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor を定期実行（MONITOR_POLL_INTERVAL で調整）
  - 監視データは本番 sqlite_path に書き込む（環境に依存せず本番 DB を使用）
- 監視ライブラリ（kabusys.monitoring）
  - SystemMonitor: CPU/Memory/Disk、プロセス存在、データ鮮度
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイル書き込みで ExecutionEngine 停止シグナル
  - AlertManager: LINE push による通知（クールダウン管理）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（score 降順）
  - 等金額/スコア重み配分
  - セクターキャップ適用、レジーム乗数
  - 株数決定（リスクベース、等配分、単元株丸め、aggregate cap）
- 研究モジュール（kabusys.research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）算出、統計サマリー
  - DuckDB 接続を受け取り SQL+Python で計算
- AI モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄ごとにセンチメント算出 → ai_scores へ書込
  - regime_detector.score_regime: ETF ma200 とマクロニュース（LLM）を合成して日次レジーム判定
  - API エラー時のリトライ・フォールバック実装あり
- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポートを標準出力に表示
- ユーティリティ
  - process_priority: Windows / POSIX に対応したプロセス優先度設定、CPU affinity

セットアップ手順
---------------
前提
- Python 3.10+（注: typing の | None 等を使用）
- SQLite（標準ライブラリで OK）
- DuckDB（Python パッケージ）
- 必要パッケージ（例）
  - duckdb, psutil, requests, openai, streamlit

例: 仮想環境とパッケージ導入
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb psutil requests openai streamlit

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 起動モード: development | paper_trading | live（デフォルト: development）
  - paper_trading: 実行時に paper DB を使用
- PAPER_FILL_MODE — Paper Trading の約定動作（instant|partial|never|reject、デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

.env の自動ロード
- プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動読み込みします。
- テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要コマンド）
---------------------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒指定できます（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading DB を使用（本番 DB と分離）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数を上書き）

- AI モジュールの利用（プログラム内から）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...") などで呼び出し可能

- 設定参照（プログラム内）
  - from kabusys.config import settings
  - settings.sqlite_path, settings.duckdb_path, settings.is_paper, など

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                        # 環境変数 / .env ローダー、Settings
    run_monitoring.py                # SystemMonitor ポーリング起動スクリプト
    run_execution.py                 # ExecutionEngine 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py   # Paper Trading 検証レポートツール
    monitoring/
      __init__.py
      monitoring_db.py               # SQLite スキーマ定義 + MonitoringDB
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    execution/
      order_manager.py
      reconciler.py
      (その他: broker_factory, order_repository, execution_engine 等 — 実装の一部は省略)
    utils/
      __init__.py
      process_priority.py

データ / DB
- デフォルトファイル:
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- monitoring_db.init_monitoring_db() によって必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）が作成されます（冪等）。

注意事項 / 運用メモ
-------------------
- Paper Trading と Live は DB を分離するよう設計されています。KABUSYS_ENV を必ず確認してください。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライ・フォールバックの仕組みがありますが、キー未設定だと例外となる箇所があります。
- run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番監視 DB）を使用します。つまり監視は常に本番 DB を監視します。
- ExecutionEngine の停止は kill.flag（デフォルト data/kill.flag）で行う仕組みです。KillSwitch はリスク条件に応じてファイルを作成します。
- process_priority.set_process_priority は管理者権限が必要になる場合があります。失敗した場合はログに警告を出してスキップします。
- DuckDB の executemany に関する互換性や空リストの扱いなど、実行時の DB バージョン差分に注意してください（コード中に互換性対応の記述あり）。

サンプル .env（例）
------------------
以下は最小限の例です（本番用の秘密情報は安全に管理してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=                    # 通知を使う場合に設定
LINE_USER_ID=

貢献・拡張案
------------
- stocks マスタを導入して銘柄ごとの lot_size を扱う（position_sizing の TODO）
- Order / Broker 周りのエラーハンドリング強化とユニットテスト拡充
- Streamlit ダッシュボードの表示強化（時系列チャート、フィルタ）
- CI で DuckDB/SQLite を使った統合テストを追加

問い合わせ
----------
この README はコードベースの解析に基づいて生成しています。実運用前に以下を確認してください:
- 実際の requirements.txt / pyproject.toml に記載された依存関係
- Broker API 周り（認証やリクエスト仕様）
- セキュリティ（API キー・パスワードの取り扱い）

--- 
（以上）