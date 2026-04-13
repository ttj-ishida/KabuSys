# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ＋実行スクリプト群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、注文発行・リコンシリエーション、監視・アラート、Paper Trading の検証ツール、および AI を使ったニュース／レジーム判定などを含むモジュール群で構成されています。

以下ではプロジェクト概要、機能一覧、セットアップ手順、主要な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

- モジュール化された自動売買プラットフォームのコア機能を提供します（研究用ファクター計算、ポートフォリオ構築、発注ロジック、監視・アラート、Paper Trading 用ツール、LLM を使ったニュースセンチメント／レジーム判定など）。
- SQLite（監視ログ等）、DuckDB（時系列・ファクターデータ）をデータ層に使用します。
- 本番（live）・ペーパー（paper_trading）・開発（development）環境を環境変数 `KABUSYS_ENV` で切り替え可能です。
- OpenAI API を利用する機能（ニュース NLP / レジーム判定）は API キーが必要です。

---

## 主な機能一覧

- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- portfolio
  - 候補選定、等配分・スコア配分、リスク調整（セクター制限、レジーム乗数）、ポジションサイズ計算
- execution（発注系）
  - OrderManager / OrderRepository / Reconciler を含む発注管理・再同期間合処理（実際の broker 実装は抽象化）
  - Paper Trading モードでは MockBrokerClient を用いて `data/paper_trading.db` に記録（本番 DB と分離）
- monitoring（監視系）
  - SystemMonitor: CPU／メモリ／ディスク／データ鮮度／PID 生存チェック
  - TradeMonitor: 滞留注文・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ記録（kill flag による Execution 停止トリガー）
  - AlertManager: LINE Push によるアラート送信（クールダウン付き）
  - Streamlit ダッシュボード（read-only）
- tools
  - Paper Trading 検証レポート生成（成功率、稼働率、P95 レイテンシ等を算出）
- ai
  - news_nlp: OpenAI を用いたニュース記事の銘柄別センチメント評価 → `ai_scores` へ書込
  - regime_detector: ETF とマクロ記事を合成して日次で市場レジーム判定

---

## セットアップ手順

前提: Python 3.9+（モジュールの typing / 機能に依存）。プロジェクトルートは .git または pyproject.toml を含むディレクトリを想定。

1. 仮想環境作成（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 依存パッケージインストール（例）
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトで requirements.txt があれば `pip install -r requirements.txt`）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  # AI 機能を使う場合に必須
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject  (デフォルト: instant)
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO

   - 例 .env:
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     ```

4. データディレクトリの作成
   - mkdir -p data

---

## 使い方（主要スクリプト・コマンド）

※ すべてのスクリプトはパッケージとして import 可能な形で実装されています。パッケージルート（src が PYTHONPATH にある場合）で実行してください。

- Execution Engine（発注セッション起動）
  - Paper Trading モードで実行する例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 本番モード（注意して使用）
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 実行時の挙動:
    - プロセス優先度を "high" に設定（可能な場合）
    - sqlite（paper_trading.db または monitoring.db）と DuckDB に接続
    - BrokerClientFactory により broker を生成（paper_trading では MockBrokerClient）
    - ExecutionEngine.run_session() を実行

- Monitoring（ポーリング監視）
  - デフォルトは 60 秒間隔（環境変数で上書き可）
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング
  - 実行:
    - python -m kabusys.run_monitoring
  - 備考:
    - Monitoring は環境（KABUSYS_ENV）に関わらず production の sqlite_path（`SQLITE_PATH`）を使用します。
    - 起動時に `pid_file_path` を参照してプロセス生存チェック等を行います。

- Paper Trading 検証レポート（CLI ツール）
  - 期間を指定して検証レポートを生成:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイルを明示する:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード（読み取り専用）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB が存在しない / 開けない場合はエラーメッセージが表示されます（MonitoringEngine を先に起動してログを作成してください）。

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キー（env `OPENAI_API_KEY` または関数引数）を設定した上で、コード内 API を呼び出せます。
  - 例: スクリプトや REPL から
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026, 4, 10))
  - 同様に regime_detector.score_regime を呼んで market_regime テーブルへ書き込めます。

---

## 設定・環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視ログ（monitoring）用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（MockBroker の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill flag を自動クリアするフラグ（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` および `.env.local` を読み込みます。OS 環境変数が優先され、`.env.local` は上書き（override）で読み込まれます。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 実装上の注意事項 / ユーザー向けメモ

- Monitoring は常に `SQLITE_PATH` の DB を使います（paper_trading と分けたい場合は別途 DB を指定してください）。
- ExecutionEngine は paper_trading モード時に `PAPER_TRADING_SQLITE_PATH` を使用して DB を分離します。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存（psutil を使用）。権限不足の場合は警告ログを出してスキップします。
- OpenAI 呼び出しはエラー・レート制限時に指数バックオフでリトライする実装がありますが、API キーや利用制限に注意してください。
- DuckDB を使ったリサーチモジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。必要なデータ投入やスキーマ準備は別に行う必要があります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数/設定管理（.env 自動読込含む）
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py      — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP / OpenAI 連携
    - regime_detector.py                — レジーム判定（ETF + マクロ記事）
  - research/
    - __init__.py
    - factor_research.py                — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py            — 将来リターン・IC・統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py              — 候補選定 / ウェイト計算
    - risk_adjustment.py                — セクターキャップ / レジーム乗数
    - position_sizing.py                — 発注株数計算・スケールダウン
  - execution/
    - order_manager.py                  — 注文発行/状態管理
    - reconciler.py                     — 起動時リコンシリエーション
    - (その他 broker_factory 等)
  - monitoring/
    - __init__.py
    - monitoring_db.py                  — SQLite テーブル作成・永続化レイヤ
    - system_monitor.py                 — システム状態・データ鮮度監視
    - trade_monitor.py                  — 滞留注文・約定価格異常監視
    - risk_monitor.py                   — ドローダウン・ポジション監視
    - kill_switch.py                    — kill.flag 書き込みユーティリティ
    - alert_manager.py                  — LINE Push 通知
    - monitoring_engine.py              — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py            — Streamlit ダッシュボード（read-only）
  - utils/
    - __init__.py
    - process_priority.py               — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (想定されるデータ格納場所)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## よくある操作例

- 監視をデーモン的に実行（簡易）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Paper Trading で発注セッションを1回起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（ローカル）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 追加情報 / 開発者向け

- テストや CI では `.env` 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると安定します。
- DuckDB SQL クエリは大きめのウィンドウで過去データを参照する設計になっているため、prices_daily 等のテーブルは十分な履歴を揃えてください。
- ai.news_nlp や ai.regime_detector は外部 API を呼び出します。テストでは `_call_openai_api` をモック化してユニットテストを実施してください（コードにモック用注記あり）。
- `monitoring_db.init_monitoring_db` は冪等でスキーマを作成 / 必要に応じてマイグレーション（列追加）を行います。

---

この README はコードベースの主要点をまとめたものです。細かい挙動や設計の背景は各モジュールの docstring / コメントを参照してください。必要であれば各機能の API 使用例や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）の補足 README を作成できます。