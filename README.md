KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／研究／監視を想定した Python パッケージ群です。本プロジェクトは以下の主な機能群を含みます。

- 注文・執行管理（ExecutionEngine 周辺）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- ファクター計算・リサーチ（DuckDB を使ったファクター計算・IC 等）
- AI を用いたニュースセンチメント評価（OpenAI API 経由）
- 監視（システム状態・注文滞留・リスク監視）とダッシュボード（Streamlit）
- 運用補助ツール（Paper Trading 検証レポート等）

主な設計方針
- DuckDB / SQLite を用いたローカル DB を中心に計算・永続化を行う
- 本番／ペーパー（paper_trading）モードの分離
- ルックアヘッドバイアス回避のため日付参照に注意（多くの関数で date を引数で受ける）
- 外部 API 呼び出し（OpenAI 等）は失敗しても安全にフェイルオーバーする実装

機能一覧
--------
- Execution
  - 注文作成・送信・同期・リコンシリエーション機能（OrderManager / Reconciler）
  - ペーパー取引モードでは MockBroker を使い本番 DB と分離
- Portfolio
  - 候補選定（select_candidates）
  - 等金額／スコア重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクターキャップ適用 / レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計（feature_exploration）
- AI
  - ニュースセンチメントのスコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を利用（API キー必須）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - MonitoringDB（SQLite）へのログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch（フラグファイルを書いて ExecutionEngine を停止させる）
  - LINE Push によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
- Tools
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提: Python 3.10+（型ヒントに | を使うため）を使用してください。

1. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 代表的な依存: duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使ってください）

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化）。
   - 主要な環境変数（デフォルト値や必須項目）:
     - KABUSYS_ENV: environment（development / paper_trading / live）、デフォルト: development
     - JQUANTS_REFRESH_TOKEN:（必須）J-Quants API 用トークン
     - KABU_API_PASSWORD:（必須）kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI 利用時に必須（AI モジュールを使う場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: KillSwitch 用フラグファイルパス（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE: paper_trading の約定動作（instant / partial / never / reject）、デフォルト: instant
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

使い方
------
実行系（ExecutionEngine）
- 本番／検証モードに応じて KABUSYS_ENV を設定して起動します。
  - 本番想定:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - ペーパー取引:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - この場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番監視 DB とは分離されます。
- 実行時に最初にプロセス優先度を "high" に設定します（psutil を利用）。権限不足などで失敗した場合は警告が出ます。

監視（Monitoring）
- 監視ポーリングループを起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（例: export MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring
  - 注意: run_monitoring は monitoring 用に Settings.sqlite_path（監視用 DB）を環境にかかわらず使用します（コード設計上の仕様）。

Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示するダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- data/paper_trading.db を集計して期間レポートを出力します:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI モジュール
- ニューススコアリング:
  - kabusys.ai.score_news（内部で OpenAI を呼ぶ）
  - 必須: OPENAI_API_KEY（引数で渡すことも可能）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime
  - 必須: OPENAI_API_KEY（記事がない場合は LLM 呼び出しをスキップして中立値で継続）

DB 初期化
- run_execution / run_monitoring の起動時に init_monitoring_db を呼び出して必須テーブルを冪等に作成します。手動で初期化したい場合は MonitoringDB.init 互換の関数を呼べば OK（init_monitoring_db(sqlite_conn)）。

主な設定例
- 開発（ローカル）:
  - KABUSYS_ENV=development
  - .env に最低限 KABU_API_PASSWORD / JQUANTS_REFRESH_TOKEN を設定
- ペーパー（安全に検証）:
  - KABUSYS_ENV=paper_trading
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - PAPER_FILL_MODE=instant

ディレクトリ構成（抜粋）
--------------------
以下は本リポジトリの主要ファイル・モジュールの概観（実際のリポジトリにはさらにファイルが存在する可能性があります）。

- src/kabusys/
  - __init__.py             — パッケージ初期化、__version__
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_monitoring.py       — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト（paper_trading に対応）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール（CLI）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定（リスクベース等）
    - risk_adjustment.py     — セクター制限 / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + macro sentiment）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag を書くロジック
    - alert_manager.py       — LINE Push によるアラート送信
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py      — 注文の状態遷移を扱うマネージャ
    - reconciler.py         — 起動時の復旧・リコンシリエーション
    - （その他 broker / order_repository 等の実装）
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ
  - research/              — リサーチ関連（factor_research 等）
  - monitoring/            — 監視関連（上にまとめ）

注意事項・運用メモ
-----------------
- Monitoring の DB（SQLITE_PATH）は run_monitoring が常に使用します。run_execution は KABUSYS_ENV が paper_trading の場合、PAPER_TRADING_SQLITE_PATH を使用して DB を分離します。
- MONITOR_POLL_INTERVAL の値は 1 秒以上にしてください（0 や負値は無効でデフォルト 60 秒にフォールバックします）。
- PAPER_FILL_MODE（instant / partial / never / reject）は paper_trading 時の MockBroker の約定挙動を制御します。不正な値は例外になります。
- OpenAI を利用する機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・バックオフを実装していますが、API 制限や料金に注意してください。
- process_priority の設定は OS に依存します。psutil による権限不足で失敗することがあります（警告ログが出ますが処理は継続します）。
- KillSwitch はファイルベースのシグナル機構です。flag ファイルを書き込むと ExecutionEngine 側が検出して安全に停止する設計になっています。

サポート／拡張
---------------
- DuckDB のテーブル（prices_daily, raw_financials, raw_news, ai_scores, market_regime など）にはデータ投入が必要です。データパイプライン周り（kabusys.data.pipeline 等）を用意して取り込みます。
- 将来的な拡張案として、銘柄別の単元（lot_size）や手数料モデル、複数ブローカー対応などが想定されています。

ライセンス等
-------------
- 本ドキュメントではライセンス表記は含めていません。実プロジェクトでは LICENSE ファイルを追加してください。

以上。運用や導入にあたって不明点があれば、どの機能について詳しく知りたいか教えてください。README を用途（開発者向け / 運用者向け）に合わせて調整します。