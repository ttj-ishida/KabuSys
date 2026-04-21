# KabuSys — 日本株自動売買システム

この README はコードベースの概要、主要機能、セットアップ手順、利用方法、ディレクトリ構成を日本語でまとめたものです。

注意: 実行には各種 API キーやデータベース（DuckDB / SQLite）といった外部資源が必要です。まずはローカル開発向け（KABUSYS_ENV=development / paper_trading）で動作確認することを推奨します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（ポートフォリオ構築 → 注文管理 → 実行 → 監視）を意図したモジュール群です。  
主な特徴:

- ポートフォリオ構築（シグナル選定、重み算出、ポジションサイズ決定）
- ExecutionEngine（発注ロジック、リスク管理、注文リコンシリエーション）
- 監視コンポーネント（システム稼働監視、注文ログ監視、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI 補助（ニュース NLP を用いたセンチメントスコアリング、市場レジーム判定）
- ペーパートレード専用モード（実環境 DB とは分離された SQLite を使用）

---

## 機能一覧

- 環境設定管理
  - .env ファイルの自動読み込み（.env / .env.local）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - 対話式設定ウィザード: `kabusys.config_setup`
  - 起動前チェック: `kabusys.validate_config`

- 実行・発注
  - Execution エンジン起動スクリプト: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、`data/paper_trading.db` に記録

- 監視
  - System / Trade / Risk の各種モニタリング実装
  - 監視ループ起動スクリプト: `run_monitoring.py`
  - Kill Switch によるフラグファイル (`data/kill.flag`) 書き込みで ExecutionEngine を安全停止

- ポートフォリオ関連（純関数群）
  - 候補選定、等比／スコア重み計算、ポジションサイズ計算、セクター制限、レジーム乗数

- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー

- AI モジュール
  - ニュースのセンチメントを OpenAI（gpt-4o-mini）で評価し `ai_scores` に書き込み
  - マクロニュース + ETF MA を使った市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

- ユーティリティ
  - ログ設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提: Python 3.9+（またはプロジェクトポリシーに従うバージョン）を想定。

1. リポジトリをチェックアウトし、作業ディレクトリをプロジェクトルートに移動。

2. 必要パッケージをインストール（例）
   - 基本依存:
     - duckdb
     - psutil
     - openai
   - 開発・オプション:
     - PyYAML（config YAML 検証用）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   注: requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須となる最小環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development  # development / paper_trading / live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
   - 自動読み込み:
     - プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データベース
   - DuckDB（分析用）と SQLite（監視・発注ログ）ファイルは初回起動時に自動作成されます。パスは環境変数で調整可能。
   - Paper Trading モードでは SQLite の代替 DB (`PAPER_TRADING_SQLITE_PATH` / default: data/paper_trading.db) が使用されます。

6. ログ
   - デフォルトで `logs/` にアプリケーション別ログ（例: logs/execution.log, logs/monitoring.log）が日次ローテーションで保存されます。
   - ログディレクトリは `LOG_DIR` 環境変数または `setup_logging()` の引数で変更可能。

---

## 使い方

- 起動スクリプト

  - ExecutionEngine（発注エンジン）起動:
    - python -m kabusys.run_execution
    - 挙動:
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 SQLite（`data/paper_trading.db`）へ記録。
      - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了。
      - 実行中は `data/execution.pid` に PID を書き込みます。

  - Monitoring（監視ループ）起動:
    - python -m kabusys.run_monitoring
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 `SQLITE_PATH`（monitoring DB）を使用します。
    - 終了は `data/stop_requested.flag` を置くか Ctrl+C（KeyboardInterrupt）。

- .env の編集 / 再作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 系処理
  - OpenAI を使う機能（ニュース NLP、regime detector）は `OPENAI_API_KEY` が必要。関数から直接 API キーを渡すことも可能。
  - 例: kabusys.ai.news_nlp.score_news に DuckDB 接続と target_date を渡して呼び出す。

- Kill Switch / 停止フラグ
  - KillSwitch は条件を満たすと `data/kill.flag` を作成し、ExecutionEngine に停止シグナルを送ります。
  - 実行開始時の自動クリアを無効化する（本番では推奨）ために `KILL_FLAG_CLEAR_ON_START=0` を使用します（既定は 0）。

- ログ出力挙動
  - 共通ログ設定: コンソール(stdout) + 日次ファイルローテーション（30 日保持）。
  - `setup_logging(app_name="execution")` のように各スクリプトから呼び出して統一管理。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading モードで使用）
- LOG_LEVEL — DEBUG/INFO/…
- OPENAI_API_KEY — AI 機能利用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1, 本番は 0 推奨）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成です（実際のリポジトリ構成に応じて多少の差分あり）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - trade_monitor.py  (参照あり)
      - alert_manager.py  (参照あり)
    - execution/
      - execution_engine.py  (参照あり)
      - order_manager.py  (参照あり)
      - order_repository.py  (参照あり)
      - reconciler.py  (参照あり)
      - broker_factory.py  (参照あり)
      - risk_manager.py  (参照あり)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/  (実行時に生成されるデータ/フラグファイル)
      - monitoring.db (SQLite) / paper_trading.db
      - kabusys.duckdb
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - config/  (設定テンプレート/ YAML — 一部検証処理で参照)
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml

---

## 開発時の注意点 / 補足

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テストや一時的な起動時には `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って無効化できます。
- Paper Trading は本番 DB と分離されるよう設計されています。実稼働時は `KABUSYS_ENV=live` を慎重に設定してください（validate_config でも警告あり）。
- OpenAI を利用する処理は API 呼び出しに対してリトライ・クリップ・バリデーション等の安全装置が実装されていますが、API キーの管理やコストに注意してください。
- 実行プロセスの優先度（High/Normal/Low）設定や CPU Affinity は `psutil` を用いています。権限不足で設定に失敗することがありますが、その場合は警告が出て処理は継続します。
- 監視・Kill Switch の設計は「部分失敗時に既存データを守る」ことを重視しています（部分的に削除/書込みを絞る等の実装がある）。

---

## よく使うコマンド例

- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution（本番 / ペーパートレードモードで挙動が変わる）:
  - python -m kabusys.run_execution
- Monitoring（監視ループ）:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に「開発者向けセットアップ」や「テスト方法」「CI 設定」「API リファレンス」などの追加項目を追記できます。どの追加情報が欲しいか教えてください。