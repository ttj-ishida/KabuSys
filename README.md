# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群の抜粋）。  
この README はコードベースから読み取れる仕様・使い方をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えた Python パッケージです。

- シグナル生成・ポートフォリオ構築（候補選定、重み計算、株数決定）
- リスク調整（セクター上限、レジーム乗数）
- 実行エンジン（実際のブローカー/モックブローカーを利用した発注管理）
- 監視（システム状態、注文の監視、リスク監視、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量解析）
- ニュースを使った AI ベースのセンチメント（OpenAI API を利用）
- 運用補助ツール（.env 作成ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部:
- 本番とペーパートレードはデータベースを分離（paper_trading モードでは data/paper_trading.db を使用）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に利用
- 環境変数（.env）で挙動を制御し、config_setup.py で対話的に .env を生成可能
- OpenAI を利用する部分は API キーを外部から渡す（環境変数 OPENAI_API_KEY）

---

## 主な機能一覧

- 実行 / 監視
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV によりモック/本番切替）
  - run_monitoring.py: SystemMonitor をポーリングする監視プロセス起動スクリプト
- 設定
  - config_setup.py: .env 対話式ウィザード（初期作成・更新）
  - validate_config.py: 起動前の設定検証 CLI（--strict オプションあり）
- データベース / 永続化
  - monitoring_db.py: 監視ログ用 SQLite スキーマ初期化・読み書き
- 監視コンポーネント
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager（監視・通知・Kill Switch）
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py, risk_adjustment.py, position_sizing.py
- 研究（Research）
  - factor_research.py（モメンタム・バリュー・ボラティリティ）、feature_exploration.py（IC/統計）
- AI
  - news_nlp.py: raw_news をまとめて OpenAI でセンチメント評価し ai_scores に書き込む
  - regime_detector.py: マクロ + ETF MA を組み合わせて market regime を判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## 前提 / 必要なもの

主に以下のライブラリを想定しています（コード内で使用）:

- Python 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, etc.
- 外部ライブラリ:
  - duckdb
  - psutil
  - openai (OpenAI Python SDK)
  - PyYAML（設定ファイル検証時に任意）
  - （必要に応じて）その他の依存を requirements.txt にまとめてください

※ requirements.txt はこの抜粋には含まれていません。実運用時は上記を含む仮想環境を作成してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

4. ディレクトリ準備（logs, data）
   - mkdir -p data logs
   - 一部スクリプトは起動時に自動作成しますが、明示的に作ると権限問題を回避できます。

5. 環境変数の設定（.env）
   - 対話式で作成:
     - python -m kabusys.config_setup
   - 生成後、内容を確認し必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。
   - 重要:
     - .env は絶対に Git にコミットしないでください（config_setup.py に注意書きあり）。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も failure 扱いになります。

---

## 環境変数（代表例）

主に Settings クラスで参照されるもの（デフォルト値はコード参照）:

必須（起動時に必要な値）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用 / 任意
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB path（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news/regime 判定で必要）
- LOG_LEVEL: DEBUG/INFO/…
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill フラグ自動クリア（"0" 推奨）

詳しくは `kabusys.config.Settings` を参照してください。

---

## 起動・使い方

1. 監視プロセス起動（SystemMonitor のポーリング）
   - デフォルト: 60秒間隔（環境変数 MONITOR_POLL_INTERVAL で上書き）
   - python -m kabusys.run_monitoring
   - 停止: data/stop_requested.flag を作成するとループが検知して終了します（または Ctrl+C）

2. 実行エンジン起動（ExecutionEngine）
   - paper_trading モード（モックブローカー、データ分離）: KABUSYS_ENV=paper_trading を設定
   - python -m kabusys.run_execution
   - 停止: data/stop_requested.flag を作成するか ExecutionEngine の停止ロジックに従います
   - 実行開始時、設定により kill_flag（data/kill.flag）を自動クリアするかどうかが制御されます

3. .env 作成ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - 簡易にペーパートレード SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標を算出します。

6. プログラムからの呼び出し例（AI スコア付与）
   - Python から直接利用:
     - from kabusys.ai.news_nlp import score_news
     - import duckdb, datetime
     - conn = duckdb.connect("data/kabusys.duckdb")
     - score_news(conn, datetime.date(2026, 4, 1), api_key="（または環境変数）")

7. ログ
   - デフォルトのログ出力先: logs/<app_name>.log（日次ローテーション、30日保持）
   - logging は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で初期化されます。

---

## 運用上の注意 / フラグ類

- Stop フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して安全に停止します。
- Kill Switch:
  - リスク条件により data/kill.flag が書き込まれると ExecutionEngine 停止トリガーになります。
  - KILL_FLAG_CLEAR_ON_START（.env）で起動時に kill.flag を自動的に消すかどうかを制御できます（本番では 0 推奨）。
- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、発注ログなどは data/paper_trading.db に書き込みます（本番 DB と分離）。
- OpenAI:
  - API の利用はコストとレート制限に注意してください。news/regime にはリトライ・バックオフ実装がありますが、APIキーは秘匿してください。

---

## ディレクトリ構成（抜粋説明）

以下は主要モジュールの構成（src/kabusys 以下を想定）:

- kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — Settings クラス（環境変数 / .env 自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・投下資金調整
    - risk_adjustment.py       — セクター・レジーム調整
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ + DB 操作ラッパ
    - system_monitor.py        — システム・データ鮮度監視
    - trade_monitor.py         — 注文関連監視（抜粋には一部のみ）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書込みロジック
    - monitoring_engine.py     — 各 Monitor をまとめるループ
    - alert_manager.py         — 通知管理（抜粋中参照あり）
  - execution/
    - execution_engine.py      — 実行エンジン本体（抜粋では参照あり）
    - broker_factory.py        — ブローカークライアント生成（Mock/Real 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py              — ニュースセンチメント生成（OpenAI）
    - regime_detector.py       — 市場レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（リポジトリ全体のファイルはここに示したもの以外にも存在する可能性があります。コード先頭の docstring／コメントも参考にしてください）

---

## 開発・拡張のヒント

- settings / .env を経由して挙動を切り替える設計なので、ローカルでは KABUSYS_ENV=development、ペーパートレード検証は paper_trading を使うと安全です。
- DuckDB をローカルで用意しておくと研究モジュール（factor_research, feature_exploration）がすぐに利用できます。
- OpenAI を使う機能は API レート制限・コストに注意し、テスト時は外部呼び出しをモックしてください（コード中で _call_openai_api を patch する想定あり）。
- monitoring_db.init_monitoring_db() は起動スクリプト内で呼ばれるため、通常は手動でスキーマを作る必要はありません。

---

もし README に追加して欲しい項目（例: 実際の ExecutionEngine の設定例、Broker の接続手順、詳細な API 仕様、requirements.txt の具体化、サンプル .env.example 生成など）があれば教えてください。必要に応じて詳しい手順やサンプルを追記します。