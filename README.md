# KabuSys

日本株向け自動売買システムの一部を切り出したコードベースの README。  
主要コンポーネント（実行エンジン / 監視 / ポートフォリオ構築 / リサーチ / AI 補助機能 等）を含みます。

※ 本ドキュメントはリポジトリ内のソースコードを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。  
主な役割は以下のとおりです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状況・リスクを監視しアラートや Kill Switch を制御
- Portfolio：銘柄選定、配分、ポジションサイズ計算などポートフォリオ構築ロジック
- Research：ファクター計算・特徴量探索（DuckDB を使用）
- AI：ニュースの自然言語処理（OpenAI）を使ったセンチメント評価・レジーム判定
- Tools：ペーパートレードの検証レポートなどのユーティリティ

設計方針として、可能な箇所は「外部 API を直接叩かない」「ルックアヘッドを防ぐ（日付参照の扱い）」「フェイルセーフで処理継続」などの注意が取られています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`（KABUSYS_ENV により paper_trading を分離）
- Monitoring 起動スクリプト（ポーリングループ）: `kabusys.run_monitoring`
- Monitoring 用 DB 初期化 / 永続化層（SQLite）: `kabusys.monitoring.monitoring_db`
- Kill Switch（停止フラグをファイルで発行）: `kabusys.monitoring.kill_switch`
- Risk / System / Trade の各種モニタ
- Portfolio 構築ロジック（候補選定 / 重み算出 / 単元丸め / リスク調整）
- Research（ファクター・将来リターン・IC 計算）
- AI モジュール：ニュースを LLM でスコアリング（OpenAI）・レジーム判定
- Tools：Paper Trading の検証レポート生成スクリプト

---

## 前提・依存関係（代表）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
- 任意（validate_config の YAML 検証を有効化するなら）
  - PyYAML

（環境に合わせ requirements.txt を作ることを推奨します）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - （必要なら）pip install pyyaml

4. 環境変数の用意
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（リポジトリルートに配置）
     - 例（最小）:
       - JQUANTS_REFRESH_TOKEN=your_token_here
       - KABU_API_PASSWORD=your_password_here
       - KABUSYS_ENV=development
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - LOG_LEVEL=INFO

   - 自動ロード:
     - 起動時にプロジェクトルート（.git や pyproject.toml があるディレクトリ）から `.env` / `.env.local` が自動読み込みされます。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 初回 DB 初期化
   - 実行スクリプト（run_execution/run_monitoring）が内部で監視用 SQLite のスキーマ初期化を呼びます（init_monitoring_db）。手動で行う必要はありません。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（1/0）

---

## 使い方（主なコマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告もエラー扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - Note:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
    - 実行中の PID ファイル: data/execution.pid（設定で変更可能）
    - 起動前に data/stop_requested.flag が存在する場合は起動を行いません（停止フラグ）

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を常に使用（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OpenAI API キーを使用してテーブルへ結果を書き込みます。

---

## 停止・Kill Switch の操作

- 停止フラグ（外部から ExecutionEngine を停止する方法）
  - ファイル: data/kill.flag（KillSwitch が生成）
  - ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照します。
  - Monitoring の KillSwitch が条件を満たすと kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。

- 強制終了（監視プロセスの停止）
  - stop_requested.flag ファイル（run_monitoring/run_execution が監視している停止フラグ）
  - ファイルの存在を確認してプロセスを穏やかに停止します。

---

## ログ

- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されます。
- デフォルト:
  - コンソール出力（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（30日分保持）
- 環境変数 LOG_DIR や引数でログディレクトリを変更可能

---

## ディレクトリ構成（抜粋）

リポジトリの主要モジュール構成例（`src/kabusys` 以下）:

- run_monitoring.py — Monitoring ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数 / Settings 管理（.env 自動ロード等）
- validate_config.py — 設定検証 CLI
- config_setup.py — .env 対話ウィザード
- __init__.py — パッケージ定義・バージョン
- tools/
  - paper_verification_report.py — Paper Trading レポート生成
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- monitoring/
  - monitoring_db.py — SQLite 永続化層（スキーマ初期化 / CRUD ヘルパ）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文関連監視（省略された実装ファイルが存在）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — アラート送信（LINE 等、別実装）
- utils/
  - logging_setup.py — ログ統一設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — IC 計算・統計サマリー
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- data/ — 実行時に利用されるデフォルト DB / フラグ / PID 等（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）

（上記は主要ファイルの抜粋です。実際のツリーはリポジトリの内容に依存します。）

---

## 開発上の注意点 / 補足

- 環境の分離
  - paper_trading モードでは実取引 API を叩かない（MockBrokerClient を使用）ため、本番 DB と完全に分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。
- ルックアヘッド防止
  - AI/Research 系の処理は内部で日時の参照を明示的に扱い、未来データを参照しないよう設計されています（テスト容易性・評価バイアス低減）。
- フェイルセーフ
  - OpenAI API 呼び出し等の外部依存はリトライやフォールバック（0.0 等）で処理を継続する設計です。
- .env の自動読み込み
  - プロジェクトルートを .git または pyproject.toml で探索し `.env` / `.env.local` を自動で読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- validate_config は PyYAML がなければ YAML のパースチェックをスキップします（警告出力）。

---

## よくある操作例

- 監視 (デフォルト60秒間隔)
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン（ペーパートレードで起動）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート（2026-04-01〜2026-04-10）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

必要であれば、README に含めるサンプル .env テンプレートや systemd/cron 用の起動例、より詳細な開発者向けドキュメント（テストの実行方法、lint/format、CI 設定など）も追記します。どの情報を優先して追加しましょうか？