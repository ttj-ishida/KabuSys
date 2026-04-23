# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋起動スクリプト）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせた自動売買基盤の一部を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の機能群を備えた自動売買フレームワークです。

- DuckDB / SQLite を用いたデータ管理（時系列価格、財務データ、監視ログなど）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、サイズ算出）
- ExecutionEngine（発注、注文管理、リスク制御） — 本番 / ペーパートレード対応
- 監視コンポーネント（システム状態、注文監視、リスク監視、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード／検証ツール、レポート生成）

設計方針の要点:
- できるだけ副作用を限定した純粋関数群（研究・ポートフォリオ計算等）
- 起動スクリプトで統一的なログ設定・プロセス優先度設定を実行
- 本番 DB とペーパートレード用 DB を分離（KABUSYS_ENV による切り替え）
- ルックアヘッドバイアス防止のため datetime.today()/date.today() の乱用を避ける実装

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- Execution エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を参照
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ファクター計算・研究ツール: kabusys.research.*
- AI ベースのニュース評価 / レジーム判定: kabusys.ai.*
- ロギング設定ユーティリティ: kabusys.utils.logging_setup
- プロセス優先度設定: kabusys.utils.process_priority
- 監視 DB 操作ラッパー: kabusys.monitoring.monitoring_db

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（duckdb, psutil, openai 等が必要）
- システムにより追加パッケージのインストールや権限が必要になることがあります（psutil の CPU affinity / nice の呼び出しなど）

1. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil openai PyYAML
   - ※ 実際の依存関係はプロジェクトの requirements.txt や pyproject.toml を参照してください。

3. プロジェクトルートに data/ ディレクトリを用意（ログ・DB・フラグファイル保存用）
   - mkdir -p data logs

4. 環境変数 (.env) の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記のサンプルを参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

6. 起動（下記「使い方」参照）

環境変数の主要項目（例）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB パス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 DB, default: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (default: logs)
- OpenAI:
  - OPENAI_API_KEY (AI モジュール使用時に必要)
- その他:
  - MONITOR_POLL_INTERVAL (監視ポーリング秒, デフォルト 60)
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - PID_FILE_PATH (default: data/execution.pid)

簡易 .env テンプレート（例）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

注意: .env は機密情報を含むため Git にコミットしないでください。

---

## 使い方

基本的なコマンド例:

- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使い、MockBroker を利用してペーパー発注
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に stop flag が作成されると Engine.stop() を呼んで終了

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に（環境にかかわらず）settings.sqlite_path を使用します
  - stop flag ファイル（data/stop_requested.flag）を検知するとループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュールの使用例（Python から直接）
  - from kabusys.ai import score_news
  - score_news(conn, target_date)  — OpenAI API キーが必要

ログ:
- デフォルトログディレクトリ: logs/
- ログファイルは起動スクリプト名で作成（例: logs/execution.log, logs/monitoring.log）
- ログはコンソール (stdout) と日次ローテートファイルに出力（30日保持）

Kill Switch / 停止フラグ
- KillSwitch は監視モジュールが条件を満たした場合に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組みです
- 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番では 0 を推奨）

Paper Trading の分離
- KABUSYS_ENV=paper_trading の場合、ExecutionEngine は PAPER_TRADING_SQLITE_PATH を使用します（本番 DB と完全分離）

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python パッケージ構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証ツール
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py            — ログ初期化ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 監視用 DB 層
    - system_monitor.py
    - trade_monitor.py            — （注文監視、該当ファイルあり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            —（アラート送信を扱う実装がある想定）
  - execution/
    - execution_engine.py         — ExecutionEngine 実装
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                          — データパイプライン / DB 接続関連（prices, stats 等、モジュールあり）
  - tools/
    - paper_verification_report.py
  - logs/                          — ログディレクトリ（runtime）

（上記はこのコードベースで検出されたファイル群の抜粋です。）

---

## 実運用上の注意点

- 本番（KABUSYS_ENV=live）では特にシークレットや kill/stop 設定を注意して管理してください。validate_config は本番向けチェック（LINE 通知設定等）を行います。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。
- psutil を使った優先度設定や CPU affinity は権限が必要になる場合があります（Linux の nice 値変更や Windows の優先度設定）。
- OpenAI など外部 API を使う機能は API キーの管理・レート制限・コストに注意してください。AI モジュールは失敗時にフォールバック処理を行い全面停止しない設計になっていますが、運用方針を定めてください。
- データのルックアヘッドバイアス防止に留意して実装されているため、テスト/開発時も target_date を明示的に渡す等の操作を行うと本番と同様の振る舞いを検証できます。

---

必要であれば、README に依存関係の正確なリスト（requirements.txt）や起動例の systemd/cron ユニット例、アーキテクチャ図、各コンポーネントの API ドキュメントを追加します。どの情報を優先して追加しますか？