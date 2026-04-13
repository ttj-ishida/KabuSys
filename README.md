# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、発注エンジン、監視、リサーチ、AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

## プロジェクト概要
KabuSys は以下を目的としたモジュール群で構成されています。

- データ処理とファクター計算（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注管理・Execution Engine（ブローカー抽象化、paper/live 切替）
- 監視機能（システム状態、注文滞留、リスク監視、アラート）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、テスト容易性・フェイルセーフ・ルックアヘッドバイアス回避に配慮されています（多くの処理は外部 API を参照せず DB を主体に実行、API 呼び出しは失敗時にフォールバックする等）。

## 機能一覧
- ポートフォリオ構築
  - 候補選定（スコア/ランク）
  - 等重・スコア加重の重み算出
  - リスク調整（セクター上限、レジーム乗数）
  - Position sizing（リスクベース／等配分等、単元丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計要約
- Execution（発注）
  - Broker クライアント抽象化（paper_trading: MockBroker）
  - OrderManager、Reconciler（再起動時の同期）
  - RiskManager（発注時の各種制約）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク/プロセス検査、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルで ExecutionEngine を停止
  - AlertManager: LINE Push を用いた通知（クールダウン管理）
  - Streamlit ダッシュボード（監視可視化）
- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュースを銘柄ごとにスコア化
  - regime_detector: MA 乖離とマクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポート出力

## 前提（依存パッケージ）
主に以下のパッケージを使用します（環境やバージョンにより追加が必要になる場合があります）。

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai (AI 機能利用時)

インストール例（仮の requirements が無い場合）:
pip install duckdb psutil requests streamlit openai

※ 実運用ではプロジェクトの requirements.txt を用意して pip install -r requirements.txt を推奨します。

## セットアップ手順
1. リポジトリをクローンしてプロジェクトルートに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
4. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 主要な環境変数は下記「環境変数 / 設定」を参照
5. データディレクトリを作成
   - mkdir -p data
6. 必要に応じて DuckDB / SQLite の初期データを用意

自動的な .env 読み込みについて:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` が起動時に読み込まれます。
- OS 環境変数の優先順位が高く、`.env.local` は `.env` を上書きします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 環境変数 / 設定（主要なもの）
（Settings クラスで参照されているプロパティを抜粋）

- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker が使われ、DB は分離されます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API を使う場合に必要（AI 機能）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。0 以下・無効値はデフォルトにフォールバック。
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

## 実行方法（代表的なコマンド）
- 監視ループ（SystemMonitor の簡易起動）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は run_monitoring 内の注記の通り、Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します

- Execution Engine（発注ループ）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading とすると MockBroker を使用し DB を data/paper_trading.db に分離
  - 起動直後にプロセス優先度が "high" にセットされます（psutil が必要）
  - ExecutionEngine は設定に従って発注・リスク管理を行います

- Streamlit ダッシュボード（監視の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数で渡すか、api_key 引数で指定します

## 運用上の注意
- run_monitoring のドキュメントにある通り、監視は常に本番の sqlite_path を使います。テストや paper_trading 環境で監視を分離したい場合は設定に注意してください。
- ExecutionEngine を停止する安全手段として KillSwitch（data/kill.flag）を使用します。kill.flag は存在すると Execution 側で停止シグナルとして扱われます。
- .env の自動読み込みはプロジェクトルートを検出して行われます。CI / テスト中に干渉する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を使う処理はネットワークエラーやレート制限を考慮してリトライやフォールバックを実装していますが、API キー未設定だと実行不可になります（呼び出し側で ValueError が発生）。

## ディレクトリ構成（主要ファイルと責務）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper/live 切替）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数計算・投下資金調整
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化層（テーブル初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag を管理するユーティリティ
    - alert_manager.py — LINE によるプッシュ通知管理
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベース監視ダッシュボード
  - execution/
    - order_manager.py — 発注フローと状態遷移の外向き API
    - reconciler.py — 起動時の注文・ポジションの突合せ
    - （その他 broker/ risk_manager 等のモジュール群）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/（実データ・DB は通常ここに配置）
    - data/kabusys.duckdb（デフォルト）
    - data/monitoring.db（監視用 sqlite、デフォルト）
    - data/paper_trading.db（paper_trading 用 sqlite、デフォルト）

（上記はソース内ドキュメント・モジュール名を基に要約しています。各モジュール内の docstring を参照すると詳細な設計意図が書かれています。）

---

必要であれば README に追加で「運用チェックリスト」「よくあるエラーと対処」「詳細な .env.example」などを追記できます。どの情報を拡張しましょうか？