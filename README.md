# KabuSys

日本株自動売買システムの一部を実装したコードベースの README（日本語）。

このリポジトリは、自動売買エンジン（ExecutionEngine）、監視系（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築ロジック、リサーチ機能、及び AI を使ったニュース解析／レジーム判定などのモジュールを含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。本コードベースでは主に以下を提供します。

- Execution: 注文作成・送信・再同期・リコンシリエーション機能（ExecutionEngine 関連）。
- Monitoring: プロセス／リソース監視・注文滞留検出・ドローダウン監視・アラート送信（LINE）や停止フラグ（kill flag）発動。
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限などのポートフォリオ構築ロジック（純粋関数）。
- Research: DuckDB 上でのファクター計算・将来リターン計算・IC（Information Coefficient）など。
- AI: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- Tools: Paper Trading の検証レポート生成スクリプトなど。
- Dashboard: Streamlit を使った監視ダッシュボード。

設計方針として、外部 API 呼び出しや DB 書き込みは明示的に分離され、フェイルセーフ（API失敗時のフォールバック）や冪等性（同一処理を複数回実行しても安全）を重視しています。

---

## 主な機能一覧

- プロセス優先度・CPU affinity の設定（utils/process_priority.py）
- 監視ループ（system resource、データ鮮度、プロセス生存確認）
- 取引監視（滞留注文検出、約定価格異常検出）
- リスク監視（ドローダウン検知、ポジション上限超過検知）
- Kill Switch（kill.flag 書き込みで ExecutionEngine に停止シグナルを発行）
- LINE によるアラート通知（AlertManager）
- ExecutionEngine 起動スクリプト（run_execution.py）：
  - 本番 / paper_trading の切替（paper_trading は MockBroker を使用して専用 DB に記録）
  - Reconciler による復旧処理
- MonitoringEngine / run_monitoring.py による周期的監視
- Streamlit ダッシュボード（監視 DB の可視化）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- DuckDB を使ったファクター計算・リサーチモジュール
- OpenAI を利用したニュースのセンチメント解析（gpt-4o-mini を想定）

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化（例: Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
     - sqlite3（標準ライブラリ）
   - 例:
     - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt がある場合はそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は上書きされません）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（主要なもの）:
   - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
   - KABU_API_PASSWORD — 必須（kabuステーション API 用）
   - OPENAI_API_KEY — AI 機能実行時に必要
   - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
   - LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE — paper_trading の約定振る舞い（instant|partial|never|reject）
   - PID_FILE_PATH, KILL_FLAG_PATH — 各種パス

   例の .env（参考）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

5. 初期データディレクトリ作成
   - mkdir -p data

---

## 使い方（実行例）

リポジトリをソースのまま実行する場合は、プロジェクトルートに `src` を PYTHONPATH に含めるか、パッケージとしてインストールしてください。開発中は簡単に `PYTHONPATH=src` を指定して実行できます。

- Monitoring（監視ループ）を起動
  - 簡易:
    - PYTHONPATH=src python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き（デフォルト 60 秒）。1 未満や不正値は無視されデフォルトにフォールバックします。
  - 監視は常に本番の `SQLITE_PATH` を使用します（KABUSYS_ENV に関係なく）。

- Execution（注文エンジン）を起動
  - PYTHONPATH=src python -m kabusys.run_execution
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録して本番 DB とは完全に分離されます。
    - 実行時、data/stop_requested.flag が存在すると起動を回避します。停止は同ファイルによって行います（run_execution/run_monitoring は stop flag を監視）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます。

- Paper Trading 検証レポート生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で別 DB を指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

- AI 機能
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に API キーが必要。

- 停止・強制停止の仕組み
  - run_* スクリプトはプロジェクトの data 配下にある `stop_requested.flag` をチェックします。手動で作成すれば安全に停止できます。
  - ExecutionEngine の停止を強制したい場合は `kill.flag` を書き込む（KillSwitch が原因で停止）。KillSwitch は `Settings.kill_flag_path` を参照して扱います。

---

## 設定と挙動の詳細

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動で読み込みます。
  - OS の既存環境変数は保護され、`.env` は未設定キーのみ追加、`.env.local` は既存環境変数を除き上書きします。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- KABUSYS_ENV の有効値
  - development / paper_trading / live
  - 不正値は例外を発生させます。

- PAPER_FILL_MODE 有効値
  - instant / partial / never / reject

- DB
  - DuckDB（時系列データ・リサーチ用）: デフォルト `data/kabusys.duckdb`
  - SQLite（監視ログ）: デフォルト `data/monitoring.db`
  - Paper trading 用 SQLite: `data/paper_trading.db`（paper_trading 環境で使用）

- ログレベル
  - LOG_LEVEL 環境変数で指定（INFO デフォルト）。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下の簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 読み込みと Settings
  - run_monitoring.py             — SystemMonitor のポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite テーブル初期化、ログ永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py         — （コード内で参照されるが省略）
    - execution_engine.py         — （本体は省略）
    - broker_factory.py
    - broker_api.py
    - ... (他の実装ファイル)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py                  — OpenAI でニュースをスコアリング
    - regime_detector.py          — 市場レジーム判定
  - data/                          — 実行時に生成するファイル（例: .pid / .flag / sqlite files）
  - tools/
    - __init__.py
    - paper_verification_report.py

（注）実際のリポジトリでは execution以下や data pipeline など、さらに多くのファイルが存在します。上は本 README 作成対象の主要モジュールを要約しています。

---

## 開発・運用上の注意

- paper_trading 環境は本番 DB と完全分離されます。テスト・検証時は必ず KABUSYS_ENV=paper_trading を使用してください。
- OpenAI API を使うモジュール（news_nlp / regime_detector）は API 呼び出しに対してリトライ・フォールバックを実装していますが、API キーの管理には注意してください。
- run_execution.py / run_monitoring.py は `data/stop_requested.flag` を監視します。安全に停止したい場合はこのファイルを作成してください。
- Monitoring の DB マイグレーション（monitoring_db.init_monitoring_db）は冪等であり、起動時に必要なカラムが存在しない場合に追加します。
- Process priority や CPU affinity の設定は OS に依存します（psutil を利用）。権限不足で設定に失敗しても警告のみで処理は継続します。

---

## よく使うコマンドまとめ

- 監視を起動
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- 実行エンジンを起動
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## サポート / 参考

- 環境変数や .env のフォーマットは `src/kabusys/config.py` を参照してください。特にクォート・エスケープの扱いやコメント処理の挙動があります。
- DuckDB 上のスキーマ（prices_daily, raw_financials, raw_news 等）はリサーチ / AI モジュールから参照されます。必要なテーブルを用意してください。
- 追加の設定や運用フロー（デプロイ・監視アラートの閾値調整など）はプロジェクトの運用マニュアルに従ってください。

---

以上が本コードベースの README.md（日本語）になります。必要であれば、実際のインストール用 requirements.txt の例、.env.example のテンプレート、実行時のユースケース別手順（デバッグ／本番デプロイ）などを追記します。どの情報を追加しますか？