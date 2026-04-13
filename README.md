# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには、実行エンジン、監視コンポーネント、ポートフォリオ構築・サイズ計算、リサーチ（ファクター計算）、および AI を使ったニュースセンチメント評価など、取引運用に必要な主要機能が含まれます。

以下はこのコードベースの概要、機能、セットアップ・使い方、ディレクトリ構成の説明です。

## プロジェクト概要
- 目的：日本株の自動売買運用を支える実行エンジンおよび運用監視ツール群を提供する。
- 主なコンポーネント：
  - ExecutionEngine（発注・リスク管理・再突合）
  - Monitoring（システム状態・注文滞留・リスク監視・アラート）
  - Portfolio（候補選定・配分・ポジションサイズ計算・リスク調整）
  - Research（ファクター計算・IC/統計解析）
  - AI（ニュース NLP によるセンチメント評価、レジーム判定）
  - Tools（Paper Trading 検証レポート生成など）
- DB：
  - SQLite を監視ログ/発注ログの永続化に使用（デフォルト: data/monitoring.db）
  - DuckDB を時系列データ・リサーチ用途に使用（デフォルト: data/kabusys.duckdb）
- 環境切替：
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切替可能。
  - paper_trading 時は発注はモックブローカーを使い、paper_sqlite_path（デフォルト data/paper_trading.db）に分離して記録。

## 機能一覧
- 実行（Execution）
  - 発注フロー管理（OrderManager, OrderRepository 等）
  - ブローカーとの再突合（Reconciler）
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス死活・データ鮮度を監視し system_status に記録
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限を監視しリスクイベント記録
  - KillSwitch：条件に応じてフラグファイルを書き実行エンジンを停止させる
  - AlertManager：LINE Push による通知（トークン未設定時はログに留める）
  - Streamlit ダッシュボードで監視データ参照可能
- ポートフォリオ構築（Portfolio）
  - 候補選定（スコア順）、等金額・スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、aggregate cap）
- リサーチ（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由で prices_daily 等を参照）
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリ
- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini 想定）でセンチメント化し ai_scores に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- ユーティリティ
  - .env 自動ローディング（プロジェクトルートの .env / .env.local を読み込み）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - Paper Trading 検証レポート生成ツール（console 出力）

## セットアップ手順（ローカル開発向け）
前提：Python 3.10+ を推奨（PEP 604 の型記法などを使用）

1. リポジトリをクローン、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 主要依存（最小例）:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数（デフォルト値 / 必須は下記を参照）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合は必須）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - MONITOR_POLL_INTERVAL（監視ループ間隔、秒。デフォルト 60。run_monitoring から読み込み可能）
   - 注意: Settings クラスは必須項目未設定時に ValueError を出します（JQUANTS_REFRESH_TOKEN 等）。

4. データディレクトリの準備
   - data ディレクトリを作成（DB ファイルの出力先）
     - mkdir -p data

## 使い方（代表的な実行例）
以下はパッケージ内スクリプトの起動方法。いずれも仮想環境を有効にした上で実行します。

- 監視ポーリングを単独で起動（SystemMonitor の簡易ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を設定（秒単位）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 実行中は monitoring DB（settings.sqlite_path）を使用して system_status 等を書き込みます。
  - 監視は KABUSYS_ENV にかかわらず production sqlite_path を使用する設計です（監視は本番 DB を参照）。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper trading 用 DB（PAPER_TRADING_SQLITE_PATH）に分離して記録されます。
  - 実行時にプロセス優先度を high に設定します（psutil による best-effort）。

- Streamlit ダッシュボードを起動（監視 DB を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB にアクセスできない場合はエラー表示（MonitoringEngine を先に起動してください）。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - レポートは稼働率・注文成功率・送信率・レイテンシ（P95）などを計算し PASS/FAIL 判定を出力します。

- AI 関連（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定することで、以下の API を利用できます（プログラム的に呼び出し）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - AI 呼び出しは外部 API（OpenAI）に依存し、429/タイムアウト/5xx に対して指数バックオフのリトライ実装あり。失敗時は安全側のフォールバックをする設計です。

## 重要な挙動／注意点
- .env 自動読み込み：
  - プロジェクトルート（.git または pyproject.toml を基準）を検出し `.env` と `.env.local` を順に読み込みます。
  - OS 環境変数は保護され、.env.local は既存 OS 環境変数を上書きできますが protected なキーは書き換えません。
- 監視 DB（monitoring）は常に settings.sqlite_path（production 想定）を使用する設計です。paper_trading のみ発注 DB を分離します。
- MONITOR_POLL_INTERVAL は run_monitoring でポーリング間隔を上書きできます。1 秒未満や 0 は無効でデフォルト 60 秒にフォールバックします。
- Kill switch はファイル data/kill.flag（デフォルト）に理由文字列を書き、ExecutionEngine がこのファイルの存在を検知して安全に停止する仕組みです。
- OpenAI API キーは必須設定箇所があるため、AI 機能を使用する場合は環境変数 OPENAI_API_KEY を設定してください。未設定時は API 呼び出しが ValueError を投げます。
- プロセス優先度設定や CPU affinity は OS と権限に依存します。権限不足時は WARNING を出してスキップします。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/設定読み込み（.env 自動ロード・Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE Push 通知ラッパー
  - monitoring_engine.py — 各モニタを束ねるポーリング実行ロジック
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 発注フロー管理
  - reconciler.py — 起動時の注文・ポジション再突合
  - （その他: broker_factory, execution_engine, order_repository 等が想定される）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 配分計算（純粋関数）
  - position_sizing.py — 発注株数算出（単元丸め・リスク制約含む）
  - risk_adjustment.py — セクター上限 / レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュース文章を LLM でスコア化して ai_scores に書き込み
  - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（補足）data/ ディレクトリ（コード外）：DuckDB / SQLite DB ファイルや pid/flag ファイルが置かれる想定（デフォルトパスは Settings に定義）。

## よく使うコマンドまとめ（例）
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン（本番/シミュレーション）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

## 開発／拡張のヒント
- DuckDB 接続を受け取り SQL + Python でファクター等を計算する設計のため、データスキーマ（prices_daily, raw_financials, raw_news など）に合わせたデータ投入が必要です。
- AI 呼び出し部分は関数単位でモック可能（テスト時は _call_openai_api を patch する設計）。
- DB スキーマの後方互換を意識してマイグレーションコード（monitoring_db.init_monitoring_db 内）を確認してください（カラム追加処理済み）。

---

以上が本コードベースの README（概要・セットアップ・使い方・構成）です。追加で README に載せたい運用手順（例：デプロイ手順、systemd ユニット例、CI 設定、詳細な環境変数一覧表）などがあれば教えてください。必要に応じて追記します。