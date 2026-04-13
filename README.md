# KabuSys

日本株向け自動売買システムのコードベース README（日本語）

この README はリポジトリ内の主要モジュールをまとめたもので、ローカルでのセットアップ・起動方法、主要機能、ディレクトリ構成、環境変数の説明を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を含むパッケージです。主な責務は以下の通りです。

- 取引執行（ExecutionEngine、OrderManager、Broker クライアントの抽象化）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、ログ永続化）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターンや IC 計算）
- AI 補助（ニュースのセンチメントスコアリング、レジーム判定）
- ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計方針として、DuckDB / SQLite を用いたデータ処理、外部 API 呼び出し（ブローカー・OpenAI 等）は抽象化され、フェイルセーフやリトライ、冪等性（IDEMPOTENCE）を意識した実装がされています。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 状態同期（OrderManager, Reconciler）
  - Paper Trading による本番と分離されたモック実行
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留・約定価格異常の検出
  - ドローダウン / ポジション上限の監視と kill.flag による停止シグナル
  - LINE へ一方向通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア降順）、等重・スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）
- Research
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC（Spearman の ρ）、ファクター統計サマリ
- AI
  - ニュースを OpenAI に投げて銘柄毎のセンチメントスコア算出（ai_scores へ書込）
  - マクロニュース＋ETF MA を使った市場レジーム判定（market_regime へ保存）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視データの可視化）

---

## セットアップ手順（ローカル）

以下は開発・検証用の基本セットアップ手順です。プロダクションデプロイ方法や CI はここに含みません。

1. Python 仮想環境を作成・有効化（例: pyenv / venv）
   - Python 3.10+ を推奨（コード上の型ヒントや機能を想定）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージのインストール
   - 主要依存（コードから推測）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - requirements.txt がある場合は:
     - pip install -r requirements.txt
   - 最低限の例:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリ作成（デフォルト）
   - data/ ディレクトリを作成しておくと便利:
     - mkdir -p data

4. 環境変数設定
   - .env をプロジェクトルートに置くと自動で読み込まれます（既存の OS 環境変数は保護されます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数は以下参照（次節で詳細）。

---

## 環境変数（主要）

Settings クラス（kabusys.config）で参照される主な環境変数と意味：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（AI モジュール）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（AlertManager）
- LINE_USER_ID — LINE Push 宛先ユーザー ID
- KABUSYS_ENV — 環境識別子（"development" | "paper_trading" | "live"、デフォルト: development）
  - paper_trading の場合、専用の paper DB を使用して本番 DB と分離
- PAPER_FILL_MODE — Paper Trading の約定モード（"instant" | "partial" | "never" | "reject"、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL — SystemMonitor を直接起動する run_monitoring スクリプトでのポーリング間隔（秒。デフォルト: 60）
- LOG_LEVEL — ログレベル（"DEBUG","INFO",...）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値（%）

例（.env）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 起動方法・使い方

主要な実行スクリプトと使い方を示します。モジュールはパッケージとして実行できます（python -m kabusys.xxx）。

1. ExecutionEngine（取引実行）
   - 目的: 実取引（live）または paper_trading の実行
   - 起動:
     - python -m kabusys.run_execution
   - KABUSYS_ENV が `paper_trading` の場合:
     - MockBrokerClient が使われ、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。
   - 起動時にプロセス優先度を "high" に設定します（可能な場合）。

2. System Monitor（継続監視ループ）
   - 目的: 定期的にシステム状態を記録し、監視ログを永続化
   - 起動:
     - python -m kabusys.run_monitoring
   - ポーリング間隔:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
   - 注意:
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

3. Paper Trading 検証レポート
   - 目的: Paper Trading の検証（稼働率、注文成功率、レイテンシ等）
   - 起動:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. Streamlit ダッシュボード（監視 UI）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で monitoring.db を参照し、Overview/Positions/Orders/System タブで可視化します。

5. AI モジュール（ニュース NLP / レジーム判定）
   - ニュースセンチメント集計:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - OpenAI API キー（OPENAI_API_KEY または引数）が必須
     - 呼び出しは DuckDB 接続を受け取ります（raw_news, news_symbols, ai_scores, prices_daily 等を参照）

---

## 重要挙動・運用メモ

- PID ファイル / kill.flag
  - ExecutionEngine は起動時に PID ファイルを書き、SystemMonitor はそのファイルの有無とプロセス存否を監視します。
  - KillSwitch はリスク条件（ドローダウン超過、ポジション数上限超過等）を満たすと kill.flag を書き、ExecutionEngine 側で停止トリガーとして利用できます。
  - Settings で KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に既存の kill.flag をクリアします。

- DB マイグレーション / 冪等性
  - monitoring_db.init_monitoring_db(conn) は冪等でテーブルを作成し、既存 DB に対する簡易マイグレーション（カラム追加）を行います。

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading のとき、paper_sqlite_path（デフォルト data/paper_trading.db）に発注ログ等を記録し、本番 DB と分離します。これによりテスト実行が本番データに影響しません。

- ログレベル
  - Settings.log_level 環境変数で制御可能（"DEBUG", "INFO", ...）。スクリプト内では logging.basicConfig(level=logging.INFO) が設定されていますが、必要に応じて起動方法で上書きしてください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル／モジュールの簡易ツリーです。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - (broker_factory / execution_engine 等、実行に関する他モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定される配置場所)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite、監視ログ)
    - paper_trading.db (Paper Trading 用 SQLite)

---

## 開発・テストに関する補足

- .env のパースは config._load_env_file / _parse_env_line で細かく扱われます。export 形式やクォート、インラインコメント等に対応しています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして自動ロードを無効化できます。
- OpenAI など外部 API 呼び出しは例外や 5xx、429 を考慮してリトライやフェイルセーフ（スコア 0.0 フォールバック等）を実装しています。テストでは API 呼び出し関数を unittest.mock.patch で差し替える設計になっています。
- psutil を使ってプロセス優先度や CPU affinity を設定しますが、権限不足や未対応 OS の場合は警告を出してスキップします。

---

## よくある起動例

- 監視ループ（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution（Paper Trading）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要があれば、README に以下の追記が可能です：
- 要求される Python バージョン明記（実際の CI / pyproject.toml に基づく）
- requirements.txt または poetry/poetry.lock に基づくインストール手順
- 実行フロー図（起動順序: ExecutionEngine <-> MonitoringEngine / KillSwitch）
- 各テーブルスキーマ詳細（monitoring_db に記載あり）

補足・修正したい箇所があれば教えてください。README をプロジェクトの実際の依存ファイル（requirements.txt や pyproject.toml）に合わせて調整できます。