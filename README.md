# KabuSys

日本株向け自動売買システムのコアモジュール群（ライブラリ / CLI スクリプト群）のリポジトリ内 README。

以下はこのコードベースの概要・セットアップ・起動方法・主要コンポーネント構成の説明です。

注意: 実際に本番発注を行う構成（KABUSYS_ENV=live）では十分な検証と運用体制が必要です。`.env` は秘匿情報を含むため絶対に Git 管理下に置かないでください。

---

## プロジェクト概要

KabuSys は日本株自動売買のための内部ライブラリ群と付随する CLI スクリプトを提供します。主な責務は次のとおりです。

- データ処理・ファクター計算（DuckDB 経由での prices_daily / raw_financials 参照）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 実行エンジン（BrokerClient 経由での発注制御、Paper / Live 切替）
- 監視（システム状態、注文滞留、リスク監視、Kill Switch）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、分析処理は DuckDB、永続ログ/監視は SQLite を使用し、本番と paper_trading（ペーパートレード）は DB を分離できるようになっています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に生成
- 設定検証ツール（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
- 監視プロセス起動スクリプト（python -m kabusys.run_monitoring）
  - システム状態、データ鮮度、注文滞留、ドローダウン等を定期記録
  - Kill Switch による実行エンジン停止（data/kill.flag）
- AI 機能
  - ニュースセンチメントスコア生成（kabusys.ai.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector）
- 研究用 / 運用用ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
  - ポートフォリオ構築（kabusys.portfolio.*）
  - ファクター計算 / 研究機能（kabusys.research.*）

---

## 必要要件（主な依存パッケージ）

実行に必要と思われる主なパッケージ（プロジェクトの requirements.txt がある場合はそちらを使用してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- requests (LINE 通知)
- PyYAML（設定ファイル YAML 検証時にあればより詳細検証）

開発環境では仮想環境を作ってから依存をインストールしてください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install -U pip
- pip install duckdb psutil openai requests pyyaml

（パッケージ名は用途に応じて調整してください）

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成・有効化する

   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする

   - pip install duckdb psutil openai requests pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt）

3. 環境変数設定（.env）を作成

   - 対話形式で .env を作る:
     - python -m kabusys.config_setup

   - もしくは .env.example を参考に手動作成

4. 設定を検証する

   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付与

5. データディレクトリの準備（必要に応じて）

   - デフォルトでは data/ 配下に DB や pid/flag を格納します。必要なら作成してくださいが、多くのスクリプトは自動作成を行います。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

重要な任意 / デフォルト:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（未設定なら送信はスキップ）

監視関連:
- PID_FILE_PATH（デフォルト data/execution.pid）
- KILL_FLAG_PATH（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL（監視ループの間隔を秒で上書き、run_monitoring で使用）

Paper trading 固有:
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

---

## 使い方

以下は代表的なコマンド例と使い方です。

1. 設定ウィザード（.env の初期作成/更新）
   - python -m kabusys.config_setup
   - 指示に従って入力し、最終確認で保存します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

3. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - デフォルトは 60 秒間隔でポーリングします。環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能（例: export MONITOR_POLL_INTERVAL=30）。
   - 監視プロセスは Settings で指定された sqlite_path（監視用 DB）と duckdb_path に接続します。
   - プロセスは起動時にプロセス優先度を "high" にセットしようとします（実行環境に依存して失敗することがあります）。

4. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用の SQLite に記録します（本番 DB と分離）。
   - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
   - 実行中は stop フラグ（data/stop_requested.flag）を作成することで停止要求できます（ラッパー等がチェックしてエンジンを止めます）。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH を優先）

6. AI 機能（ニューススコアリング / レジーム判定）
   - 関数 API:
     - kabusys.ai.score_news(conn, target_date, api_key=None) — ai_scores を更新（OpenAI API キー必須）
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime を更新
   - 実行には OpenAI API キー（OPENAI_API_KEY または引数経由）が必要です。

7. Kill Switch / 停止
   - KillSwitch はリスク条件（ドローダウンやポジション上限）発生時に `data/kill.flag` を書き込みます（Settings.kill_flag_path で変更可能）。これを ExecutionEngine が検出して安全に停止するフローになっています。
   - 外部からプロセス全体を停止する際は `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが終了します。

---

## 実行時の挙動（運用上の注意点）

- 監視（run_monitoring）は Settings.env に関わらず常に本番 sqlite_path を使用します（監視情報は production DB を想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading_db を使い本番 DB と分離します。
- init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対する軽微なカラム追加マイグレーションも行います。
- プロセス優先度設定は psutil を用いて OS に依存した方法で行います。権限不足などで設定に失敗する場合は警告が出ますが実行は続行します。
- .env 自動読み込み: config.Settings はプロジェクトルート（.git か pyproject.toml を基準）から .env/.env.local を自動で読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — LINE Push 通知ユーティリティ
  - execution/ (発注周り: BrokerFactory, Engine, OrderRepository 等) — 実行エンジン・注文管理（ソース全体は一部省略）
  - portfolio/
    - portfolio_builder.py — 候補選定・等重 / スコア重み計算
    - position_sizing.py — 株数計算・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングするロジック
    - regime_detector.py — ETF ma200 とマクロニュースを組み合わせたレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

data/ 以下（実行時作成される）
- data/kabusys.duckdb （DuckDB デフォルト）
- data/monitoring.db （監視 SQLite デフォルト）
- data/paper_trading.db（ペーパートレード用 SQLite、paper_trading 時）
- data/execution.pid（ExecutionEngine PID 保存）
- data/stop_requested.flag（process wrapper 停止要求用）
- data/kill.flag（KillSwitch が書き込む停止フラグ）

---

## 開発・運用に関する補足

- テスト: 各モジュールは外部副作用（DB/ネットワーク）を注入できる設計になっており、ユニットテストでの差し替えが容易です（例: OpenAI 呼び出しはラップして patch 可能）。
- 安全策: AI 呼び出しや発注操作は失敗時にフェイルセーフ（スコア=0 やスキップ）となるよう設計されていますが、本番では監視とアラート設定を必ず行ってください。
- ログ: スクリプトは基本的に logging.basicConfig(level=logging.INFO) で起動します。環境変数 LOG_LEVEL で調整できます。
- データ鮮度: SystemMonitor は DuckDB 内の prices_daily の最終日と比較してデータ鮮度チェックを行います（デフォルト許容差: 3 日以内）。

---

README はここまでです。必要であれば次の追加ドキュメントを作成できます:

- 各モジュール（ExecutionEngine、OrderManager、BrokerClient）の詳細設計ドキュメント
- 運用手順（デプロイ・監視ダッシュボード・障害対応フロー）
- 依存関係の固定化（requirements.txt / poetry の設定例）
- サンプル .env.example ファイル

どれを優先して欲しいか指示してください。